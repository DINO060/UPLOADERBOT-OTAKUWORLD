import os
from typing import List, Optional
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()


def get_channels() -> List[str]:
    """Retourne la liste des canaux depuis TELEGRAM_CHANNELS dans .env."""
    raw = os.getenv("TELEGRAM_CHANNELS", "")
    if not raw:
        return []
    return [ch.strip() for ch in raw.split(",") if ch.strip()]


async def announce_chapter(
    bot: Bot,
    title: str,
    chapter_number: int,
    description: Optional[str] = None,
    cover_url: Optional[str] = None,
    site_url: Optional[str] = None,
) -> dict:
    """
    Publie une annonce de nouveau chapitre manga sur tous les canaux.
    Envoie la cover + message texte. Pas d'envoi de pages individuelles.
    """
    channels = get_channels()
    if not channels:
        return {"success": 0, "failed": 0, "channels": []}

    caption = f"*{title}* — Chapitre {chapter_number}\n"
    if description:
        caption += f"\n{description}\n"
    if site_url:
        caption += f"\n[Lire sur le site]({site_url})"

    success, failed, ok_channels = 0, 0, []

    for ch in channels:
        try:
            if cover_url:
                await bot.send_photo(
                    chat_id=ch,
                    photo=cover_url,
                    caption=caption,
                    parse_mode="Markdown",
                )
            else:
                await bot.send_message(
                    chat_id=ch,
                    text=caption,
                    parse_mode="Markdown",
                )
            success += 1
            ok_channels.append(ch)
        except Exception as e:
            failed += 1
            print(f"[channel] Erreur annonce sur {ch}: {e}")

    return {"success": success, "failed": failed, "channels": ok_channels}


async def announce_video(
    bot: Bot,
    series_title: str,
    episode: int,
    season: int,
    language: str,
    cover_url: Optional[str] = None,
    site_url: Optional[str] = None,
) -> dict:
    """
    Publie une annonce de nouvel épisode vidéo sur tous les canaux.
    """
    channels = get_channels()
    if not channels:
        return {"success": 0, "failed": 0, "channels": []}

    ep_label = f"S{season:02d}E{episode:02d}" if season > 1 else f"Episode {episode}"
    caption = f"*{series_title}* — {ep_label} [{language}]\n"
    if site_url:
        caption += f"\n[Regarder]({site_url})"

    success, failed, ok_channels = 0, 0, []

    for ch in channels:
        try:
            if cover_url:
                await bot.send_photo(
                    chat_id=ch,
                    photo=cover_url,
                    caption=caption,
                    parse_mode="Markdown",
                )
            else:
                await bot.send_message(
                    chat_id=ch,
                    text=caption,
                    parse_mode="Markdown",
                )
            success += 1
            ok_channels.append(ch)
        except Exception as e:
            failed += 1
            print(f"[channel] Erreur annonce vidéo sur {ch}: {e}")

    return {"success": success, "failed": failed, "channels": ok_channels}


async def broadcast_message(bot: Bot, message: str) -> dict:
    """Envoie un message texte simple à tous les canaux."""
    channels = get_channels()
    success, failed = 0, 0

    for ch in channels:
        try:
            await bot.send_message(chat_id=ch, text=message, parse_mode="Markdown")
            success += 1
        except Exception as e:
            failed += 1
            print(f"[channel] broadcast error {ch}: {e}")

    return {"success": success, "failed": failed}
