"""ensure career master seed data exists

Revision ID: c9d4e2f8a6b1
Revises: b4f8c2d6e9a1
Create Date: 2026-07-14 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import json


revision: str = "c9d4e2f8a6b1"
down_revision: Union[str, Sequence[str], None] = "b4f8c2d6e9a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


JOB_GROUPS = [
    {
        "name": "개발/IT",
        "description": "개발자, 데이터, 인프라 등 IT 직무군",
        "criteria": [
            (
                "프로젝트 경험",
                "실제 개발 프로젝트 경험이 있는지 평가합니다.",
                ["프로젝트", "구현", "개발", "기능", "서비스", "팀프로젝트", "개인프로젝트"],
                25,
                1,
                "대표 프로젝트를 구체화하세요",
                "프로젝트 목적, 본인 역할, 사용 기술, 구현 기능, 문제 해결 경험, 결과를 6개 항목으로 정리하세요.",
            ),
            (
                "기술스택 적합도",
                "희망 IT 직무와 관련된 기술을 보유했는지 평가합니다.",
                ["python", "java", "spring", "fastapi", "react", "vue", "mysql", "postgresql", "sqlalchemy"],
                25,
                2,
                "기술스택 설명을 보완하세요",
                "사용한 기술을 단순 나열하지 말고, 왜 사용했는지와 어떤 기능에 적용했는지 함께 정리하세요.",
            ),
            (
                "문제 해결 경험",
                "오류 해결, 구조 개선, 성능 개선 등 문제 해결 경험이 있는지 평가합니다.",
                ["오류", "에러", "개선", "리팩토링", "최적화", "트러블슈팅", "해결"],
                20,
                3,
                "트러블슈팅 사례를 정리하세요",
                "오류 상황, 원인 분석, 해결 방법, 결과 순서로 최소 1개 이상의 문제 해결 경험을 작성하세요.",
            ),
            (
                "문서화/포트폴리오",
                "GitHub, README, API 명세, ERD 등 결과물을 정리했는지 평가합니다.",
                ["github", "readme", "erd", "api 명세", "포트폴리오", "문서화", "wiki"],
                15,
                4,
                "GitHub README를 보완하세요",
                "프로젝트 소개, 실행 방법, 주요 기능, 기술스택, ERD, API 명세, 트러블슈팅 항목을 추가하세요.",
            ),
            (
                "배포/운영 경험",
                "서비스 배포, 서버 운영, 클라우드 사용 경험이 있는지 평가합니다.",
                ["aws", "ec2", "docker", "nginx", "pm2", "배포", "운영", "서버"],
                15,
                5,
                "배포 경험을 구조화하세요",
                "실제 배포 경험이 있다면 배포 주소와 서버 구조를 정리하고, 없다면 배포 계획과 학습 내용을 정리하세요.",
            ),
        ],
    },
    {
        "name": "마케팅/기획",
        "description": "콘텐츠, 서비스 기획, 마케팅 직무군",
        "criteria": [
            (
                "콘텐츠/기획 경험",
                "콘텐츠 제작 또는 기획 경험이 있는지 평가합니다.",
                ["콘텐츠", "카드뉴스", "캠페인", "기획", "sns", "서비스기획"],
                25,
                1,
                "콘텐츠 사례를 정리하세요",
                "제작한 콘텐츠의 목적, 대상, 제작 과정, 반응을 정리하세요.",
            ),
            (
                "고객/시장 이해",
                "타깃, 고객, 시장 분석 경험이 있는지 평가합니다.",
                ["타깃", "고객", "시장조사", "경쟁사", "니즈", "페르소나"],
                20,
                2,
                "타깃 분석을 보완하세요",
                "콘텐츠나 기획의 대상 사용자가 누구였는지, 어떤 니즈를 고려했는지 작성하세요.",
            ),
            (
                "성과 지표 제시",
                "활동 결과를 수치로 설명할 수 있는지 평가합니다.",
                ["조회수", "클릭률", "전환율", "팔로워", "참여율", "%", "증가"],
                25,
                3,
                "성과 수치를 정리하세요",
                "조회수, 클릭률, 팔로워 증가, 참여율 등 가능한 지표를 수치로 정리하세요.",
            ),
            (
                "툴 활용 능력",
                "마케팅/기획 관련 도구를 활용했는지 평가합니다.",
                ["ga4", "excel", "notion", "figma", "광고관리자", "엑셀"],
                15,
                4,
                "사용한 툴과 활용 목적을 정리하세요",
                "Notion, Excel, GA4, Figma 등을 어떤 목적으로 사용했는지 구체화하세요.",
            ),
            (
                "자료화 능력",
                "기획서, 보고서, 포트폴리오로 경험을 정리했는지 평가합니다.",
                ["기획서", "보고서", "제안서", "포트폴리오", "문서", "발표자료"],
                15,
                5,
                "기획서를 포트폴리오화하세요",
                "기획 배경, 문제 정의, 실행 과정, 결과를 한 장짜리 요약 자료로 정리하세요.",
            ),
        ],
    },
    {
        "name": "사무/행정",
        "description": "사무보조, 행정, 운영지원 직무군",
        "criteria": [
            (
                "문서 작성 능력",
                "회의록, 보고서, 문서 정리 경험이 있는지 평가합니다.",
                ["회의록", "보고서", "문서", "정리", "작성", "공문"],
                25,
                1,
                "문서 작성 사례를 정리하세요",
                "회의록, 보고서, 정리 문서 등 본인이 작성한 문서 유형과 목적을 정리하세요.",
            ),
            (
                "OA/Excel 활용",
                "Excel, Word, PPT 등 사무 도구 활용 경험이 있는지 평가합니다.",
                ["excel", "엑셀", "word", "ppt", "함수", "피벗", "데이터"],
                25,
                2,
                "Excel 활용 사례를 구체화하세요",
                "사용해본 함수, 표 정리, 데이터 관리 경험을 구체적으로 작성하세요.",
            ),
            (
                "일정/업무 관리",
                "일정 조율, 업무 분담, 관리 경험이 있는지 평가합니다.",
                ["일정", "관리", "조율", "체크리스트", "업무분장", "마감"],
                20,
                3,
                "일정 관리 경험을 정리하세요",
                "일정 조율, 마감 관리, 업무 분담 경험을 상황-역할-결과 순서로 정리하세요.",
            ),
            (
                "커뮤니케이션",
                "팀원, 고객, 조직 내 소통 경험이 있는지 평가합니다.",
                ["협업", "소통", "전달", "조율", "응대", "커뮤니케이션"],
                15,
                4,
                "협업 경험을 정리하세요",
                "팀원, 교수, 고객, 동료와의 소통 경험을 구체적으로 작성하세요.",
            ),
            (
                "정확성/꼼꼼함",
                "반복 업무, 자료 검토, 오류 방지 경험이 있는지 평가합니다.",
                ["검토", "확인", "정확성", "꼼꼼", "누락", "오류 방지"],
                15,
                5,
                "실수 방지 경험을 정리하세요",
                "자료 검토, 누락 확인, 반복 업무 처리 경험을 사례 중심으로 정리하세요.",
            ),
        ],
    },
]


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _scalar(sql: str, params: dict | None = None):
    return op.get_bind().execute(sa.text(sql), params or {}).scalar()


def _ensure_job_group(name: str, description: str) -> int:
    group_id = _scalar("SELECT id FROM job_group WHERE name = :name", {"name": name})
    if group_id:
        op.get_bind().execute(
            sa.text("UPDATE job_group SET description = :description, is_active = 1 WHERE id = :id"),
            {"id": group_id, "description": description},
        )
        return int(group_id)

    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO job_group (name, description, is_active)
            VALUES (:name, :description, 1)
            """
        ),
        {"name": name, "description": description},
    )
    return int(_scalar("SELECT id FROM job_group WHERE name = :name", {"name": name}))


