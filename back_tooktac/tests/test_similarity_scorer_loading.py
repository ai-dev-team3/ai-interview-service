"""SimilarityScorer의 모델 로딩 전략 테스트 (실제 모델을 내려받지 않는다).

캐시가 있으면 네트워크 없이 로드하고, 없으면 평소대로 내려받아야 한다.
폴백을 지우면 캐시가 없는 새 환경(배포 서버, 신규 팀원)에서 앱이 죽는다.
"""
import pytest

from app.services.text.scorer import SimilarityScorer


def test_uses_cache_and_never_touches_network_when_cached():
    calls = []

    def loader(local_files_only):
        calls.append(local_files_only)
        return "model"

    assert SimilarityScorer._load_cached_first(loader, "some/model") == "model"
    assert calls == [True], "캐시가 있으면 네트워크 로더를 부르면 안 된다"


def test_falls_back_to_download_when_not_cached(caplog):
    calls = []

    def loader(local_files_only):
        calls.append(local_files_only)
        if local_files_only:
            raise OSError("캐시에 없음")  # HF가 실제로 던지는 예외 타입
        return "downloaded"

    with caplog.at_level("INFO"):
        result = SimilarityScorer._load_cached_first(loader, "some/model")

    assert result == "downloaded"
    assert calls == [True, False], "캐시 미스면 네트워크로 다시 시도해야 한다"
    assert "캐시 없음" in caplog.text


def test_download_failure_propagates():
    def loader(local_files_only):
        raise OSError("네트워크도 실패")

    with pytest.raises(OSError):
        SimilarityScorer._load_cached_first(loader, "some/model")
