from typing import Any, Dict, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from app.services.llm import get_chat_model

_CONCEPTUAL_TEMPLATE = """
당신은 경험 많은 기술 면접관입니다.

지원자의 이력서 정보:
전공: {major}
기술 스택: {skills}

위 정보를 바탕으로 지원자의 개념 이해도를 평가할 수 있는 질문을 1개 생성해주세요.
반드시 질문은 **한두 문장 이내**로 **간결하게 작성하세요.

요구사항:
- 지원자가 보유한 기술이나 도구에 대한 깊은 이해도를 확인
- "~에 대해 설명해주세요" 형식
- 단순 암기가 아닌 실제 이해도를 평가할 수 있는 질문
- 질문은 명확하고 구체적이어야 함
- 면접 질문을 생성할 때 출력 어디에도 별표(*)나 ‘ ’ 패턴을 절대 포함하지 말고, 마크다운이나 글머리표 없이 순수한 문장 형태로만 작성하라

질문만 출력하세요:
"""

_TECHNICAL_TEMPLATE = """
당신은 경험 많은 기술 면접관입니다.

지원자의 이력서 정보:
경력: {career_status} ({career_years})
기술 스택: {skills}
프로젝트 수: {project_count}개

위 정보를 바탕으로 지원자의 기술적 역량과 구현 능력을 평가할 수 있는 질문을 1개 생성해주세요.
반드시 질문은 **한두 문장 이내**로 **간결하게 작성하세요.

요구사항:
- 실제 구현 경험을 확인하는 질문
- "어떻게 구현하셨나요?" 또는 "어떤 방식으로 해결하셨나요?" 형식
- 기술 선택의 이유와 장단점에 대한 이해도 확인
- 프로젝트나 업무 경험과 연관된 구체적인 질문
- 면접 질문을 생성할 때 출력 어디에도 별표(*)나 ‘ ’ 패턴을 절대 포함하지 말고, 마크다운이나 글머리표 없이 순수한 문장 형태로만 작성하라

질문만 출력하세요:
"""

_FOLLOWUP_RESUME_TEMPLATE = """
당신은 경험 많은 기술 면접관입니다.

지원자의 기술 스택: {skills}

이전 질문과 답변:
Q1: {q1}
A1: {a1}

Q2: {q2}
A2: {a2}

위 두 답변을 종합적으로 분석하여, 더 깊이 파고드는 꼬리물기 질문을 1개 생성해주세요.
반드시 질문은 **한두 문장 이내**로 **간결하게 작성하세요.

요구사항:
- 답변에서 언급한 내용을 더 구체화하는 질문
- 두 답변 간의 연관성이나 일관성을 확인하는 질문
- 실무 적용 가능성을 검증하는 질문
- 답변에서 모호하거나 추상적인 부분을 명확히 하는 질문
- 면접 질문을 생성할 때 출력 어디에도 별표(*)나 ‘ ’ 패턴을 절대 포함하지 말고, 마크다운이나 글머리표 없이 순수한 문장 형태로만 작성하라

 **질문에서 'Q1', 'Q2' 등의 구체적인 질문 번호는 언급하지 말고, '앞선 질문', '이전 답변', '방금 말씀하신' 등의 자연스러운 표현을 사용하세요**


질문만 출력하세요:
"""

_SITUATIONAL_TEMPLATE = """
당신은 경험 많은 인사 담당자입니다.

지원자의 자기소개서 정보:
지원동기: {motivation}
강점: {strengths}
희망직무: {job_type}

위 정보를 바탕으로 지원자의 문제 해결 능력과 상황 대처 능력을 평가할 수 있는 상황형 질문을 1개 생성해주세요.
반드시 질문은 **한두 문장 이내**로 **간결하게 작성하세요.

요구사항:
- "만약 ~한 상황이라면 어떻게 하시겠습니까?" 형식
- 실제 업무에서 발생할 수 있는 현실적인 상황
- 스트레스 상황이나 딜레마 상황에서의 대응 평가
- 우선순위 설정과 의사결정 능력 확인
- 면접 질문을 생성할 때 출력 어디에도 별표(*)나 ‘ ’ 패턴을 절대 포함하지 말고, 마크다운이나 글머리표 없이 순수한 문장 형태로만 작성하라

질문만 출력하세요:
"""

_BEHAVIORAL_TEMPLATE = """
당신은 경험 많은 인사 담당자입니다.

지원자의 자기소개서 정보:
강점: {strengths}
주요 경험: {key_experiences}
목표: {career_goals}

위 정보를 바탕으로 지원자의 과거 행동 패턴을 파악할 수 있는 행동형 질문을 1개 생성해주세요.
반드시 질문은 **한두 문장 이내**로 **간결하게 작성하세요.

요구사항:
- STAR 기법을 활용한 질문
- "~했던 경험을 구체적으로 말씀해주세요" 형식
- 자소서에서 언급한 역량이나 성과를 검증하는 질문
- 구체적인 상황, 행동, 결과를 요구하는 질문
- 면접 질문을 생성할 때 출력 어디에도 별표(*)나 ‘ ’ 패턴을 절대 포함하지 말고, 마크다운이나 글머리표 없이 순수한 문장 형태로만 작성하라

질문만 출력하세요:
"""

