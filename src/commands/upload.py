import os
import uuid
import httpx
from telegram import Update
from telegram.ext import ContextTypes

from models.types import UploadSession
from services.whitelist import is_authorized, get_supabase_id
from services.r2_storage import upload_bytes, build_path
from services.supabase_client import create_chapter, get_next_chapter_number
from services.channel import announce_chapter

# Sessions actives en mémoire  {telegram_id: UploadSession}
sessions: dict[int, UploadSession] = {}


# ─────────────────────────────────────────
#  /upload
# ─────────────────────────────────────────

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("Acces refuse.")
        return

    sessions[user_id] = UploadSession(user_id=user_id)
    await update.message.reply_text(
        "*Nouvel upload*\n\nTitre de l'oeuvre ?",
        parse_mode="Markdown",
    )


# ─────────────────────────────────────────
#  /cancel
# ─────────────────────────────────────────

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id in sessions:
        del sessions[user_id]
        await update.message.reply_text("Upload annule.")
    else:
        await update.message.reply_text("Aucun upload en cours.")


# ─────────────────────────────────────────
#  /skip
# ─────────────────────────────────────────

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in sessions:
        await update.message.reply_text("Aucun upload en cours.")
        return

    session = sessions[user_id]
    if session.step == "description":
        session.step = "cover"
        await update.message.reply_text(
            "Description ignoree.\n\nEnvoyez une image de couverture (ou /skip) :",
            parse_mode="Markdown",
        )
    elif session.step == "cover":
        session.step = "file"
        await update.message.reply_text(
            "Couverture ignoree.\n\nEnvoyez le fichier *PDF* ou *CBZ* :",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("Cette etape ne peut pas etre ignoree.")


# ─────────────────────────────────────────
#  Handler messages texte
# ─────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in sessions:
        return

    session = sessions[user_id]
    text = update.message.text.strip()

    if session.step == "title":
        session.title = text
        session.step = "description"
        await update.message.reply_text(
            f"Titre : *{text}*\n\nDescription ? (ou /skip)",
            parse_mode="Markdown",
        )

    elif session.step == "description":
        session.description = text
        session.step = "cover"
        await update.message.reply_text(
            "Description enregistree.\n\nImage de couverture ? (ou /skip)",
            parse_mode="Markdown",
        )

    elif session.step == "confirm":
        answer = text.lower()
        if answer == "oui":
            await _process_upload(update, context, session)
            del sessions[user_id]
        elif answer == "non":
            del sessions[user_id]
            await update.message.reply_text("Upload annule.")
        else:
            await update.message.reply_text("Repondez oui ou non.")


# ─────────────────────────────────────────
#  Handler photos (couverture)
# ─────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in sessions:
        return

    session = sessions[user_id]
    if session.step != "cover":
        return

    photo = update.message.photo[-1]
    try:
        tg_file = await context.bot.get_file(photo.file_id)
        session.cover_telegram_url = tg_file.file_path
        session.step = "file"
        await update.message.reply_text(
            "Couverture recue !\n\nEnvoyez le fichier PDF ou CBZ :",
        )
    except Exception:
        await update.message.reply_text("Erreur image, reessayez.")


# ─────────────────────────────────────────
#  Handler documents (PDF / CBZ)
# ─────────────────────────────────────────

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in sessions:
        await update.message.reply_text("Aucun upload en cours. Utilisez /upload.")
        return

    session = sessions[user_id]
    if session.step != "file":
        await update.message.reply_text("Envoyez le fichier uniquement a l'etape prevue.")
        return

    doc = update.message.document
    if not doc:
        return

    file_name = doc.file_name or ""
    ext = os.path.splitext(file_name)[1].lower()

    if ext not in {".pdf", ".cbz"}:
        await update.message.reply_text("Format non supporte. Envoyez un PDF ou CBZ.")
        return

    supabase_id = get_supabase_id(user_id)
    next_num = get_next_chapter_number(session.title, supabase_id)

    # Stocker les identifiants Telegram — le fichier reste sur Telegram
    session.file_telegram_id = doc.file_id
    session.file_telegram_message_id = update.message.message_id
    session.file_telegram_chat_id = str(update.message.chat_id)
    session.file_size = doc.file_size
    session.file_ext = ext.lstrip(".")
    session.file_name = file_name
    session.chapter_number = next_num
    session.step = "confirm"

    size_mb = round(doc.file_size / 1024 / 1024, 1) if doc.file_size else "?"
    cover_status = "Oui" if session.cover_telegram_url else "Non"

    summary = (
        f"Resume :\n\n"
        f"Titre : {session.title}\n"
        f"Description : {session.description or 'Aucune'}\n"
        f"Couverture : {cover_status}\n"
        f"Fichier : {file_name} ({size_mb} MB)\n"
        f"Chapitre : {next_num}\n\n"
        f"Confirmer ? oui / non"
    )
    await update.message.reply_text(summary)


# ─────────────────────────────────────────
#  Traitement final — cover → R2, fichier reste sur Telegram
# ─────────────────────────────────────────

async def _process_upload(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: UploadSession,
) -> None:
    await update.message.reply_text("Traitement en cours...")

    supabase_id = get_supabase_id(session.user_id)
    chapter_id = str(uuid.uuid4())

    try:
        # 1. Cover uniquement → R2 (petite image JPEG)
        cover_r2_url = None
        if session.cover_telegram_url:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(session.cover_telegram_url)
                cover_data = resp.content
            cover_path = build_path(supabase_id, chapter_id, "cover.jpg")
            cover_r2_url = upload_bytes(cover_data, cover_path, "image/jpeg")

        # 2. Insert Supabase — fichier identifié par telegram_file_id, PAS uploadé sur R2
        chapter = create_chapter(
            chapter_id=chapter_id,
            title=session.title,
            user_id=supabase_id,
            chapter_number=session.chapter_number,
            content_type=session.file_ext,
            file_type=session.file_ext,
            cover_url=cover_r2_url,
            description=session.description,
            status=session.status,
            telegram_file_id=session.file_telegram_id,
            telegram_message_id=session.file_telegram_message_id,
            telegram_chat_id=session.file_telegram_chat_id,
            file_size=session.file_size,
        )
        if not chapter:
            raise Exception("Echec insertion Supabase")

        # 3. Annonce canaux
        result = await announce_chapter(
            bot=context.bot,
            title=session.title,
            chapter_number=session.chapter_number,
            description=session.description,
            cover_url=cover_r2_url,
        )

        # 4. Confirmation
        msg = (
            f"Chapitre publie !\n\n"
            f"{session.title} - Chapitre {session.chapter_number}\n"
            f"Format : {session.file_ext.upper()}\n"
        )
        if result["success"] > 0:
            msg += f"Annonce sur : {', '.join(result['channels'])}"

        await update.message.reply_text(msg)

    except Exception as e:
        print(f"[upload] Erreur: {e}")
        await update.message.reply_text(f"Erreur : {e}")
