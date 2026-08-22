import requests

LATITUDE = 13.1492
LONGITUDE = 80.0876

url = "https://api.open-meteo.com/v1/forecast"

params = {
    "latitude": LATITUDE,
    "longitude": LONGITUDE,
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

response = requests.get(url, params=params, timeout=10)

response.raise_for_status()

data = response.json()

current = data["current"]

print()
print("ARC STATION WEATHER")
print("-------------------")
print(f"Location : Avadi")
print(f"Temperature : {current['temperature_2m']} °C")
print(f"Humidity    : {current['relative_humidity_2m']} %")
print(f"Feels Like  : {current['apparent_temperature']} °C")
print(f"Wind        : {current['wind_speed_10m']} km/h")
print(f"Weather Code: {current['weather_code']}")
print()

