#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>

// =====================================================
// OLED
// =====================================================

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

// =====================================================
// BLE
// =====================================================

#define SERVICE_UUID \
"12345678-1234-1234-1234-123456789001"

#define CHARACTERISTIC_UUID \
"12345678-1234-1234-1234-123456789002"

BLEServer *bleServer;

// =====================================================
// CURRENT SCREEN
// =====================================================

String currentScreen = "HOME";

// =====================================================
// WEATHER
// =====================================================

float weatherTemperature = 0;
float weatherHumidity = 0;
float weatherFeelsLike = 0;

String weatherCondition = "WAIT";

// =====================================================
// MAC
// =====================================================

int macCPU = 0;
int macRAM = 0;
int macBattery = 0;

// =====================================================
// DEVELOPER / GIT
// =====================================================

String devProject = "--";
String devGit = "--";
String devBranch = "--";
String devChanges = "0";
String devCommits = "0";

// =====================================================
// MUSIC
// =====================================================

String musicTitle = "No Music";
String musicCurrent = "00:00";
String musicDuration = "00:00";
String musicStatus = "PAUSED";

// =====================================================
// FOCUS TIMER
// =====================================================

const unsigned long FOCUS_DURATION =
  25UL * 60UL * 1000UL;

unsigned long focusStartMillis = 0;
unsigned long focusElapsed = 0;

bool focusRunning = false;

// =====================================================
// EYE ANIMATION
// =====================================================

unsigned long lastEyeUpdate = 0;
int eyeState = 0; // 0 = open, 1 = closed

// =====================================================
// DRAW SMALL HEADER EYE
// =====================================================

void drawEye() {

  // Clear just the eye box instead of the whole screen
  display.fillRect(
    0,
    0,
    10,
    9,
    SSD1306_BLACK
  );

  if (eyeState == 0) {
    display.drawCircle(5, 4, 3, SSD1306_WHITE);
    display.fillCircle(5, 4, 1, SSD1306_WHITE);
  } else {
    display.drawLine(2, 5, 8, 5, SSD1306_WHITE);
  }
}

// =====================================================
// DRAW BIG CUTE FACE (HOME SCREEN)
// =====================================================

void drawBigFace() {

  // Clear the entire screen for the home face
  display.clearDisplay();

  if (eyeState == 0) {
    // ── EYES OPEN ──────────────────────────────────
    // Left eye:  x=18, y=10, w=36, h=34, r=10
    display.fillRoundRect(18, 10, 36, 34, 10, SSD1306_WHITE);
    // Right eye: x=74, y=10, w=36, h=34, r=10
    display.fillRoundRect(74, 10, 36, 34, 10, SSD1306_WHITE);

    // Dark pupils centered in each eye
    display.fillCircle(36, 27, 7, SSD1306_BLACK);
    display.fillCircle(92, 27, 7, SSD1306_BLACK);

  } else {
    // ── EYES CLOSED (blink) ─────────────────────────
    // Left eye: just a thick horizontal line
    display.fillRoundRect(18, 22, 36, 10, 5, SSD1306_WHITE);
    // Right eye
    display.fillRoundRect(74, 22, 36, 10, 5, SSD1306_WHITE);
  }

  // ── SMILE ───────────────────────────────────────
  // Curved smile using arc-like lines
  display.drawLine(46, 53, 50, 57, SSD1306_WHITE);
  display.drawLine(50, 57, 64, 59, SSD1306_WHITE);
  display.drawLine(64, 59, 78, 57, SSD1306_WHITE);
  display.drawLine(78, 57, 82, 53, SSD1306_WHITE);

  display.display();
}

// =====================================================
// HEADER
// =====================================================

void drawHeader(const char *title) {

  display.setTextColor(
    SSD1306_WHITE
  );

  display.setTextSize(1);

  drawEye();

  display.setCursor(
    13,
    1
  );

  display.print(
    "ARC STATION"
  );

  display.drawLine(
    0,
    12,
    127,
    12,
    SSD1306_WHITE
  );

  display.setCursor(
    2,
    16
  );

  display.print(
    title
  );
}

// =====================================================
// HOME
// =====================================================

void showHome() {

  currentScreen = "HOME";

  display.clearDisplay();
  
  // Draw the initial big face
  drawBigFace();

  display.display();
}

// =====================================================
// WEATHER
// =====================================================

