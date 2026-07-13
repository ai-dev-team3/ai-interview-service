"""음성 답변 분석 파이프라인.

audio.py 웹소켓 핸들러에서 계산 로직을 분리해 테스트 가능하게 하고,
서로 독립적인 Vito STT·pitch 분석·LLM 평가를 병렬 실행해
답변 후 로딩 시간을 줄인다. (기존에는 전부 직렬 실행)
"""
import asyncio
import logging
import subprocess
import threading
from typing import Optional

from app.services.feedback.speechfeedback import SpeechFeedbackGenerator
from app.services.speech.speech_analyzer import SpeechAnalyzer
from app.services.stt.stt_service import STTService
from app.services.text.orchestrator import EvaluationOrchestrator

logger = logging.getLogger(__name__)


class FfmpegNotFoundError(Exception):
    """ffmpeg 바이너리가 PATH에 없음 (서버 설치 필요 — README 참고)"""


class AudioConversionError(Exception):
    """ffmpeg 변환 실패 (손상된 오디오 등)"""


# EvaluationOrchestrator는 임베딩 모델 로드 비용이 커 프로세스당 1회만 생성
_ORCHESTRATOR_SINGLETON: Optional[EvaluationOrchestrator] = None
_ORCHESTRATOR_LOCK = threading.Lock()


def get_orchestrator_singleton() -> EvaluationOrchestrator:
    global _ORCHESTRATOR_SINGLETON
    if _ORCHESTRATOR_SINGLETON is None:
        with _ORCHESTRATOR_LOCK:
            if _ORCHESTRATOR_SINGLETON is None:
                _ORCHESTRATOR_SINGLETON = EvaluationOrchestrator()
    return _ORCHESTRATOR_SINGLETON


class AnswerAnalysisPipeline:
    """webm→wav 변환, STT, 음성 분석, LLM 평가를 담당 (DB 저장은 라우터 책임)

    연습 면접과 실전 면접이 STT를 달리 쓴다.

      연습: Clova(외부 API) + Vito(간투어 보조)
        Clova는 간투어를 지워버리므로 Vito를 한 번 더 돌려야 간투어를 센다.

      실전: SenseVoice(로컬 GPU) 하나로 끝
        간투어가 텍스트에 그대로 남으므로 Vito가 필요 없다. 외부 STT 호출이
        0회가 되고, 병렬 작업도 하나 줄어 백그라운드 분석이 가벼워진다.
    """

    def __init__(
        self,
        stt_factory=STTService,
        analyzer_factory=SpeechAnalyzer,
        feedback_factory=SpeechFeedbackGenerator,
        orchestrator: Optional[EvaluationOrchestrator] = None,
        stt_type: str = "clova",
        filler_from_vito: bool = True,
    ):
        self.stt_factory = stt_factory
        self.analyzer_factory = analyzer_factory
        self.feedback_factory = feedback_factory
        self._orchestrator = orchestrator  # None이면 싱글턴 사용
        self.stt_type = stt_type
        self.filler_from_vito = filler_from_vito

    @classmethod
    def for_real_interview(cls, **kwargs) -> "AnswerAnalysisPipeline":
        """실전 면접용 — 로컬 GPU STT, Vito 없음"""
        return cls(stt_type="sensevoice", filler_from_vito=False, **kwargs)

    async def convert_webm_to_wav(self, webm_path: str, wav_path: str) -> None:
        cmd = ["ffmpeg", "-i", webm_path, "-ar", "16000", "-ac", "1",
               "-f", "wav", wav_path, "-y", "-loglevel", "error"]
        try:
            # 동기 subprocess는 이벤트 루프를 멈추므로 워커 스레드로 위임
            proc = await asyncio.to_thread(subprocess.run, cmd, capture_output=True)
        except FileNotFoundError as e:
            raise FfmpegNotFoundError("ffmpeg를 찾을 수 없습니다. 서버에 설치가 필요합니다.") from e
        if proc.returncode != 0:
            stderr = (proc.stderr or b"").decode(errors="ignore")[:500]
            raise AudioConversionError(stderr or "ffmpeg 변환 실패")

    async def transcribe(self, wav_path: str) -> tuple[str, dict]:
        """주 STT 실행 → (정리된 텍스트, 타임스탬프 포함 원본 응답)

        실전에서는 이 호출이 사용자를 기다리게 한다 — 꼬리질문이 이 텍스트를 받아야
        다음 질문을 만든다. 준비 시간(10초) 안에 끝나야 한다.
        """
        stt = self.stt_factory(self.stt_type)
        text, raw = await asyncio.to_thread(stt.transcribe, wav_path)
        return (text or "").strip(), raw

    async def analyze_and_evaluate(
        self,
        wav_path: str,
        stt_raw: dict,
        text_clean: str,
        question_text: str,
        question_type: str,
    ) -> tuple[dict, Optional[dict]]:
        """pitch 분석·LLM 평가(·필요하면 Vito STT)를 병렬 실행.

        Returns:
            (음성 피드백 dict, LLM 평가 dict 또는 실패 시 None)
        """
        analyzer = self.analyzer_factory(stt_raw)
        speed = analyzer.speech_speed_calculate()

        # 서로 독립인 작업들 → 동시에 실행 (가장 느린 작업 시간만큼만 소요)
        tasks = [
            asyncio.to_thread(analyzer.calculate_pitch_variation, wav_path),
            asyncio.to_thread(self._evaluate_safe, question_text, text_clean, question_type),
        ]
        if self.filler_from_vito:
            tasks.append(asyncio.to_thread(self._vito_transcribe_safe, wav_path))

        results = await asyncio.gather(*tasks)
        pitch, evaluation = results[0], results[1]

        # Clova는 간투어를 지운다 → Vito 텍스트에서 센다.
        # SenseVoice는 간투어를 남긴다 → 그 텍스트에서 바로 센다.
        filler_source = results[2] if self.filler_from_vito else text_clean
        fillers = analyzer.find_filler_words(filler_source)

        feedback = self.feedback_factory(speed, pitch, fillers).generate_feedback()
        return feedback, evaluation

    def _vito_transcribe_safe(self, wav_path: str) -> str:
        """Vito는 간투어 탐지 보조용 — 실패해도 전체 분석을 막지 않는다"""
        try:
            vito = self.stt_factory("vito")
            text, _ = vito.transcribe(wav_path)
            return text or ""
        except Exception:
            logger.exception("Vito STT 실패 — 간투어 분석 없이 진행")
            return ""

    def _evaluate_safe(self, question_text: str, text_clean: str, question_type: str) -> Optional[dict]:
        """LLM 평가 — 실패 시 None (라우터가 최소 결과 저장으로 처리)"""
        try:
            orchestrator = self._orchestrator or get_orchestrator_singleton()
            return orchestrator.evaluate_answer(question_text, text_clean, question_type)
        except Exception:
            logger.exception("LLM 평가 실패")
            return None
