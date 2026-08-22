import sys
import os
import asyncio
import subprocess
import time
import json
import ssl
from urllib.parse import urlencode
from urllib.request import urlopen
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread, QSize, QRect
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen, QBrush, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSystemTrayIcon, QMenu, QProgressBar, QMessageBox
)

try:
    import AppKit
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False

import controller
import git_tracker


# =====================================================
# HIDE DOCK ICON (macOS Native Menu Bar Utility)
# =====================================================

def hide_dock_icon():
    if HAS_APPKIT:
        try:
            app = AppKit.NSApplication.sharedApplication()
            # NSApplicationActivationPolicyAccessory = 1
            app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
        except Exception as e:
            print("Error setting macOS activation policy:", e)


# =====================================================
# TRAY ICON GENERATOR (Sleek Arc Station Logo)
# =====================================================

def create_tray_icon():
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Draw sleek Arc Station emblem
    pen = QPen(QColor(255, 255, 255), 2.5)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)

    # Arc curve
    painter.drawArc(4, 4, 24, 24, 30 * 16, 120 * 16)
    
    # Station A shape
    painter.drawLine(16, 8, 8, 24)
    painter.drawLine(16, 8, 24, 24)
    painter.drawLine(11, 19, 21, 19)

    painter.end()
    return QIcon(pixmap)


# =====================================================
# BACKGROUND WORKER THREADS (Never Block UI Thread)
# =====================================================

class SystemWorker(QThread):
    stats_updated = Signal(int, int, int)  # cpu, ram, battery

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        while self._running:
            try:
                cpu, ram, battery = controller.get_mac_status()
                self.stats_updated.emit(cpu, ram, battery)
            except Exception as e:
                print("SystemWorker error:", e)
            
            # Sleep 3 seconds between checks
            for _ in range(30):
                if not self._running:
                    break
                time.sleep(0.1)

    def stop(self):
        self._running = False
        self.quit()
        self.wait(2000)


class DevWorker(QThread):
    dev_updated = Signal(str, str, str, str, str)  # proj, branch, changes, commits, git_state

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        while self._running:
            try:
                window_title = git_tracker.get_vscode_window_title()
                if window_title:
                    proj = git_tracker.clean_project_name(window_title)
                    if proj:
                        proj_path = git_tracker.find_project_folder(proj)
                        if proj_path:
                            git_info = git_tracker.get_git_status(proj_path)
                            branch = git_info.get("branch", "main")
                            changes = str(git_info.get("changes", "0"))
                            commits = str(git_info.get("commits", "0"))
                            git_state = git_info.get("git", "CLEAN")
                            self.dev_updated.emit(proj, branch, changes, commits, git_state)
            except Exception as e:
                print("DevWorker error:", e)

            # Sleep 2 seconds between checks
            for _ in range(20):
                if not self._running:
                    break
                time.sleep(0.1)

    def stop(self):
        self._running = False
        self.quit()
        self.wait(2000)


class MusicWorker(QThread):
    music_updated = Signal(str, str, str, str)  # name, cur_fmt, dur_fmt, status

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        while self._running:
            try:
                music = controller.get_youtube_music()
                if music:
                    name, cur_fmt, dur_fmt, status = music
                    self.music_updated.emit(name, cur_fmt, dur_fmt, status)
                else:
                    self.music_updated.emit("No YouTube Music", "00:00", "00:00", "PAUSED")
            except Exception as e:
                print("MusicWorker error:", e)

            # Sleep 2 seconds between checks
            for _ in range(20):
                if not self._running:
                    break
                time.sleep(0.1)

    def stop(self):
        self._running = False
        self.quit()
        self.wait(2000)



