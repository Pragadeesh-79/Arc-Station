import asyncio
import sys
import subprocess
import re
import json
from urllib.parse import urlencode
from urllib.request import urlopen

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    BleakClient = None
    BleakScanner = None


# =====================================================
# ARC STATION
# =====================================================

DEVICE_NAME = "Arc Station"

CHARACTERISTIC_UUID = (
    "12345678-1234-1234-1234-123456789002"
)


# =====================================================
# AVADI WEATHER
# =====================================================

LATITUDE = 13.1492
LONGITUDE = 80.0876


# =====================================================
# WEATHER DESCRIPTION
# =====================================================

def weather_description(code):

    if code == 0:
        return "CLEAR"

    if code in [1, 2, 3]:
        return "CLOUDY"

    if code in [45, 48]:
        return "FOG"

    if code in [51, 53, 55]:
        return "DRIZZLE"

    if code in [61, 63, 65]:
        return "RAIN"

    if code in [71, 73, 75, 77]:
        return "SNOW"

    if code in [80, 81, 82]:
        return "SHOWERS"

    if code in [95, 96, 99]:
        return "STORM"

    return "UNKNOWN"


# =====================================================
# GET AVADI WEATHER
# =====================================================

def get_weather():

    print("Getting Avadi weather...")

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "weather_code"
        ),

        "temperature_unit": "celsius",

        "timezone": "Asia/Kolkata"
    }

    query = urlencode(params)
    with urlopen(f"{url}?{query}", timeout=10) as response:
        data = json.load(response)

    current = data["current"]

    temperature = round(
        current["temperature_2m"]
    )

    humidity = round(
        current["relative_humidity_2m"]
    )

    feels_like = round(
        current["apparent_temperature"]
    )

    weather_code = current["weather_code"]

    condition = weather_description(
        weather_code
    )

    return (
        temperature,
        humidity,
        feels_like,
        condition
    )


# =====================================================
# GET MAC STATUS
# =====================================================

def get_mac_status():

    # =================================================
    # CPU
    # =================================================

    try:

        cpu_output = subprocess.check_output(
            [
                "sh",
                "-c",
                "top -l 1 | grep 'CPU usage'"
            ],
            text=True
        )

        cpu_match = re.search(
            r"(\d+(?:\.\d+)?)%\s*user.*?"
            r"(\d+(?:\.\d+)?)%\s*sys",
            cpu_output
        )

        if cpu_match:

            user_cpu = float(
                cpu_match.group(1)
            )

            system_cpu = float(
                cpu_match.group(2)
            )

            cpu = round(
                user_cpu + system_cpu
            )

        else:

            cpu = 0

    except Exception:

        cpu = 0


    # =================================================
    # RAM
    # =================================================

    try:

        vm_output = subprocess.check_output(
            [
                "sh",
                "-c",
                "vm_stat"
            ],
            text=True
        )

        def get_pages(name):

            match = re.search(
                rf"{re.escape(name)}:\s+(\d+)",
                vm_output
            )

            if match:

                return int(
                    match.group(1)
                )

            return 0


        free_pages = (
            get_pages("Pages free")
            +
            get_pages("Pages inactive")
            +
            get_pages("Pages speculative")
        )

        active_pages = get_pages(
            "Pages active"
        )

        wired_pages = get_pages(
            "Pages wired down"
        )

        compressed_pages = get_pages(
            "Pages occupied by compressor"
        )

        total_pages = (
            free_pages
            +
            active_pages
            +
            wired_pages
            +
            compressed_pages
        )

        used_pages = (
            active_pages
            +
            wired_pages
            +
            compressed_pages
        )

        if total_pages > 0:

            ram = round(
                (
                    used_pages /
                    total_pages
                ) * 100
            )

        else:

            ram = 0

    except Exception:

        ram = 0


    # =================================================
    # BATTERY
    # =================================================

    try:

        battery_output = subprocess.check_output(
            [
                "sh",
                "-c",
                "pmset -g batt"
            ],
            text=True
        )

        battery_match = re.search(
            r"(\d+)%\s*;",
            battery_output
        )

        if battery_match:

            battery = int(
                battery_match.group(1)
            )

        else:

            battery_match = re.search(
                r"(\d+)%",
                battery_output
            )

            if battery_match:

                battery = int(
                    battery_match.group(1)
                )

            else:

                battery = 0

    except Exception:

        battery = 0


    return (
        cpu,
        ram,
        battery
    )


# =====================================================
# YOUTUBE / CHROME
# =====================================================

