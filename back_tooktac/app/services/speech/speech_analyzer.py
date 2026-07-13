from typing import Dict, List, Tuple
import librosa
import numpy as np
import re

# 사람 말소리의 기본주파수 범위. 남성 85~180Hz, 여성 165~255Hz 를 넉넉히 감싼다.
PITCH_FMIN_HZ = 65
PITCH_FMAX_HZ = 400
PITCH_HOP = 1024
MIN_VOICED_FRAMES = 30
OCTAVE_ST = 12  # 중앙값에서 한 옥타브 넘게 벗어난 프레임은 추정 오류로 본다

# 음조 변동성 경계 (세미톤 표준편차).
# 음성학에서 통용되는 범위를 따랐다. 손에 있던 샘플 8개는 전부 2.8~4.5(평범한 화자)라
# 단조로운/과장된 화자로 경계를 검증하지는 못했다.
MONOTONE_ST = 1.5      # 이 아래는 단조로움
NATURAL_MIN_ST = 2.0   # 자연스러운 억양의 하한
NATURAL_MAX_ST = 5.0   # 자연스러운 억양의 상한
EXCESSIVE_ST = 6.0     # 이 위는 과장·불안정
ZERO_ST = 8.0          # 여기서 0점


def _pitch_feedback(st_std: float) -> str:
    if st_std < MONOTONE_ST:
        return "음조가 단조로워 들릴 수 있어요. 억양에 변화를 줘보세요."
    if st_std > EXCESSIVE_ST:
        return "음조 변화가 과해 산만하게 들릴 수 있어요."
    return "음조 변화가 적절합니다"


class SpeechAnalyzer:
    def __init__(self, result: Dict):
        """
        :param result: ClovaSpeechClient의 response.json() 결과
        :param filler_words: 간투어 리스트 (예: ['어', '음', '아', '그', ...])
        """
        self.result = result
        self.segments = result.get("segments", [])
        self.total_text = ""
        self.total_duration = 0.0
        self.filler_words = [
            "음", "어", "아", "그", "저", "뭐", "이제", "그러니까", "있잖아요", "뭐랄까",
            "뭔가", "약간", "그니까", "뭐지", "어떻게", "뭐라고 해야 하지", "어떻게 보면",
            "사실", "약간은", "그런데", "근데", "그러면", "그런가", "뭐랄까요", "아마도",
            "혹시", "일단", "다만", "결국", "음...", "그…", "어…", "음… 그니까"
        ]

    def speech_speed_calculate(self) -> Dict:
        """
        내부 상태(self.segments)를 기반으로 말속도 분석 수행
        """
        for segment in self.segments:
            text = segment.get("text", "")
            start = float(segment.get("start", 0)) / 1000
            end = float(segment.get("end", 0)) / 1000
            duration = end - start

            self.total_text += text
            self.total_duration += duration

        if self.total_duration == 0:
            return {
                "syllables_per_min": 0.0,
                "words_per_min": 0.0,
                "total_duration_sec": 0.0,
                "total_text": ""
            }

        syllable_count = len(self.total_text.replace(" ", ""))
        word_count = len(self.total_text.strip().split())

        syllables_per_min = (syllable_count / self.total_duration) * 60
        words_per_min = (word_count / self.total_duration) * 60

        return {
            "syllables_per_min": round(syllables_per_min, 2),
            "words_per_min": round(words_per_min, 2),
            "total_duration_sec": round(self.total_duration, 2),
            "total_text": self.total_text.strip()
        }
    
    def calculate_pitch_variation(self, wav_path: str) -> Dict:
        """음조 변동성을 세미톤 표준편차로 잰다.

        Hz가 아니라 세미톤(로그)으로 재는 이유:
          기본 음높이가 남성은 100Hz대, 여성은 200Hz대다. 같은 억양이라도 목소리가
          높으면 Hz 표준편차가 2배로 나온다. 실측(남 135/137Hz, 여 284/272Hz)에서도
          Hz std는 35~60으로 성별을 따라 갈렸지만 세미톤 std는 2.8~4.5로 모였다.
          Hz로 고정 임계값을 쓰면 저음 화자가 자동으로 '단조로움'이 된다.

          semitone = 12 * log2(f0 / 화자 자신의 중앙값)
          중앙값 기준이라 화자의 절대 음높이가 상쇄된다.

        탐색 범위(65~400Hz)는 사람 말소리 기준이다. 예전에는 C2~C7(65~2093Hz)을
        뒤졌는데, 2093Hz는 아무도 내지 않는 음역이라 계산 대부분을 버리고 있었다.
        범위를 좁히고 hop을 늘려 90초 답변 기준 14초 -> 2초가 됐다.
        """
        try:
            y, _ = librosa.load(wav_path, sr=16000)

            f0, _, _ = librosa.pyin(y, fmin=PITCH_FMIN_HZ, fmax=PITCH_FMAX_HZ,
                                    hop_length=PITCH_HOP)

            voiced = f0[~np.isnan(f0)]  # 비발화 구간 제외
            if len(voiced) < MIN_VOICED_FRAMES:
                return {"pitch_feedback": "음성이 짧아 분석 불가", "pitch_std": 0.0}

            median = float(np.median(voiced))
            semitones = 12 * np.log2(voiced / median)

            # 옥타브 오검출을 버린다. pyin 은 기본주파수를 절반/두 배로 잘못 짚는 일이 있다.
            # 실측 사례: 한 화자의 프레임 10%가 중앙값보다 -22 세미톤(거의 2옥타브 아래)에
            # 몰려 std 가 9.20 으로 튀었다. 그것만 빼면 2.85 로, 다른 화자들과 같은 범위였다.
            # 사람이 자기 중앙 음높이에서 한 옥타브 넘게 벗어나 말하지는 않는다.
            semitones = semitones[np.abs(semitones) <= OCTAVE_ST]
            if len(semitones) < MIN_VOICED_FRAMES:
                return {"pitch_feedback": "음성이 짧아 분석 불가", "pitch_std": 0.0}

            st_std = float(np.std(semitones))

            return {
                "pitch_feedback": _pitch_feedback(st_std),
                "pitch_std": round(st_std, 2),  # 단위: 세미톤 (예전에는 Hz였다)
            }

        except Exception as e:
            return {"pitch_feedback": f"pitch 분석 실패: {str(e)}", "pitch_std": 0.0}
    
    def find_filler_words(self, text) -> List[Tuple[str, int]]:
        """
        전체 텍스트에서 간투어를 (간투어, 위치)로 반환
        """
        # 1. 구두점 제거
        cleaned_text = re.sub(r'[^\w\s]', '', text)

        # 2. 토큰화
        tokens = cleaned_text.strip().split()

        # 3. 간투어 탐지
        return [(word, idx) for idx, word in enumerate(tokens) if word in self.filler_words]


