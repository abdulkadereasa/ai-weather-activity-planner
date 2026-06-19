import json
import os
import re

from google import genai
from dotenv import load_dotenv
from utils.api_status import record as record_api_error

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _local_evaluation(weather_data, activities, likes=None, dislikes=None, final_response=""):
    likes = likes or []
    dislikes = dislikes or []
    score = 10
    issues = []
    strengths = []

    activity_text = " ".join(
        f"{activity.get('name', '')} {activity.get('reason', '')}".lower()
        for activity in activities
    )

    for dislike in dislikes:
        if str(dislike).lower() in activity_text:
            score -= 2
            issues.append(f"Recommendation may include disliked topic: {dislike}.")

    summary = weather_data.get("forecast_summary", {})
    risk_flags = set(summary.get("risk_flags", []))
    has_high_risk = bool(
        risk_flags.intersection(
            {
                "precipitation risk",
                "high wind",
                "high temperature",
                "low temperature",
                "storm risk",
            }
        )
    )
    outdoor_count = sum(1 for activity in activities if activity.get("type") == "outdoor")

    if has_high_risk and outdoor_count > len(activities) / 2:
        score -= 2
        issues.append("Too many outdoor activities for risky weather.")
    else:
        strengths.append("Activity mix is reasonable for the detected weather risks.")

    if len(activities) < 5:
        score -= 1
        issues.append("Fewer than five activities were recommended.")
    else:
        strengths.append("The recommendation set has enough options for comparison.")

    if not final_response or len(final_response.strip()) < 80:
        score -= 1
        issues.append("Final explanation is too short or missing.")
    else:
        strengths.append("Final explanation is present.")

    score = max(1, min(score, 10))

    return {
        "score": score,
        "verdict": "pass" if score >= 7 else "needs improvement",
        "strengths": strengths or ["The system produced an evaluable recommendation set."],
        "weaknesses": issues or ["No major local evaluation issues found."],
        "source": "local fallback evaluator",
    }


def _parse_evaluation(raw_response):
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group())


def evaluate_recommendations(weather_data, activities, likes=None, dislikes=None, final_response=""):
    fallback = _local_evaluation(weather_data, activities, likes, dislikes, final_response)

    if not os.getenv("GEMINI_API_KEY"):
        return fallback

    prompt = f"""
You are an evaluator for an agentic AI weather activity recommendation system.

Weather data:
{weather_data}

User likes:
{likes or []}

User dislikes:
{dislikes or []}

Activities:
{activities}

Final response:
{final_response}

Evaluate whether the system succeeded.
Check weather fit, preference fit, safety, variety, and explanation quality.

Return only valid JSON with this format:
{{
  "score": 1-10,
  "verdict": "pass | needs improvement",
  "strengths": ["short item"],
  "weaknesses": ["short item"],
  "source": "llm evaluator"
}}
"""

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(temperature=0.0),
        )
        result = _parse_evaluation(response.text)
    except Exception as e:
        record_api_error("Quality evaluation", e)
        return fallback

    result.setdefault("score", fallback["score"])
    result.setdefault("verdict", fallback["verdict"])
    result.setdefault("strengths", fallback["strengths"])
    result.setdefault("weaknesses", fallback["weaknesses"])
    result.setdefault("source", "llm evaluator")

    return result
