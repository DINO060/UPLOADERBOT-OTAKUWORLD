import os
import json
from typing import Optional

# Chemin vers whitelist.json (à la racine du projet)
WHITELIST_PATH = os.path.join(os.path.dirname(__file__), "../../whitelist.json")


def load_whitelist() -> dict:
    """Charge le fichier whitelist.json. Retourne {} si absent."""
    try:
        with open(WHITELIST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def is_authorized(telegram_id: int) -> bool:
    """Vérifie si un Telegram ID est autorisé à utiliser le bot."""
    wl = load_whitelist()
    return str(telegram_id) in wl


def get_supabase_id(telegram_id: int) -> Optional[str]:
    """Retourne le Supabase UUID associé à un Telegram ID, ou None."""
    wl = load_whitelist()
    return wl.get(str(telegram_id))


def add_user(telegram_id: int, supabase_uuid: str) -> None:
    """Ajoute un utilisateur dans la whitelist."""
    wl = load_whitelist()
    wl[str(telegram_id)] = supabase_uuid
    with open(WHITELIST_PATH, "w", encoding="utf-8") as f:
        json.dump(wl, f, indent=2)


def remove_user(telegram_id: int) -> bool:
    """Supprime un utilisateur de la whitelist. Retourne True si trouvé."""
    wl = load_whitelist()
    key = str(telegram_id)
    if key in wl:
        del wl[key]
        with open(WHITELIST_PATH, "w", encoding="utf-8") as f:
            json.dump(wl, f, indent=2)
        return True
    return False
