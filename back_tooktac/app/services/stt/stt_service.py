# app/services/stt/stt_service.py

from typing import Tuple

from app.services.stt.clovaspeech import ClovaSpeechClient
from app.services.stt.vitospeech import VitoSpeechClient


class STTService:
    """어떤 구현을 쓰든 (텍스트, {"segments": [{text, start, end}, ...]}) 를 돌려준다.

    segments 의 start/end(ms)는 SpeechAnalyzer 의 말속도 계산이 쓴다.
    이 계약을 깨면 speed 점수가 조용히 0이 된다.

    clova      : 연습 면접 (외부 API)
    sensevoice : 실전 면접 (로컬 GPU) — 꼬리질문이 STT 를 기다리므로 빨라야 한다
    vito       : 간투어 탐지 보조 (Clova 는 간투어를 지워버린다)
    """

    def __init__(self, stt_type: str = "clova"):
        self.stt_type = stt_type.lower()

        if self.stt_type == "clova":
            self.client = ClovaSpeechClient()
        elif self.stt_type == "vito":
            self.client = VitoSpeechClient()
        elif self.stt_type == "sensevoice":
            from app.services.stt.sensevoice import SenseVoiceClient  # torch 로딩이 무겁다

            self.client = SenseVoiceClient()
        else:
            raise ValueError(f"지원하지 않는 STT 타입: {stt_type}")

    def transcribe(self, wav_path: str) -> Tuple[str, dict]:
        if self.stt_type == "clova":
            response = self.client.req_upload(file=wav_path, completion="sync")
            result = response.json()
            segments = result.get("segments", [])
            text = " ".join(seg.get("text", "") for seg in segments)
            return text, result

        elif self.stt_type == "vito":
            text = self.client.get_full_text_from_file(wav_path)
            result = {"segments": [{"text": text, "start": 0, "end": 0}]}  # 형식 통일
            return text, result

        elif self.stt_type == "sensevoice":
            return self.client.transcribe(wav_path)
