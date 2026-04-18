from telegram.ext import Application, CommandHandler, MessageHandler, filters, AIORateLimiter

from commands.start import start_command, help_command
from commands.upload import upload_command, cancel_command, skip_command
from commands.addchapter import addchapter_command
from commands.status import status_command
from commands.video import addvideo_command, listvids_command
from handlers.message import route_text, route_photo, route_document, route_video


def create_bot(token: str) -> Application:
    """Crée et configure l'application Telegram avec tous les handlers."""
    app = Application.builder().token(token).rate_limiter(AIORateLimiter()).build()

    # Commandes manga
    app.add_handler(CommandHandler("start",      start_command))
    app.add_handler(CommandHandler("help",       help_command))
    app.add_handler(CommandHandler("upload",     upload_command))
    app.add_handler(CommandHandler("addchapter", addchapter_command))
    app.add_handler(CommandHandler("status",     status_command))
    app.add_handler(CommandHandler("cancel",     cancel_command))
    app.add_handler(CommandHandler("skip",       skip_command))

    # Commandes vidéo
    app.add_handler(CommandHandler("addvideo",  addvideo_command))
    app.add_handler(CommandHandler("listvids",  listvids_command))

    # Messages entrants
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text))
    app.add_handler(MessageHandler(filters.PHOTO,                   route_photo))
    app.add_handler(MessageHandler(filters.Document.ALL,            route_document))
    app.add_handler(MessageHandler(filters.VIDEO,                   route_video))

    return app
