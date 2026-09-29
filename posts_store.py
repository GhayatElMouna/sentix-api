import json
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse, urlunparse

DATA_PATH = Path(__file__).parent / "data" / "posts.json"
_lock = Lock()


def normalize_url(url: str) -> str:
    text = (url or "").strip()
    if not text:
        return ""
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if not host:
        return text.rstrip("/")
    netloc = host
    if parsed.port:
        netloc = f"{host}:{parsed.port}"
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), netloc, path, "", parsed.query, ""))


def comment_key(text: str) -> str:
    return " ".join(text.strip().casefold().split())


def _empty_post(url: str) -> dict:
    return {
        "url": url,
        "positiveCount": 0,
        "negativeCount": 0,
        "neutralCount": 0,
        "total": 0,
        "comments": [],
    }


def _load() -> dict:
    if not DATA_PATH.exists():
        return {}
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save(store: dict) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = DATA_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_PATH)


def get_post(url: str) -> dict:
    key = normalize_url(url)
    with _lock:
        store = _load()
        post = store.get(key)
        if not post:
            empty = _empty_post(key)
            empty["exists"] = False
            return empty
        return {**post, "exists": True}


def find_comment(url: str, text: str) -> dict | None:
    key = normalize_url(url)
    fingerprint = comment_key(text)
    with _lock:
        post = _load().get(key)
        if not post:
            return None
        for item in post["comments"]:
            if item.get("key") == fingerprint:
                return {**item, "post": {**post, "exists": True}}
    return None


def record_analysis(url: str, result: dict) -> dict:
    key = normalize_url(url)
    fingerprint = comment_key(result["text"])
    with _lock:
        store = _load()
        post = store.get(key) or _empty_post(key)
        for item in post["comments"]:
            if item.get("key") == fingerprint:
                return {
                    "duplicate": True,
                    "result": item,
                    "post": {**post, "exists": True},
                }

        entry = {
            "key": fingerprint,
            "text": result["text"],
            "sentiment": result["sentiment"],
            "confidence": result["confidence"],
            "star_rating": result["star_rating"],
        }
        post["comments"].append(entry)
        post["total"] += 1
        if result["sentiment"] == "positive":
            post["positiveCount"] += 1
        elif result["sentiment"] == "negative":
            post["negativeCount"] += 1
        else:
            post["neutralCount"] += 1

        store[key] = post
        _save(store)
        return {
            "duplicate": False,
            "result": entry,
            "post": {**post, "exists": True},
        }
