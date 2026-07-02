"""면접 데이터(JSON) 파싱 및 검증"""
import json
from typing import Dict, List, Union

from .models import UserInfo, QuestionAnalysis


class DataParser:
    """JSON 데이터를 파싱하고 검증하는 클래스"""

    def parse_interview_data(self, interview_data: Union[str, Dict, List]) -> Dict:
        """
        다양한 형태의 면접 데이터를 파싱하여 표준 형식으로 변환

        Args:
            interview_data: 면접 데이터 (다양한 형태)

        Returns:
            파싱된 데이터 딕셔너리
        """

        # 1. JSON 문자열인 경우 딕셔너리로 변환
        if isinstance(interview_data, str):
            try:
                interview_data = json.loads(interview_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"유효하지 않은 JSON 형식입니다: {str(e)}")

        # 2. 데이터 형태에 따라 처리 분기
        if isinstance(interview_data, list):
            # 리스트 형태: [{"question_id": "q1", ...}, {"question_id": "q2", ...}]
            return self._parse_list_format(interview_data)

        elif isinstance(interview_data, dict):
            # 딕셔너리 형태: {"user_info": {...}, "questions": [...]}
            return self._parse_dict_format(interview_data)

        else:
            raise ValueError(f"지원하지 않는 데이터 형태입니다: {type(interview_data)}")

    def _parse_list_format(self, questions_list: List[Dict]) -> Dict:
        """
        리스트 형태의 데이터 파싱

        형태: [
            {
                "question_id": "q1",
                "user_info": {"user_nickname": "김면접", ...},  # 첫 번째 질문에만 있을 수 있음
                "question_number": 1,
                "question_type": "개념설명형",
                "final_score": 88,




                "question_text": "질문 내용",
                "user_answer": "사용자 답변",
                "model_answer": "모범답안",
                "detail_analysis": {...},
                "feedback": "피드백",
                "strengths": ["강점1", "강점2"],
                "improvements": ["개선점1", "개선점2"]
            },
            {...}, # 질문 2~6
        ]
        """

        if not questions_list or len(questions_list) != 6:
            raise ValueError(f"질문 데이터는 정확히 6개여야 합니다. 현재: {len(questions_list)}개")

        # 사용자 정보 추출 (첫 번째 질문에서 또는 별도로 제공)
        user_info = self._extract_user_info(questions_list)

        # 질문별 분석 데이터 변환
        question_analyses = []
        for i, question_data in enumerate(questions_list):
            try:
                qa = self._convert_to_question_analysis(question_data, i + 1)
                question_analyses.append(qa)
            except Exception as e:
                raise ValueError(f"질문 {i + 1} 데이터 변환 실패: {str(e)}")

        return {
            'user_info': user_info,
            'question_analyses': question_analyses
        }

    def _parse_dict_format(self, data_dict: Dict) -> Dict:
        """
        딕셔너리 형태의 데이터 파싱

        형태: {
            "user_info": {
                "user_id": "user123",
                "user_nickname": "김면접",
                "interview_id": "interview456",
                "interview_date": "2024-08-04",
                "interview_duration": 25
            },
            "questions": [
                {"question_id": "q1", ...},
                {"question_id": "q2", ...},
                ...
            ]
        }
        """

        # 필수 키 검증
        if 'user_info' not in data_dict:
            raise ValueError("user_info 필드가 없습니다")

        questions_key = None
        for key in ['questions', 'question_analyses', 'question_scores']:
            if key in data_dict:
                questions_key = key
                break

        if not questions_key:
            raise ValueError("질문 데이터 필드를 찾을 수 없습니다 (questions, question_analyses, question_scores 중 하나 필요)")

        # 사용자 정보 변환
        user_info = self._convert_to_user_info(data_dict['user_info'])

        # 질문 데이터 변환
        questions_list = data_dict[questions_key]
        # if len(questions_list) != 6:
        #     raise ValueError(f"질문 데이터는 정확히 6개여야 합니다. 현재: {len(questions_list)}개")

        question_analyses = []
        for i, question_data in enumerate(questions_list):
            qa = self._convert_to_question_analysis(question_data, i + 1)
            question_analyses.append(qa)

        return {
            'user_info': user_info,
            'question_analyses': question_analyses
        }

    def _extract_user_info(self, questions_list: List[Dict]) -> UserInfo:
        """리스트 형태 데이터에서 사용자 정보 추출"""

        # 첫 번째 질문에서 사용자 정보 찾기
        first_question = questions_list[0]

        if 'user_info' in first_question:
            return self._convert_to_user_info(first_question['user_info'])

        # user_info가 별도로 없으면 개별 필드에서 추출
        user_data = {}
        for field in ['user_id', 'user_nickname', 'interview_id', 'interview_date', 'interview_duration']:
            if field in first_question:
                user_data[field] = first_question[field]

        if not user_data:
            # 기본값 설정
            user_data = {
                'user_id': 'unknown',
                'user_nickname': '면접자',
                'interview_id': 'interview_unknown',
                'interview_date': '2024-08-04',
                'interview_duration': 30
            }

        return self._convert_to_user_info(user_data)

    def _convert_to_user_info(self, user_data: Dict) -> UserInfo:
        """딕셔너리를 UserInfo 객체로 변환"""
        return UserInfo(
            user_id=user_data.get('user_id', 'unknown'),
            user_nickname=user_data.get('user_nickname', '면접자'),
            interview_id=user_data.get('interview_id', 'interview_unknown'),
            interview_date=user_data.get('interview_date', '2024-08-04'),
            interview_duration=user_data.get('interview_duration', 30)
        )

    def _convert_to_question_analysis(self, question_data: Dict, question_number: int) -> QuestionAnalysis:
        """딕셔너리를 QuestionAnalysis 객체로 변환"""

        # 필수 필드 검증
        required_fields = ['final_score', 'question_text', 'user_answer', 'detail_analysis']
        for field in required_fields:
            if field not in question_data and field.replace('_', '') not in question_data:
                # 대체 필드명도 확인
                alt_names = {
                    'final_score': ['score', 'total_score'],
                    'question_text': ['question', 'question_content'],
                    'user_answer': ['my_answer', 'answer'],
                    'detail_analysis': ['analysis', 'detailed_analysis']
                }

                found = False
                if field in alt_names:
                    for alt_name in alt_names[field]:
                        if alt_name in question_data:
                            question_data[field] = question_data[alt_name]
                            found = True
                            break

                if not found:
                    raise ValueError(f"필수 필드가 없습니다: {field}")

        # QuestionAnalysis 객체 생성
        return QuestionAnalysis(
            question_id=question_data.get('question_id', f'q{question_number}'),
            name=question_data.get('name', f'질문 {question_number}'),
            type=question_data.get('question_type', question_data.get('type', '일반형')),
            final_score=int(question_data['final_score']),
            question=question_data['question_text'],
            my_answer=question_data['user_answer'],
            model_answer=question_data.get('model_answer', '모범답안이 없습니다.'),
            detail_analysis=question_data['detail_analysis'],
            feedback=question_data.get('feedback', '분석 중입니다.'),
            strengths=question_data.get('strengths', []),
            improvements=question_data.get('improvements', [])
        )

    def validate_detail_analysis(self, detail_analysis: Dict) -> bool:
        """상세 분석 데이터 구조 검증"""
        required_areas = ['text', 'voice', 'video', 'emotion']

        for area in required_areas:
            if area not in detail_analysis:
                raise ValueError(f"상세 분석에서 {area} 영역이 없습니다")

            area_data = detail_analysis[area]
            if 'score' not in area_data:
                raise ValueError(f"{area} 영역에 score 필드가 없습니다")

        return True
