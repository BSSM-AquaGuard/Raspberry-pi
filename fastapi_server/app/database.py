import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# .env 파일에서 환경 변수 로드
# 데이터베이스 경로를 ../lora_data.db 와 같이 상대 경로로 설정하기 위해 load_dotenv 호출 위치를 조정할 수 있습니다.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lora_data.db")

# 데이터베이스 엔진 생성
engine = create_engine(
    DATABASE_URL,
    # SQLite는 단일 스레드에서만 사용 가능하므로 check_same_thread=False 옵션이 필요합니다.
    connect_args={"check_same_thread": False}
)

# 데이터베이스 세션 생성을 위한 클래스
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy 모델의 기본 클래스
Base = declarative_base()

# API 엔드포인트에서 데이터베이스 세션을 얻기 위한 의존성 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