class WeatherWorker(QThread):
    # temp, humidity, feels_like, condition, wind_speed
    weather_updated = Signal(float, float, float, str, float)

    # WMO weather interpretation code -> text
    WMO_CODES = {
        0: "CLEAR", 1: "CLEAR", 2: "PCLOUDY", 3: "CLOUDY",
        45: "FOG", 48: "FOG",
        51: "DRIZZLE", 53: "DRIZZLE", 55: "DRIZZLE",
        61: "RAIN", 63: "RAIN", 65: "H.RAIN",
        71: "SNOW", 73: "SNOW", 75: "H.SNOW",
        77: "SLEET",
        80: "SHOWERS", 81: "SHOWERS", 82: "H.SHOWERS",
        95: "STORM", 96: "STORM", 99: "STORM",
    }

    LATITUDE = 13.1492
    LONGITUDE = 80.0876

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        while self._running:
            try:
                ssl_context = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
                url = "https://api.open-meteo.com/v1/forecast"
                params = {
                    "latitude": self.LATITUDE,
                    "longitude": self.LONGITUDE,
                    "current": (
                        "temperature_2m,"
                        "relative_humidity_2m,"
                        "apparent_temperature,"
                        "weather_code,"
                        "wind_speed_10m"
                    ),
                    "temperature_unit": "celsius",
                    "wind_speed_unit": "kmh",
                    "timezone": "Asia/Kolkata"
                }
                query = urlencode(params)
                with urlopen(f"{url}?{query}", timeout=10, context=ssl_context) as resp:
                    cur = json.load(resp)["current"]
                temp = cur["temperature_2m"]
                humidity = cur["relative_humidity_2m"]
                feels = cur["apparent_temperature"]
                wind = cur["wind_speed_10m"]
                code = cur["weather_code"]
                condition = self.WMO_CODES.get(code, "UNKNOWN")
                self.weather_updated.emit(temp, humidity, feels, condition, wind)
            except Exception as e:
                print("WeatherWorker error:", e)

            # Refresh every 5 minutes
            for _ in range(3000):
                if not self._running:
                    break
                time.sleep(0.1)

    def stop(self):
        self._running = False
        self.quit()
        self.wait(2000)


class BLEWorker(QThread):
    connected_status = Signal(bool, str)
    command_result = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = asyncio.Queue()
        self.loop = None
        self._running = True

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._process_queue())

    async def _process_queue(self):
        while self._running:
            try:
                # Wait for next command with timeout
                try:
                    command_str = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                success = await controller.send_command(command_str)
                self.connected_status.emit(success, "Connected" if success else "Disconnected")
                self.command_result.emit(command_str, success)
                self._queue.task_done()
            except Exception as e:
                print("BLEWorker process error:", e)
                self.connected_status.emit(False, str(e))

    def send_command_async(self, command_str):
        if self.loop and self._running:
            # Clear the queue to prevent massive backlog (drop old states)
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except asyncio.QueueEmpty:
                    break
            self.loop.call_soon_threadsafe(self._queue.put_nowait, command_str)

    def stop(self):
        self._running = False
        self.quit()
        self.wait(2000)


# =====================================================
# POPUP PANEL WIDGET (macOS Dark Glass Utility Style)
# =====================================================

