from telegram import Update
from telegram.ext import ContextTypes
from services.whitelist import is_authorized


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche le message de bienvenue."""
    user = update.effective_user
    authorized = is_authorized(user.id)

    if not authorized:
        await update.message.reply_text(
            "Bonjour ! Ce bot est réservé aux uploadeurs autorisés.\n"
            "Contactez l'administrateur pour obtenir l'accès."
        )
        return

    msg = (
        f"Bonjour *{user.first_name}* !\n\n"
        "*Commandes manga (PDF/CBZ):*\n"
        "/upload — Nouvel upload\n"
        "/addchapter — Ajouter un chapitre à une oeuvre existante\n"
        "/status — Voir vos derniers chapitres\n"
        "/cancel — Annuler l'upload en cours\n"
        "/skip — Passer une étape optionnelle\n\n"
        "*Commandes vidéo (anime):*\n"
        "/addvideo — Indexer une vidéo manuellement\n"
        "/listvids — Lister les épisodes d'une série\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche le guide d'utilisation."""
    msg = (
        "*Guide complet*\n\n"
        "*Upload manga:*\n"
        "1. /upload → entre le titre\n"
        "2. Entre la description (ou /skip)\n"
        "3. Envoie une image cover (ou /skip)\n"
        "4. Envoie le fichier PDF ou CBZ\n"
        "5. Confirme avec *oui* ou *non*\n\n"
        "*Ajouter un chapitre:*\n"
        "/addchapter <titre exact> → envoie le fichier directement\n\n"
        "*Formats supportés:*\n"
        "PDF, CBZ\n\n"
        "*Vidéos anime:*\n"
        "/addvideo → follow les étapes\n"
        "/listvids <titre> → liste les épisodes\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
