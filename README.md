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

**SEN4018 Semester Project — Bahcesehir University**
**Team:** Abdulkader Al-Easa & Maeen Alganimi

**Live app:** https://huggingface.co/spaces/abdulkadereasa/ai-weather-activity-planner
**Blog post:** https://medium.com/@abdulkader.aleasa19/project-upload-1-system-definition-motivation-8f2445306b76

---

## What it does

Every weather app can tell you it is 28°C with 15% rain. Almost none tell you what to do with that information. This system closes that gap — it reads a live weather forecast, reasons about risk and comfort, and returns a ranked set of personalized activities, each tied to a real nearby venue and plotted on an interactive map.

---

## How the system thinks

The application is built as four cooperating layers that run autonomously after the user clicks Generate.

**1. Weather layer**
Fetches live data from OpenWeatherMap and reshapes it into a decision context — per-day comfort scores, risk flags (precipitation, wind, extreme temperature, storm), and best-day detection across the forecast window.

**2. Agent decision layer**
The autonomous loop in `activity_agent.py`:
- Assigns a planning priority from weather risk flags
- Calls Gemini 2.5 Flash to generate 10 candidate activities as structured JSON
- Filters by safety, score, and user dislikes
- Loops with self-feedback if fewer than 6 quality activities survive
- Falls back to rule-based suggestions if the LLM is unavailable

**3. Evaluation layer**
A second independent agent (`evaluator_agent.py`) scores the output 1–10, returns a pass / needs-improvement verdict, and lists strengths and weaknesses. If actionable weaknesses are found, the system regenerates and only accepts the revision if quality improved. A "Revised" badge appears in the UI when self-correction fires.

**4. Venue layer**
After the plan is finalized, the venue service queries OpenStreetMap:
- **Nominatim** — geocodes the city to coordinates
- **Overpass** — finds real places within 8 km (museums, restaurants, beaches, landmarks, etc.)

Every activity card shows a venue name and address. All venues are plotted on a pydeck interactive map.

---

## Agent loop at a glance

```
Assess weather risk → set priority
→ Generate activities (Gemini 2.5 Flash)
→ Filter by safety and preferences
→ Loop if set is too thin
→ Evaluate with second LLM call
→ Revise if weaknesses found (accept only if quality improved)
→ Find venues from OpenStreetMap
→ Present final plan
```

---

## Tech stack

| Component | Technology |
|---|---|
| Web interface | Streamlit |
| AI model | Google Gemini 2.5 Flash |
| Weather data | OpenWeatherMap API |
| Venue data | OpenStreetMap (Nominatim + Overpass) |
| Location lists | geonamescache |
| Map rendering | pydeck with Carto tiles |
| Charts | Plotly |
| Deployment | HuggingFace Spaces |

---

## Syllabus requirements covered

- **Autonomous decision loop** — agent sets priority, filters, loops, evaluates, and revises without user input
- **Tool usage** — OpenWeather API, OpenStreetMap APIs, Google Gemini API
- **Evaluation framework** — LLM-in-the-loop evaluator scores and triggers revision of the primary agent's output

---

## How to run locally

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

## Team

Both members worked across the full stack — agent logic, data services, and UI — and understand every layer of the system end to end.

**Abdulkader Al-Easa** — agent pipeline and autonomous decision loop, weather service and risk analysis, prompt engineering, OpenStreetMap venue service, pydeck interactive map, planning-period flow, deployment pipeline to HuggingFace

**Maeen Alganimi** — evaluator agent and self-revision loop, per-day comfort scoring and best-day detection, fallback behavior, tabbed UI layout, day-by-day forecast cards, CSS theming, cross-country testing
