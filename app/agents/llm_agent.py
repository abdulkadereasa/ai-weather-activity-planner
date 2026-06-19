import os
from google import genai
from dotenv import load_dotenv
from utils.user_profile import load_profile
from utils.api_status import record as record_api_error

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _fallback_summary(weather_data, activities, likes=None, dislikes=None, decision_steps=None):
    city = weather_data.get("city", "the selected city")
    condition = weather_data.get("weather", "current conditions")
    priority = "balanced activities"

    if decision_steps:
        priority = decision_steps[0].split("Priority:")[-1].strip(". ") if "Priority:" in decision_steps[0] else priority

    names = ", ".join(activity.get("name", "") for activity in activities[:3])
    likes_text = ", ".join(likes or []) or "no specific interests"
    dislikes_text = ", ".join(dislikes or []) or "no specific exclusions"

    return (
        f"For {city}, the system prioritized {priority} because the current condition is {condition}. "
        f"The strongest recommendations are {names}. "
        f"The plan considers interests such as {likes_text} and avoids exclusions such as {dislikes_text}. "
        "The final suggestion is to choose the highest-scoring activity first and keep the indoor or relaxed option as a backup if the forecast changes."
    )


def explain_and_recommend(weather_data, activities, likes=None, dislikes=None, decision_steps=None):
    if likes is None or dislikes is None:
        profile = load_profile()
        likes = profile.get("likes", [])
        dislikes = profile.get("dislikes", [])

    prompt = f"""
You are a personalized AI activity planner.

USER PROFILE:
Likes: {likes or []}
Dislikes: {dislikes or []}

WEATHER:
{weather_data}

ACTIVITIES:
{activities}

AGENT DECISION LOOP:
{decision_steps or []}

TASK:
1. Personalize recommendations based on user preferences
2. Avoid disliked activities
3. Rank best activities
4. Explain reasoning simply
5. Give final suggestion

Return a concise, presentation-ready recommendation summary.
Use plain text only.
Do not use markdown, asterisks, numbered lists, bullet symbols, tables, or emojis.
Use these labels exactly once:
Overview:
Preference fit:
Weather reasoning:
Top options:
Final suggestion:
"""

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
    except Exception as e:
        record_api_error("Recommendation summary", e)
        return _fallback_summary(weather_data, activities, likes, dislikes, decision_steps)

    return response.text
