import threading
from fastapi import FastAPI

# app 디렉토리에서 필요한 모듈과 변수들을 가져옵니다.
from app.database import engine, Base
from app.api import router as api_router
from app.lora_receiver import read_serial_data

# 데이터베이스 테이블 생성
# 만약 데이터베이스가 없으면, 모든 테이블을 생성합니다.
Base.metadata.create_all(bind=engine)

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI(
    title="Aqua Guard LoRa API (Refactored)",
    description="라즈베리파이의 시리얼(UART) 포트를 통해 LoRa 데이터를 수신하여 API로 제공합니다. (리팩토링 버전)",
    version="4.0.0"
)

@app.on_event("startup")
def startup_event():
    """
    애플리케이션 시작 시 실행되는 이벤트 핸들러입니다.
    """
    print("🚀 서버가 시작됩니다.")
    print("🔩 데이터베이스 테이블이 준비되었습니다.")

    # 시리얼 리더를 백그라운드 스레드에서 시작합니다.
    serial_thread = threading.Thread(target=read_serial_data, daemon=True)
    serial_thread.start()
    print("📡 LoRa 데이터 수신 대기를 시작합니다...")

# app.api 에서 정의한 라우터를 메인 앱에 포함합니다.
app.include_router(api_router)
