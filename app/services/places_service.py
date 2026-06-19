import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_HEADERS = {"User-Agent": "WeatherActivityPlanner/1.0 (student-project)"}

_KEYWORD_MAP = [
    # --- Food & drink ---
    (["cafe", "coffee", "work session", "coworking"],
        [("amenity", "cafe")]),
    (["restaurant", "food", "dining", "cuisine", "dine", "eat",
      "culinary", "local food", "gastronomy", "tasting", "foodie",
      "street food", "kebab", "seafood", "meze"],
        [("amenity", "restaurant")]),
    (["bar", "pub", "club", "nightlife", "cocktail", "lounge", "rooftop bar"],
        [("amenity", "bar"), ("amenity", "pub")]),

    # --- Nature & outdoors ---
    (["beach", "seaside", "coastal", "shoreline"],
        [("natural", "beach")]),
    (["park", "garden", "nature reserve", "botanical", "forest", "woodland"],
        [("leisure", "park"), ("leisure", "garden")]),
    (["hik", "trail", "trek", "mountain", "hill climb"],
        [("leisure", "nature_reserve"), ("leisure", "park")]),
    (["swim", "pool", "water park", "lido"],
        [("leisure", "swimming_pool")]),

    # --- Shopping ---
    (["market", "bazaar", "grand bazaar", "souk", "spice",
      "covered market", "flea market", "antique"],
        [("amenity", "marketplace"), ("tourism", "attraction")]),
    (["shopping", "mall", "retail"],
        [("shop", "mall")]),

    # --- Culture / arts ---
    (["museum"],
        [("tourism", "museum")]),
    (["gallery", "art centre", "art center", "exhibition"],
        [("tourism", "gallery"), ("amenity", "arts_centre")]),
    (["theatre", "theater", "opera", "concert", "performance"],
        [("amenity", "theatre")]),
    (["cinema", "movie", "film"],
        [("amenity", "cinema")]),
    (["library", "book"],
        [("amenity", "library")]),

    # --- Sightseeing / landmarks ---
    (["mosque", "church", "temple", "cathedral", "synagogue",
      "basilica", "worship", "shrine", "sacred", "religious"],
        [("amenity", "place_of_worship")]),
    (["palace", "castle", "fort", "fortress", "citadel",
      "historical", "heritage", "monument", "ruins", "ancient",
      "archaeological", "ottoman", "roman", "byzantine",
      "medieval", "topkapi", "dolmabahce"],
        [("tourism", "attraction"), ("historic", "monument")]),
    (["hagia", "sophia", "sultanahmet", "blue mosque", "galata",
      "bosphorus", "golden horn", "taksim", "beyoglu",
      "uskudar", "kadikoy", "eminonu"],
        [("tourism", "attraction")]),
    (["landmark", "sightseeing", "tour", "touring",
      "cruise", "ferry", "boat trip", "yacht", "sailing",
      "attraction", "iconic", "famous", "scenic"],
        [("tourism", "attraction")]),
    (["cultural", "culture", "tradition", "local experience",
      "heritage walk", "old town"],
        [("tourism", "attraction"), ("amenity", "community_centre")]),
    (["viewpoint", "photo", "photography", "panoramic",
      "overlook", "observation", "rooftop view"],
        [("tourism", "viewpoint"), ("tourism", "attraction")]),
    (["walk", "route", "stroll", "city walk", "promenade",
      "waterfront", "pier", "harbour", "port", "coast"],
        [("leisure", "park"), ("tourism", "attraction")]),

    # --- Wellness & leisure ---
    (["spa", "wellness", "hamam", "hammam", "bath",
      "turkish bath", "thermal", "sauna", "massage"],
        [("leisure", "spa"), ("amenity", "spa")]),
    (["gym", "fitness", "workout", "crossfit"],
        [("leisure", "fitness_centre")]),
    (["bowling"],
        [("leisure", "bowling_alley")]),
    (["aquarium"],
        [("tourism", "aquarium")]),
    (["zoo", "wildlife", "safari", "animal park"],
        [("tourism", "zoo")]),

    # --- Accommodation ---
    (["hotel", "accommodation", "stay", "resort", "hostel"],
        [("tourism", "hotel")]),
]


