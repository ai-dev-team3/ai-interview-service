# app/services/user/background_tasks.py
import os
from sqlalchemy.orm import Session
from app.repository.database import SessionLocal
from app.repository.resume import Resume
from app.services.text.document_parser import VertexDocumentParser
from dotenv import load_dotenv

load_dotenv()

def structure_resume_background(file_path: str, user_id: int):
    """이력서 구조화 및 DB 반영을 백그라운드에서 수행"""
    try:
        parser = VertexDocumentParser(
            project_id=os.getenv("PROJECT_ID"),
            location=os.getenv("LOCATION", "us"),
            processor_id=os.getenv("PROCESSOR_ID"),
            gemini_api_key=os.getenv("GOOGLE_API_KEY")
        )

        parsed = parser.parse_document(file_path)
        structured = parsed["structured_content"]
        full_text = parsed["full_text"]

        # DB에 구조화 내용 저장
        db: Session = SessionLocal()
        resume = db.query(Resume).filter(Resume.user_id == user_id).first()
        if resume:
            # resume.content = full_text
            resume.content = "개인정보"
            resume.structured = structured
            db.commit()
        db.close()

    except Exception as e:
        print("구조화 백그라운드 작업 실패:", e)

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