if __name__ == "__main__":
    from app.services.stt.clovaspeech import ClovaSpeechClient
    from app.services.stt.vitospeech import VitoSpeechClient

    filler_words = [
    "음", "어", "아", "그", "저", "뭐", "이제", "그러니까", "있잖아요", "뭐랄까",
    "뭔가", "약간", "그니까", "뭐지", "어떻게", "뭐라고 해야 하지", "어떻게 보면",
    "사실", "약간은", "그런데", "근데", "그러면", "그런가", "뭐랄까요", "아마도",
    "혹시", "일단", "다만", "결국", "음...", "그…", "어…", "음… 그니까"
    ]

    clova = ClovaSpeechClient()
    vito = VitoSpeechClient()
    wav_file = r'C:\Users\UserK\AppData\Local\Temp\tmp63ci_9kv.wav'
    response = clova.req_upload(file=wav_file, completion="sync")
    text = vito.get_full_text_from_file(wav_file)
    result = response.json()

    analyzer = SpeechAnalyzer(result)
    speed_result = analyzer.speech_speed_calculate()
    pitch_result = analyzer.calculate_pitch_variation(wav_file)
    filler_result = analyzer.find_filler_words(text)

    print("📝 전체 텍스트:", speed_result["total_text"])
    print("🕒 발화 시간:", speed_result["total_duration_sec"], "초")
    print("💬 음절 기준 속도:", speed_result["syllables_per_min"], "음절/분")
    print("📖 단어 기준 속도:", speed_result["words_per_min"], "단어/분")
    print("🎼 음조 피드백:", pitch_result["pitch_feedback"])
    print("📊 표준편차:", pitch_result["pitch_std"], "Hz")
    print("🔍 간투어 탐지:", filler_result)