import httpx
from typing import Optional
from rapidfuzz import fuzz

JIKAN_BASE = "https://api.jikan.moe/v4"


async def search_jikan(query: str) -> Optional[dict]:
    """
    Cherche un anime sur MyAnimeList via Jikan v4.
    Retourne le meilleur résultat ou None.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{JIKAN_BASE}/anime", params={
                "q": query, "limit": 5, "order_by": "score", "sort": "desc"
            })
            r.raise_for_status()
            results = r.json().get("data", [])

        if not results:
            return None

        return _best_match(query, results, key_fn=_jikan_titles)
    except Exception as e:
        print(f"[Jikan] Erreur: {e}")
        return None


async def search_tmdb(query: str, api_key: str) -> Optional[dict]:
    """
    Cherche une série/film sur TMDB.
    Retourne le meilleur résultat ou None.
    """
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.themoviedb.org/3/search/tv", params={
                "api_key": api_key, "query": query, "language": "fr-FR", "page": 1
            })
            r.raise_for_status()
            results = r.json().get("results", [])[:5]

        if not results:
            return None

        return _best_match(query, results, key_fn=_tmdb_titles)
    except Exception as e:
        print(f"[TMDB] Erreur: {e}")
        return None


def _jikan_titles(item: dict) -> list[str]:
    titles = [item.get("title", ""), item.get("title_english", "")]
    for t in item.get("titles", []):
        titles.append(t.get("title", ""))
    return [t for t in titles if t]


def _tmdb_titles(item: dict) -> list[str]:
    return [t for t in [item.get("name", ""), item.get("original_name", "")] if t]


def _best_match(query: str, results: list, key_fn, threshold: int = 60) -> Optional[dict]:
    """Retourne le résultat dont le titre ressemble le plus à la query."""
    query_clean = query.lower().strip()
    best, best_score = None, 0

    for item in results:
        for title in key_fn(item):
            score = max(
                fuzz.WRatio(query_clean, title.lower()),
                fuzz.token_set_ratio(query_clean, title.lower()),
            )
            if score > best_score:
                best, best_score = item, score

    return best if best_score >= threshold else None


def extract_jikan_info(item: dict) -> dict:
    """Extrait les champs utiles d'un résultat Jikan."""
    images = item.get("images", {}).get("jpg", {})
    return {
        "title": item.get("title_english") or item.get("title", ""),
        "synopsis": item.get("synopsis", ""),
        "cover_url": images.get("large_image_url") or images.get("image_url"),
        "mal_id": item.get("mal_id"),
        "tmdb_id": None,
    }


def extract_tmdb_info(item: dict) -> dict:
    """Extrait les champs utiles d'un résultat TMDB."""
    poster = item.get("poster_path")
    return {
        "title": item.get("name", ""),
        "synopsis": item.get("overview", ""),
        "cover_url": f"https://image.tmdb.org/t/p/w500{poster}" if poster else None,
        "mal_id": None,
        "tmdb_id": item.get("id"),
    }
