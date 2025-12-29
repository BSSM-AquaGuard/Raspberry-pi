// LoRa 및 SPI 라이브러리 포함
#include <SPI.h>
#include <LoRa.h>

// --- LoRa 모듈 핀 설정 (사용자 보드에 맞게 수정) ---
#define LORA_NSS_PIN   18
#define LORA_RST_PIN   14
#define LORA_DIO0_PIN  26

// --- LoRa 주파수 설정 ---
#define LORA_FREQUENCY 923E6

// --- 장치 정보 ---
#define DEVICE_ID "aqua-guard-unit-01"

// 전송 카운터
int counter = 0;

// --- 가상 센서 데이터 생성 함수 ---
float getTemperature() {
  // 15.0 ~ 25.0 사이의 임의의 수온 데이터 생성
  return 15.0 + (rand() % 100) / 10.0;
}

float getTurbidity() {
  // 0.1 ~ 5.0 NTU 사이의 임의의 탁도 데이터 생성
  return (rand() % 50) / 10.0;
}

float getPh() {
  // 6.0 ~ 8.5 사이의 임의의 pH 데이터 생성
  return 6.0 + (rand() % 25) / 10.0;
}

String getEspCamReference() {
  // ESP-CAM이 이미지를 찍고 SD 카드에 저장했다고 가정
  return "img_" + String(millis()) + ".jpg";
}


void setup() {
  Serial.begin(115200);
  while (!Serial);
  Serial.println("LoRa Multi-Sensor Sender Started");

  // SPI 및 LoRa 핀 설정
  SPI.begin(5, 19, 27, 18);
  LoRa.setPins(LORA_NSS_PIN, LORA_RST_PIN, LORA_DIO0_PIN);

  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("Starting LoRa failed!");
    while (1);
  }
  Serial.println("LoRa Initialized OK");
  
  // 난수 생성을 위한 시드 설정
  srand(analogRead(0));
}

void loop() {
  // 각 센서로부터 데이터 읽기 (시뮬레이션)
  float temp = getTemperature();
  float turbidity = getTurbidity();
  float ph = getPh();
  String image_ref = getEspCamReference();
  
  // JSON 형식으로 데이터 패킷 구성
  String jsonPacket = "{";
  jsonPacket += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  jsonPacket += "\"temperature\":" + String(temp, 2) + ",";
  jsonPacket += "\"turbidity\":" + String(turbidity, 2) + ",";
  jsonPacket += "\"ph\":" + String(ph, 2) + ",";
  jsonPacket += "\"image_ref\":\"" + image_ref + "\",";
  jsonPacket += "\"packet_no\":" + String(counter);
  jsonPacket += "}";

  Serial.print("송신 데이터: ");
  Serial.println(jsonPacket);

  // LoRa 패킷 전송
  LoRa.beginPacket();
  LoRa.print(jsonPacket);
  LoRa.endPacket();

  counter++;

  // 10초 대기
  delay(10000);
}