import os
import json
import time
import serial
from dotenv import load_dotenv

# 상위 디렉토리의 .env 파일을 로드하기 위함
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from .database import SessionLocal
from .models import LoRaData

SERIAL_PORT = os.getenv("SERIAL_PORT")
BAUD_RATE = int(os.getenv("BAUD_RATE", 9600))

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