class ArcStationPanel(QWidget):
    def __init__(self, ble_worker, parent=None):
        super().__init__(parent)
        self.ble_worker = ble_worker
        self.current_screen = "SYSTEM"
        self.esp32_connected = False
        
        # Live Tracked States
        self.sys_cpu = 0
        self.sys_ram = 0
        self.sys_battery = 0
        
        self.dev_project = "ArcStation"
        self.dev_branch = "main"
        self.dev_changes = "0"
        self.dev_commits = "0"
        self.dev_git_state = "CLEAN"
        
        self.music_name = "No Music"
        self.music_current_formatted = "00:00"
        self.music_duration_formatted = "00:00"
        self.music_status = "PAUSED"

        self.weather_temp = 0.0
        self.weather_humidity = 0.0
        self.weather_feels = 0.0
        self.weather_condition = "LOADING..."
        self.weather_wind = 0.0
        
        self.focus_seconds = 25 * 60
        self.focus_running = True

        self.last_hidden_time = 0

        self.init_window_flags()
        self.init_ui()
        self.setup_shortcuts()
        self.setup_focus_timer()

    def init_window_flags(self):
        # We use Tool instead of Popup to allow custom drag and reliable focus loss handling
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(300, 480)

    # -------------------------------------------------
    # DRAGGABLE WINDOW SUPPORT
    # -------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_pos'):
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    # -------------------------------------------------
    # HIDE ON CLICK OUTSIDE
    # -------------------------------------------------
    def event(self, e):
        import PySide6.QtCore as core
        if e.type() == core.QEvent.WindowDeactivate:
            self.last_hidden_time = time.time()
            self.hide()
        return super().event(e)

    def init_ui(self):
        # Master panel layout
        master_layout = QVBoxLayout(self)
        master_layout.setContentsMargins(0, 0, 0, 0)

        # Background Card
        self.container = QFrame(self)
        self.container.setStyleSheet("""
            QFrame {
                background-color: #141417;
                border: 1px solid #2D2D35;
                border-radius: 12px;
            }
            QLabel {
                color: #E1E1E6;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
            }
            QPushButton {
                background-color: #1E1E24;
                color: #C4C4CC;
                border: 1px solid #2D2D35;
                border-radius: 6px;
                padding: 7px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2A2A34;
                color: #FFFFFF;
                border: 1px solid #4A4A5A;
            }
            QPushButton:pressed {
                background-color: #0066FF;
                color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        master_layout.addWidget(self.container)

        # -------------------------------------------------
        # HEADER: ARC STATION
        # -------------------------------------------------
        header_layout = QHBoxLayout()
        header_title = QLabel("ARC STATION")
        header_title.setStyleSheet("font-size: 13px; font-weight: 800; letter-spacing: 1px; color: #FFFFFF;")
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        
        self.header_badge = QLabel("READY")
        self.header_badge.setStyleSheet("font-size: 9px; font-weight: 700; color: #71717A; background-color: #1C1C22; padding: 2px 6px; border-radius: 4px;")
        header_layout.addWidget(self.header_badge)

        layout.addLayout(header_layout)
        layout.addWidget(self.create_separator())

        # -------------------------------------------------
        # SECTION: DISPLAY (Buttons)
        # -------------------------------------------------
        display_label = QLabel("DISPLAY")
        display_label.setStyleSheet("font-size: 10px; font-weight: 700; color: #71717A; letter-spacing: 0.5px;")
        layout.addWidget(display_label)

        btn_grid = QVBoxLayout()
        btn_grid.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        self.btn_home = QPushButton("HOME")
        self.btn_system = QPushButton("SYSTEM")
        self.btn_dev = QPushButton("DEV")
        row1.addWidget(self.btn_home)
        row1.addWidget(self.btn_system)
        row1.addWidget(self.btn_dev)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self.btn_music = QPushButton("MUSIC")
        self.btn_focus = QPushButton("FOCUS")
        self.btn_weather = QPushButton("WEATHER")
        row2.addWidget(self.btn_music)
        row2.addWidget(self.btn_focus)
        row2.addWidget(self.btn_weather)

        btn_grid.addLayout(row1)
        btn_grid.addLayout(row2)
        layout.addLayout(btn_grid)

        # Direct signal connections for instant response
        self.btn_home.clicked.connect(lambda: self.switch_module("HOME"))
        self.btn_system.clicked.connect(lambda: self.switch_module("SYSTEM"))
        self.btn_dev.clicked.connect(lambda: self.switch_module("DEV"))
        self.btn_music.clicked.connect(lambda: self.switch_module("MUSIC"))
        self.btn_focus.clicked.connect(lambda: self.switch_module("FOCUS"))
        self.btn_weather.clicked.connect(lambda: self.switch_module("WEATHER"))

        layout.addWidget(self.create_separator())

        # -------------------------------------------------
        # SECTION: ESP32 STATUS
        # -------------------------------------------------
        esp_layout = QHBoxLayout()
        esp_title = QLabel("ESP32")
        esp_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #71717A; letter-spacing: 0.5px;")
        esp_layout.addWidget(esp_title)
        esp_layout.addStretch()

        self.esp_status_dot = QLabel("● Disconnected")
        self.esp_status_dot.setStyleSheet("font-size: 11px; font-weight: 600; color: #FF453A;")
        esp_layout.addWidget(self.esp_status_dot)

        layout.addLayout(esp_layout)
        layout.addWidget(self.create_separator())

        # -------------------------------------------------
        # SECTION: CURRENT SCREEN
        # -------------------------------------------------

        self.content_box = QFrame()
        self.content_box.setStyleSheet("""
            QFrame {
                background-color: #1E1E24;
                border-radius: 8px;
            }
        """)
        self.content_layout = QVBoxLayout(self.content_box)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(8)

        self.lbl_primary = QLabel("CPU: --%   |   RAM: --%")
        self.lbl_primary.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: 600;")
        self.lbl_primary.setWordWrap(True)

        self.lbl_secondary = QLabel("Battery: --%")
        self.lbl_secondary.setStyleSheet("color: #A0A0A5; font-size: 12px;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #2D2D35;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #0066FF;
                border-radius: 2px;
            }
        """)

        self.content_layout.addWidget(self.lbl_primary)
        self.content_layout.addWidget(self.lbl_secondary)
        self.content_layout.addWidget(self.progress_bar)

        # -------------------------------------------------
        # FOCUS CONTROLS
        # -------------------------------------------------
        self.focus_controls = QFrame()
        focus_layout = QHBoxLayout(self.focus_controls)
        focus_layout.setContentsMargins(0, 4, 0, 0)
        focus_layout.setSpacing(6)

        self.btn_focus_start = QPushButton("Start")
        self.btn_focus_pause = QPushButton("Pause")
        self.btn_focus_reset = QPushButton("Stop")

        for btn in (self.btn_focus_start, self.btn_focus_pause, self.btn_focus_reset):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2D2D35;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 0px;
                    font-size: 10px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #3D3D48;
                }
            """)
            focus_layout.addWidget(btn)

        self.btn_focus_start.clicked.connect(self.action_focus_start)
        self.btn_focus_pause.clicked.connect(self.action_focus_pause)
        self.btn_focus_reset.clicked.connect(self.action_focus_reset)

        self.content_layout.addWidget(self.focus_controls)
        self.focus_controls.hide()

        layout.addWidget(self.content_box)
        layout.addStretch()

        # FOOTER: Settings & Quit
        footer_layout = QHBoxLayout()
        
        btn_settings = QPushButton("Settings")
        btn_quit = QPushButton("Quit Arc Station")
        
        for btn in (btn_settings, btn_quit):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #8E8E93;
                    border: none;
                    font-size: 11px;
                    font-weight: 500;
                    text-align: left;
                }
                QPushButton:hover {
                    color: #FFFFFF;
                }
            """)
        
        btn_quit.setStyleSheet(btn_quit.styleSheet().replace("text-align: left;", "text-align: right;"))
        btn_quit.clicked.connect(QApplication.quit)
        
        footer_layout.addWidget(btn_settings)
        footer_layout.addStretch()
        footer_layout.addWidget(btn_quit)
        
        layout.addLayout(footer_layout)

    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #23232C; border: none; min-height: 1px; max-height: 1px;")
        return line

    def setup_shortcuts(self):
        from PySide6.QtGui import QKeySequence
        sc_m0 = QShortcut(QKeySequence("Ctrl+1"), self)
        sc_m1 = QShortcut(QKeySequence("Ctrl+2"), self)
        sc_m2 = QShortcut(QKeySequence("Ctrl+3"), self)
        sc_m3 = QShortcut(QKeySequence("Ctrl+4"), self)
        sc_m4 = QShortcut(QKeySequence("Ctrl+5"), self)
        
        sc_c0 = QShortcut(QKeySequence("Cmd+1"), self)
        sc_c1 = QShortcut(QKeySequence("Cmd+2"), self)
        sc_c2 = QShortcut(QKeySequence("Cmd+3"), self)
        sc_c3 = QShortcut(QKeySequence("Cmd+4"), self)
        sc_c4 = QShortcut(QKeySequence("Cmd+5"), self)
        
        sc_m0.activated.connect(lambda: self.switch_module("HOME"))
        sc_m1.activated.connect(lambda: self.switch_module("SYSTEM"))
        sc_m2.activated.connect(lambda: self.switch_module("DEV"))
        sc_m3.activated.connect(lambda: self.switch_module("MUSIC"))
        sc_m4.activated.connect(lambda: self.switch_module("FOCUS"))
        
        sc_c0.activated.connect(lambda: self.switch_module("HOME"))
        sc_c1.activated.connect(lambda: self.switch_module("SYSTEM"))
        sc_c2.activated.connect(lambda: self.switch_module("DEV"))
        sc_c3.activated.connect(lambda: self.switch_module("MUSIC"))
        sc_c4.activated.connect(lambda: self.switch_module("FOCUS"))

    def setup_focus_timer(self):
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self._tick_focus)
        self.focus_timer.start(1000)

    def _tick_focus(self):
        if self.focus_running and self.focus_seconds > 0:
            self.focus_seconds -= 1
            if self.current_screen == "FOCUS":
                self.refresh_display()

    # -------------------------------------------------
    # SLOTS FOR WORKER SIGNALS
    # -------------------------------------------------
    def on_system_data(self, cpu, ram, battery):
        self.sys_cpu = cpu
        self.sys_ram = ram
        self.sys_battery = battery
        if self.current_screen == "SYSTEM":
            self.refresh_display()
            self.ble_worker.send_command_async(f"MAC|{cpu}|{ram}|{battery}")

    def on_dev_data(self, proj, branch, changes, commits, git_state):
        self.dev_project = proj
        self.dev_branch = branch
        self.dev_changes = changes
        self.dev_commits = commits
        self.dev_git_state = git_state
        if self.current_screen == "DEV":
            self.refresh_display()
            self.ble_worker.send_command_async(f"DEV|{proj}|{git_state}|{branch}|{changes}|{commits}")

    def on_music_data(self, name, cur_fmt, dur_fmt, status):
        self.music_name = name
        self.music_current_formatted = cur_fmt
        self.music_duration_formatted = dur_fmt
        self.music_status = status
        if self.current_screen == "MUSIC":
            self.refresh_display()
            self.ble_worker.send_command_async(f"MUSIC|{name}|{cur_fmt}|{dur_fmt}|{status}")

    def on_weather_data(self, temp, humidity, feels, condition, wind):
        self.weather_temp = temp
        self.weather_humidity = humidity
        self.weather_feels = feels
        self.weather_condition = condition
        self.weather_wind = wind
        if self.current_screen == "WEATHER":
            self.refresh_display()
            env_cmd = f"ENV|{temp:.0f}|{humidity:.0f}|{feels:.0f}|{condition}"
            self.ble_worker.send_command_async(env_cmd)

    # -------------------------------------------------
    # MODULE SWITCHING & BLE DISPATCH
    # -------------------------------------------------
    def switch_module(self, module_name):
        self.current_screen = module_name
        self.update_active_button_style()
        self.refresh_display()
        print(f"Switching to module: {module_name}")
        if module_name == "SYSTEM":
            self.ble_worker.send_command_async("MAC")
        elif module_name == "HOME":
            self.ble_worker.send_command_async("HOME")
        elif module_name == "DEV":
            dev_cmd = f"DEV|{self.dev_project}|{self.dev_git_state}|{self.dev_branch}|{self.dev_changes}|{self.dev_commits}"
            self.ble_worker.send_command_async(dev_cmd)
        elif module_name == "MUSIC":
            music_cmd = f"MUSIC|{self.music_name}|{self.music_current_formatted}|{self.music_duration_formatted}|{self.music_status}"
            self.ble_worker.send_command_async(music_cmd)
        elif module_name == "FOCUS":
            self.ble_worker.send_command_async("FOCUS")
        elif module_name == "WEATHER":
            env_cmd = f"ENV|{self.weather_temp:.0f}|{self.weather_humidity:.0f}|{self.weather_feels:.0f}|{self.weather_condition}"
            self.ble_worker.send_command_async(env_cmd)

    def update_active_button_style(self):
        active_style = """
            QPushButton {
                background-color: #0066FF;
                color: #FFFFFF;
                border: 1px solid #3385FF;
                border-radius: 6px;
                padding: 7px;
                font-size: 11px;
                font-weight: 700;
            }
        """
        normal_style = """
            QPushButton {
                background-color: #1E1E24;
                color: #C4C4CC;
                border: 1px solid #2D2D35;
                border-radius: 6px;
                padding: 7px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2A2A34;
                color: #FFFFFF;
                border: 1px solid #4A4A5A;
            }
        """
        self.btn_home.setStyleSheet(active_style if self.current_screen == "HOME" else normal_style)
        self.btn_system.setStyleSheet(active_style if self.current_screen == "SYSTEM" else normal_style)
        self.btn_dev.setStyleSheet(active_style if self.current_screen == "DEV" else normal_style)
        self.btn_music.setStyleSheet(active_style if self.current_screen == "MUSIC" else normal_style)
        self.btn_focus.setStyleSheet(active_style if self.current_screen == "FOCUS" else normal_style)
        self.btn_weather.setStyleSheet(active_style if self.current_screen == "WEATHER" else normal_style)

    def refresh_display(self):
        if self.current_screen == "HOME":
            self.lbl_primary.setText("ARC STATION")
            self.lbl_secondary.setText("System Online")
            self.progress_bar.setVisible(False)
            self.focus_controls.hide()

        elif self.current_screen == "SYSTEM":
            self.lbl_primary.setText(f"CPU: {self.sys_cpu}%   |   RAM: {self.sys_ram}%")
            self.lbl_secondary.setText(f"Battery: {self.sys_battery}%")
            self.progress_bar.setValue(min(max(self.sys_cpu, 0), 100))
            self.progress_bar.setVisible(True)
            self.focus_controls.hide()

        elif self.current_screen == "DEV":
            self.lbl_primary.setText(self.dev_project)
            self.lbl_secondary.setText(f"Branch: {self.dev_branch}  •  Changes: {self.dev_changes}")
            self.progress_bar.setVisible(False)
            self.focus_controls.hide()

        elif self.current_screen == "MUSIC":
            self.lbl_primary.setText(self.music_name)
            self.lbl_secondary.setText(f"{self.music_current_formatted} / {self.music_duration_formatted}  ({self.music_status})")
            
            cur_sec = self._parse_seconds(self.music_current_formatted)
            dur_sec = self._parse_seconds(self.music_duration_formatted)
            pct = int((cur_sec / dur_sec * 100)) if dur_sec > 0 else 0
            self.progress_bar.setValue(min(max(pct, 0), 100))
            self.progress_bar.setVisible(True)
            self.focus_controls.hide()

        elif self.current_screen == "FOCUS":
            mins = self.focus_seconds // 60
            secs = self.focus_seconds % 60
            self.lbl_primary.setText("Focus Session")
            self.lbl_secondary.setText(f"{mins:02d}:{secs:02d} Remaining  ({'Active' if self.focus_running else 'Paused'})")
            pct = int(((25 * 60 - self.focus_seconds) / (25 * 60)) * 100)
            self.progress_bar.setValue(min(max(pct, 0), 100))
            self.progress_bar.setVisible(True)
            self.focus_controls.show()

        elif self.current_screen == "WEATHER":
            condition_emoji = {
                "CLEAR": "☀️", "PCLOUDY": "⛅", "CLOUDY": "☁️",
                "FOG": "🌫️", "DRIZZLE": "🌦️", "RAIN": "🌧️",
                "H.RAIN": "⛈️", "SNOW": "❄️", "H.SNOW": "🌨️",
                "SLEET": "🌨️", "SHOWERS": "🌧️", "H.SHOWERS": "⛈️",
                "STORM": "⛈️", "LOADING...": "🔄",
            }
            icon = condition_emoji.get(self.weather_condition, "🌡️")
            self.lbl_primary.setText(f"{icon}  {self.weather_temp:.0f}°C  {self.weather_condition}")
            self.lbl_secondary.setText(
                f"Humidity: {self.weather_humidity:.0f}%  •  Feels: {self.weather_feels:.0f}°C  •  Wind: {self.weather_wind:.0f} km/h"
            )
            # Use humidity as progress bar
            self.progress_bar.setValue(int(self.weather_humidity))
            self.progress_bar.setVisible(True)
            self.focus_controls.hide()

    def action_focus_start(self):
        self.focus_running = True
        self.ble_worker.send_command_async("FOCUS_START")
        self.refresh_display()

    def action_focus_pause(self):
        self.focus_running = False
        self.ble_worker.send_command_async("FOCUS_PAUSE")
        self.refresh_display()

    def action_focus_reset(self):
        self.focus_running = False
        self.focus_seconds = 25 * 60
        self.ble_worker.send_command_async("FOCUS_RESET")
        self.refresh_display()

    def _parse_seconds(self, time_str):
        try:
            parts = time_str.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except Exception:
            pass
        return 0.0

    def update_ble_status(self, is_connected, message):
        self.esp32_connected = is_connected
        if is_connected:
            self.esp_status_dot.setText("● Connected")
            self.esp_status_dot.setStyleSheet("font-size: 11px; font-weight: 600; color: #30D158;")
            self.header_badge.setText("BLE ONLINE")
            self.header_badge.setStyleSheet("font-size: 9px; font-weight: 700; color: #30D158; background-color: #102818; padding: 2px 6px; border-radius: 4px;")
        else:
            self.esp_status_dot.setText("● Disconnected")
            self.esp_status_dot.setStyleSheet("font-size: 11px; font-weight: 600; color: #FF453A;")
            self.header_badge.setText("DISCONNECTED")
            self.header_badge.setStyleSheet("font-size: 9px; font-weight: 700; color: #FF453A; background-color: #281014; padding: 2px 6px; border-radius: 4px;")

    def on_settings_clicked(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Arc Station Settings")
        msg.setText("Arc Station Menu Bar Utility v1.0\n\n- Auto-Detects YouTube Music in Chrome\n- Monitors VS Code & Git repositories\n- Tracks macOS CPU, RAM & Battery\n- Connects to ESP32 via BLE GATT")
        msg.setStyleSheet("QLabel{color: #FFFFFF;} QPushButton{background-color: #0066FF; color: #FFFFFF; font-weight: bold;}")
        msg.exec()


# =====================================================
# MAIN APPLICATION CONTROLLER
# =====================================================

class ArcStationApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        hide_dock_icon()
        self.app.setQuitOnLastWindowClosed(False)

        # 1. Start BLE Worker
        self.app.aboutToQuit.connect(self.clean_exit)
        self.ble_worker = BLEWorker()
        self.ble_worker.start()

        # 2. UI Panel
        self.panel = ArcStationPanel(self.ble_worker)

        # 3. Start Telemetry Background Workers (Never block UI)
        self.sys_worker = SystemWorker()
        self.sys_worker.stats_updated.connect(self.panel.on_system_data)
        self.sys_worker.start()

        self.dev_worker = DevWorker()
        self.dev_worker.dev_updated.connect(self.panel.on_dev_data)
        self.dev_worker.start()

        self.music_worker = MusicWorker()
        self.music_worker.music_updated.connect(self.panel.on_music_data)
        self.music_worker.start()

        self.weather_worker = WeatherWorker()
        self.weather_worker.weather_updated.connect(self.panel.on_weather_data)
        self.weather_worker.start()

        # Connect BLE signals to UI
        self.ble_worker.connected_status.connect(self.panel.update_ble_status)

        # Menu Bar Tray Icon
        self.tray_icon = QSystemTrayIcon(create_tray_icon(), self.app)
        self.tray_icon.setToolTip("Arc Station")

        # Tray Click Signal
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            # Prevent re-opening immediately if it just lost focus from the tray click
            if time.time() - self.panel.last_hidden_time < 0.2:
                return

            if self.panel.isVisible():
                self.panel.hide()
            else:
                self.position_panel()
                self.panel.show()
                self.panel.raise_()
                self.panel.activateWindow()

    def position_panel(self):
        from PySide6.QtGui import QCursor
        
        # Get the screen where the cursor currently is (which is where the user clicked the menu bar)
        screen = QApplication.screenAt(QCursor.pos())
        if not screen:
            screen = QApplication.primaryScreen()
            
        screen_geo = screen.availableGeometry()
        geo = self.tray_icon.geometry()
        
        panel_width = self.panel.width()
        panel_height = self.panel.height()

        if geo.x() > 0 or geo.y() > 0:
            x = geo.x() + (geo.width() // 2) - (panel_width // 2)
            y = geo.y() + geo.height() + 4
        else:
            x = QCursor.pos().x() - (panel_width // 2)
            y = QCursor.pos().y() + 20

        # Boundaries check against the SPECIFIC screen geometry
        if x + panel_width > screen_geo.x() + screen_geo.width():
            x = screen_geo.x() + screen_geo.width() - panel_width - 10
        if x < screen_geo.x() + 10:
            x = screen_geo.x() + 10

        self.panel.move(x, y)

    def clean_exit(self):
        print("Stopping workers and exiting Arc Station...")
        self.sys_worker.stop()
        self.dev_worker.stop()
        self.music_worker.stop()
        self.weather_worker.stop()
        self.ble_worker.stop()

    def run(self):
        print("Arc Station Menu Bar Application is running...")
        ret = self.app.exec()
        self.clean_exit()
        sys.exit(ret)


# =====================================================
# START ENTRY POINT
# =====================================================

if __name__ == "__main__":
    app = ArcStationApp()
    app.run()