def _ensure_criterion(
    job_group_id: int,
    name: str,
    description: str,
    keywords: list[str],
    weight: int,
    sort_order: int,
) -> int:
    criterion_id = _scalar(
        """
        SELECT id FROM job_readiness_criteria
        WHERE job_group_id = :job_group_id AND criterion_name = :name
        """,
        {"job_group_id": job_group_id, "name": name},
    )
    if criterion_id:
        op.get_bind().execute(
            sa.text(
                """
                UPDATE job_readiness_criteria
                SET description = :description,
                    keywords = :keywords,
                    weight = :weight,
                    sort_order = :sort_order
                WHERE id = :id
                """
            ),
            {
                "id": criterion_id,
                "description": description,
                "keywords": json.dumps(keywords, ensure_ascii=False),
                "weight": weight,
                "sort_order": sort_order,
            },
        )
        return int(criterion_id)

    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO job_readiness_criteria
                (job_group_id, criterion_name, description, keywords, weight, sort_order)
            VALUES
                (:job_group_id, :name, :description, :keywords, :weight, :sort_order)
            """
        ),
        {
            "job_group_id": job_group_id,
            "name": name,
            "description": description,
            "keywords": json.dumps(keywords, ensure_ascii=False),
            "weight": weight,
            "sort_order": sort_order,
        },
    )
    return int(
        _scalar(
            """
            SELECT id FROM job_readiness_criteria
            WHERE job_group_id = :job_group_id AND criterion_name = :name
            """,
            {"job_group_id": job_group_id, "name": name},
        )
    )


def _ensure_action_template(
    job_group_id: int,
    criterion_id: int,
    title: str,
    detail: str,
    sort_order: int,
) -> None:
    action_id = _scalar(
        """
        SELECT id FROM action_template
        WHERE job_group_id = :job_group_id
          AND criterion_id = :criterion_id
          AND action_title = :title
        """,
        {"job_group_id": job_group_id, "criterion_id": criterion_id, "title": title},
    )
    if action_id:
        op.get_bind().execute(
            sa.text(
                """
                UPDATE action_template
                SET action_detail = :detail, sort_order = :sort_order
                WHERE id = :id
                """
            ),
            {"id": action_id, "detail": detail, "sort_order": sort_order},
        )
        return

    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO action_template
                (job_group_id, criterion_id, action_title, action_detail, sort_order)
            VALUES
                (:job_group_id, :criterion_id, :title, :detail, :sort_order)
            """
        ),
        {
            "job_group_id": job_group_id,
            "criterion_id": criterion_id,
            "title": title,
            "detail": detail,
            "sort_order": sort_order,
        },
    )


def upgrade() -> None:
    required_tables = ("job_group", "job_readiness_criteria", "action_template")
    if not all(_has_table(table_name) for table_name in required_tables):
        return

    action_sort_order = 1
    for group in JOB_GROUPS:
        group_id = _ensure_job_group(group["name"], group["description"])
        for criterion in group["criteria"]:
            (
                criterion_name,
                description,
                keywords,
                weight,
                sort_order,
                action_title,
                action_detail,
            ) = criterion
            criterion_id = _ensure_criterion(
                group_id,
                criterion_name,
                description,
                keywords,
                weight,
                sort_order,
            )
            _ensure_action_template(
                group_id,
                criterion_id,
                action_title,
                action_detail,
                action_sort_order,
            )
            action_sort_order += 1


def downgrade() -> None:
    pass
