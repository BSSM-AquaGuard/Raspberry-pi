import os
import threading
import json
import time
import serial
from datetime import datetime
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# --- 환경 변수 로드 ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lora_data.db")
SERIAL_PORT = os.getenv("SERIAL_PORT")
BAUD_RATE = int(os.getenv("BAUD_RATE", 9600))

# --- SQLAlchemy 설정 ---
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- 데이터베이스 모델 ---
class LoRaData(Base):
    __tablename__ = "lora_data"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    temperature = Column(Float, nullable=True)
    turbidity = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    image_ref = Column(String, nullable=True)
    payload = Column(String, nullable=True)

# --- Pydantic 스키마 ---
class LoRaDataSchema(BaseModel):
    id: int
    device_id: str
    timestamp: datetime
    temperature: float | None = None
    turbidity: float | None = None
    ph: float | None = None
    image_ref: str | None = None
    payload: str | None = None
    class Config:
        orm_mode = True

# --- FastAPI 앱 초기화 ---
app = FastAPI(
    title="Aqua Guard LoRa API (UART Edition)",
    description="라즈베리파이의 시리얼(UART) 포트를 통해 LoRa 데이터를 수신하여 API로 제공합니다.",
    version="3.0.0"
)

# --- 백그라운드 시리얼 리더 함수 ---
def read_serial_data():
    """시리얼 포트에서 데이터를 지속적으로 읽고 데이터베이스에 저장하는 백그라운드 스레드"""
    if not SERIAL_PORT:
        print("⚠️ .env 파일에 SERIAL_PORT가 설정되지 않았습니다. 시리얼 리더를 시작할 수 없습니다.")
        return

    while True:
        try:
            print(f"📡 시리얼 포트({SERIAL_PORT}) 연결 시도 중...")
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                print(f"✅ 시리얼 포트({SERIAL_PORT})에 성공적으로 연결되었습니다. 데이터 수신 대기 중...")
                while True:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            print(f"受信データ: {line}")
                            try:
                                # JSON 파싱 로직을 제거하고, 수신된 라인 전체를 payload에 저장
                                db = SessionLocal()
                                db_data = LoRaData(
                                    device_id="unknown-sender", # 송신자 ID를 알 수 없으므로 기본값 사용
                                    payload=line
                                )
                                db.add(db_data)
                                db.commit()
                                print(f"📝 데이터베이스에 저장됨: {line}")
                                db.close()

                            except Exception as e:
                                print(f"🚨 데이터 처리 또는 DB 저장 중 오류 발생: {e}")
        except serial.SerialException:
            print(f"❌ 시리얼 포트({SERIAL_PORT})를 찾을 수 없거나 연결에 실패했습니다. 5초 후 재시도합니다.")
            time.sleep(5)
        except Exception as e:
            print(f"🚨 예상치 못한 오류 발생: {e}. 5초 후 재시도합니다.")
            time.sleep(5)

# --- 데이터베이스 의존성 ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- FastAPI 이벤트 핸들러 ---
@app.on_event("startup")
def startup_event():
    print("🚀 서버가 시작됩니다.")
    Base.metadata.create_all(bind=engine)
    print("🔩 데이터베이스 테이블이 준비되었습니다.")

    # 시리얼 리더를 백그라운드 스레드에서 시작
    serial_thread = threading.Thread(target=read_serial_data, daemon=True)
    serial_thread.start()

# --- API 엔드포인트 ---
@app.get("/", tags=["Status"])
def read_root():
    return {"status": "ok", "message": "Aqua Guard API (UART) is running."}

@app.get("/api/data", response_model=list[LoRaDataSchema], tags=["LoRa Data"])
def get_all_data(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    data = db.query(LoRaData).order_by(LoRaData.timestamp.desc()).offset(skip).limit(limit).all()
    return data

@app.get("/api/data/latest", response_model=LoRaDataSchema, tags=["LoRa Data"])
def get_latest_data(db: Session = Depends(get_db)):
    latest_data = db.query(LoRaData).order_by(LoRaData.timestamp.desc()).first()
    if latest_data is None:
        raise HTTPException(status_code=404, detail="수신된 데이터가 없습니다.")
    return latest_data