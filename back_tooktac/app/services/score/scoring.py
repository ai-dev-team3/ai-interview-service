from app.services.score.scale import clamp_score

# app/utils/scoring.py

class QuestionTypeWeights:
    """질문 유형별 가중치 시스템"""

    WEIGHTS = {
        "개념설명형": {"text": 0.6, "voice": 0.2, "video": 0.2},
        "기술형": {"text": 0.6, "voice": 0.3, "video": 0.1},
        "상황형": {"text": 0.65, "voice": 0.15, "video": 0.2},
        "행동형": {"text": 0.6, "voice": 0.2, "video": 0.2},
    }

    @classmethod
    def calculate_weighted_score(cls, question_analysis: dict) -> float:
        question_type = question_analysis.get('type', '개념설명형')
        detail_analysis = question_analysis.get('detailAnalysis', {})

        weights = cls.WEIGHTS.get(question_type, cls.WEIGHTS['개념설명형'])

        text_score = detail_analysis.get('text', {}).get('score', 0)
        voice_score = detail_analysis.get('voice', {}).get('score', 0)
        video_score = detail_analysis.get('video', {}).get('score', 0)

        weighted_score = (
            text_score * weights['text'] +
            voice_score * weights['voice'] +
            video_score * weights['video']
        )

        # 가중치 합이 1이므로 입력이 0~100이면 결과도 0~100이다.
        # 그래도 잘라둔다 — 예전에 영상 점수가 음수였고 그 탓에 문항 점수가 -5.6까지 갔다.
        return float(clamp_score(weighted_score))
