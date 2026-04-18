import os
import sys
import asyncio
import threading
from dotenv import load_dotenv

load_dotenv()


def _check_env():
    required = ["TELEGRAM_BOT_TOKEN", "SUPABASE_URL", "SUPABASE_SERVICE_KEY",
                "R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        for k in missing:
            print(f"[ERREUR] Variable manquante dans .env : {k}")
        sys.exit(1)


def _start_api():
    """Lance le serveur FastAPI dans un thread séparé."""
    try:
        import uvicorn
        from api.server import app
        port = int(os.getenv("API_PORT", "8000"))
        print(f"[API] Serveur streaming demarrage sur http://0.0.0.0:{port}")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
    except ImportError:
        print("[API] uvicorn/fastapi non installe — serveur streaming desactive")


def main():
    _check_env()

    token = os.getenv("TELEGRAM_BOT_TOKEN")

    # Démarrer l'API dans un thread daemon
    api_thread = threading.Thread(target=_start_api, daemon=True)
    api_thread.start()

    # Démarrer le bot Telegram
    from bot import create_bot
    app = create_bot(token)
    print("[Bot] Demarrage en mode polling...")
    app.run_polling(
        allowed_updates=["message"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
