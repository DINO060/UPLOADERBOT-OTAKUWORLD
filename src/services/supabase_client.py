import os
import uuid
from typing import Optional, List
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL ou SUPABASE_SERVICE_KEY manquant dans .env")
        _client = create_client(url, key)
    return _client


# ─────────────────────────────────────────
#  MANGA / CHAPITRES  (table Comment Live)
# ─────────────────────────────────────────

def get_next_chapter_number(title: str, user_id: str) -> int:
    """Retourne le prochain numéro de chapitre pour une oeuvre donnée."""
    try:
        res = get_client().table("chapters") \
            .select("chapter_number") \
            .eq("title", title) \
            .eq("user_id", user_id) \
            .order("chapter_number", desc=True) \
            .limit(1) \
            .execute()
        if res.data:
            return res.data[0]["chapter_number"] + 1
        return 1
    except Exception as e:
        print(f"[Supabase] get_next_chapter_number: {e}")
        return 1


def get_work_info(title: str, user_id: str) -> Optional[dict]:
    """Récupère cover_url + description + status du premier chapitre d'une oeuvre."""
    try:
        res = get_client().table("chapters") \
            .select("cover_url, description, status") \
            .eq("title", title) \
            .eq("user_id", user_id) \
            .order("chapter_number", desc=False) \
            .limit(1) \
            .execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[Supabase] get_work_info: {e}")
        return None


def create_chapter(
    chapter_id: str,
    title: str,
    user_id: str,
    chapter_number: int,
    content_type: str,
    file_type: str,
    cover_url: Optional[str] = None,
    description: Optional[str] = None,
    status: str = "ongoing",
    tags: Optional[List[str]] = None,
    # Fichier stocké sur Telegram — jamais uploadé sur R2
    telegram_file_id: Optional[str] = None,
    telegram_message_id: Optional[int] = None,
    telegram_chat_id: Optional[str] = None,
    file_size: Optional[int] = None,
) -> Optional[dict]:
    """
    Insère un nouveau chapitre dans la table chapters de Comment Live.
    Le fichier (PDF/CBZ) reste sur Telegram — seuls les identifiants sont stockés.
    Seule la cover est uploadée sur R2.
    """
    try:
        row = {
            "id": chapter_id,
            "title": title,
            "user_id": user_id,
            "chapter_number": chapter_number,
            "content_type": content_type,
            "file_type": file_type,
            "cover_url": cover_url,
            "description": description or "",
            "status": status,
            "content_rating": "all",
            "telegram_file_id": telegram_file_id,
            "telegram_message_id": telegram_message_id,
            "telegram_chat_id": telegram_chat_id,
            "file_size": file_size,
        }
        res = get_client().table("chapters").insert(row).execute()
        chapter = res.data[0] if res.data else None

        if chapter and tags:
            tag_rows = [{"chapter_id": chapter_id, "tag": t} for t in tags]
            get_client().table("chapter_tags").insert(tag_rows).execute()

        return chapter
    except Exception as e:
        print(f"[Supabase] create_chapter: {e}")
        return None


def get_chapter_by_id(chapter_id: str) -> Optional[dict]:
    """Récupère un chapitre par son ID (pour le download)."""
    try:
        res = get_client().table("chapters") \
            .select("id, title, chapter_number, telegram_file_id, telegram_message_id, telegram_chat_id, file_size, file_type, cover_url") \
            .eq("id", chapter_id) \
            .limit(1) \
            .execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[Supabase] get_chapter_by_id: {e}")
        return None


def get_user_chapters(user_id: str, limit: int = 10) -> List[dict]:
    """Retourne les derniers chapitres d'un utilisateur."""
    try:
        res = get_client().table("chapters") \
            .select("title, chapter_number, created_at, content_type") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        return res.data or []
    except Exception as e:
        print(f"[Supabase] get_user_chapters: {e}")
        return []


# ─────────────────────────────────────────
#  VIDEOS — table bot_series + bot_videos
# ─────────────────────────────────────────

def upsert_series(
    title: str,
    series_type: str = "anime",
    cover_url: Optional[str] = None,
    synopsis: Optional[str] = None,
    mal_id: Optional[int] = None,
    tmdb_id: Optional[int] = None,
) -> Optional[dict]:
    """Crée ou met à jour une série dans bot_series."""
    try:
        existing = get_client().table("bot_series") \
            .select("id") \
            .eq("title", title) \
            .limit(1) \
            .execute()

        if existing.data:
            series_id = existing.data[0]["id"]
            updates = {k: v for k, v in {
                "cover_url": cover_url,
                "synopsis": synopsis,
                "mal_id": mal_id,
                "tmdb_id": tmdb_id,
            }.items() if v is not None}
            if updates:
                get_client().table("bot_series").update(updates).eq("id", series_id).execute()
            return {"id": series_id, "title": title}
        else:
            row = {
                "id": str(uuid.uuid4()),
                "title": title,
                "type": series_type,
                "cover_url": cover_url,
                "synopsis": synopsis,
                "mal_id": mal_id,
                "tmdb_id": tmdb_id,
            }
            res = get_client().table("bot_series").insert(row).execute()
            return res.data[0] if res.data else None
    except Exception as e:
        print(f"[Supabase] upsert_series: {e}")
        return None


def create_video(
    series_id: str,
    episode: int,
    season: int,
    language: str,
    file_id: str,
    message_id: int,
    channel_id: str,
    file_size: Optional[int] = None,
    file_name: Optional[str] = None,
) -> Optional[dict]:
    """Indexe un épisode vidéo Telegram dans bot_videos."""
    try:
        row = {
            "id": str(uuid.uuid4()),
            "series_id": series_id,
            "episode": episode,
            "season": season,
            "language": language,
            "file_id": file_id,
            "message_id": message_id,
            "channel_id": channel_id,
            "file_size": file_size,
            "file_name": file_name,
        }
        res = get_client().table("bot_videos").insert(row).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[Supabase] create_video: {e}")
        return None


def get_video_by_id(video_id: str) -> Optional[dict]:
    """Récupère un enregistrement vidéo par son ID (pour le streaming)."""
    try:
        res = get_client().table("bot_videos") \
            .select("*, bot_series(title)") \
            .eq("id", video_id) \
            .limit(1) \
            .execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[Supabase] get_video_by_id: {e}")
        return None


def get_series_episodes(series_id: str) -> List[dict]:
    """Retourne tous les épisodes d'une série, triés."""
    try:
        res = get_client().table("bot_videos") \
            .select("id, episode, season, language, file_name, created_at") \
            .eq("series_id", series_id) \
            .order("season", desc=False) \
            .order("episode", desc=False) \
            .execute()
        return res.data or []
    except Exception as e:
        print(f"[Supabase] get_series_episodes: {e}")
        return []
