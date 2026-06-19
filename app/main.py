from services.weather_service import get_weather
from services.places_service import enrich_with_venues
from agents.activity_agent import recommend_activities
from agents.llm_agent import explain_and_recommend
from agents.evaluator_agent import evaluate_recommendations
from utils.user_profile import parse_preferences


def main():
    city = input("Enter city name: ").strip()
    country_code = input("Enter country code, or press Enter to skip: ").strip() or None
    likes_text = input("Enter interests separated by commas, or press Enter to skip: ")
    dislikes_text = input("Enter exclusions separated by commas, or press Enter to skip: ")

    likes = parse_preferences(likes_text)
    dislikes = parse_preferences(dislikes_text)

    print("\nFetching weather data...")
    weather = get_weather(city, country_code=country_code)

    if weather.get("error"):
        print(f"Error: {weather['error']}")
        return

    print("Analyzing weather and generating activities...")
    result = recommend_activities(weather, city, likes=likes, dislikes=dislikes)
    activities = result["activities"]

    print("Generating AI recommendation summary...")
    final_output = explain_and_recommend(
        weather,
        activities,
        likes=likes,
        dislikes=dislikes,
        decision_steps=result["decision_steps"],
    )

    print("Evaluating recommendation quality...")
    evaluation = evaluate_recommendations(
        weather,
        activities,
        likes=likes,
        dislikes=dislikes,
        final_response=final_output,
    )

    weaknesses = [
        w for w in (evaluation.get("weaknesses") or [])
        if w and "no major" not in w.lower() and "none" not in w.lower()
    ]
    if weaknesses and evaluation.get("score", 10) < 8:
        print("Revising recommendations based on evaluation feedback...")
        revised_result = recommend_activities(
            weather, city, likes=likes, dislikes=dislikes,
            evaluator_feedback=weaknesses, max_iterations=1,
        )
        revised_activities = revised_result["activities"]
        revised_response = explain_and_recommend(
            weather, revised_activities, likes=likes, dislikes=dislikes,
            decision_steps=revised_result["decision_steps"],
        )
        revised_eval = evaluate_recommendations(
            weather, revised_activities, likes=likes, dislikes=dislikes,
            final_response=revised_response,
        )
        if revised_activities and revised_eval.get("score", 0) >= evaluation.get("score", 0):
            result, activities, final_output, evaluation = (
                revised_result, revised_activities, revised_response, revised_eval
            )
            print("Revised plan accepted.")

    print("Finding local venues...")
    enrichment = enrich_with_venues(activities, city, country_code=weather.get("country"))
    activities = enrichment["activities"]

    print("\n--- Agent Decision Steps ---")
    for step in result["decision_steps"]:
        print(f"  {step}")

    print("\n--- Recommended Activities ---")
    for activity in activities:
        print(f"  {activity['name']} ({activity['type']}, score {activity['score']}/10)")
        print(f"    {activity['reason']}")
        venue = activity.get("venue")
        if venue:
            addr = venue.get("address") or "Address not listed"
            print(f"    Venue: {venue['name']} — {addr}")
        else:
            print(f"    Venue: No specific venue found — search locally.")

    print("\n--- AI Recommendation Summary ---")
    print(final_output)

    print(f"\n--- Evaluation ---")
    print(f"  Score  : {evaluation.get('score')}/10")
    print(f"  Verdict: {evaluation.get('verdict')}")
    print(f"  Source : {evaluation.get('source')}")
    strengths = evaluation.get("strengths") or []
    if strengths:
        print("  Strengths:")
        for s in strengths:
            print(f"    + {s}")
    filtered_weaknesses = [
        w for w in (evaluation.get("weaknesses") or [])
        if w and "no major" not in w.lower() and "none" not in w.lower()
    ]
    if filtered_weaknesses:
        print("  Weaknesses:")
        for w in filtered_weaknesses:
            print(f"    ! {w}")


if __name__ == "__main__":
    main()