def run_chrome_javascript(javascript):

    """
    Searches every Chrome window and tab.

    YouTube does NOT need to be the active tab.

    Chrome must have:

    View
    → Developer
    → Allow JavaScript from Apple Events

    enabled.
    """

    applescript = f'''
tell application "Google Chrome"

    repeat with w in windows

        repeat with t in tabs of w

            if (URL of t) contains "youtube.com" then

                return (execute t javascript {json.dumps(javascript)})

            end if

        end repeat

    end repeat

    return "NO YOUTUBE TAB"

end tell
'''

    try:

        result = subprocess.check_output(
            [
                "osascript",
                "-e",
                applescript
            ],
            text=True,
            stderr=subprocess.STDOUT
        )

        return result.strip()

    except subprocess.CalledProcessError:

        return None

    except Exception:

        return None


# =====================================================
# FORMAT TIME
# =====================================================

def format_time(seconds):

    try:

        seconds = float(seconds)

    except Exception:

        return "--:--"

    if seconds < 0:

        seconds = 0

    total_seconds = int(
        seconds
    )

    minutes = (
        total_seconds // 60
    )

    remaining_seconds = (
        total_seconds % 60
    )

    return (
        f"{minutes:02d}:"
        f"{remaining_seconds:02d}"
    )


# =====================================================
# CLEAN MUSIC NAME
# =====================================================

def clean_music_name(title):

    if not title:

        return "No Music"


    title = title.strip()


    # -------------------------------------------------
    # Remove YouTube suffix
    # -------------------------------------------------

    title = re.sub(
        r"\s*-\s*YouTube\s*$",
        "",
        title,
        flags=re.IGNORECASE
    ).strip()


    # -------------------------------------------------
    # Remove leading video number
    #
    # Example:
    # (488) Master - Vaathi Raid Lyric
    #
    # becomes:
    # Master - Vaathi Raid Lyric
    # -------------------------------------------------

    title = re.sub(
        r"^\s*\([^)]*\)\s*",
        "",
        title
    )


    # -------------------------------------------------
    # Remove everything after first |
    #
    # Example:
    #
    # Master - Vaathi Raid Lyric |
    # Thalapathy Vijay |
    #
    # becomes:
    #
    # Master - Vaathi Raid Lyric
    # -------------------------------------------------

    if "|" in title:

        title = title.split(
            "|",
            1
        )[0].strip()


    # -------------------------------------------------
    # Remove common YouTube words
    # -------------------------------------------------

    title = re.sub(
        r"\bofficial\s+music\s+video\b",
        "",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\bofficial\s+video\b",
        "",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\bofficial\s+audio\b",
        "",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\blyrics?\b",
        "",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\blyric\b",
        "",
        title,
        flags=re.IGNORECASE
    )

    title = re.sub(
        r"\bfull\s+video\b",
        "",
        title,
        flags=re.IGNORECASE
    )


    # -------------------------------------------------
    # If title contains:
    #
    # Artist - Song
    #
    # choose the part after the last " - "
    #
    # Example:
    #
    # Master - Vaathi Raid
    #
    # becomes:
    #
    # Vaathi Raid
    # -------------------------------------------------

    parts = re.split(
        r"\s+-\s+",
        title
    )

    if len(parts) >= 2:

        title = parts[-1].strip()


    # -------------------------------------------------
    # Remove brackets at beginning/end
    # -------------------------------------------------

    title = re.sub(
        r"^[\[\(]+",
        "",
        title
    )

    title = re.sub(
        r"[\]\)]+$",
        "",
        title
    )


    # -------------------------------------------------
    # Clean extra spaces
    # -------------------------------------------------

    title = re.sub(
        r"\s+",
        " ",
        title
    ).strip()


    if not title:

        return "No Music"


    # -------------------------------------------------
    # Keep BLE packet small
    # -------------------------------------------------

    if len(title) > 32:

        title = (
            title[:29]
            +
            "..."
        )


    # -------------------------------------------------
    # "|" is used as our BLE separator
    # -------------------------------------------------

    title = title.replace(
        "|",
        "-"
    )


    return title


# =====================================================
# GET YOUTUBE MUSIC
# =====================================================

