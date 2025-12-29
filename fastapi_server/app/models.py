from sqlalchemy import Column, Integer, String, DateTime, Float
from datetime import datetime
from .database import Base

class LoRaData(Base):
    __tablename__ = "lora_data"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # 센서 데이터 필드
    temperature = Column(Float, nullable=True)
    turbidity = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)
    image_ref = Column(String, nullable=True)
    
    # 원본 페이로드
    payload = Column(String, nullable=True)
