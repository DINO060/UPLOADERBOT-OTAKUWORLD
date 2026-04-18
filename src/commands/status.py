from telegram import Update
from telegram.ext import ContextTypes

from services.whitelist import is_authorized, get_supabase_id
from services.supabase_client import get_user_chapters


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche les 10 derniers chapitres publiés par l'utilisateur."""
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Acces refuse.")
        return

    supabase_id = get_supabase_id(user_id)
    chapters = get_user_chapters(supabase_id, limit=10)

    if not chapters:
        await update.message.reply_text("Aucun chapitre publie pour l'instant.")
        return

    lines = ["*Vos derniers chapitres :*\n"]
    for ch in chapters:
        date = ch["created_at"][:10]
        ctype = ch["content_type"].upper()
        lines.append(f"• {ch['title']} — Ch.{ch['chapter_number']} [{ctype}] ({date})")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