def get_youtube_music():

    # -------------------------------------------------
    # Get title
    # -------------------------------------------------

    title = run_chrome_javascript(
        "document.title"
    )


    if not title:

        return None


    if title == "NO YOUTUBE TAB":

        return None


    # -------------------------------------------------
    # Get current time
    # -------------------------------------------------

    current_time = run_chrome_javascript(
        """
        (() => {

            const video =
                document.querySelector("video");

            if (!video) {

                return "NO VIDEO";
            }

            return video.currentTime;

        })()
        """
    )


    # -------------------------------------------------
    # Get duration
    # -------------------------------------------------

    duration = run_chrome_javascript(
        """
        (() => {

            const video =
                document.querySelector("video");

            if (!video) {

                return "NO VIDEO";
            }

            return video.duration;

        })()
        """
    )


    # -------------------------------------------------
    # Get play state
    # -------------------------------------------------

    paused = run_chrome_javascript(
        """
        (() => {

            const video =
                document.querySelector("video");

            if (!video) {

                return "NO VIDEO";
            }

            return video.paused
                ? "PAUSED"
                : "PLAYING";

        })()
        """
    )


    # -------------------------------------------------
    # Validate
    # -------------------------------------------------

    if current_time in [
        None,
        "NO VIDEO",
        "NO YOUTUBE TAB"
    ]:

        return None


    if duration in [
        None,
        "NO VIDEO",
        "NO YOUTUBE TAB"
    ]:

        return None


    # -------------------------------------------------
    # Clean title
    # -------------------------------------------------

    music_name = clean_music_name(
        title
    )


    # -------------------------------------------------
    # Format time
    # -------------------------------------------------

    current_formatted = format_time(
        current_time
    )

    duration_formatted = format_time(
        duration
    )


    return (
        music_name,
        current_formatted,
        duration_formatted,
        paused
    )


# =====================================================
# SEND BLE COMMAND
# =====================================================

async def send_command(command):

    if BleakScanner is None or BleakClient is None:
        print("BLE support unavailable; skipping command.")
        return False

    print()
    print(
        f"Searching for {DEVICE_NAME}..."
    )


    device = await (
        BleakScanner.find_device_by_name(
            DEVICE_NAME
        )
    )


    if device is None:

        print(
            "❌ Arc Station not found."
        )

        print(
            "Make sure the ESP32 is powered on "
            "and advertising."
        )

        return False


    print(
        "✅ Arc Station found."
    )


    try:

        async with BleakClient(
            device
        ) as client:

            print(
                "✅ Bluetooth connected."
            )


            await client.write_gatt_char(
                CHARACTERISTIC_UUID,
                command.encode()
            )


            print(
                f"✅ Sent: {command}"
            )

            return True


    except Exception as error:

        print()
        print(
            "❌ Bluetooth error:"
        )

        print(error)

        return False


# =====================================================
# CONTINUOUS MUSIC TRACKER
# =====================================================

async def track_music():

    print()
    print(
        "================================"
    )

    print(
        "       ARC STATION MUSIC"
    )

    print(
        "================================"
    )

    print()

    print(
        "YouTube Music Tracker: ON"
    )

    print(
        "Checking Chrome every 2 seconds..."
    )

    print(
        "Press Ctrl+C to stop."
    )

    print()


    last_music_name = None

    last_status = None

    last_duration = None


    while True:

        try:

            music = get_youtube_music()


            if music is None:

                if last_music_name != "NO MUSIC":

                    print(
                        "No YouTube music found."
                    )

                    last_music_name = (
                        "NO MUSIC"
                    )

                await asyncio.sleep(
                    2
                )

                continue


            (
                music_name,
                current_time,
                duration,
                status
            ) = music


            # -------------------------------------------------
            # Detect new song
            # -------------------------------------------------

            new_song = (
                music_name !=
                last_music_name
            )


            # -------------------------------------------------
            # Detect play/pause
            # -------------------------------------------------

            state_changed = (
                status !=
                last_status
            )


            # -------------------------------------------------
            # Send if:
            #
            # 1. New song
            # 2. Play/pause changed
            # 3. Timeline update
            #
            # Timeline is sent every 2 seconds.
            # -------------------------------------------------

            if new_song:

                print()
                print(
                    "🎵 NEW SONG"
                )

                print(
                    f"Music: {music_name}"
                )

                print(
                    f"Time:  "
                    f"{current_time} / "
                    f"{duration}"
                )

                print(
                    f"State: {status}"
                )


            elif state_changed:

                print(
                    f"▶ State: {status}"
                )


            # -------------------------------------------------
            # ESP32 command
            #
            # MUSIC|NAME|CURRENT|DURATION|STATUS
            # -------------------------------------------------

            command = (
                "MUSIC|"
                f"{music_name}|"
                f"{current_time}|"
                f"{duration}|"
                f"{status}"
            )


            # -------------------------------------------------
            # Send every 2 seconds
            # -------------------------------------------------

            await send_command(
                command
            )


            last_music_name = (
                music_name
            )

            last_status = (
                status
            )

            last_duration = (
                duration
            )


            await asyncio.sleep(
                2
            )


        except asyncio.CancelledError:

            break


        except KeyboardInterrupt:

            break


        except Exception as error:

            print()
            print(
                "⚠ Music tracker error:"
            )

            print(error)

            await asyncio.sleep(
                2
            )


# =====================================================
# SHOW HELP
# =====================================================

