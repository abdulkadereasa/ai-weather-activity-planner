import os
from collections import Counter
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5"


def _empty_forecast_summary():
    return {
        "period_hours": 0,
        "min_temperature": None,
        "max_temperature": None,
        "average_temperature": None,
        "max_wind_speed": None,
        "max_precipitation_probability": 0,
        "total_precipitation_mm": 0,
        "dominant_condition": "unknown",
        "risk_flags": [],
    }


def _build_location_query(city, country_code=None):
    if country_code:
        return f"{city},{country_code}"
    return city


def _request_openweather(endpoint, params):
    if not API_KEY:
        return None, "Missing OPENWEATHER_API_KEY in the environment."

    try:
        response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=12)
    except requests.RequestException as exc:
        return None, f"Could not connect to OpenWeather: {exc}"

    if response.status_code != 200:
        message = response.json().get("message", "Could not fetch weather data.")
        return None, f"OpenWeather error: {message}"

    return response.json(), None


def _precipitation_from_entry(entry):
    rain = entry.get("rain", {})
    snow = entry.get("snow", {})
    return (
        rain.get("1h", 0)
        + rain.get("3h", 0)
        + snow.get("1h", 0)
        + snow.get("3h", 0)
    )


def _summarize_forecast(forecast_items):
    if not forecast_items:
        return _empty_forecast_summary()

    temperatures = [item["temperature"] for item in forecast_items]
    winds = [item["wind_speed"] for item in forecast_items]
    probabilities = [item["precipitation_probability"] for item in forecast_items]
    precipitation = [item["precipitation_mm"] for item in forecast_items]
    conditions = [item["condition"] for item in forecast_items]

    summary = {
        "period_hours": len(forecast_items) * 3,
        "min_temperature": round(min(temperatures), 1),
        "max_temperature": round(max(temperatures), 1),
        "average_temperature": round(sum(temperatures) / len(temperatures), 1),
        "max_wind_speed": round(max(winds), 1),
        "max_precipitation_probability": round(max(probabilities), 1),
        "total_precipitation_mm": round(sum(precipitation), 1),
        "dominant_condition": Counter(conditions).most_common(1)[0][0],
        "risk_flags": [],
    }

    if summary["max_precipitation_probability"] >= 60 or summary["total_precipitation_mm"] >= 3:
        summary["risk_flags"].append("precipitation risk")
    if summary["max_wind_speed"] and summary["max_wind_speed"] >= 10:
        summary["risk_flags"].append("high wind")
    if summary["max_temperature"] is not None and summary["max_temperature"] >= 35:
        summary["risk_flags"].append("high temperature")
    if summary["min_temperature"] is not None and summary["min_temperature"] <= 0:
        summary["risk_flags"].append("low temperature")
    if any("storm" in condition or "thunder" in condition for condition in conditions):
        summary["risk_flags"].append("storm risk")

    return summary


def _group_forecast_by_day(forecast_items):
    days = {}
    for item in forecast_items:
        time_str = item.get("time", "")
        try:
            date = time_str.split(" ")[0]
            day_name = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
        except Exception:
            continue
        if date not in days:
            days[date] = {"date": date, "day_name": day_name,
                          "temperatures": [], "precipitation_probabilities": [],
                          "wind_speeds": [], "conditions": []}
        days[date]["temperatures"].append(item["temperature"])
        days[date]["precipitation_probabilities"].append(item["precipitation_probability"])
        days[date]["wind_speeds"].append(item["wind_speed"])
        days[date]["conditions"].append(item["condition"])

    result = []
    for date, data in sorted(days.items()):
        temps = data["temperatures"]
        precips = data["precipitation_probabilities"]
        winds = data["wind_speeds"]
        conditions = data["conditions"]
        avg_temp = round(sum(temps) / len(temps), 1)
        max_precip = round(max(precips), 1)
        max_wind = round(max(winds), 1)
        dominant = Counter(conditions).most_common(1)[0][0]

        comfort = 10
        if max_precip >= 60:
            comfort -= 4
        elif max_precip >= 30:
            comfort -= 2
        if max_wind >= 10:
            comfort -= 2
        elif max_wind >= 7:
            comfort -= 1
        if avg_temp >= 35 or avg_temp <= 5:
            comfort -= 3
        elif avg_temp >= 30 or avg_temp <= 10:
            comfort -= 1
        if "storm" in dominant or "thunder" in dominant:
            comfort -= 3

        result.append({
            "date": date,
            "day_name": data["day_name"],
            "min_temp": round(min(temps), 1),
            "max_temp": round(max(temps), 1),
            "avg_temp": avg_temp,
            "max_precipitation_probability": max_precip,
            "max_wind_speed": max_wind,
            "dominant_condition": dominant,
            "outdoor_comfort_score": max(1, comfort),
        })
    return result


def _parse_forecast(data, forecast_days=1):
    limit = min(forecast_days * 8, 40)
    forecast_items = []

    for item in data.get("list", [])[:limit]:
        main = item.get("main", {})
        weather = item.get("weather", [{}])[0]
        wind = item.get("wind", {})

        forecast_items.append(
            {
                "time": item.get("dt_txt", ""),
                "temperature": round(main.get("temp", 0), 1),
                "humidity": main.get("humidity", 0),
                "condition": weather.get("description", "unknown"),
                "wind_speed": round(wind.get("speed", 0), 1),
                "precipitation_probability": round(item.get("pop", 0) * 100, 1),
                "precipitation_mm": round(_precipitation_from_entry(item), 1),
            }
        )

    return forecast_items


def get_weather(city, country_code=None, forecast_days=1):
    location_query = _build_location_query(city, country_code)
    params = {"q": location_query, "appid": API_KEY, "units": "metric"}

    current_data, current_error = _request_openweather("weather", params)
    if current_error:
        return {
            "error": current_error,
            "city": city,
            "forecast": [],
            "forecast_summary": _empty_forecast_summary(),
        }

    forecast_data, forecast_error = _request_openweather("forecast", params)
    forecast_items = [] if forecast_error else _parse_forecast(forecast_data, forecast_days=forecast_days)
    forecast_summary = _summarize_forecast(forecast_items)
    daily_forecast = _group_forecast_by_day(forecast_items)
    if daily_forecast:
        max_score = max(d["outdoor_comfort_score"] for d in daily_forecast)
        best_candidates = [d for d in daily_forecast if d["outdoor_comfort_score"] == max_score]
        best_day = best_candidates[0] if len(best_candidates) < len(daily_forecast) else None
    else:
        best_day = None

    main = current_data.get("main", {})
    weather = current_data.get("weather", [{}])[0]
    wind = current_data.get("wind", {})

    current_precipitation = _precipitation_from_entry(current_data)
    precipitation_probability = forecast_summary["max_precipitation_probability"]

    return {
        "city": current_data.get("name", city),
        "country": current_data.get("sys", {}).get("country", country_code or ""),
        "temperature": round(main.get("temp", 0), 1),
        "feels_like": round(main.get("feels_like", 0), 1),
        "humidity": main.get("humidity", 0),
        "weather": weather.get("description", "unknown"),
        "wind_speed": round(wind.get("speed", 0), 1),
        "wind_unit": "m/s",
        "precipitation_mm": round(current_precipitation, 1),
        "precipitation_probability": precipitation_probability,
        "forecast": forecast_items,
        "forecast_summary": forecast_summary,
        "daily_forecast": daily_forecast,
        "best_day": best_day,
        "forecast_error": forecast_error,
        "source": "OpenWeather",
    }