_FOLLOWUP_COVERLETTER_TEMPLATE = """
당신은 경험 많은 인사 담당자입니다.

지원자의 자기소개서 핵심 내용:
지원동기: {motivation}
목표: {career_goals}

이전 질문과 답변:
Q4: {q4}
A4: {a4}

Q5: {q5}
A5: {a5}

위 두 답변을 종합적으로 분석하여, 더 깊이 파고드는 꼬리물기 질문을 1개 생성해주세요.
반드시 질문은 **한두 문장 이내**로 **간결하게 작성하세요.

요구사항:
- 답변에서 언급한 경험이나 역량을 구체적으로 검증
- 두 답변의 일관성과 진정성을 확인
- 자소서 내용과 답변의 일치성 검토
- 향후 업무 수행 가능성을 예측할 수 있는 질문
- 면접 질문을 생성할 때 출력 어디에도 별표(*)나 ‘ ’ 패턴을 절대 포함하지 말고, 마크다운이나 글머리표 없이 순수한 문장 형태로만 작성하라

 **질문에서 'Q4', 'Q5' 등의 구체적인 질문 번호는 언급하지 말고, '앞선 질문', '이전 답변', '방금 말씀하신' 등의 자연스러운 표현을 사용하세요**

질문만 출력하세요:
"""


class InterviewQuestionGenerator:
    """LCEL 체인 기반 면접 질문 생성 클래스

    입력(parsed_data)은 {"structured_content": {...}} 형태이며,
    구조화 이력서 로드/생성은 app.services.resume.resume_service가 담당한다.
    """

    def __init__(self, llm: Optional[Runnable] = None):
        self.llm = llm if llm is not None else get_chat_model(primary="gemini")

    def _generate(self, template: str, variables: Dict[str, Any]) -> str:
        chain = ChatPromptTemplate.from_template(template) | self.llm | StrOutputParser()
        return chain.invoke(variables).strip()

    def generate_conceptual_question(self, parsed_data: Dict[str, Any]) -> Dict[str, str]:
        """Q1: 개념설명형 질문 생성 (이력서 기반)"""
        structured = parsed_data['structured_content']
        skills = structured.get('skills', [])
        education = structured.get('education', {})

        question = self._generate(_CONCEPTUAL_TEMPLATE, {
            "major": education.get('major', ''),
            "skills": ', '.join(skills),
        })
        return {"question": question, "question_type": "개념설명형"}

    def generate_technical_question(self, parsed_data: Dict[str, Any]) -> Dict[str, str]:
        """Q2: 기술형 질문 생성 (이력서 기반)"""
        structured = parsed_data['structured_content']
        skills = structured.get('skills', [])
        projects = structured.get('projects', [])
        career = structured.get('career', {})

        question = self._generate(_TECHNICAL_TEMPLATE, {
            "career_status": career.get('status', '신입'),
            "career_years": career.get('years', '0년'),
            "skills": ', '.join(skills),
            "project_count": len(projects),
        })
        return {"question": question, "question_type": "기술형"}

    def generate_followup_resume_question(self, parsed_data: Dict[str, Any],
                                        q1: str, a1: str, q2: str, a2: str) -> Dict[str, str]:
        """Q3: 이력서 기반 꼬리물기 질문 (Q1+Q2 답변 참고)"""
        structured = parsed_data['structured_content']
        skills = structured.get('skills', [])

        question = self._generate(_FOLLOWUP_RESUME_TEMPLATE, {
            "skills": ', '.join(skills),
            "q1": q1, "a1": a1, "q2": q2, "a2": a2,
        })
        return {"question": question, "question_type": "개념설명형"}

    def generate_situational_question(self, parsed_data: Dict[str, Any]) -> Dict[str, str]:
        """Q4: 상황형 질문 생성 (자소서 기반)"""
        structured = parsed_data['structured_content']
        self_intro = structured.get('self_introduction', {})
        desired = structured.get('desired_position', {})

        question = self._generate(_SITUATIONAL_TEMPLATE, {
            "motivation": self_intro.get('motivation', ''),
            "strengths": self_intro.get('strengths', ''),
            "job_type": desired.get('job_type', ''),
        })
        return {"question": question, "question_type": "상황형"}

    def generate_behavioral_question(self, parsed_data: Dict[str, Any]) -> Dict[str, str]:
        """Q5: 행동형 질문 생성 (자소서 기반)"""
        structured = parsed_data['structured_content']
        self_intro = structured.get('self_introduction', {})

        question = self._generate(_BEHAVIORAL_TEMPLATE, {
            "strengths": self_intro.get('strengths', ''),
            "key_experiences": self_intro.get('key_experiences', ''),
            "career_goals": self_intro.get('career_goals', ''),
        })
        return {"question": question, "question_type": "행동형"}

    def generate_followup_coverletter_question(self, parsed_data: Dict[str, Any],
                                             q4: str, a4: str, q5: str, a5: str) -> Dict[str, str]:
        """Q6: 자소서 기반 꼬리물기 질문 (Q4+Q5 답변 참고)"""
        structured = parsed_data['structured_content']
        self_intro = structured.get('self_introduction', {})

        question = self._generate(_FOLLOWUP_COVERLETTER_TEMPLATE, {
            "motivation": self_intro.get('motivation', ''),
            "career_goals": self_intro.get('career_goals', ''),
            "q4": q4, "a4": a4, "q5": q5, "a5": a5,
        })
        return {"question": question, "question_type": "상황형"}
