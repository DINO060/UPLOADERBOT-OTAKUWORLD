from telegram import Update
from telegram.ext import ContextTypes

from commands.upload import handle_text, handle_photo, handle_document
from commands.video import handle_video_text, handle_video_file


async def route_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route les messages texte vers le bon handler (manga ou vidéo)."""
    # Essayer d'abord le flow vidéo
    if await handle_video_text(update, context):
        return
    # Sinon flow manga
    await handle_text(update, context)


async def route_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route les photos (couvertures manga)."""
    await handle_photo(update, context)


async def route_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route les documents (PDF/CBZ manga ou vidéo)."""
    # Essayer d'abord si c'est une vidéo
    if await handle_video_file(update, context):
        return
    # Sinon document manga
    await handle_document(update, context)


async def route_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route les fichiers vidéo natifs Telegram."""
    await handle_video_file(update, context)
