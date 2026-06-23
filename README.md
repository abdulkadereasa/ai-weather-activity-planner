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

**SEN4018 — Data Science with Python | Bahcesehir University**
**Team:** Abdulkader Al-Easa & Maeen Alganimi

An end-to-end agentic AI system that analyzes real-time weather forecasts and autonomously recommends suitable activities with real venue suggestions and an interactive map.

**Live App:** https://huggingface.co/spaces/abdulkadereasa/ai-weather-activity-planner

---

## Project Overview

Users struggle with weather-dependent planning. Standard weather apps show raw data but leave the user to interpret it. This system bridges that gap — it autonomously analyzes conditions, generates ranked activity recommendations, evaluates their quality, and suggests real nearby venues, all in one pipeline.

---

## Features

- **Live weather data** — fetches current conditions and up to 5-day forecasts via OpenWeather API
- **Planning period selector** — Today, Next 3 days, or Next 5 days; forecast and recommendations adapt accordingly
- **Autonomous agent loop** — generates, filters, scores, and revises activity suggestions without user input
- **AI quality evaluation** — a second LLM call independently scores the output and triggers a revision if needed
- **Day-by-day breakdown** — visual weather cards per day with best outdoor day detection
- **Real venue suggestions** — finds actual nearby venues from OpenStreetMap (name + address)
- **Interactive map** — pydeck map with city centre and venue pins, click for details
- **Preference filtering** — respects user interests and exclusions throughout the pipeline
- **API warning banner** — clearly notifies when AI quota is reached and fallback is used

---

## Architecture

```
User Input (city, period, preferences)
        |
        v
Weather Service (OpenWeather API)
        |
        v
Activity Agent (Gemini 2.5 Flash)
  - Analyze weather conditions
  - Generate 10 candidate activities
  - Filter unsafe / disliked activities
  - Loop if not enough quality results
        |
        v
LLM Summary Agent (Gemini 2.5 Flash)
        |
        v
Evaluator Agent (Gemini 2.5 Flash)
  - Score output 1-10
  - Identify strengths / weaknesses
  - Trigger revision loop if needed
        |
        v
Venue Service (OpenStreetMap - Nominatim + Overpass)
        |
        v
Streamlit UI (tabbed: Activities & Map / Weather / Analysis)
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Web interface | Streamlit |
| AI model | Google Gemini 2.5 Flash |
| Weather data | OpenWeather API |
| Venue data | OpenStreetMap (Nominatim + Overpass) |
| Location lists | geonamescache |
| Map rendering | pydeck with Carto tiles |
| Charts | Plotly |
| Deployment | HuggingFace Spaces |

---

## Project Requirements Covered

- **Autonomous decision loop** — the agent decides priority, filters activities, loops for quality, and accepts/rejects revisions
- **Tool usage** — OpenWeather API (weather), OpenStreetMap APIs (venues), Gemini API (AI)
- **Evaluation framework** — LLM-in-the-loop evaluator scores and revises the primary agent's output

---

## How to Run Locally

```bash
pip install -r requirements.txt
streamlit run app/ui.py
```

Create a `.env` file in the project root:
```
OPENWEATHER_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

---

## Team Responsibilities

- **Abdulkader Al-Easa** — backend AI architecture, agent loop, API integration, venue service, deployment
- **Maeen Alganimi** — UI design, data presentation, testing