void showEnvironment() {

  currentScreen = "ENV";

  display.clearDisplay();

  drawHeader(
    "AVADI WEATHER"
  );

  display.setTextSize(2);

  display.setCursor(
    4,
    29
  );

  display.print(
    weatherTemperature,
    0
  );

  display.print(
    "C"
  );

  display.setCursor(
    76,
    29
  );

  display.print(
    weatherHumidity,
    0
  );

  display.print(
    "%"
  );

  display.drawLine(
    0,
    48,
    127,
    48,
    SSD1306_WHITE
  );

  display.setTextSize(1);

  display.setCursor(
    3,
    52
  );

  display.print(
    "FEELS "
  );

  display.print(
    weatherFeelsLike,
    0
  );

  display.print(
    "C"
  );

  display.setCursor(
    73,
    52
  );

  display.print(
    weatherCondition
  );

  display.display();
}

// =====================================================
// FOCUS
// =====================================================

void showFocus() {

  currentScreen = "FOCUS";

  display.clearDisplay();

  drawHeader(
    "FOCUS"
  );

  unsigned long remaining;

  if (focusRunning) {

    unsigned long nowElapsed =
      millis() -
      focusStartMillis;

    unsigned long totalElapsed =
      focusElapsed +
      nowElapsed;

    if (
      totalElapsed >=
      FOCUS_DURATION
    ) {

      focusRunning = false;

      focusElapsed =
        FOCUS_DURATION;

      remaining = 0;

      Serial.println(
        "FOCUS COMPLETE"
      );

    } else {

      remaining =
        FOCUS_DURATION -
        totalElapsed;
    }

  } else {

    if (
      focusElapsed >=
      FOCUS_DURATION
    ) {

      remaining = 0;

    } else {

      remaining =
        FOCUS_DURATION -
        focusElapsed;
    }
  }

  unsigned long totalSeconds =
    remaining / 1000;

  int minutes =
    totalSeconds / 60;

  int seconds =
    totalSeconds % 60;

  display.setTextSize(2);

  display.setCursor(
    30,
    29
  );

  if (minutes < 10) {
    display.print("0");
  }

  display.print(
    minutes
  );

  display.print(":");

  if (seconds < 10) {
    display.print("0");
  }

  display.print(
    seconds
  );

  display.setTextSize(1);

  display.setCursor(
    42,
    53
  );

  if (focusRunning) {

    display.print(
      "RUNNING"
    );

  } else if (
    focusElapsed >=
    FOCUS_DURATION
  ) {

    display.print(
      "DONE"
    );

  } else if (
    focusElapsed > 0
  ) {

    display.print(
      "PAUSED"
    );

  } else {

    display.print(
      "READY"
    );
  }

  display.display();
}

// =====================================================
// MAC
// =====================================================

void showMac() {

  currentScreen = "MAC";

  display.clearDisplay();

  drawHeader(
    "MAC STATUS"
  );

  display.setTextSize(1);

  display.setCursor(
    5,
    30
  );

  display.print(
    "CPU"
  );

  display.setCursor(
    88,
    30
  );

  display.print(
    macCPU
  );

  display.print("%");

  display.setCursor(
    5,
    41
  );

  display.print(
    "RAM"
  );

  display.setCursor(
    88,
    41
  );

  display.print(
    macRAM
  );

  display.print("%");

  display.setCursor(
    5,
    52
  );

  display.print(
    "BATTERY"
  );

  display.setCursor(
    88,
    52
  );

  display.print(
    macBattery
  );

  display.print("%");

  display.display();
}

// =====================================================
// DEVELOPER
// =====================================================

void printClipped(
  const String &value,
  int x,
  int y,
  int maxChars
) {

  if (maxChars <= 0) {
    return;
  }

  String text = value;

  if (text.length() > maxChars) {

    if (maxChars > 3) {

      text =
        text.substring(
          0,
          maxChars - 3
        ) +
        "...";

    } else {

      text =
        text.substring(
          0,
          maxChars
        );
    }
  }

  display.setCursor(
    x,
    y
  );

  display.print(
    text
  );
}

// =====================================================
// DEVELOPER SCREEN
// =====================================================

void showDeveloper() {

  currentScreen = "DEV";

  display.clearDisplay();

  drawHeader(
    "DEVELOPER"
  );

  display.setTextColor(
    SSD1306_WHITE
  );

  display.setTextSize(1);

  // Project

  display.setCursor(
    3,
    27
  );

  display.print(
    "PROJECT"
  );

  printClipped(
    devProject,
    3,
    35,
    20
  );

  // Git

  display.setCursor(
    3,
    46
  );

  display.print(
    "GIT"
  );

  printClipped(
    devGit,
    24,
    46,
    6
  );

  // Branch

  display.setCursor(
    66,
    46
  );

  display.print(
    "BR"
  );

  printClipped(
    devBranch,
    82,
    46,
    7
  );

  // Changes

  display.setCursor(
    3,
    56
  );

  display.print(
    "CHG"
  );

  printClipped(
    devChanges,
    24,
    56,
    5
  );

  // Commits

  display.setCursor(
    66,
    56
  );

  display.print(
    "COM"
  );

  printClipped(
    devCommits,
    88,
    56,
    6
  );

  display.display();
}