def show_help():

    print()

    print(
        "================================"
    )

    print(
        "       ARC STATION CONTROLLER"
    )

    print(
        "================================"
    )

    print()

    print(
        "Available commands:"
    )

    print()

    print("HOME")

    print("ENV")

    print("FOCUS")

    print("FOCUS_START")

    print("FOCUS_PAUSE")

    print("FOCUS_RESET")

    print("MAC")

    print("DEV")

    print("DAVINCI")

    print("MUSIC")

    print()

    print(
        "Developer format:"
    )

    print(
        'DEV|V4|CLEAN|main|0|22'
    )

    print()

    print(
        "Examples:"
    )

    print(
        "python3 controller.py ENV"
    )

    print(
        'python3 controller.py "DEV|V4|CLEAN|main|0|22"'
    )

    print(
        "python3 controller.py MUSIC"
    )

    print()


# =====================================================
# DEVELOPER COMMAND
# =====================================================

async def handle_dev_command(command):

    parts = command.split("|")


    if len(parts) == 1:

        print()

        print(
            "Developer command requires project data."
        )

        print()

        print(
            "Expected:"
        )

        print(
            "DEV|PROJECT|GIT|BRANCH|CHANGES|COMMITS"
        )

        print()

        print(
            "Example:"
        )

        print(
            "DEV|V4|CLEAN|main|0|22"
        )

        print()

        return


    if len(parts) != 6:

        print()

        print(
            "❌ Invalid DEV command."
        )

        print()

        print(
            "Expected:"
        )

        print(
            "DEV|PROJECT|GIT|BRANCH|CHANGES|COMMITS"
        )

        print()

        return


    project = parts[1]

    git_status = parts[2]

    branch = parts[3]

    changes = parts[4]

    commits = parts[5]


    print()

    print(
        "================================"
    )

    print(
        "       ARC STATION DEVELOPER"
    )

    print(
        "================================"
    )

    print()

    print(
        f"Project: {project}"
    )

    print(
        f"Git:     {git_status}"
    )

    print(
        f"Branch:  {branch}"
    )

    print(
        f"Changes: {changes}"
    )

    print(
        f"Commits: {commits}"
    )

    print()


    await send_command(
        command
    )


# =====================================================
# MUSIC COMMAND
# =====================================================

async def handle_music_command():

    await track_music()


# =====================================================
# MAIN
# =====================================================

async def main():

    if len(sys.argv) < 2:

        show_help()

        return


    raw_command = (
        sys.argv[1].strip()
    )


    mode = raw_command.upper()


    # =================================================
    # DEV
    # =================================================

    if mode.startswith(
        "DEV|"
    ):

        await handle_dev_command(
            raw_command
        )

        return


    # =================================================
    # WEATHER
    # =================================================

    if mode == "ENV":

        try:

            (
                temperature,
                humidity,
                feels_like,
                condition
            ) = get_weather()


        except Exception as error:

            print()

            print(
                "❌ Weather request failed:"
            )

            print(
                error
            )

            return


        print()

        print(
            "================================"
        )

        print(
            "       ARC STATION WEATHER"
        )

        print(
            "================================"
        )

        print()

        print(
            "Location: Avadi"
        )

        print(
            f"Temperature: {temperature}°C"
        )

        print(
            f"Humidity: {humidity}%"
        )

        print(
            f"Feels Like: {feels_like}°C"
        )

        print(
            f"Condition: {condition}"
        )

        print()


        command = (
            f"ENV|"
            f"{temperature}|"
            f"{humidity}|"
            f"{feels_like}|"
            f"{condition}"
        )


        await send_command(
            command
        )

        return


    # =================================================
    # MAC
    # =================================================

    if mode == "MAC":

        try:

            (
                cpu,
                ram,
                battery
            ) = get_mac_status()


        except Exception as error:

            print()

            print(
                "❌ Mac status error:"
            )

            print(
                error
            )

            return


        print()

        print(
            "================================"
        )

        print(
            "       ARC STATION MAC"
        )

        print(
            "================================"
        )

        print()

        print(
            f"CPU:     {cpu}%"
        )

        print(
            f"RAM:     {ram}%"
        )

        print(
            f"Battery: {battery}%"
        )

        print()


        command = (
            f"MAC|"
            f"{cpu}|"
            f"{ram}|"
            f"{battery}"
        )


        await send_command(
            command
        )

        return


    # =================================================
    # MUSIC
    # =================================================

    if mode == "MUSIC":

        await handle_music_command()

        return


    # =================================================
    # NORMAL COMMANDS
    # =================================================

    valid_modes = [

        "HOME",

        "FOCUS",

        "FOCUS_START",

        "FOCUS_PAUSE",

        "FOCUS_RESET",

        "DEV",

        "DAVINCI"

    ]


    if mode not in valid_modes:

        print()

        print(
            f"❌ Unknown mode: {raw_command}"
        )

        show_help()

        return


    await send_command(
        mode
    )


# =====================================================
# START
# =====================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()
        print(
            "Music tracker stopped."
        )
