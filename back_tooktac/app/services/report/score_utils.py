"""리포트 점수 관련 공용 헬퍼 (report/training 라우터에서 공유)"""
from typing import List


def to_number_score(maybe_json) -> int:
    """
    ReportAreaScore.score가 JSON(dict) 또는 숫자로 저장될 수 있어
    프론트에서 기대하는 '정수 점수'로 통일한다.
    우선순위: score > value > total > average > 자체가 숫자
    """
    if isinstance(maybe_json, (int, float)):
        return int(round(maybe_json))
    if isinstance(maybe_json, dict):
        for key in ("score", "value", "total", "average"):
            if key in maybe_json and isinstance(maybe_json[key], (int, float)):
                return int(round(maybe_json[key]))
    # 그 외 형식은 0으로 처리
    return 0


def normalize_question_type(name: str) -> str:
    """질문유형 문자열을 프론트에서 쓰는 5키로 정규화."""
    n = (name or "").strip().lower()
    mapper = {
        "개념": "concept", "개념설명": "concept", "concept": "concept",
        "기술": "technical", "기술형": "technical", "technical": "technical",
        "상황": "situation", "상황형": "situation", "situation": "situation",
        "행동": "behavior", "행동형": "behavior", "behavior": "behavior",
        "꼬리": "followUp", "꼬리질문": "followUp", "followup": "followUp", "follow_up": "followUp"
    }
    for k, v in mapper.items():
        if k in n:
            return v
    return "concept"  # 기본값


def avg_or_zero(values: List[int]) -> int:
    return int(round(sum(values) / len(values))) if values else 0


# 영역명이 한국어/영어로 섞여 저장될 수 있어 매핑으로 조회
AREA_NAME_MAP = {
    "text": ["답변 내용", "텍스트", "text"],
    "voice": ["음성", "voice"],
    "video": ["영상", "video"],
    "emotion": ["감정", "emotion"],
}


def find_area_score(area_scores, key: str) -> int:
    """ReportAreaScore 목록에서 key(text/voice/video/emotion) 영역 점수 추출"""
    names = set(a.lower() for a in AREA_NAME_MAP[key])
    for area in area_scores:
        if (area.area_name or "").lower() in names:
            return to_number_score(area.score)
    return 0
