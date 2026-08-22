#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

#define OLED_SDA 21
#define OLED_SCL 22

Adafruit_SSD1306 display(
  SCREEN_WIDTH,
  SCREEN_HEIGHT,
  &Wire,
  -1
);

// BLE
#define SERVICE_UUID \
"12345678-1234-1234-1234-123456789001"

#define CHARACTERISTIC_UUID \
"12345678-1234-1234-1234-123456789002"

BLECharacteristic *commandCharacteristic;


// ---------------- HOME ----------------

void showHome() {

  display.clearDisplay();

  display.setTextColor(
    SSD1306_WHITE
  );

  display.setTextSize(1);

  display.setCursor(0, 0);
  display.println("ARC STATION");

  display.drawLine(
    0, 11,
    127, 11,
    SSD1306_WHITE
  );

  display.setTextSize(2);

  display.setCursor(20, 23);
  display.println("HOME");

  display.setTextSize(1);

  display.setCursor(20, 50);
  display.println("BLE CONNECTED");

  display.display();
}


// ---------------- DAVINCI ----------------

void showDavinci() {

  display.clearDisplay();

  display.setTextColor(
    SSD1306_WHITE
  );

  display.setTextSize(1);

  display.setCursor(0, 0);
  display.println("ARC STATION");

  display.drawLine(
    0, 11,
    127, 11,
    SSD1306_WHITE
  );

  display.setCursor(0, 18);
  display.println("DAVINCI RENDER");

  display.setTextSize(2);

  display.setCursor(35, 32);
  display.println("82%");

  display.display();
}


// ---------------- CALLBACK ----------------

class CommandCallback :
  public BLECharacteristicCallbacks {

  void onWrite(
    BLECharacteristic *characteristic
  ) override {

    String command =
      characteristic
        ->getValue()
        .c_str();

    command.trim();
    command.toUpperCase();

    Serial.print("Command: ");
    Serial.println(command);

    if (command == "HOME") {

      showHome();

    }

    else if (
      command == "DAVINCI"
    ) {

      showDavinci();

    }

  }
};


// ---------------- SETUP ----------------

void setup() {

  Serial.begin(115200);

  // OLED

  Wire.begin(
    OLED_SDA,
    OLED_SCL
  );

  if (!display.begin(
        SSD1306_SWITCHCAPVCC,
        0x3C
      )) {

    Serial.println(
      "OLED not found!"
    );

    while (true);
  }

  showHome();


  // BLE

  BLEDevice::init(
    "Arc Station"
  );

  BLEServer *server =
    BLEDevice::createServer();

  BLEService *service =
    server->createService(
      SERVICE_UUID
    );

  commandCharacteristic =
    service->createCharacteristic(
      CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_READ |
      BLECharacteristic::PROPERTY_WRITE
    );

  commandCharacteristic
    ->setCallbacks(
      new CommandCallback()
    );

  service->start();


  BLEAdvertising *
    advertising =
      BLEDevice::getAdvertising();

  advertising->addServiceUUID(
    SERVICE_UUID
  );

  advertising->setScanResponse(
    true
  );

  BLEDevice::startAdvertising();

  Serial.println(
    "Arc Station BLE ready"
  );
}


// ---------------- LOOP ----------------

void loop() {

  delay(10);

}