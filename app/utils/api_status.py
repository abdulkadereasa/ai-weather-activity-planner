_warnings = []


def record(source, error):
    name = type(error).__name__
    text = str(error).lower()

    auth_names = {"Unauthenticated", "PermissionDenied", "Authentication", "Unauthorized"}
    rate_names = {"ResourceExhausted", "RateLimit"}

    if any(n in name for n in auth_names) or "401" in text or "403" in text or "api key" in text or "api_key" in text:
        msg = (
            f"{source}: Invalid API key — check your GEMINI_API_KEY in the .env file."
        )
    elif any(n in name for n in rate_names) or "429" in text or "quota" in text or "resource_exhausted" in text:
        msg = (
            f"{source}: Daily quota reached — check remaining quota at "
            "aistudio.google.com (Rate Limit page). Resets at midnight Pacific Time. "
            "Results below are from the built-in fallback."
        )
    elif "Connection" in name or "Timeout" in name:
        msg = f"{source}: Could not reach the AI API — check your internet connection."
    else:
        msg = f"{source}: AI call failed ({name}) — results shown are from the built-in fallback."
    _warnings.append(msg)


def warnings():
    return list(_warnings)


def clear():
    _warnings.clear()
