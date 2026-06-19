---
title: AI Weather Activity Planner
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: 1.58.0
app_file: app/ui.py
pinned: false
---

# AI-Based Weather Activity Planner

An agentic AI system that analyzes real weather forecasts and recommends suitable activities with venue suggestions and an interactive map.

## Features
- Live weather data via OpenWeather API
- AI-generated activity recommendations using Gemini 2.5 Flash
- Real venue suggestions from OpenStreetMap
- Interactive venue map with pins
- Multi-day forecast with best-day recommendation
- Autonomous quality evaluation and revision loop

## How to Run Locally
```bash
pip install -r requirements.txt
streamlit run app/ui.py
```

## Environment Variables Required
- `OPENWEATHER_API_KEY`
- `GEMINI_API_KEY`
