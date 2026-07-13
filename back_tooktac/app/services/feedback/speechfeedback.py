from typing import Dict, List, Tuple

from app.services.speech.speech_analyzer import (
    EXCESSIVE_ST,
    MONOTONE_ST,
    NATURAL_MAX_ST,
    NATURAL_MIN_ST,
    ZERO_ST,
)

class SpeechFeedbackGenerator:
    def __init__(self, speed_result: Dict, pitch_result: Dict, filler_result: List[Tuple[str, int]]):
        self.speed_result = speed_result
        self.pitch_result = pitch_result
        self.filler_result = filler_result

    def score_speed(self, spm: float) -> int:
        """
        말속도 점수: 이상적 범위는 280~400 음절/분 (최대 40점)
        """
        if 280 <= spm <= 400:
            return 40
        elif spm < 280:
            return max(0, int(40 - ((280 - spm) * 0.5)))
        else:  # spm > 400
            return max(0, int(40 - ((spm - 400) * 0.5)))

    def score_filler(self, count: int) -> int:
        """
        간투어 점수:
        - 0개: 40점
        - 1~3개: 점진적 감점 (각각 38, 36, 34점)
        - 4개 이상: 가속 감점 (5점씩 감소)
        """
        if count == 0:
            return 40
        elif count <= 3:
            return 40 - count * 2
        else:
            return max(0, 34 - (count - 3) * 5)

    def score_pitch(self, st_std: float) -> int:
        """음조 점수 (최대 20점). 입력은 세미톤 표준편차다 (예전에는 Hz였다).

        예전 산식은 10~20Hz를 이상적이라 봤는데, 실제 화자는 전부 35~60Hz였다.
        즉 모든 사람이 0점이었다. 게다가 '평탄한 창이 하나라도 있으면' 그 창의
        작은 std가 반환돼 점수가 올라갔다 — 단조로운 사람이 더 높은 점수를 받았다.

        지금은 발화 전체의 세미톤 변동성 하나로만 매긴다.
        """
        if st_std <= 0:
            return 0

        if NATURAL_MIN_ST <= st_std <= NATURAL_MAX_ST:
            return 20

        if st_std < NATURAL_MIN_ST:
            # 단조로움 쪽. MONOTONE_ST(1.5) 까지는 0~8점, 거기서 2.0 까지 8~20점.
            if st_std <= MONOTONE_ST:
                return int(round(st_std / MONOTONE_ST * 8))
            ratio = (st_std - MONOTONE_ST) / (NATURAL_MIN_ST - MONOTONE_ST)
            return int(round(8 + ratio * 12))

        # 과장 쪽. 5.0~6.0 은 20~14점, 6.0~8.0 은 14~0점.
        if st_std <= EXCESSIVE_ST:
            ratio = (st_std - NATURAL_MAX_ST) / (EXCESSIVE_ST - NATURAL_MAX_ST)
            return int(round(20 - ratio * 6))
        if st_std < ZERO_ST:
            ratio = (st_std - EXCESSIVE_ST) / (ZERO_ST - EXCESSIVE_ST)
            return max(0, int(round(14 - ratio * 14)))
        return 0

    def classify_labels(self) -> Dict[str, str]:
        """
        수치 기반 결과를 바탕으로 speed / fluency / tone을 등급화
        """
        # 1. 속도: syllables_per_min 기준
        spm = self.speed_result.get("syllables_per_min", 0)
        if spm < 280:
            speed_label = "느림"
        elif spm > 400:
            speed_label = "빠름"
        else:
            speed_label = "적절"

        # 2. 간투어 수: fluency
        filler_count = len(self.filler_result)
        if filler_count == 0:
            fluency_label = "매끄러움"
        elif 1 <= filler_count <= 3:
            fluency_label = "무난"
        else:
            fluency_label = "버벅거림"

        # 3. 음조 변동성(세미톤 std): tone
        pitch_std = self.pitch_result.get("pitch_std", 0)
        if pitch_std < MONOTONE_ST:
            tone_label = "단조로움"
        elif pitch_std > EXCESSIVE_ST:
            tone_label = "과장됨"
        else:
            tone_label = "밝음"

        return {
            "speed": speed_label,
            "fluency": fluency_label,
            "tone": tone_label
        }

    def generate_feedback(self) -> Dict:
        """
        점수 및 자연어 피드백과 정규화 종합점수(1.0 기준) 반환
        """
        feedback_parts = []

        # 1. 말속도 분석 및 피드백
        spm = self.speed_result.get("syllables_per_min", 0)
        speed_score = self.score_speed(spm)
        if speed_score == 40:
            feedback_parts.append(f"말의 속도가 적절합니다. ({spm} 음절/분)")
        elif spm < 280:
            feedback_parts.append(f"말의 속도가 다소 느립니다. ({spm} 음절/분) 조금 더 자신감 있게 말해보세요.")
        else:
            feedback_parts.append(f"말의 속도가 빠릅니다. ({spm} 음절/분) 천천히 또박또박 말해보세요.")

        # 2. 간투어 분석 및 피드백
        filler_count = len(self.filler_result)
        filler_score = self.score_filler(filler_count)
        if filler_count == 0:
            feedback_parts.append("간투어 없이 명확하게 말했습니다!")
        elif filler_count <= 3:
            feedback_parts.append(f"간투어가 {filler_count}회 사용되었습니다. 조금만 줄이면 더 매끄러워질 거예요.")
        else:
            feedback_parts.append(f"간투어가 {filler_count}회 사용되었습니다. 말하기 전에 잠시 생각하고 말해보세요.")

        # 3. 음조 분석 및 피드백
        pitch_std = self.pitch_result.get("pitch_std", 0)
        pitch_score = self.score_pitch(pitch_std)
        feedback_parts.append(self.pitch_result.get("pitch_feedback", "음조 분석 결과 없음."))

        total_score = speed_score + filler_score + pitch_score

        # 4. 가중치 기반 종합 점수 (1.0 정규화)
        weighted_score = (
            total_score
        ) / 100.0  # 총점 100 기준

        return {
            "feedback": " ".join(feedback_parts),
            "score_detail": {
                "speed": speed_score,
                "filler": filler_score,
                "pitch": pitch_score
            },
            "total_score": total_score,
            "labels": self.classify_labels()
        }
