import os
from typing import Optional, AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

_telethon_client = None


async def get_telethon_client():
    """
    Retourne le client Telethon (MTProto), le crée si nécessaire.
    Nécessite API_ID, API_HASH, BOT_TOKEN dans .env
    """
    global _telethon_client

    if _telethon_client and _telethon_client.is_connected():
        return _telethon_client

    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession

        api_id   = int(os.getenv("TELEGRAM_API_ID", "0"))
        api_hash = os.getenv("TELEGRAM_API_HASH", "")
        session  = os.getenv("TELETHON_SESSION", "")

        _telethon_client = TelegramClient(
            StringSession(session) if session else "bot_session",
            api_id,
            api_hash,
        )
        await _telethon_client.start(bot_token=os.getenv("TELEGRAM_BOT_TOKEN"))
        return _telethon_client

    except ImportError:
        print("[Telethon] telethon non installé — streaming vidéo désactivé")
        return None
    except Exception as e:
        print(f"[Telethon] Erreur connexion: {e}")
        return None


async def stream_file_chunks(
    channel_id: str,
    message_id: int,
    start_byte: int = 0,
    end_byte: Optional[int] = None,
    chunk_size: int = 524288,  # 512 KB
) -> AsyncGenerator[bytes, None]:
    """
    Stream les bytes d'un fichier Telegram via MTProto.
    Supporte les byte-range requests pour le seeking vidéo.

    Args:
        channel_id:  ID ou @username du canal
        message_id:  ID du message contenant le fichier
        start_byte:  Début du range (aligné sur 4096)
        end_byte:    Fin du range (None = jusqu'à la fin)
        chunk_size:  Taille des chunks en bytes
    """
    client = await get_telethon_client()
    if client is None:
        return

    # Aligner le start sur 4096 bytes (contrainte MTProto)
    aligned_start = (start_byte // 4096) * 4096
    offset_correction = start_byte - aligned_start

    try:
        message = await client.get_messages(channel_id, ids=message_id)
        if not message or not message.media:
            print(f"[Telethon] Message {message_id} introuvable ou sans media")
            return

        document = message.media.document
        limit = None
        if end_byte is not None:
            limit = end_byte - aligned_start + 1

        first_chunk = True
        async for chunk in client.iter_download(
            document,
            offset=aligned_start,
            limit=limit,
            chunk_size=chunk_size,
            file_size=document.size,
        ):
            if first_chunk and offset_correction > 0:
                chunk = chunk[offset_correction:]
                first_chunk = False
            yield chunk

    except Exception as e:
        print(f"[Telethon] Erreur stream {channel_id}/{message_id}: {e}")


async def get_file_size(channel_id: str, message_id: int) -> Optional[int]:
    """Retourne la taille en bytes d'un fichier depuis un message Telegram."""
    client = await get_telethon_client()
    if client is None:
        return None
    try:
        message = await client.get_messages(channel_id, ids=message_id)
        if message and message.media and hasattr(message.media, "document"):
            return message.media.document.size
        return None
    except Exception as e:
        print(f"[Telethon] get_file_size: {e}")
        return None