def _get_osm_tags(activity_name, activity_type=None):
    name_lower = activity_name.lower()
    for keywords, tags in _KEYWORD_MAP:
        if any(kw in name_lower for kw in keywords):
            return tags
    # Fallback by activity type so we always try something sensible
    if activity_type == "outdoor":
        return [("tourism", "attraction"), ("leisure", "park")]
    if activity_type == "indoor":
        return [("tourism", "museum"), ("amenity", "arts_centre")]
    return [("tourism", "attraction")]


def _get_city_coords(city, country_code=None):
    params = {"q": city, "format": "json", "limit": 1}
    if country_code:
        params["countrycodes"] = country_code.lower()
    try:
        response = requests.get(
            NOMINATIM_URL,
            params=params,
            headers=_HEADERS,
            timeout=8,
        )
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None


def _query_overpass(lat, lon, all_tags, radius=8000, limit=100):
    conditions = "\n".join(
        item
        for k, v in all_tags
        for item in [
            f'  node["{k}"="{v}"](around:{radius},{lat:.5f},{lon:.5f});',
            f'  way["{k}"="{v}"](around:{radius},{lat:.5f},{lon:.5f});',
            f'  relation["{k}"="{v}"](around:{radius},{lat:.5f},{lon:.5f});',
        ]
    )
    query = f"[out:json][timeout:20];\n(\n{conditions}\n);\nout center {limit};"
    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers=_HEADERS,
            timeout=25,
        )
        if response.status_code != 200:
            return []
        return response.json().get("elements", [])
    except Exception:
        return []


def _format_venue(element):
    tags = element.get("tags", {})
    name = tags.get("name") or tags.get("name:en", "")
    if not name:
        return None

    parts = []
    housenumber = tags.get("addr:housenumber", "")
    street = tags.get("addr:street", "")
    suburb = tags.get("addr:suburb", "")
    city = tags.get("addr:city", "")

    if housenumber and street:
        parts.append(f"{housenumber} {street}")
    elif street:
        parts.append(street)

    if suburb and suburb.lower() != (city or "").lower():
        parts.append(suburb)
    if city:
        parts.append(city)

    # nodes have lat/lon directly; ways expose a center object
    lat = element.get("lat") or (element.get("center") or {}).get("lat")
    lon = element.get("lon") or (element.get("center") or {}).get("lon")

    return {
        "name": name,
        "address": ", ".join(parts) if parts else None,
        "lat": float(lat) if lat is not None else None,
        "lon": float(lon) if lon is not None else None,
    }


def enrich_with_venues(activities, city, country_code=None):
    empty = {"activities": activities, "city_coords": None}

    if not activities:
        return empty

    coords = _get_city_coords(city, country_code)
    if not coords:
        for a in activities:
            a["venue"] = None
        return empty

    lat, lon = coords

    activity_tags = [
        _get_osm_tags(a.get("name", ""), activity_type=a.get("type"))
        for a in activities
    ]
    all_tags = list({tag for tags in activity_tags for tag in tags})

    if not all_tags:
        for a in activities:
            a["venue"] = None
        return {"activities": activities, "city_coords": coords}

    elements = _query_overpass(lat, lon, all_tags)

    elements_by_tag = {}
    for el in elements:
        el_tags = el.get("tags", {})
        for key, value in all_tags:
            if el_tags.get(key) == value:
                elements_by_tag.setdefault((key, value), []).append(el)

    tag_use_count = {}
    for i, activity in enumerate(activities):
        tags = activity_tags[i]
        venue = None
        for tag in tags:
            candidates = elements_by_tag.get(tag, [])
            if candidates:
                idx = tag_use_count.get(tag, 0)
                venue = _format_venue(candidates[idx % len(candidates)])
                if venue:
                    tag_use_count[tag] = idx + 1
                    break
        activity["venue"] = venue

    return {"activities": activities, "city_coords": coords}
