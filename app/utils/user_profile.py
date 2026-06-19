import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_FILE = os.path.join(_HERE, "..", "..", "data", "user_profile.json")


def parse_preferences(value):
    if isinstance(value, list):
        items = value
    else:
        items = re.split(r"[,;\n]+", value or "")

    cleaned = []
    seen = set()

    for item in items:
        text = str(item).strip()
        key = text.lower()

        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)

    return cleaned


def load_profile():
    if not os.path.exists(PROFILE_FILE):
        return {
            "likes": [],
            "dislikes": [],
            "preferred_activity": None
        }

    with open(PROFILE_FILE, "r") as f:
        return json.load(f)


def save_profile(profile):
    os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)

    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=4)


def save_current_profile(likes=None, dislikes=None):
    profile = {
        "likes": parse_preferences(likes),
        "dislikes": parse_preferences(dislikes),
        "preferred_activity": None,
    }

    save_profile(profile)
    return profile
