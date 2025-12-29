from pydantic import BaseModel
from datetime import datetime

# API 응답을 위한 Pydantic 스키마
class LoRaDataSchema(BaseModel):
    id: int
    device_id: str | None
    timestamp: datetime
    
    temperature: float | None = None
    turbidity: float | None = None
    ph: float | None = None
    image_ref: str | None = None
    
    payload: str | None = None

    # SQLAlchemy 모델과 호환되도록 orm_mode (v2에서는 from_attributes) 설정
    class Config:
        from_attributes = True
