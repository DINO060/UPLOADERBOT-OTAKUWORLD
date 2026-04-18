from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional

from services.supabase_client import (
    get_video_by_id, get_series_episodes, get_client, get_chapter_by_id
)
from services.telethon_client import stream_file_chunks

router = APIRouter()


# ─────────────────────────────────────────
#  VIDEOS — stream byte-range (seeking)
# ─────────────────────────────────────────

@router.get("/stream/{video_id}")
async def stream_video(video_id: str, range: Optional[str] = Header(None)):
    """
    Stream une vidéo depuis Telegram via MTProto avec support byte-range.
    Permet le seeking dans le player HTML5.
    """
    video = get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video introuvable")

    file_size = video.get("file_size", 0)
    if not file_size:
        raise HTTPException(status_code=500, detail="Taille du fichier inconnue")

    start, end = 0, file_size - 1
    if range:
        try:
            parts = range.replace("bytes=", "").split("-")
            start = int(parts[0])
            end = int(parts[1]) if parts[1] else min(start + 1_048_576, file_size - 1)
        except Exception:
            raise HTTPException(status_code=416, detail="Range invalide")

    if start > end or start >= file_size:
        raise HTTPException(status_code=416, detail="Range hors limites")

    async def generate():
        async for chunk in stream_file_chunks(
            channel_id=video["channel_id"],
            message_id=video["message_id"],
            start_byte=start,
            end_byte=end,
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        status_code=206,
        media_type="video/mp4",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Disposition": f"inline; filename=\"{video.get('file_name', 'video.mp4')}\"",
        },
    )


# ─────────────────────────────────────────
#  MANGA — download depuis Telegram
# ─────────────────────────────────────────

@router.get("/download/{chapter_id}")
async def download_chapter(chapter_id: str):
    """
    Télécharge un chapitre manga (PDF/CBZ) directement depuis Telegram.
    Le fichier n'a jamais été uploadé sur R2 — il est servi à la demande via MTProto.
    """
    chapter = get_chapter_by_id(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapitre introuvable")

    if not chapter.get("telegram_message_id") or not chapter.get("telegram_chat_id"):
        raise HTTPException(status_code=404, detail="Fichier non disponible")

    file_type = chapter.get("file_type", "pdf")
    file_name = f"{chapter['title']}_ch{chapter['chapter_number']}.{file_type}"
    file_size = chapter.get("file_size")

    mime_types = {
        "pdf": "application/pdf",
        "cbz": "application/x-cbz",
    }
    mime = mime_types.get(file_type, "application/octet-stream")

    async def generate():
        yielded = False
        try:
            async for chunk in stream_file_chunks(
                channel_id=chapter["telegram_chat_id"],
                message_id=chapter["telegram_message_id"],
            ):
                yielded = True
                yield chunk
        except Exception as e:
            print(f"[stream] generate error: {e}")
        if not yielded:
            print(f"[stream] Telethon n'a rien retourné pour chapter {chapter_id}")

    # PDF → inline pour l'iframe, CBZ → attachment pour JSZip fetch
    disposition = "inline" if file_type == "pdf" else "attachment"
    headers = {
        "Content-Disposition": f"{disposition}; filename=\"{file_name}\"",
        "Transfer-Encoding": "chunked",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }

    return StreamingResponse(
        generate(),
        status_code=200,
        media_type=mime,
        headers=headers,
    )


# ─────────────────────────────────────────
#  LISTES
# ─────────────────────────────────────────

@router.get("/videos")
async def list_series():
    """Liste toutes les séries vidéo indexées."""
    try:
        res = get_client().table("bot_series") \
            .select("id, title, type, cover_url, synopsis, mal_id") \
            .order("title") \
            .execute()
        return {"series": res.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/videos/{series_id}/episodes")
async def list_episodes(series_id: str):
    """Liste les épisodes d'une série."""
    episodes = get_series_episodes(series_id)
    return {"episodes": episodes}