// =====================================================
// DAVINCI
// =====================================================

void showDavinci() {

  currentScreen = "DAVINCI";

  display.clearDisplay();

  drawHeader(
    "DAVINCI"
  );

  display.setTextSize(2);

  display.setCursor(
    45,
    28
  );

  display.print(
    "--%"
  );

  display.setTextSize(1);

  display.setCursor(
    48,
    40
  );

  display.print(
    "RENDER"
  );

  display.drawRect(
    8,
    50,
    112,
    8,
    SSD1306_WHITE
  );

  display.display();
}

// =====================================================
// MUSIC
// =====================================================

void showMusic() {

  currentScreen = "MUSIC";

  display.clearDisplay();

  drawHeader(
    "MUSIC"
  );

  display.setTextSize(1);

  // ---------------------------------------------------
  // SONG TITLE
  // ---------------------------------------------------

  String title = musicTitle;

  if (title.length() > 20) {

    title =
      title.substring(
        0,
        17
      ) +
      "...";
  }

  display.setCursor(
    5,
    29
  );

  display.print(
    title
  );

  // ---------------------------------------------------
  // CURRENT TIME
  // ---------------------------------------------------

  display.setCursor(
    5,
    43
  );

  display.print(
    musicCurrent
  );

  // ---------------------------------------------------
  // TOTAL TIME
  // ---------------------------------------------------

  display.setCursor(
    92,
    43
  );

  display.print(
    musicDuration
  );

  // ---------------------------------------------------
  // CONVERT CURRENT TIME
  // ---------------------------------------------------

  float currentSeconds = 0;

  int currentColon =
    musicCurrent.indexOf(':');

  if (currentColon >= 0) {

    int minutes =
      musicCurrent.substring(
        0,
        currentColon
      ).toInt();

    int seconds =
      musicCurrent.substring(
        currentColon + 1
      ).toInt();

    currentSeconds =
      (minutes * 60) +
      seconds;
  }

  // ---------------------------------------------------
  // CONVERT DURATION
  // ---------------------------------------------------

  float durationSeconds = 0;

  int durationColon =
    musicDuration.indexOf(':');

  if (durationColon >= 0) {

    int minutes =
      musicDuration.substring(
        0,
        durationColon
      ).toInt();

    int seconds =
      musicDuration.substring(
        durationColon + 1
      ).toInt();

    durationSeconds =
      (minutes * 60) +
      seconds;
  }

  // ---------------------------------------------------
  // TIMELINE OUTLINE
  // ---------------------------------------------------

  display.drawRect(
    5,
    54,
    118,
    7,
    SSD1306_WHITE
  );

  // ---------------------------------------------------
  // TIMELINE PROGRESS
  // ---------------------------------------------------

  if (
    durationSeconds > 0
  ) {

    float progress =
      currentSeconds /
      durationSeconds;

    if (progress < 0) {
      progress = 0;
    }

    if (progress > 1) {
      progress = 1;
    }

    int progressWidth =
      (int)(
        114 * progress
      );

    if (
      progressWidth > 0
    ) {

      display.fillRect(
        7,
        56,
        progressWidth,
        3,
        SSD1306_WHITE
      );
    }
  }

  display.display();
}

// =====================================================
// UNKNOWN
// =====================================================

void showUnknown() {

  currentScreen = "ERROR";

  display.clearDisplay();

  drawHeader(
    "ERROR"
  );

  display.setTextSize(1);

  display.setCursor(
    20,
    35
  );

  display.print(
    "UNKNOWN COMMAND"
  );

  display.display();
}

// =====================================================
// REDRAW CURRENT SCREEN
// =====================================================

void redrawCurrentScreen() {

  if (
    currentScreen == "HOME"
  ) {

    showHome();

  } else if (
    currentScreen == "ENV"
  ) {

    showEnvironment();

  } else if (
    currentScreen == "FOCUS"
  ) {

    showFocus();

  } else if (
    currentScreen == "MAC"
  ) {

    showMac();

  } else if (
    currentScreen == "DEV"
  ) {

    showDeveloper();

  } else if (
    currentScreen == "DAVINCI"
  ) {

    showDavinci();

  } else if (
    currentScreen == "MUSIC"
  ) {

    showMusic();
  }
}

