import os
import threading
import json
from datetime import datetime
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# --- pyLoRa 및 라즈베리파이 관련 라이브러리 ---
# 이 코드는 라즈베리파이 환경에서만 정상적으로 실행됩니다.
try:
    from LoRa.controller import Controller
    from LoRa.lora import LoRa
except ImportError:
    print("⚠️ 경고: LoRa 라이브러리를 찾을 수 없습니다. 라즈베리파이 환경이 아닐 수 있습니다.")
    Controller = None
    LoRa = None

# --- 환경 변수 로드 ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lora_data.db")

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
    title="Aqua Guard LoRa API (Raspberry Pi Edition)",
    description="Raspberry Pi에서 직접 LoRa 데이터를 수신하여 API로 제공합니다.",
    version="2.0.0"
)

# --- LoRa 컨트롤러 및 콜백 ---
class LoRaController(Controller):
    def __init__(self):
        # SPI 및 핀 설정 (사용하는 LoRa 모듈 및 라즈베리파이 핀 배치에 맞게 수정)
        # SPI: MOSI=10, MISO=9, SCK=11
        # 핀: CS=8, IRQ=7, RST=4
        super(LoRaController, self).__init__(lora_class=LoRa, spi_device=0, cs_pin=8, irq_pin=7, rst_pin=4)
        self.set_freq(923.0) # 대한민국 주파수 대역
        print("📡 LoRa 컨트롤러 초기화 완료. 주파수: 923.0 MHz")

    def on_recv(self, payload):
        try:
            # 수신 데이터 파싱
            rssi = self.get_rssi()
            data_str = payload.decode('utf-8')
            print(f"受信データ: {data_str} (RSSI: {rssi})")
            
            data = json.loads(data_str)
            
            # 데이터베이스 세션 생성 및 데이터 저장
            db = SessionLocal()
            db_data = LoRaData(
                device_id=data.get("device_id"),
                temperature=data.get("temperature"),
                turbidity=data.get("turbidity"),
                ph=data.get("ph"),
                image_ref=data.get("image_ref"),
                payload=data.get("payload")
            )
            db.add(db_data)
            db.commit()
            print(f"📝 데이터베이스에 저장됨: {db_data.device_id}")
            db.close()
            
        except json.JSONDecodeError:
            print(f"⚠️ JSON 파싱 오류: '{data_str}'")
        except Exception as e:
            print(f"🚨 콜백 함수에서 오류 발생: {e}")

# --- 백그라운드 LoRa 리스너 함수 ---
def start_lora_listener():
    if LoRa is None:
        print("❌ LoRa 라이브러리가 없어 리스너를 시작할 수 없습니다. (개발 환경)")
        return
    try:
        lora_controller = LoRaController()
        lora_controller.start() # 수신 대기 시작 (블로킹)
    except Exception as e:
        print(f"🚨 LoRa 리스너 시작 중 심각한 오류 발생: {e}")
        print("   라즈베리파이의 SPI 인터페이스가 활성화되었는지, 핀 번호가 올바른지 확인하세요.")

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

    # LoRa 리스너를 백그라운드 스레드에서 시작
    lora_thread = threading.Thread(target=start_lora_listener, daemon=True)
    lora_thread.start()

# --- API 엔드포인트 ---
@app.get("/", tags=["Status"])
def read_root():
    return {"status": "ok", "message": "Aqua Guard API (Raspberry Pi) is running."}

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