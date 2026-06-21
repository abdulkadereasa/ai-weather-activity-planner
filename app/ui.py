import html
import inspect

import geonamescache
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st

from agents.activity_agent import recommend_activities
from agents.evaluator_agent import evaluate_recommendations
from agents.llm_agent import explain_and_recommend
from services.places_service import enrich_with_venues
from services.weather_service import get_weather
from utils.api_status import clear as clear_api_warnings, warnings as get_api_warnings
from utils.user_profile import parse_preferences, save_current_profile


COUNTRY_PLACEHOLDER = "Select country"
CITY_PLACEHOLDER = "Select city"


st.set_page_config(
    page_title="Weather-Based Activity Planner",
    layout="wide",
)


st.markdown(
    """
<style>
:root {
    --page: #f4f8fb;
    --panel: #ffffff;
    --panel-strong: #eef6fb;
    --ink: #172033;
    --muted: #64748b;
    --line: #d7e2ee;
    --blue: #2563eb;
    --cyan: #0891b2;
    --teal: #0f766e;
    --slate: #0f172a;
    --soft-blue: #e8f1ff;
    --soft-cyan: #e5f7fb;
    --soft-teal: #e6f6f1;
}

.stApp {
    background:
        linear-gradient(180deg, #f8fbfd, #eef5fa 46%, #f7fafc),
        var(--page);
    color: var(--ink);
}

.block-container {
    max-width: 1180px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, #ffffff, #f1f6fb);
    border-right: 1px solid var(--line);
}

[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div {
    color: var(--ink);
}

[data-testid="stSidebar"] .stButton button {
    width: 100%;
    background: linear-gradient(90deg, #2563eb, #0891b2);
    color: #ffffff;
    border: 1px solid rgba(37,99,235,0.18);
    border-radius: 8px;
    font-weight: 750;
    box-shadow: 0 10px 22px rgba(37,99,235,0.16);
}

.stSelectbox div[data-baseweb="select"],
.stTextInput input {
    background: #ffffff !important;
    border: 1px solid #d7e2ee !important;
    border-radius: 8px !important;
    color: #172033 !important;
}

.stSelectbox div[data-baseweb="select"] span,
.stTextInput input::placeholder {
    color: #64748b !important;
}

h1, h2, h3 {
    color: var(--ink);
    letter-spacing: 0;
}

.section-title {
    font-size: 12px;
    font-weight: 800;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin: 26px 0 12px;
    padding-left: 10px;
    border-left: 3px solid var(--teal);
}

.sidebar-title {
    font-size: 20px;
    font-weight: 800;
    margin: 8px 0 14px;
    color: var(--slate);
}

.brand-header {
    background:
        linear-gradient(135deg, #0f3b57, #146c83 58%, #2563eb);
    border-radius: 12px;
    color: white;
    padding: 24px 26px;
    margin-bottom: 20px;
    box-shadow: 0 18px 42px rgba(15,59,87,0.18);
}

.brand-row {
    display: flex;
    align-items: center;
    gap: 16px;
}

.brand-mark {
    width: 58px;
    height: 58px;
    border-radius: 14px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.28);
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 58px;
    padding: 6px;
}

.brand-title {
    font-size: 34px;
    font-weight: 850;
    line-height: 1.1;
}

.brand-subtitle {
    margin-top: 7px;
    color: rgba(255,255,255,0.86);
    font-size: 15px;
}

.status-strip {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-top: 18px;
}

.status-item {
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.24);
    border-radius: 8px;
    padding: 10px 12px;
}

.status-label {
    color: rgba(255,255,255,0.72);
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
}

.status-value {
    color: white;
    font-size: 15px;
    font-weight: 760;
    margin-top: 4px;
}

.metric-panel {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 14px 16px;
    min-height: 96px;
    box-shadow: 0 12px 28px rgba(15,59,87,0.08);
}

.metric-label {
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    margin-bottom: 7px;
}

.metric-value {
    color: var(--ink);
    font-size: 24px;
    font-weight: 800;
    overflow-wrap: anywhere;
}

.weather-card-teal {
    background: linear-gradient(135deg, var(--soft-teal), #ffffff);
    border-left: 4px solid var(--teal);
}

.weather-card-sky {
    background: linear-gradient(135deg, var(--soft-blue), #ffffff);
    border-left: 4px solid var(--blue);
}

.weather-card-amber {
    background: linear-gradient(135deg, var(--soft-cyan), #ffffff);
    border-left: 4px solid var(--cyan);
}

.activity-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-left: 5px solid var(--teal);
    border-radius: 8px;
    padding: 15px 16px;
    min-height: 170px;
    margin-bottom: 12px;
    box-shadow: 0 12px 28px rgba(15,59,87,0.08);
}

.activity-card:hover {
    border-color: rgba(37,99,235,0.28);
    box-shadow: 0 18px 40px rgba(37,99,235,0.12);
}

.activity-title {
    color: var(--ink);
    font-size: 18px;
    font-weight: 800;
    margin-bottom: 10px;
    overflow-wrap: anywhere;
}

.activity-meta {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 10px;
}

.tag {
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 4px 8px;
    color: #334155;
    background: #f8fbfd;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
}

.activity-reason {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.5;
    overflow-wrap: anywhere;
}

.insight-panel {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 18px;
    color: var(--ink);
    box-shadow: 0 12px 28px rgba(15,59,87,0.08);
    line-height: 1.65;
}

.small-note {
    color: var(--muted);
    font-size: 13px;
}

.audit-summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 12px;
}

.audit-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 12px;
    box-shadow: 0 12px 28px rgba(15,59,87,0.08);
}

.audit-label {
    color: var(--muted);
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
}

.audit-value {
    color: var(--ink);
    font-size: 15px;
    font-weight: 760;
    margin-top: 4px;
}

.summary-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 12px;
}

.summary-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 12px 28px rgba(15,59,87,0.08);
    min-height: 142px;
}

.summary-card-blue {
    border-left: 4px solid var(--blue);
}

.summary-card-teal {
    border-left: 4px solid var(--teal);
}

.summary-card-cyan {
    border-left: 4px solid var(--cyan);
}

.summary-label {
    color: var(--muted);
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.summary-title {
    color: var(--ink);
    font-size: 19px;
    font-weight: 800;
    margin-bottom: 8px;
    overflow-wrap: anywhere;
}

.summary-body {
    color: var(--muted);
    font-size: 14px;
    line-height: 1.55;
    overflow-wrap: anywhere;
}

.summary-wide {
    background: var(--panel);
    border: 1px solid var(--line);
    border-left: 4px solid var(--blue);
    border-radius: 8px;
    padding: 18px;
    box-shadow: 0 12px 28px rgba(15,59,87,0.08);
    line-height: 1.65;
}

.loading-card {
    display: flex;
    align-items: center;
    gap: 12px;
    background: #ffffff;
    border: 1px solid var(--line);
    border-left: 4px solid var(--blue);
    border-radius: 8px;
    padding: 14px 18px;
    box-shadow: 0 12px 28px rgba(15,59,87,0.08);
    margin: 12px 0 18px;
}

.loading-spinner {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 3px solid #d7e2ee;
    border-top-color: var(--blue);
    animation: spin 0.8s linear infinite;
    flex: 0 0 20px;
}

.loading-text {
    color: var(--ink);
    font-size: 15px;
    font-weight: 650;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.eval-panel {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 12px 28px rgba(15,59,87,0.08);
}

.eval-score-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 18px;
    flex-wrap: wrap;
}

.score-badge {
    font-size: 32px;
    font-weight: 900;
    line-height: 1;
}

.verdict-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.verdict-pass {
    background: #dcfce7;
    color: #15803d;
    border: 1px solid #bbf7d0;
}

.verdict-improve {
    background: #fef3c7;
    color: #b45309;
    border: 1px solid #fde68a;
}

.verdict-revised {
    background: #e0f2fe;
    color: #0369a1;
    border: 1px solid #bae6fd;
}

.eval-source {
    color: var(--muted);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    margin-left: auto;
}

.eval-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.eval-col-label {
    color: var(--muted);
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    margin-bottom: 10px;
}

.eval-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

.eval-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 7px 0;
    border-bottom: 1px solid var(--line);
    font-size: 14px;
    color: var(--ink);
    line-height: 1.5;
    overflow-wrap: anywhere;
}

.eval-item:last-child {
    border-bottom: none;
}

.eval-dot {
    font-weight: 900;
    font-size: 15px;
    flex: 0 0 16px;
    line-height: 1.4;
}

.eval-dot-green { color: #16a34a; }
.eval-dot-orange { color: #d97706; }

.venue-box {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--line);
}

.venue-label {
    color: var(--muted);
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    margin-bottom: 4px;
    letter-spacing: 0.04em;
}

.venue-name {
    color: var(--ink);
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 2px;
    overflow-wrap: anywhere;
}

.venue-address {
    color: var(--muted);
    font-size: 13px;
    overflow-wrap: anywhere;
}

.venue-missing {
    color: var(--muted);
    font-size: 13px;
    font-style: italic;
}

.day-row {
    display: grid;
    gap: 10px;
    margin-bottom: 4px;
}

.day-card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-top: 4px solid var(--line);
    border-radius: 8px;
    padding: 14px 10px;
    text-align: center;
    box-shadow: 0 8px 20px rgba(15,59,87,0.07);
}

.day-card-best {
    border-top-color: var(--teal);
    background: linear-gradient(180deg, var(--soft-teal), #ffffff);
}

.day-name {
    color: var(--ink);
    font-size: 15px;
    font-weight: 800;
    margin-bottom: 2px;
}

.day-date {
    color: var(--muted);
    font-size: 11px;
    font-weight: 700;
    margin-bottom: 8px;
}

.day-condition {
    color: var(--ink);
    font-size: 12px;
    margin-bottom: 6px;
    overflow-wrap: anywhere;
    min-height: 30px;
}

.day-temp {
    color: var(--ink);
    font-size: 15px;
    font-weight: 800;
    margin-bottom: 4px;
}

.day-precip {
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 8px;
}

.day-best-badge {
    display: inline-block;
    background: #dcfce7;
    color: #15803d;
    border: 1px solid #bbf7d0;
    border-radius: 12px;
    padding: 3px 9px;
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.map-note {
    color: var(--muted);
    font-size: 13px;
    margin-top: 8px;
}

/* ── Tabs ─────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #f1f6fb;
    border-radius: 10px;
    padding: 4px;
    border: 1px solid var(--line);
}

.stTabs [data-baseweb="tab"] {
    border-radius: 7px;
    padding: 8px 22px;
    font-weight: 700;
    font-size: 14px;
    color: var(--muted);
    background: transparent;
    border: none;
}

.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    color: var(--ink) !important;
    box-shadow: 0 1px 6px rgba(15,59,87,0.10);
}

.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {
    display: none;
}

/* ── Welcome screen ───────────────────────────────────── */
.welcome-panel {
    background: linear-gradient(135deg, #f0f7ff 0%, #ffffff 100%);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 36px 32px;
    margin: 8px 0 24px;
}

.welcome-title {
    font-size: 22px;
    font-weight: 900;
    color: var(--ink);
    margin-bottom: 8px;
}

.welcome-subtitle {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.6;
    margin-bottom: 28px;
    max-width: 640px;
}

.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-bottom: 28px;
}

.feature-card {
    background: #ffffff;
    border: 1px solid var(--line);
    border-top: 3px solid var(--teal);
    border-radius: 8px;
    padding: 16px;
}

.feature-card-blue { border-top-color: var(--blue); }
.feature-card-cyan { border-top-color: var(--cyan); }

.feature-title {
    color: var(--ink);
    font-size: 14px;
    font-weight: 800;
    margin-bottom: 6px;
}

.feature-desc {
    color: var(--muted);
    font-size: 13px;
    line-height: 1.55;
}

.steps-guide {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
}

.step-card {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 14px 12px;
    text-align: center;
}

.step-number {
    color: var(--blue);
    font-size: 24px;
    font-weight: 900;
    margin-bottom: 4px;
}

.step-label {
    color: var(--muted);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 2px;
}

.step-text {
    color: var(--ink);
    font-size: 13px;
    font-weight: 700;
}

.welcome-ready {
    background: var(--soft-teal);
    border: 1px solid #bbf7d0;
    border-left: 4px solid var(--teal);
    border-radius: 8px;
    padding: 22px 26px;
    margin: 8px 0;
}

.welcome-ready-title {
    color: var(--ink);
    font-size: 17px;
    font-weight: 800;
    margin-bottom: 4px;
}

.welcome-ready-dest {
    color: #0f766e;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 6px;
}

.welcome-ready-hint {
    color: var(--muted);
    font-size: 13px;
}

.api-warning-banner {
    background: #fef3c7;
    border: 1px solid #fde68a;
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 16px;
    color: #92400e;
    font-size: 14px;
    line-height: 1.6;
}

.api-warning-title {
    font-weight: 800;
    margin-bottom: 6px;
}

.api-warning-list {
    margin: 0 0 0 16px;
    padding: 0;
}

.api-warning-list li {
    margin-bottom: 2px;
}

.steps-panel {
    background: var(--panel-strong);
    border: 1px solid var(--line);
    border-left: 4px solid var(--cyan);
    border-radius: 8px;
    padding: 14px 18px;
    box-shadow: 0 12px 28px rgba(15,59,87,0.06);
}

.step-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 6px 0;
    border-bottom: 1px solid var(--line);
    font-size: 13px;
    color: var(--ink);
    line-height: 1.5;
    overflow-wrap: anywhere;
}

.step-item:last-child {
    border-bottom: none;
}

.step-num {
    color: var(--cyan);
    font-weight: 800;
    font-size: 12px;
    flex: 0 0 20px;
    padding-top: 1px;
}

</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_location_data():
    cache = geonamescache.GeonamesCache()
    countries = cache.get_countries()
    cities = cache.get_cities()
    return countries, cities


def safe_text(value):
    if value is None:
        return ""
    return html.escape(str(value))


def render_loading(target, message):
    target.markdown(
        f"""
        <div class="loading-card">
            <div class="loading-spinner"></div>
            <div class="loading-text">{safe_text(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clean_ai_text(value):
    text = str(value or "")
    for marker in ["**", "__", "`", "###", "##", "#"]:
        text = text.replace(marker, "")

    cleaned_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        stripped = stripped.lstrip("- ").strip()
        if len(stripped) > 2 and stripped[0].isdigit() and stripped[1:3] in {". ", ") "}:
            stripped = stripped[3:].strip()
        if stripped:
            cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines)


def metric_panel(label, value, variant=""):
    classes = "metric-panel"
    if variant:
        classes = f"{classes} {variant}"

    st.markdown(
        f"""
        <div class="{classes}">
            <div class="metric-label">{safe_text(label)}</div>
            <div class="metric-value">{safe_text(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def activity_card(activity):
    activity_type = activity.get("type", "relax")
    border_color = {
        "outdoor": "#0f766e",
        "indoor": "#2563eb",
        "relax": "#0891b2",
    }.get(activity_type, "#0f766e")

    venue = activity.get("venue")
    if venue:
        venue_name = safe_text(venue.get("name", ""))
        venue_address = safe_text(venue.get("address") or "Address not listed on OpenStreetMap")
        venue_html = f"""
        <div class="venue-box">
            <div class="venue-label">Suggested venue</div>
            <div class="venue-name">{venue_name}</div>
            <div class="venue-address">{venue_address}</div>
        </div>"""
    else:
        venue_html = """
        <div class="venue-box">
            <div class="venue-label">Suggested venue</div>
            <div class="venue-missing">No specific venue found — search locally for options near you.</div>
        </div>"""

    st.markdown(
        f"""
        <div class="activity-card" style="border-left-color:{border_color}">
            <div class="activity-title">{safe_text(activity.get("name"))}</div>
            <div class="activity-meta">
                <span class="tag">{safe_text(activity_type)}</span>
                <span class="tag">Score {safe_text(activity.get("score"))}/10</span>
            </div>
            <div class="activity-reason">{safe_text(activity.get("reason"))}</div>
            {venue_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def plot_forecast(forecast):
    if not forecast:
        st.info("Forecast data is not available for this location.")
        return

    times = [item["time"] for item in forecast]
    temperatures = [item["temperature"] for item in forecast]
    precipitation = [item["precipitation_probability"] for item in forecast]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=times,
            y=temperatures,
            name="Temperature C",
            mode="lines+markers",
            line={"color": "#0f766e", "width": 3},
        )
    )
    fig.add_trace(
        go.Bar(
            x=times,
            y=precipitation,
            name="Precipitation probability",
            marker={"color": "#2563eb"},
            opacity=0.35,
            yaxis="y2",
        )
    )
    fig.update_layout(
        height=340,
        margin={"l": 20, "r": 20, "t": 35, "b": 30},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font={"color": "#172033"},
        legend={"orientation": "h", "y": 1.12},
        yaxis={"title": "Temperature C", "gridcolor": "#e5edf5"},
        yaxis2={
            "title": "Precipitation %",
            "overlaying": "y",
            "side": "right",
            "range": [0, 100],
            "gridcolor": "#f8fbfd",
        },
        xaxis={"tickangle": -30},
    )
    st.plotly_chart(fig, use_container_width=True)


def render_text_panel(text):
    formatted = safe_text(text).replace("\n", "<br>")
    st.markdown(
        f'<div class="insight-panel">{formatted}</div>',
        unsafe_allow_html=True,
    )


def _section_from_text(text, label, labels):
    cleaned = clean_ai_text(text)
    lowered = cleaned.lower()
    label_key = label.lower()
    start = lowered.find(label_key)

    if start == -1:
        return ""

    start += len(label)
    end = len(cleaned)

    for other_label in labels:
        if other_label == label:
            continue
        other_start = lowered.find(other_label.lower(), start)
        if other_start != -1:
            end = min(end, other_start)

    return cleaned[start:end].strip(" :\n")


def _short_text(text, limit=520):
    cleaned = clean_ai_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0] + "..."


def _format_preferences(values, empty_text):
    if not values:
        return empty_text
    return ", ".join(values)


def render_recommendation_summary(weather, activities, likes, dislikes, final_response):
    labels = [
        "Overview:",
        "Preference fit:",
        "Weather reasoning:",
        "Top options:",
        "Final suggestion:",
    ]
    best_activity = activities[0] if activities else {}
    overview = _section_from_text(final_response, "Overview:", labels)
    preference_fit = _section_from_text(final_response, "Preference fit:", labels)
    weather_reasoning = _section_from_text(final_response, "Weather reasoning:", labels)
    top_options = _section_from_text(final_response, "Top options:", labels)
    final_suggestion = _section_from_text(final_response, "Final suggestion:", labels)

    if not overview:
        overview = _short_text(final_response, 360)
    if not preference_fit:
        preference_fit = (
            "Interests: "
            + _format_preferences(likes, "None entered")
            + ". Exclusions: "
            + _format_preferences(dislikes, "None entered")
            + "."
        )
    if not weather_reasoning:
        weather_reasoning = (
            f"Condition: {weather.get('weather')}. Temperature: {weather.get('temperature')} C. "
            f"Precipitation chance: {weather.get('precipitation_probability', 0)}%. "
            f"Wind: {weather.get('wind_speed')} {weather.get('wind_unit', 'm/s')}."
        )
    if not top_options:
        top_options = ", ".join(activity.get("name", "") for activity in activities[:3]) or "No activities available."
    if not final_suggestion:
        final_suggestion = best_activity.get("reason") or overview

    st.markdown(
        f"""
        <div class="summary-grid">
            <div class="summary-card summary-card-blue">
                <div class="summary-label">Best match</div>
                <div class="summary-title">{safe_text(best_activity.get("name", "No recommendation"))}</div>
                <div class="summary-body">{safe_text(best_activity.get("reason", "The agent did not return a top activity."))}</div>
            </div>
            <div class="summary-card summary-card-teal">
                <div class="summary-label">Preference fit</div>
                <div class="summary-title">User-aware plan</div>
                <div class="summary-body">{safe_text(preference_fit)}</div>
            </div>
            <div class="summary-card summary-card-cyan">
                <div class="summary-label">Weather reasoning</div>
                <div class="summary-title">Condition-aware choice</div>
                <div class="summary-body">{safe_text(weather_reasoning)}</div>
            </div>
        </div>
        <div class="summary-wide">
            <div class="summary-label">Final suggestion</div>
            <div class="summary-body">{safe_text(final_suggestion).replace(chr(10), "<br>")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_brand_header(
    status_left="Ready",
    status_middle="Weather tool",
    status_right="Personalization ready",
    target=None,
):
    target = target or st
    target.markdown(
        f"""
        <div class="brand-header">
            <div class="brand-row">
                <div class="brand-mark">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="36" height="36">
                        <circle cx="21" cy="19" r="7" fill="#fbbf24"/>
                        <line x1="21" y1="7" x2="21" y2="10" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
                        <line x1="21" y1="28" x2="21" y2="31" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
                        <line x1="9" y1="19" x2="12" y2="19" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
                        <line x1="30" y1="19" x2="33" y2="19" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
                        <line x1="12.9" y1="10.9" x2="15" y2="13" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
                        <line x1="27" y1="25" x2="29.1" y2="27.1" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
                        <line x1="29.1" y1="10.9" x2="27" y2="13" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
                        <line x1="15" y1="25" x2="12.9" y2="27.1" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
                        <ellipse cx="28" cy="33" rx="10" ry="6" fill="white" opacity="0.9"/>
                        <ellipse cx="20" cy="34" rx="6" ry="5" fill="white" opacity="0.9"/>
                        <ellipse cx="33" cy="34.5" rx="6" ry="5" fill="white" opacity="0.9"/>
                        <ellipse cx="26" cy="30" rx="7" ry="6" fill="white" opacity="0.9"/>
                    </svg>
                </div>
                <div>
                    <div class="brand-title">Weather-Based Activity Planner</div>
                    <div class="brand-subtitle">Weather-aware activity ideas tailored to your destination and preferences.</div>
                </div>
            </div>
            <div class="status-strip">
                <div class="status-item">
                    <div class="status-label">Planning state</div>
                    <div class="status-value">{safe_text(status_left)}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Tool capability</div>
                    <div class="status-value">{safe_text(status_middle)}</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Personalization</div>
                    <div class="status-value">{safe_text(status_right)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_plan_fit_summary(result, likes, dislikes, revision_applied):
    context = result.get("decision_context", {})
    risk_flags = context.get("risk_flags", [])
    if likes or dislikes:
        personalization = "Interests and exclusions applied"
    else:
        personalization = "Based on weather only"

    if revision_applied:
        personalization = "Plan refined for better fit"

    st.markdown(
        f"""
        <div class="audit-summary">
            <div class="audit-card">
                <div class="audit-label">Activity focus</div>
                <div class="audit-value">{safe_text(context.get("priority", "Ready"))}</div>
            </div>
            <div class="audit-card">
                <div class="audit-label">Weather risks</div>
                <div class="audit-value">{safe_text(", ".join(risk_flags) if risk_flags else "None")}</div>
            </div>
            <div class="audit-card">
                <div class="audit-label">Personalization</div>
                <div class="audit-value">{safe_text(personalization)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def evaluation_has_actionable_feedback(evaluation):
    weaknesses = evaluation.get("weaknesses", []) or []
    if not weaknesses:
        return False

    ignored_phrases = [
        "no major",
        "no weakness",
        "none",
    ]

    for weakness in weaknesses:
        cleaned = clean_ai_text(weakness).lower()
        if cleaned and not any(phrase in cleaned for phrase in ignored_phrases):
            return True

    return False


def evaluation_score(evaluation):
    try:
        return float(evaluation.get("score", 0))
    except (TypeError, ValueError):
        return 0


def render_evaluation(evaluation, revision_applied):
    score = evaluation_score(evaluation)
    verdict = evaluation.get("verdict", "pass")
    strengths = [s for s in (evaluation.get("strengths") or []) if s]
    raw_weaknesses = evaluation.get("weaknesses") or []
    weaknesses = [
        w for w in raw_weaknesses
        if w and not any(p in clean_ai_text(w).lower() for p in ["no major", "no weakness", "none"])
    ]
    source = evaluation.get("source", "evaluator")

    is_pass = verdict == "pass" or score >= 7
    verdict_class = "verdict-pass" if is_pass else "verdict-improve"
    verdict_label = "Pass" if is_pass else "Needs Improvement"
    score_color = "#16a34a" if score >= 7 else "#d97706" if score >= 5 else "#dc2626"

    revised_badge = '<span class="verdict-badge verdict-revised">Revised</span>' if revision_applied else ""

    strengths_items = "".join(
        f'<li class="eval-item"><span class="eval-dot eval-dot-green">+</span>{safe_text(s)}</li>'
        for s in (strengths or ["No notable strengths recorded."])
    )
    weakness_items = (
        "".join(
            f'<li class="eval-item"><span class="eval-dot eval-dot-orange">!</span>{safe_text(w)}</li>'
            for w in weaknesses
        )
        if weaknesses
        else '<li class="eval-item"><span class="eval-dot eval-dot-green">+</span>No significant weaknesses found.</li>'
    )

    score_row = (
        f'<span class="score-badge" style="color:{score_color}">{int(score)}/10</span>'
        f'<span class="verdict-badge {verdict_class}">{safe_text(verdict_label)}</span>'
        f'{revised_badge}'
        f'<span class="eval-source">{safe_text(source)}</span>'
    )
    columns = (
        f'<div><div class="eval-col-label">Strengths</div>'
        f'<ul class="eval-list">{strengths_items}</ul></div>'
        f'<div><div class="eval-col-label">Weaknesses</div>'
        f'<ul class="eval-list">{weakness_items}</ul></div>'
    )
    st.markdown(
        f'<div class="eval-panel">'
        f'<div class="eval-score-row">{score_row}</div>'
        f'<div class="eval-columns">{columns}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_decision_steps(steps):
    if not steps:
        return
    items_html = "".join(
        f'<div class="step-item"><span class="step-num">{i + 1}</span>{safe_text(step)}</div>'
        for i, step in enumerate(steps)
    )
    st.markdown(
        f'<div class="steps-panel">{items_html}</div>',
        unsafe_allow_html=True,
    )


def render_daily_forecast(daily_forecast, best_day):
    if not daily_forecast or len(daily_forecast) < 2:
        return
    best_date = (best_day or {}).get("date")
    cols = st.columns(len(daily_forecast))
    for i, day in enumerate(daily_forecast):
        is_best = day["date"] == best_date
        card_class = "day-card day-card-best" if is_best else "day-card"
        best_badge = '<div class="day-best-badge">Best outdoor day</div>' if is_best else ""
        date_short = day["date"][5:].replace("-", "/")
        with cols[i]:
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="day-name">{safe_text(day['day_name'][:3])}</div>
                    <div class="day-date">{date_short}</div>
                    <div class="day-condition">{safe_text(day['dominant_condition'])}</div>
                    <div class="day-temp">{day['min_temp']}° – {day['max_temp']}°C</div>
                    <div class="day-precip">{day['max_precipitation_probability']}% rain</div>
                    {best_badge}
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_venue_map(city_name, activities, city_coords):
    city_lat, city_lon = city_coords

    city_data = [{"lat": city_lat, "lon": city_lon,
                  "label": safe_text(city_name), "sublabel": "City centre", "detail": ""}]

    venue_data = [
        {
            "lat": a["venue"]["lat"],
            "lon": a["venue"]["lon"],
            "label": safe_text(a.get("name", "")),
            "sublabel": safe_text(a["venue"].get("name", "")),
            "detail": safe_text(a["venue"].get("address") or ""),
        }
        for a in activities
        if a.get("venue") and a["venue"].get("lat") and a["venue"].get("lon")
    ]

    layers = [
        pdk.Layer(
            "ScatterplotLayer",
            data=city_data,
            get_position=["lon", "lat"],
            get_color=[15, 118, 110, 230],
            get_radius=220,
            pickable=True,
        ),
    ]
    if venue_data:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=venue_data,
                get_position=["lon", "lat"],
                get_color=[37, 99, 235, 210],
                get_radius=140,
                pickable=True,
            )
        )

    all_lats = [city_lat] + [v["lat"] for v in venue_data]
    all_lons = [city_lon] + [v["lon"] for v in venue_data]
    center_lat = (max(all_lats) + min(all_lats)) / 2
    center_lon = (max(all_lons) + min(all_lons)) / 2

    view = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=12, pitch=0)

    tooltip = {
        "html": "<b>{label}</b><br/><i>{sublabel}</i><br/>{detail}",
        "style": {
            "background": "#172033",
            "color": "white",
            "fontSize": "13px",
            "padding": "8px 12px",
            "borderRadius": "6px",
        },
    }

    st.pydeck_chart(
        pdk.Deck(
            layers=layers,
            initial_view_state=view,
            map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            tooltip=tooltip,
        ),
        use_container_width=True,
    )

    note = (
        f"Showing {len(venue_data)} venue{'s' if len(venue_data) != 1 else ''} on the map. "
        "Teal dot is the city centre · Blue dots are suggested venues. Click a dot to see details."
        if venue_data
        else "No venue coordinates were available to plot. Addresses are still shown on the activity cards above."
    )
    st.markdown(f'<div class="map-note">{note}</div>', unsafe_allow_html=True)


def render_welcome(ready, city=None, country=None):
    if ready:
        st.markdown(
            f"""
            <div class="welcome-ready">
                <div class="welcome-ready-title">Ready to generate your plan</div>
                <div class="welcome-ready-dest">{safe_text(city)}, {safe_text(country)}</div>
                <div class="welcome-ready-hint">Click "Generate recommendations" in the sidebar to start.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        """
        <div class="welcome-panel">
            <div class="welcome-title">AI-Based Weather Activity Planner</div>
            <div class="welcome-subtitle">
                Get personalized activity recommendations powered by real weather forecasts,
                an autonomous AI agent loop, and live venue data from OpenStreetMap.
            </div>
            <div class="feature-grid">
                <div class="feature-card">
                    <div class="feature-title">Weather-Aware Planning</div>
                    <div class="feature-desc">
                        Fetches live forecasts and analyzes temperature, precipitation,
                        and wind to filter safe and suitable activities for your dates.
                    </div>
                </div>
                <div class="feature-card feature-card-blue">
                    <div class="feature-title">AI Agent Loop</div>
                    <div class="feature-desc">
                        An autonomous agent generates, scores, and revises activity
                        suggestions using Google Gemini 2.5 Flash with a built-in quality evaluator.
                    </div>
                </div>
                <div class="feature-card feature-card-cyan">
                    <div class="feature-title">Real Venue Suggestions</div>
                    <div class="feature-desc">
                        Finds actual nearby venues from OpenStreetMap and plots them
                        on an interactive map with name and address.
                    </div>
                </div>
            </div>
            <div class="steps-guide">
                <div class="step-card">
                    <div class="step-number">1</div>
                    <div class="step-label">Location</div>
                    <div class="step-text">Select country and city</div>
                </div>
                <div class="step-card">
                    <div class="step-number">2</div>
                    <div class="step-label">Period</div>
                    <div class="step-text">Choose planning horizon</div>
                </div>
                <div class="step-card">
                    <div class="step-number">3</div>
                    <div class="step-label">Preferences</div>
                    <div class="step-text">Enter interests and exclusions</div>
                </div>
                <div class="step-card">
                    <div class="step-number">4</div>
                    <div class="step-label">Generate</div>
                    <div class="step-text">Click the button and wait</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_api_warnings(warns):
    if not warns:
        return
    items = "".join(f"<li>{safe_text(w)}</li>" for w in warns)
    st.markdown(
        f'<div class="api-warning-banner">'
        f'<div class="api-warning-title">AI API Notice</div>'
        f'<ul class="api-warning-list">{items}</ul>'
        f'</div>',
        unsafe_allow_html=True,
    )


def call_recommend_activities(weather, city, likes=None, dislikes=None, **kwargs):
    supported_params = inspect.signature(recommend_activities).parameters
    supported_kwargs = {
        key: value for key, value in kwargs.items() if key in supported_params
    }

    return recommend_activities(
        weather,
        city,
        likes=likes,
        dislikes=dislikes,
        **supported_kwargs,
    )


countries_data, cities_data = load_location_data()
country_names = sorted([country["name"] for country in countries_data.values()])
country_code_by_name = {
    country["name"]: code for code, country in countries_data.items()
}


st.sidebar.markdown('<div class="sidebar-title">Weather Activity Setup</div>', unsafe_allow_html=True)

country = st.sidebar.selectbox(
    "Country",
    [COUNTRY_PLACEHOLDER] + country_names,
    index=0,
)
country_selected = country != COUNTRY_PLACEHOLDER
country_code = country_code_by_name.get(country)

city_names = []
if country_selected:
    city_names = sorted(
        {
            city["name"]
            for city in cities_data.values()
            if city["countrycode"] == country_code
        }
    )

city = st.sidebar.selectbox(
    "City",
    [CITY_PLACEHOLDER] + city_names,
    index=0,
    disabled=not country_selected,
)
city_selected = city != CITY_PLACEHOLDER

st.sidebar.markdown('<div class="section-title">Planning Period</div>', unsafe_allow_html=True)
_PERIOD_OPTIONS = {"Today": 1, "Next 3 days": 3, "Next 5 days": 5}
period_label = st.sidebar.selectbox(
    "When are you planning?",
    list(_PERIOD_OPTIONS.keys()),
    index=0,
)
forecast_days = _PERIOD_OPTIONS[period_label]

st.sidebar.markdown('<div class="section-title">Preferences</div>', unsafe_allow_html=True)
likes_text = st.sidebar.text_input(
    "Interests",
    placeholder="Food, beaches, museums",
)
dislikes_text = st.sidebar.text_input(
    "Exclusions",
    placeholder="Crowds, hiking, nightlife",
)

ready = country_selected and city_selected
run = st.sidebar.button("Generate recommendations", disabled=not ready)

if not ready:
    st.sidebar.markdown(
        '<div class="small-note">Choose a country and city to enable recommendation generation.</div>',
        unsafe_allow_html=True,
    )


if run and ready:
    clear_api_warnings()
    likes = parse_preferences(likes_text)
    dislikes = parse_preferences(dislikes_text)
    save_current_profile(likes, dislikes)
    location_label = f"{city}, {country}"
    header_slot = st.empty()

    render_brand_header(
        status_left="Building your plan",
        status_middle=f"OpenWeather · {period_label}",
        status_right="Preferences applied" if likes or dislikes else "Weather-based",
        target=header_slot,
    )

    loading_slot = st.empty()

    render_loading(loading_slot, f"Fetching {period_label.lower()} forecast for {location_label}...")
    weather = get_weather(city, country_code=country_code, forecast_days=forecast_days)

    if weather.get("error"):
        loading_slot.empty()
        st.error(weather["error"])
        st.stop()

    revision_applied = False

    render_loading(
        loading_slot,
        f"Analyzing weather risks and generating activity ideas for {location_label}...",
    )
    recommendation_result = call_recommend_activities(
        weather,
        city,
        likes=likes,
        dislikes=dislikes,
    )
    activities = recommendation_result["activities"]

    render_loading(
        loading_slot,
        "Checking interests and exclusions against the activity list...",
    )
    final_response = explain_and_recommend(
        weather,
        activities,
        likes=likes,
        dislikes=dislikes,
        decision_steps=recommendation_result["decision_steps"],
    )

    render_loading(
        loading_slot,
        "Reviewing recommendation quality before showing the plan...",
    )
    evaluation = evaluate_recommendations(
        weather,
        activities,
        likes=likes,
        dislikes=dislikes,
        final_response=final_response,
    )

    if evaluation_has_actionable_feedback(evaluation):
        render_loading(loading_slot, "Refining the plan using quality feedback...")
        revised_result = call_recommend_activities(
            weather,
            city,
            likes=likes,
            dislikes=dislikes,
            evaluator_feedback=evaluation.get("weaknesses", []),
            max_iterations=1,
        )
        revised_activities = revised_result["activities"]
        revised_response = explain_and_recommend(
            weather,
            revised_activities,
            likes=likes,
            dislikes=dislikes,
            decision_steps=revised_result["decision_steps"],
        )
        revised_evaluation = evaluate_recommendations(
            weather,
            revised_activities,
            likes=likes,
            dislikes=dislikes,
            final_response=revised_response,
        )

        if revised_activities and evaluation_score(revised_evaluation) >= evaluation_score(evaluation):
            recommendation_result = revised_result
            activities = revised_activities
            final_response = revised_response
            evaluation = revised_evaluation
            revision_applied = True

    render_loading(loading_slot, f"Finding local venues near {location_label}...")
    enrichment = enrich_with_venues(activities, city, country_code=weather.get("country"))
    activities = enrichment["activities"]
    city_coords = enrichment.get("city_coords")

    render_loading(loading_slot, f"Preparing the final activity plan for {location_label}...")

    summary = weather.get("forecast_summary", {})
    loading_slot.empty()

    render_brand_header(
        status_left=recommendation_result["decision_context"].get("priority", "Ready"),
        status_middle=f"{weather.get('source', 'Weather')} · {period_label}",
        status_right="Preferences applied" if likes or dislikes else "Weather-based",
        target=header_slot,
    )

    render_api_warnings(get_api_warnings())

    tab_acts, tab_weather, tab_analysis = st.tabs(
        ["Activities & Map", "Weather & Forecast", "Analysis"]
    )

    with tab_acts:
        if activities:
            cols = st.columns(2)
            for index, activity in enumerate(activities):
                with cols[index % 2]:
                    activity_card(activity)
        else:
            st.warning("No suitable activities were generated.")

        if city_coords:
            st.markdown('<div class="section-title">Venue Map</div>', unsafe_allow_html=True)
            render_venue_map(city, activities, city_coords)

    with tab_weather:
        st.markdown('<div class="section-title">Current Conditions</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_panel("City", weather.get("city"), "weather-card-sky")
        with c2:
            metric_panel("Temperature", f"{weather.get('temperature')} C", "weather-card-amber")
        with c3:
            metric_panel("Humidity", f"{weather.get('humidity')}%", "weather-card-teal")
        with c4:
            metric_panel("Wind", f"{weather.get('wind_speed')} {weather.get('wind_unit', 'm/s')}", "weather-card-sky")

        c5, c6, c7 = st.columns(3)
        with c5:
            metric_panel("Condition", weather.get("weather"))
        with c6:
            metric_panel("Precipitation chance", f"{weather.get('precipitation_probability', 0)}%")
        with c7:
            risk_flags = summary.get("risk_flags", [])
            metric_panel("Risk flags", ", ".join(risk_flags) if risk_flags else "None")

        st.markdown('<div class="section-title">Forecast</div>', unsafe_allow_html=True)
        plot_forecast(weather.get("forecast", []))

        if forecast_days > 1:
            daily_forecast = weather.get("daily_forecast", [])
            best_day = weather.get("best_day")
            if len(daily_forecast) > 1:
                st.markdown('<div class="section-title">Day-by-Day Breakdown</div>', unsafe_allow_html=True)
                render_daily_forecast(daily_forecast, best_day)
                if best_day:
                    st.markdown(
                        f'<div class="map-note">Best day for outdoor activities: '
                        f'<b>{safe_text(best_day["day_name"])}</b> — '
                        f'{best_day["avg_temp"]}°C avg, '
                        f'{best_day["max_precipitation_probability"]}% rain, '
                        f'{best_day["max_wind_speed"]} m/s wind.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="map-note">All days look similarly good for outdoor activities.</div>',
                        unsafe_allow_html=True,
                    )

    with tab_analysis:
        st.markdown('<div class="section-title">Plan Summary</div>', unsafe_allow_html=True)
        render_plan_fit_summary(recommendation_result, likes, dislikes, revision_applied)

        st.markdown('<div class="section-title">AI Recommendation</div>', unsafe_allow_html=True)
        render_recommendation_summary(weather, activities, likes, dislikes, final_response)

        st.markdown('<div class="section-title">Quality Evaluation</div>', unsafe_allow_html=True)
        render_evaluation(evaluation, revision_applied)

        if recommendation_result.get("decision_steps"):
            with st.expander("Agent decision steps", expanded=False):
                render_decision_steps(recommendation_result["decision_steps"])

else:
    if ready:
        planning_status = "Ready to generate"
    elif country_selected:
        planning_status = "Waiting for city"
    else:
        planning_status = "Waiting for location"

    render_brand_header(
        status_left=planning_status,
        status_middle=f"OpenWeather · {period_label}",
        status_right="Preferences ready",
    )
    render_welcome(
        ready,
        city=city if city_selected else None,
        country=country if country_selected else None,
    )
