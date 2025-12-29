from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db

router = APIRouter()

@router.get("/", tags=["Status"])
def read_root():
    return {"status": "ok", "message": "Aqua Guard API is running."}

@router.get("/api/data", response_model=List[schemas.LoRaDataSchema], tags=["LoRa Data"])
def get_all_data(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    저장된 모든 LoRa 데이터를 최신순으로 가져옵니다.
    """
    data = db.query(models.LoRaData).order_by(models.LoRaData.timestamp.desc()).offset(skip).limit(limit).all()
    return data

@router.get("/api/data/latest", response_model=schemas.LoRaDataSchema, tags=["LoRa Data"])
def get_latest_data(db: Session = Depends(get_db)):
    """
    가장 최근에 수신된 LoRa 데이터를 가져옵니다.
    """
    latest_data = db.query(models.LoRaData).order_by(models.LoRaData.timestamp.desc()).first()
    if latest_data is None:
        raise HTTPException(status_code=404, detail="수신된 데이터가 없습니다.")
    return latest_data
