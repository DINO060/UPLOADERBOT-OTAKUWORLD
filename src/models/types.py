from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UploadSession:
    """Session active pendant un upload manga (PDF/CBZ)."""
    user_id: int
    step: str = "title"          # title | description | cover | file | confirm
    title: Optional[str] = None
    description: Optional[str] = None
    cover_telegram_url: Optional[str] = None   # URL temporaire Telegram de la cover
    file_telegram_id: Optional[str] = None     # file_id Telegram du PDF/CBZ
    file_telegram_message_id: Optional[int] = None  # message_id pour Telethon download
    file_telegram_chat_id: Optional[str] = None     # chat_id (= user Telegram ID) pour Telethon
    file_size: Optional[int] = None            # taille en bytes
    file_ext: Optional[str] = None             # 'pdf' ou 'cbz'
    file_name: Optional[str] = None
    chapter_number: int = 1
    status: str = "ongoing"
    is_add_chapter: bool = False


@dataclass
class VideoSession:
    """Session active pendant l'ajout manuel d'une vidéo."""
    user_id: int
    step: str = "title"          # title | episode | language | file | confirm
    title: Optional[str] = None
    episode: Optional[int] = None
    season: int = 1
    language: Optional[str] = None   # VF | VOSTFR | VO
    file_telegram_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    message_id: Optional[int] = None
    channel_id: Optional[str] = None


@dataclass
class ParsedFilename:
    """Résultat du parsing d'un nom de fichier anime."""
    title: str
    episode: Optional[int] = None
    season: Optional[int] = None
    language: Optional[str] = None   # VF, VOSTFR, VO
    username: Optional[str] = None   # @djd208 etc.
    raw: str = ""
