import os
import boto3
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

R2_ACCOUNT_ID     = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID  = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME    = os.getenv("R2_BUCKET_NAME", "live-chapter")
R2_PUBLIC_URL     = os.getenv("R2_PUBLIC_URL", "").rstrip("/")


def _get_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def upload_bytes(data: bytes, path: str, content_type: str = "application/octet-stream") -> Optional[str]:
    """
    Upload des bytes vers Cloudflare R2.
    Retourne l'URL publique ou None en cas d'erreur.
    """
    try:
        client = _get_client()
        client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=path,
            Body=data,
            ContentType=content_type,
        )
        return f"{R2_PUBLIC_URL}/{path}"
    except Exception as e:
        print(f"[R2] Erreur upload '{path}': {e}")
        return None


def delete_object(path: str) -> bool:
    """Supprime un objet de R2. Retourne True si succès."""
    try:
        client = _get_client()
        client.delete_object(Bucket=R2_BUCKET_NAME, Key=path)
        return True
    except Exception as e:
        print(f"[R2] Erreur delete '{path}': {e}")
        return False


def build_path(supabase_user_id: str, chapter_id: str, filename: str) -> str:
    """
    Construit le chemin R2 standard.
    Ex: "abc-uuid/def-chapter-id/chapter.pdf"
    """
    return f"{supabase_user_id}/{chapter_id}/{filename}"
