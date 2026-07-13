"""점수 스케일 유틸.

사용자에게 보여주는 모든 점수는 0~100이다. 그런데 내부 값들은 스케일이 제각각이다.

    similarity        0 ~ 1      (코사인 유사도)
    intent/knowledge  1 ~ 10     (LLM이 매기는 척도)
    speed/filler      0 ~ 40     (음성 점수 배분)
    pitch             0 ~ 20
    LLM이 뱉는 점수   무엇이든   (실제로 689가 저장돼 있었다)

여기서 한 번에 0~100으로 맞춘다. 스케일 변환을 각자 알아서 하면
similarity * 10 처럼 조용히 틀린 값이 화면에 뜬다 (실제로 그랬다).
"""

MIN_SCORE = 0
MAX_SCORE = 100


def clamp_score(value) -> int:
    """0~100 밖의 값을 잘라낸다. 숫자가 아니면 0."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return MIN_SCORE
    return int(round(max(MIN_SCORE, min(MAX_SCORE, number))))


def from_unit(value) -> int:
    """0~1 (유사도 등) -> 0~100"""
    try:
        return clamp_score(float(value) * 100)
    except (TypeError, ValueError):
        return MIN_SCORE


def from_ten_point(value) -> int:
    """1~10 (LLM 척도) -> 0~100

    1점이 최하이므로 1 -> 0, 10 -> 100 으로 편다.
    final_score 계산식(calculator.py)도 (x-1)/9 를 쓰므로 그와 일치한다.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return MIN_SCORE
    return clamp_score((number - 1) / 9 * 100)
