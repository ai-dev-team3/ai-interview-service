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
    """webm→wav 변환, STT, 음성 분석, LLM 평가를 담당 (DB 저장은 라우터 책임)"""

    def __init__(
        self,
        stt_factory=STTService,
        analyzer_factory=SpeechAnalyzer,
        feedback_factory=SpeechFeedbackGenerator,
        orchestrator: Optional[EvaluationOrchestrator] = None,
    ):
        self.stt_factory = stt_factory
        self.analyzer_factory = analyzer_factory
        self.feedback_factory = feedback_factory
        self._orchestrator = orchestrator  # None이면 싱글턴 사용

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
        """주 STT(Clova) 실행 → (정리된 텍스트, 타임스탬프 포함 원본 응답)"""
        clova = self.stt_factory("clova")
        text, raw = await asyncio.to_thread(clova.transcribe, wav_path)
        return (text or "").strip(), raw

    async def analyze_and_evaluate(
        self,
        wav_path: str,
        clova_raw: dict,
        text_clean: str,
        question_text: str,
        question_type: str,
    ) -> tuple[dict, Optional[dict]]:
        """Vito STT·pitch 분석·LLM 평가를 병렬 실행.

        Returns:
            (음성 피드백 dict, LLM 평가 dict 또는 실패 시 None)
        """
        analyzer = self.analyzer_factory(clova_raw)
        speed = analyzer.speech_speed_calculate()

        # 세 작업은 서로 독립 → 동시에 실행 (가장 느린 작업 시간만큼만 소요)
        vito_text, pitch, evaluation = await asyncio.gather(
            asyncio.to_thread(self._vito_transcribe_safe, wav_path),
            asyncio.to_thread(analyzer.calculate_pitch_variation, wav_path),
            asyncio.to_thread(self._evaluate_safe, question_text, text_clean, question_type),
        )

        fillers = analyzer.find_filler_words(vito_text)
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
