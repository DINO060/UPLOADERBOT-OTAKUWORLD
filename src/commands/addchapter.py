from telegram import Update
from telegram.ext import ContextTypes

from models.types import UploadSession
from services.whitelist import is_authorized, get_supabase_id
from services.supabase_client import get_work_info, get_next_chapter_number
from commands.upload import sessions


async def addchapter_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /addchapter <titre>
    Ajoute un chapitre à une oeuvre existante. Saute directement à l'étape fichier.
    """
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Acces refuse.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage : /addchapter <titre exact>\n"
            "Exemple : /addchapter One Piece"
        )
        return

    title = " ".join(context.args).strip()
    supabase_id = get_supabase_id(user_id)

    work = get_work_info(title, supabase_id)
    if not work:
        await update.message.reply_text(
            f"Oeuvre *{title}* introuvable.\n"
            "Utilisez /upload pour creer une nouvelle oeuvre.",
            parse_mode="Markdown",
        )
        return

    next_num = get_next_chapter_number(title, supabase_id)

    sessions[user_id] = UploadSession(
        user_id=user_id,
        title=title,
        description=work.get("description", ""),
        cover_telegram_url=None,
        status=work.get("status", "ongoing"),
        is_add_chapter=True,
        step="file",
        chapter_number=next_num,
    )

    await update.message.reply_text(
        f"*{title}* — Chapitre {next_num}\n\n"
        "Envoyez le fichier *PDF* ou *CBZ* :",
        parse_mode="Markdown",
    )
