"""Per-film rules: pick a category or sequence by the film that is about to play.

Pure functions, no database. A rule is a dict:

    {"id": 1, "name": "4K HDR night", "enabled": True, "priority": 10, "match": "all",
     "conditions": {"min_resolution": "2160p", "hdr": True, "atmos": True,
                    "genres": ["Horror"], "content_ratings": ["R", "PG-13"],
                    "title_contains": "star wars"},
     "action": {"type": "category" | "sequence", "id": 3}}

``match`` is "all" (default) or "any" of the conditions that are set. A rule with
no conditions never matches. A condition about something the media server did not
tell us counts as not met. Higher ``priority`` is tried first; the first match wins.

A film is the facts NeXroll could learn about what is about to play:

    {"title", "year", "rating_key", "genres": [], "content_rating",
     "video_resolution" ("4k", "2160p", "1080" ...), "hdr" (bool or "HDR10" ...),
     "audio_codec" ("truehd", "eac3" ...), "audio_profile" / "atmos" (optional)}
"""
from typing import Optional

from backend.media_probe import classify_resolution, resolution_height

CONDITION_KEYS = ("min_resolution", "hdr", "atmos", "genres", "content_ratings", "title_contains")
ACTION_TYPES = ("category", "sequence")
MATCH_MODES = ("all", "any")


def _words(values) -> list:
    if isinstance(values, str):
        values = values.split(",")
    return [str(v).strip().lower() for v in (values or []) if str(v).strip()]


def normalize_conditions(raw) -> dict:
    """Keep only the known conditions that are actually set."""
    raw = raw if isinstance(raw, dict) else {}
    out = {}
    if resolution_height(raw.get("min_resolution")):
        out["min_resolution"] = str(raw["min_resolution"]).strip()
    if raw.get("hdr"):
        out["hdr"] = True
    if raw.get("atmos"):
        out["atmos"] = True
    for key in ("genres", "content_ratings"):
        words = _words(raw.get(key))
        if words:
            out[key] = words
    title = str(raw.get("title_contains") or "").strip()
    if title:
        out["title_contains"] = title
    return out


def film_has_hdr(film: dict) -> Optional[bool]:
    value = film.get("hdr")
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("sdr", "none", "false", "0", "no"):
        return False
    return True


def film_has_atmos(film: dict) -> Optional[bool]:
    if film.get("atmos") is not None:
        return bool(film["atmos"])
    text = f"{film.get('audio_codec') or ''} {film.get('audio_profile') or ''}".lower()
    if not text.strip():
        return None
    return "atmos" in text


def condition_results(conditions: dict, film: dict) -> dict:
    """{condition: True | False} for every condition that is set."""
    results = {}
    if "min_resolution" in conditions:
        height = resolution_height(film.get("video_resolution"))
        results["min_resolution"] = bool(height) and height >= resolution_height(conditions["min_resolution"])
    if conditions.get("hdr"):
        results["hdr"] = film_has_hdr(film) is True
    if conditions.get("atmos"):
        results["atmos"] = film_has_atmos(film) is True
    if "genres" in conditions:
        have = set(_words(film.get("genres")))
        results["genres"] = bool(have & set(_words(conditions["genres"])))
    if "content_ratings" in conditions:
        results["content_ratings"] = str(film.get("content_rating") or "").strip().lower() in set(_words(conditions["content_ratings"]))
    if "title_contains" in conditions:
        results["title_contains"] = conditions["title_contains"].lower() in str(film.get("title") or "").lower()
    return results


def rule_matches(rule: dict, film: dict) -> bool:
    if not rule.get("enabled", True):
        return False
    results = condition_results(normalize_conditions(rule.get("conditions")), film or {})
    if not results:
        return False
    return any(results.values()) if rule.get("match") == "any" else all(results.values())


def choose_rule(rules, film: dict) -> Optional[dict]:
    """The first enabled rule that matches, highest priority first (lowest id on a tie)."""
    ordered = sorted(rules, key=lambda r: (-(r.get("priority") or 0), r.get("id") or 0))
    return next((r for r in ordered if rule_matches(r, film)), None)


def film_from_media_item(item: dict) -> dict:
    """Film facts from a Jellyfin/Emby item fetched with Fields=MediaStreams."""
    streams = [s for s in (item.get("MediaStreams") or []) if isinstance(s, dict)]
    video = next((s for s in streams if str(s.get("Type", "")).lower() == "video"), {})
    audio = [s for s in streams if str(s.get("Type", "")).lower() == "audio"]
    track = next((s for s in audio if s.get("IsDefault")), audio[0] if audio else {})
    range_type = str(video.get("VideoRangeType") or video.get("VideoRange") or "").strip()
    label = classify_resolution(video.get("Width"), video.get("Height")) or ""
    return {
        "title": item.get("Name"),
        "year": item.get("ProductionYear"),
        "genres": [g for g in (item.get("Genres") or []) if isinstance(g, str)],
        "content_rating": item.get("OfficialRating"),
        "video_resolution": label,
        "hdr": (range_type.lower() not in ("", "sdr")) if range_type else None,
        "audio_codec": track.get("Codec"),
        "audio_profile": " ".join(str(track.get(k) or "") for k in ("Profile", "DisplayTitle")).strip(),
    }