// =====================================================
// BLE SERVER CALLBACK
// =====================================================

class ServerCallbacks :
  public BLEServerCallbacks {

  void onConnect(
    BLEServer *server
  ) override {

    Serial.println(
      "BLE CLIENT CONNECTED"
    );
  }

  void onDisconnect(
    BLEServer *server
  ) override {

    Serial.println(
      "BLE CLIENT DISCONNECTED"
    );

    delay(100);

    BLEDevice::startAdvertising();

    Serial.println(
      "BLE ADVERTISING AGAIN"
    );
  }
};

// =====================================================
// BLE COMMAND CALLBACK
// =====================================================

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

    Serial.print(
      "COMMAND RECEIVED: "
    );

    Serial.println(
      command
    );

    // =================================================
    // WEATHER
    //
    // ENV|36|40|38|CLOUDY
    // =================================================

    if (
      command.startsWith(
        "ENV|"
      )
    ) {

      int p1 =
        command.indexOf('|');

      int p2 =
        command.indexOf(
          '|',
          p1 + 1
        );

      int p3 =
        command.indexOf(
          '|',
          p2 + 1
        );

      int p4 =
        command.indexOf(
          '|',
          p3 + 1
        );

      if (
        p1 >= 0 &&
        p2 >= 0 &&
        p3 >= 0 &&
        p4 >= 0
      ) {

        weatherTemperature =
          command.substring(
            p1 + 1,
            p2
          ).toFloat();

        weatherHumidity =
          command.substring(
            p2 + 1,
            p3
          ).toFloat();

        weatherFeelsLike =
          command.substring(
            p3 + 1,
            p4
          ).toFloat();

        weatherCondition =
          command.substring(
            p4 + 1
          );

        showEnvironment();

        return;
      }

      showUnknown();

      return;
    }

    // =================================================
    // MAC
    //
    // MAC|12|48|86
    // =================================================

    if (
      command.startsWith(
        "MAC|"
      )
    ) {

      int p1 =
        command.indexOf('|');

      int p2 =
        command.indexOf(
          '|',
          p1 + 1
        );

      int p3 =
        command.indexOf(
          '|',
          p2 + 1
        );

      if (
        p1 >= 0 &&
        p2 >= 0 &&
        p3 >= 0
      ) {

        macCPU =
          command.substring(
            p1 + 1,
            p2
          ).toInt();

        macRAM =
          command.substring(
            p2 + 1,
            p3
          ).toInt();

        macBattery =
          command.substring(
            p3 + 1
          ).toInt();

        showMac();

        return;
      }

      showUnknown();

      return;
    }

    // =================================================
    // DEVELOPER / GIT
    //
    // DEV|V4|CLEAN|main|0|22
    // =================================================

    if (
      command.startsWith(
        "DEV|"
      )
    ) {

      int p1 =
        command.indexOf('|');

      int p2 =
        command.indexOf(
          '|',
          p1 + 1
        );

      int p3 =
        command.indexOf(
          '|',
          p2 + 1
        );

      int p4 =
        command.indexOf(
          '|',
          p3 + 1
        );

      int p5 =
        command.indexOf(
          '|',
          p4 + 1
        );

      if (
        p1 >= 0 &&
        p2 >= 0 &&
        p3 >= 0 &&
        p4 >= 0 &&
        p5 >= 0
      ) {

        devProject =
          command.substring(
            p1 + 1,
            p2
          );

        devGit =
          command.substring(
            p2 + 1,
            p3
          );

        devBranch =
          command.substring(
            p3 + 1,
            p4
          );

        devChanges =
          command.substring(
            p4 + 1,
            p5
          );

        devCommits =
          command.substring(
            p5 + 1
          );

        showDeveloper();

        return;
      }

      showUnknown();

      return;
    }

    // =================================================
    // MUSIC
    //
    // MUSIC|TITLE|CURRENT|DURATION|STATUS
    //
    // Example:
    //
    // MUSIC|Vaathi Raid|01:18|03:36|PLAYING
    // =================================================

    if (
      command.startsWith(
        "MUSIC|"
      )
    ) {

      int p1 =
        command.indexOf('|');

      int p2 =
        command.indexOf(
          '|',
          p1 + 1
        );

      int p3 =
        command.indexOf(
          '|',
          p2 + 1
        );

      int p4 =
        command.indexOf(
          '|',
          p3 + 1
        );

      if (
        p1 >= 0 &&
        p2 >= 0 &&
        p3 >= 0 &&
        p4 >= 0
      ) {

        musicTitle =
          command.substring(
            p1 + 1,
            p2
          );

        musicCurrent =
          command.substring(
            p2 + 1,
            p3
          );

        musicDuration =
          command.substring(
            p3 + 1,
            p4
          );

        musicStatus =
          command.substring(
            p4 + 1
          );

        showMusic();

        return;
      }

      showUnknown();

      return;
    }

    // =================================================
    // NORMAL COMMANDS
    // =================================================

    String normalCommand =
      command;

    normalCommand.toUpperCase();

    // HOME

    if (
      normalCommand ==
      "HOME"
    ) {

      showHome();
    }

    // FOCUS

    else if (
      normalCommand ==
      "FOCUS"
    ) {

      showFocus();
    }

    // FOCUS START

    else if (
      normalCommand ==
      "FOCUS_START"
    ) {

      if (!focusRunning) {

        focusStartMillis =
          millis();

        focusRunning =
          true;
      }

      showFocus();
    }

    // FOCUS PAUSE

    else if (
      normalCommand ==
      "FOCUS_PAUSE"
    ) {

      if (focusRunning) {

        focusElapsed +=
          millis() -
          focusStartMillis;

        focusRunning =
          false;
      }

      showFocus();
    }

    // FOCUS RESET

    else if (
      normalCommand ==
      "FOCUS_RESET"
    ) {

      focusRunning =
        false;

      focusElapsed =
        0;

      focusStartMillis =
        0;

      showFocus();
    }

    // MAC

    else if (
      normalCommand ==
      "MAC"
    ) {

      showMac();
    }

    // DEV

    else if (
      normalCommand ==
      "DEV"
    ) {

      showDeveloper();
    }

    // DAVINCI

    else if (
      normalCommand ==
      "DAVINCI"
    ) {

      showDavinci();
    }

    // MUSIC WITHOUT DATA

    else if (
      normalCommand ==
      "MUSIC"
    ) {

      showMusic();
    }

    // UNKNOWN

    else {

      Serial.print(
        "UNKNOWN COMMAND: "
      );

      Serial.println(
        normalCommand
      );

      showUnknown();
    }
  }
};

// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(
    115200
  );

  delay(500);

  Serial.println();
  Serial.println("======================");
  Serial.println("ARC STATION");
  Serial.println("STARTING...");
  Serial.println("======================");

  // ===================================================
  // OLED
  // ===================================================

  Wire.begin(
    OLED_SDA,
    OLED_SCL
  );

  if (
    !display.begin(
      SSD1306_SWITCHCAPVCC,
      0x3C
    )
  ) {

    Serial.println("OLED ERROR");
    while (true) {
      delay(1000);
    }
  }

  Serial.println("OLED OK");

  // ===================================================
  // STARTUP
  // ===================================================

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(25, 28);
  display.println("ARC STATION");
  display.setCursor(39, 42);
  display.println("STARTING...");
  display.display();

  delay(1000);

  showHome();

  // ===================================================
  // BLE
  // ===================================================

  BLEDevice::init("Arc Station");
  bleServer = BLEDevice::createServer();
  bleServer->setCallbacks(new ServerCallbacks());
  BLEService *service = bleServer->createService(SERVICE_UUID);

  BLECharacteristic *characteristic = service->createCharacteristic(
      CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE
  );

  characteristic->setCallbacks(new CommandCallback());
  characteristic->setValue("READY");
  service->start();

  // ===================================================
  // ADVERTISING
  // ===================================================

  BLEAdvertising *advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  advertising->setScanResponse(true);
  advertising->setMinPreferred(0x06);
  advertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();

  Serial.println("BLE OK");
  Serial.println("DEVICE: Arc Station");
  Serial.println("STATUS: ADVERTISING");
  Serial.println("======================");
}

// =====================================================
// LOOP
// =====================================================

void loop() {

  // ---------------------------------------------------
  // Eye animation timing logic
  // Eyes stay open for 3 seconds, closed for 200ms
  // ---------------------------------------------------
  unsigned long now = millis();
  unsigned long interval = (eyeState == 0) ? 3000 : 200;

  if (now - lastEyeUpdate >= interval) {
    lastEyeUpdate = now;
    
    // Toggle state: 0 = Open, 1 = Closed
    eyeState = (eyeState == 0) ? 1 : 0;

    // UPDATE ONLY THE RELEVANT EYE, avoiding full screen flicker!
    if (currentScreen == "HOME") {
      drawBigFace();
      display.display();
    } else {
      drawEye();
      display.display();
    }
  }

  // ---------------------------------------------------
  // Focus timer
  // ---------------------------------------------------
  if (focusRunning) {
    showFocus();
  }

  delay(50);
}
