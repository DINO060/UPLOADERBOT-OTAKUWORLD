import os
from telegram import Update
from telegram.ext import ContextTypes

from models.types import VideoSession
from services.whitelist import is_authorized, get_supabase_id
from services.supabase_client import upsert_series, create_video, get_series_episodes
from services.filename_parser import parse_filename
from services.metadata import search_jikan, extract_jikan_info
from services.channel import announce_video

# Sessions vidéo actives  {telegram_id: VideoSession}
video_sessions: dict[int, VideoSession] = {}


async def addvideo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /addvideo
    Démarre l'indexation manuelle d'une vidéo.
    L'utilisateur doit forwarder (ou envoyer) la vidéo au bot ensuite.
    """
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("Acces refuse.")
        return

    video_sessions[user_id] = VideoSession(user_id=user_id)
    await update.message.reply_text(
        "*Nouvel episode video*\n\nTitre de la serie ?",
        parse_mode="Markdown",
    )


async def listvids_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /listvids <titre>
    Liste les épisodes indexés d'une série.
    """
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        await update.message.reply_text("Acces refuse.")
        return

    if not context.args:
        await update.message.reply_text("Usage : /listvids <titre>")
        return

    title = " ".join(context.args)
    from services.supabase_client import get_client
    try:
        res = get_client().table("bot_series").select("id, title") \
            .ilike("title", f"%{title}%").limit(1).execute()
        if not res.data:
            await update.message.reply_text(f"Serie *{title}* introuvable.", parse_mode="Markdown")
            return

        series = res.data[0]
        episodes = get_series_episodes(series["id"])

        if not episodes:
            await update.message.reply_text("Aucun episode indexe pour cette serie.")
            return

        lines = [f"*{series['title']}* — {len(episodes)} episodes\n"]
        for ep in episodes:
            lang = ep.get("language", "")
            s = ep.get("season", 1)
            e = ep.get("episode", "?")
            label = f"S{s:02d}E{e:02d}" if s > 1 else f"EP{e:02d}"
            lines.append(f"• {label} [{lang}]")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as ex:
        await update.message.reply_text(f"Erreur : {ex}")


async def handle_video_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Gère les textes dans le flow video_sessions.
    Retourne True si le message a été traité, False sinon.
    """
    user_id = update.effective_user.id
    if user_id not in video_sessions:
        return False

    session = video_sessions[user_id]
    text = update.message.text.strip()

    if session.step == "title":
        session.title = text
        session.step = "episode"
        await update.message.reply_text(
            f"Serie : *{text}*\n\nNumero d'episode ?",
            parse_mode="Markdown",
        )

    elif session.step == "episode":
        if not text.isdigit():
            await update.message.reply_text("Entrez un numero valide.")
            return True
        session.episode = int(text)
        session.step = "language"
        await update.message.reply_text(
            "Langue ? (VF / VOSTFR / VO)",
        )

    elif session.step == "language":
        lang = text.upper()
        if lang not in {"VF", "VOSTFR", "VO", "VOSTA"}:
            await update.message.reply_text("Langue invalide. Entrez VF, VOSTFR ou VO.")
            return True
        session.language = lang
        session.step = "file"
        await update.message.reply_text(
            "Envoyez maintenant la video (ou forwardez-la depuis le canal).",
        )

    elif session.step == "confirm":
        answer = text.lower()
        if answer == "oui":
            await _process_video(update, context, session)
            del video_sessions[user_id]
        elif answer == "non":
            del video_sessions[user_id]
            await update.message.reply_text("Annule.")
        else:
            await update.message.reply_text("Repondez *oui* ou *non*.", parse_mode="Markdown")

    return True


async def handle_video_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Gère la réception d'un fichier vidéo dans le flow video_sessions.
    Retourne True si traité.
    """
    user_id = update.effective_user.id
    if user_id not in video_sessions:
        return False

    session = video_sessions[user_id]
    if session.step != "file":
        return False

    video = update.message.video or update.message.document
    if not video:
        return False

    file_name = getattr(video, "file_name", None) or ""
    # Si les infos ne sont pas encore renseignées, essayer de les parser depuis le nom
    if not session.title or not session.episode:
        parsed = parse_filename(file_name)
        if not session.title and parsed.title:
            session.title = parsed.title
        if not session.episode and parsed.episode:
            session.episode = parsed.episode
        if not session.language and parsed.language:
            session.language = parsed.language

    session.file_telegram_id = video.file_id
    session.file_name = file_name
    session.file_size = getattr(video, "file_size", None)

    # Récupérer le message_id et channel_id pour le streaming
    fwd = update.message.forward_origin
    if fwd and hasattr(fwd, "chat"):
        session.channel_id = str(fwd.chat.id)
        session.message_id = fwd.message_id
    else:
        session.channel_id = str(update.message.chat_id)
        session.message_id = update.message.message_id

    session.step = "confirm"
    size_mb = round(session.file_size / 1024 / 1024, 1) if session.file_size else "?"

    # Pas de parse_mode ici — le nom de fichier peut contenir des caractères spéciaux
    summary = (
        f"Resume :\n\n"
        f"Serie : {session.title}\n"
        f"Episode : {session.episode}\n"
        f"Langue : {session.language or 'Non definie'}\n"
        f"Fichier : {file_name or 'video'}\n"
        f"Taille : {size_mb} MB\n\n"
        f"Confirmer ? oui / non"
    )
    await update.message.reply_text(summary)
    return True


async def _process_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: VideoSession,
) -> None:
    """Indexe la vidéo dans Supabase et annonce sur les canaux."""
    await update.message.reply_text("Indexation en cours...")

    try:
        # 1. Chercher metadata sur Jikan
        meta = None
        jikan_result = await search_jikan(session.title)
        if jikan_result:
            meta = extract_jikan_info(jikan_result)

        # 2. Upsert série
        series = upsert_series(
            title=session.title,
            series_type="anime",
            cover_url=meta.get("cover_url") if meta else None,
            synopsis=meta.get("synopsis") if meta else None,
            mal_id=meta.get("mal_id") if meta else None,
        )
        if not series:
            raise Exception("Echec creation serie")

        # 3. Indexer la vidéo
        video = create_video(
            series_id=series["id"],
            episode=session.episode,
            season=session.season,
            language=session.language or "VF",
            file_id=session.file_telegram_id,
            message_id=session.message_id,
            channel_id=session.channel_id,
            file_size=session.file_size,
            file_name=session.file_name,
        )
        if not video:
            raise Exception("Echec insertion video")

        # 4. Annonce canaux
        cover = meta.get("cover_url") if meta else None
        await announce_video(
            bot=context.bot,
            series_title=session.title,
            episode=session.episode,
            season=session.season,
            language=session.language or "VF",
            cover_url=cover,
        )

        await update.message.reply_text(
            f"{session.title} EP{session.episode} indexe avec succes !"
        )

    except Exception as e:
        print(f"[video] Erreur: {e}")
        await update.message.reply_text(f"Erreur : {e}")
