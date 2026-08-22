# ArcStation

ArcStation is a macOS menu-bar companion for an ESP32 device with an OLED display. It combines desktop status information, weather, music playback, focus timing, Git activity, and BLE control in one small utility.

The desktop application runs in the menu bar and does not need to appear in the macOS Dock.

## Features

- Menu-bar application built with PySide6
- macOS CPU, memory, and battery status
- Current weather from Open-Meteo
- YouTube Music information from Google Chrome
- VS Code project and Git status tracking
- Focus timer with start, pause, and reset controls
- BLE communication with an ESP32 named `Arc Station`
- OLED screens for Home, weather, system status, developer status, music, and focus
- Optional launch-at-login configuration through macOS launchd

## Requirements

### macOS

- macOS with Bluetooth enabled
- Python 3.11 or newer
- A working Python virtual environment
- Google Chrome, if YouTube Music tracking is needed
- Xcode Command Line Tools for Git and AppleScript commands

### Python packages

Install the desktop dependencies in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install PySide6 bleak pyobjc-framework-Cocoa requests
```

`requests` is used by `weather_test.py`. The main menu-bar application uses Python's built-in `urllib` module.

## Run the Menu-Bar Application

From the repository root:

```bash
source .venv/bin/activate
python arcstation_menu.py
```

The application places an ArcStation icon in the macOS menu bar. Click the icon to open the panel. The application sets the macOS activation policy to accessory mode, so it is intended to remain menu-bar-only rather than appear in the Dock.

To stop it, use the Quit button in the panel or terminate the Python process.

## Weather

Weather is fetched from Open-Meteo using the coordinates configured in `arcstation_menu.py` and `controller.py`. The current configuration is for Avadi, India and uses the `Asia/Kolkata` timezone.

Run the standalone weather check with:

```bash
source .venv/bin/activate
python weather_test.py
```

The menu-bar worker refreshes weather every five minutes. On macOS, the application uses `/etc/ssl/cert.pem` as its trusted certificate bundle for the HTTPS request.

To use another location, update the latitude, longitude, and timezone values in the weather configuration.

## BLE and ESP32 Setup

The ESP32 firmware is in `BLE/BLE.ino` and expects an SSD1306 128x64 OLED display.

Default wiring:

| OLED pin | ESP32 pin |
| --- | --- |
| SDA | GPIO 21 |
| SCL | GPIO 22 |

The firmware advertises the BLE device name `Arc Station` and uses these UUIDs:

- Service: `12345678-1234-1234-1234-123456789001`
- Characteristic: `12345678-1234-1234-1234-123456789002`

In Arduino IDE:

1. Install ESP32 board support.
2. Install the `Adafruit GFX Library` and `Adafruit SSD1306` libraries.
3. Select the correct ESP32 board and serial port.
4. Open `BLE/BLE.ino`.
5. Upload the firmware.
6. Reset the ESP32 and wait for it to advertise as `Arc Station`.

The Python application sends screen data to the ESP32 through `bleak`. If the device is not found, check its name, Bluetooth permissions, power, and UUID configuration.

## VS Code Extension

`ArcStation-VSCode` contains a VS Code extension that monitors the active workspace and sends project and Git information to `controller.py`.

To package or install the extension:

```bash
cd ArcStation-VSCode
npm install
npx vsce package
```

Install the generated VSIX from VS Code using `Extensions: Install from VSIX...`.

The extension normally resolves `controller.py` from the parent directory of the extension. A custom controller path can be supplied through the `ARC_STATION_CONTROLLER` environment variable:

```bash
export ARC_STATION_CONTROLLER="/absolute/path/to/controller.py"
```

The extension requires a workspace folder and checks Git status periodically. It also updates when files are saved or workspace folders change.

### Chrome permission

For YouTube Music tracking, enable Chrome's Apple Events JavaScript permission:

`View` -> `Developer` -> `Allow JavaScript from Apple Events`

The app only reads matching YouTube tabs. It does not send music data to a remote service.

## launchd Startup

`com.arcstation.menu.plist` is a template. Replace both `/path/to/ArcStation` values with the local repository path before installing it. Do not commit a plist containing personal machine paths.

Validate the edited plist:

```bash
plutil -lint com.arcstation.menu.plist
```

Install it for the current user:

```bash
mkdir -p "$HOME/Library/LaunchAgents"
cp com.arcstation.menu.plist "$HOME/Library/LaunchAgents/com.arcstation.menu.plist"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.arcstation.menu.plist"
```

Unload it later:

```bash
launchctl bootout "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.arcstation.menu.plist"
```

The launch agent writes application output to `/tmp/arcstation_menu.log` and errors to `/tmp/arcstation_menu.err`.

## Command-Line Controller

The controller can also be run directly for testing:

```bash
python controller.py ENV
python controller.py MAC
python controller.py HOME
python controller.py MUSIC
python controller.py FOCUS
python controller.py "DEV|Project|CLEAN|main|0|0"
```

Direct BLE commands require the ESP32 to be powered on and advertising as `Arc Station`.

## Project Layout

```text
arcstation_menu.py                 PySide6 menu-bar application
controller.py                      BLE commands and desktop data collection
git_tracker.py                     VS Code and Git project detection
weather_test.py                    Standalone weather API test
arc_station.py                     Minimal BLE command example
scan.py                            BLE scanning utility
com.arcstation.menu.plist          launchd template
BLE/BLE.ino                        ESP32 OLED and BLE firmware
ArcStation-VSCode/                 VS Code extension
```

## Troubleshooting

### Weather remains on `LOADING...`

Run `weather_test.py`. Check the network connection and confirm that Python can validate HTTPS certificates. The application expects `/etc/ssl/cert.pem` on macOS.

### ESP32 is disconnected

Confirm that the ESP32 is powered, the firmware is uploaded, and the advertised name is exactly `Arc Station`. Check macOS Bluetooth permissions and the UUID values in both Python and Arduino code.

### VS Code data is not updating

Open a workspace folder, confirm that it is a Git repository, and check the VS Code extension output log. For music tracking, enable Chrome's Apple Events JavaScript permission.

### Launch agent does not start

Run `plutil -lint` on the plist, verify that its Python and script paths exist, and inspect `/tmp/arcstation_menu.err`.

## Privacy

ArcStation is designed for local use. It reads desktop status, the active VS Code workspace, local Git metadata, Chrome tab information, and weather data from Open-Meteo. It sends display commands to the configured ESP32 over BLE.

Do not commit virtual environments, cache directories, launch plists containing personal paths, credentials, tokens, or private logs. The repository includes a `.gitignore` for common local files.
