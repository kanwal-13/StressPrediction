#include <ArduinoBLE.h>
#include <FIR.h>
#include <protocentral_TLA20xx.h>

#define TLA20XX_I2C_ADDR 0x49
#define CES_CMDIF_PKT_START_1 0x0A
#define CES_CMDIF_PKT_START_2 0xFA
#define CES_CMDIF_TYPE_DATA 0x02
#define CES_CMDIF_PKT_STOP 0x0B
#define DATA_LEN 9
#define ZERO 0

float val;
int16_t data;

volatile char DataPacket[DATA_LEN];
const char DataPacketFooter[2] = { ZERO, CES_CMDIF_PKT_STOP };
const char DataPacketHeader[5] = { CES_CMDIF_PKT_START_1, CES_CMDIF_PKT_START_2, DATA_LEN, ZERO, CES_CMDIF_TYPE_DATA };

TLA20XX tla2022(TLA20XX_I2C_ADDR);
FIR<float, 8> fir;

const int analogPin = A0;
const int numReadings = 10;
int readings[numReadings];
int stableValue = 0;

void setup() {
  delay(3000);
  Serial.begin(57600);

  float coef[8] = { 1., 1., 1., 1., 1., 1., 1., 1. };
  fir.setFilterCoeffs(coef);

  Wire.begin();

  tla2022.begin();
  tla2022.setMode(TLA20XX::OP_CONTINUOUS);
  tla2022.setDR(TLA20XX::DR_128SPS);
  tla2022.setFSR(TLA20XX::FSR_0_512V);

  for (int i = 0; i < numReadings; i++) {
    readings[i] = 0;
  }

  BLE.begin();
  BLE.setLocalName("ArduinoNano");
  BLE.setAdvertisedServiceUuid(BLEUUID((uint16_t)0x180D));

  BLEService hrService(BLEUUID((uint16_t)0x180D));
  BLECharacteristic hrCharacteristic(BLEUUID((uint16_t)0x2A37), BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  hrService.addCharacteristic(hrCharacteristic);
  BLE.addService(hrService);
  BLE.advertise();
}

void loop() {
  val = fir.processReading(tla2022.read_adc());
  data = (int16_t)val;

  Serial.print("Variable_1:");
  Serial.print(val);
  Serial.print(",");
  Serial.print("Variable_2:");
  Serial.println(data);

  DataPacket[0] = (uint8_t)data;
  DataPacket[1] = (uint8_t)(data >> 8);
  DataPacket[2] = 0x00;
  DataPacket[3] = 0x00;

  int sensorValue = analogRead(analogPin);

  for (int i = numReadings - 1; i > 0; i--) {
    readings[i] = readings[i - 1];
  }
  readings[0] = sensorValue;

  int sorted[numReadings];
  for (int i = 0; i < numReadings; i++) {
    sorted[i] = readings[i];
  }
  for (int i = 0; i < numReadings - 1; i++) {
    for (int j = 0; j < numReadings - i - 1; j++) {
      if (sorted[j] > sorted[j + 1]) {
        int temp = sorted[j];
        sorted[j] = sorted[j + 1];
        sorted[j + 1] = temp;
      }
    }
  }

  stableValue = sorted[numReadings / 2];

  int pulseRate = map(stableValue, 0, 1023, 0, 200);

  hrCharacteristic.writeValue((uint8_t*)&pulseRate, sizeof(pulseRate));
}