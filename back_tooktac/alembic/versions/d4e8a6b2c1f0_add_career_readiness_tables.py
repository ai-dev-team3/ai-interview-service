"""add career readiness tables

Revision ID: d4e8a6b2c1f0
Revises: c3f7a1d94e26
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e8a6b2c1f0"
down_revision: Union[str, Sequence[str], None] = "c3f7a1d94e26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


JOB_GROUPS = [
    {"id": 1, "name": "개발/IT", "description": "개발자, 데이터, 인프라 등 IT 직무군", "is_active": True},
    {"id": 2, "name": "마케팅/기획", "description": "콘텐츠, 서비스 기획, 마케팅 직무군", "is_active": True},
    {"id": 3, "name": "사무/행정", "description": "사무보조, 행정, 운영지원 직무군", "is_active": True},
]


CRITERIA = [
    {
        "id": 1,
        "job_group_id": 1,
        "criterion_name": "프로젝트 경험",
        "description": "실제 개발 프로젝트 경험이 있는지 평가합니다.",
        "keywords": ["프로젝트", "구현", "개발", "기능", "서비스", "팀프로젝트", "개인프로젝트"],
        "weight": 25,
        "sort_order": 1,
    },
    {
        "id": 2,
        "job_group_id": 1,
        "criterion_name": "기술스택 적합도",
        "description": "희망 IT 직무와 관련된 기술을 보유했는지 평가합니다.",
        "keywords": ["python", "java", "spring", "fastapi", "react", "vue", "mysql", "postgresql", "sqlalchemy"],
        "weight": 25,
        "sort_order": 2,
    },
    {
        "id": 3,
        "job_group_id": 1,
        "criterion_name": "문제 해결 경험",
        "description": "오류 해결, 구조 개선, 성능 개선 등 문제 해결 경험이 있는지 평가합니다.",
        "keywords": ["오류", "에러", "개선", "리팩토링", "최적화", "트러블슈팅", "해결"],
        "weight": 20,
        "sort_order": 3,
    },
    {
        "id": 4,
        "job_group_id": 1,
        "criterion_name": "문서화/포트폴리오",
        "description": "GitHub, README, API 명세, ERD 등 결과물을 정리했는지 평가합니다.",
        "keywords": ["github", "readme", "erd", "api 명세", "포트폴리오", "문서화", "wiki"],
        "weight": 15,
        "sort_order": 4,
    },
    {
        "id": 5,
        "job_group_id": 1,
        "criterion_name": "배포/운영 경험",
        "description": "서비스 배포, 서버 운영, 클라우드 사용 경험이 있는지 평가합니다.",
        "keywords": ["aws", "ec2", "docker", "nginx", "pm2", "배포", "운영", "서버"],
        "weight": 15,
        "sort_order": 5,
    },
    {
        "id": 6,
        "job_group_id": 2,
        "criterion_name": "콘텐츠/기획 경험",
        "description": "콘텐츠 제작 또는 기획 경험이 있는지 평가합니다.",
        "keywords": ["콘텐츠", "카드뉴스", "캠페인", "기획", "sns", "서비스기획"],
        "weight": 25,
        "sort_order": 1,
    },
    {
        "id": 7,
        "job_group_id": 2,
        "criterion_name": "고객/시장 이해",
        "description": "타깃, 고객, 시장 분석 경험이 있는지 평가합니다.",
        "keywords": ["타깃", "고객", "시장조사", "경쟁사", "니즈", "페르소나"],
        "weight": 20,
        "sort_order": 2,
    },
    {
        "id": 8,
        "job_group_id": 2,
        "criterion_name": "성과 지표 제시",
        "description": "활동 결과를 수치로 설명할 수 있는지 평가합니다.",
        "keywords": ["조회수", "클릭률", "전환율", "팔로워", "참여율", "%", "증가"],
        "weight": 25,
        "sort_order": 3,
    },
    {
        "id": 9,
        "job_group_id": 2,
        "criterion_name": "툴 활용 능력",
        "description": "마케팅/기획 관련 도구를 활용했는지 평가합니다.",
        "keywords": ["ga4", "excel", "notion", "figma", "광고관리자", "엑셀"],
        "weight": 15,
        "sort_order": 4,
    },
    {
        "id": 10,
        "job_group_id": 2,
        "criterion_name": "자료화 능력",
        "description": "기획서, 보고서, 포트폴리오로 경험을 정리했는지 평가합니다.",
        "keywords": ["기획서", "보고서", "제안서", "포트폴리오", "문서", "발표자료"],
        "weight": 15,
        "sort_order": 5,
    },
    {
        "id": 11,
        "job_group_id": 3,
        "criterion_name": "문서 작성 능력",
        "description": "회의록, 보고서, 문서 정리 경험이 있는지 평가합니다.",
        "keywords": ["회의록", "보고서", "문서", "정리", "작성", "공문"],
        "weight": 25,
        "sort_order": 1,
    },
    {
        "id": 12,
        "job_group_id": 3,
        "criterion_name": "OA/Excel 활용",
        "description": "Excel, Word, PPT 등 사무 도구 활용 경험이 있는지 평가합니다.",
        "keywords": ["excel", "엑셀", "word", "ppt", "함수", "피벗", "데이터"],
        "weight": 25,
        "sort_order": 2,
    },
    {
        "id": 13,
        "job_group_id": 3,
        "criterion_name": "일정/업무 관리",
        "description": "일정 조율, 업무 분담, 관리 경험이 있는지 평가합니다.",
        "keywords": ["일정", "관리", "조율", "체크리스트", "업무분장", "마감"],
        "weight": 20,
        "sort_order": 3,
    },
    {
        "id": 14,
        "job_group_id": 3,
        "criterion_name": "커뮤니케이션",
        "description": "팀원, 고객, 조직 내 소통 경험이 있는지 평가합니다.",
        "keywords": ["협업", "소통", "전달", "조율", "응대", "커뮤니케이션"],
        "weight": 15,
        "sort_order": 4,
    },
    {
        "id": 15,
        "job_group_id": 3,
        "criterion_name": "정확성/꼼꼼함",
        "description": "반복 업무, 자료 검토, 오류 방지 경험이 있는지 평가합니다.",
        "keywords": ["검토", "확인", "정확성", "꼼꼼", "누락", "오류 방지"],
        "weight": 15,
        "sort_order": 5,
    },
]


ACTIONS = [
    (1, 1, 1, "대표 프로젝트를 구체화하세요", "프로젝트 목적, 본인 역할, 사용 기술, 구현 기능, 문제 해결 경험, 결과를 6개 항목으로 정리하세요."),
    (2, 1, 2, "기술스택 설명을 보완하세요", "사용한 기술을 단순 나열하지 말고, 왜 사용했는지와 어떤 기능에 적용했는지 함께 정리하세요."),
    (3, 1, 3, "트러블슈팅 사례를 정리하세요", "오류 상황, 원인 분석, 해결 방법, 결과 순서로 최소 1개 이상의 문제 해결 경험을 작성하세요."),
    (4, 1, 4, "GitHub README를 보완하세요", "프로젝트 소개, 실행 방법, 주요 기능, 기술스택, ERD, API 명세, 트러블슈팅 항목을 추가하세요."),
    (5, 1, 5, "배포 경험을 구조화하세요", "실제 배포 경험이 있다면 배포 주소와 서버 구조를 정리하고, 없다면 배포 계획과 학습 내용을 정리하세요."),
    (6, 2, 6, "콘텐츠 사례를 정리하세요", "제작한 콘텐츠의 목적, 대상, 제작 과정, 반응을 정리하세요."),
    (7, 2, 7, "타깃 분석을 보완하세요", "콘텐츠나 기획의 대상 사용자가 누구였는지, 어떤 니즈를 고려했는지 작성하세요."),
    (8, 2, 8, "성과 수치를 정리하세요", "조회수, 클릭률, 팔로워 증가, 참여율 등 가능한 지표를 수치로 정리하세요."),
    (9, 2, 9, "사용한 툴과 활용 목적을 정리하세요", "Notion, Excel, GA4, Figma 등을 어떤 목적으로 사용했는지 구체화하세요."),
    (10, 2, 10, "기획서를 포트폴리오화하세요", "기획 배경, 문제 정의, 실행 과정, 결과를 한 장짜리 요약 자료로 정리하세요."),
    (11, 3, 11, "문서 작성 사례를 정리하세요", "회의록, 보고서, 정리 문서 등 본인이 작성한 문서 유형과 목적을 정리하세요."),
    (12, 3, 12, "Excel 활용 사례를 구체화하세요", "사용해본 함수, 표 정리, 데이터 관리 경험을 구체적으로 작성하세요."),
    (13, 3, 13, "일정 관리 경험을 정리하세요", "일정 조율, 마감 관리, 업무 분담 경험을 상황-역할-결과 순서로 정리하세요."),
    (14, 3, 14, "협업 경험을 정리하세요", "팀원, 교수, 고객, 동료와의 소통 경험을 구체적으로 작성하세요."),
    (15, 3, 15, "실수 방지 경험을 정리하세요", "자료 검토, 누락 확인, 반복 업무 처리 경험을 사례 중심으로 정리하세요."),
]


def upgrade() -> None:
    op.create_table(
        "job_group",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "job_readiness_criteria",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_group_id", sa.Integer(), nullable=False),
        sa.Column("criterion_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["job_group_id"], ["job_group.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_readiness_criteria_job_group_id"), "job_readiness_criteria", ["job_group_id"])

    op.create_table(
        "action_template",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_group_id", sa.Integer(), nullable=False),
        sa.Column("criterion_id", sa.Integer(), nullable=False),
        sa.Column("action_title", sa.String(length=100), nullable=False),
        sa.Column("action_detail", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["criterion_id"], ["job_readiness_criteria.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_group_id"], ["job_group.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_action_template_criterion_id"), "action_template", ["criterion_id"])
    op.create_index(op.f("ix_action_template_job_group_id"), "action_template", ["job_group_id"])

    op.create_table(
        "career_diagnosis_result",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("resume_id", sa.Integer(), nullable=False),
        sa.Column("job_group_id", sa.Integer(), nullable=False),
        sa.Column("desired_job", sa.String(length=100), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["job_group_id"], ["job_group.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resume.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_career_diagnosis_result_job_group_id"), "career_diagnosis_result", ["job_group_id"])
    op.create_index(op.f("ix_career_diagnosis_result_resume_id"), "career_diagnosis_result", ["resume_id"])
    op.create_index(op.f("ix_career_diagnosis_result_user_id"), "career_diagnosis_result", ["user_id"])

    job_group_table = sa.table(
        "job_group",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    criteria_table = sa.table(
        "job_readiness_criteria",
        sa.column("id", sa.Integer),
        sa.column("job_group_id", sa.Integer),
        sa.column("criterion_name", sa.String),
        sa.column("description", sa.String),
        sa.column("keywords", sa.JSON),
        sa.column("weight", sa.Integer),
        sa.column("sort_order", sa.Integer),
    )
    action_table = sa.table(
        "action_template",
        sa.column("id", sa.Integer),
        sa.column("job_group_id", sa.Integer),
        sa.column("criterion_id", sa.Integer),
        sa.column("action_title", sa.String),
        sa.column("action_detail", sa.Text),
        sa.column("sort_order", sa.Integer),
    )

    op.bulk_insert(job_group_table, JOB_GROUPS)
    op.bulk_insert(criteria_table, CRITERIA)
    op.bulk_insert(
        action_table,
        [
            {
                "id": action_id,
                "job_group_id": job_group_id,
                "criterion_id": criterion_id,
                "action_title": title,
                "action_detail": detail,
                "sort_order": action_id,
            }
            for action_id, job_group_id, criterion_id, title, detail in ACTIONS
        ],
    )


def downgrade() -> None:
    op.drop_table("career_diagnosis_result")
    op.drop_table("action_template")
    op.drop_table("job_readiness_criteria")
    op.drop_table("job_group")

