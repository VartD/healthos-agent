import hmac

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """Protect the private HealthOS API used by the Telegram bot.

    This is service authentication, not end-user authentication. A future
    multi-user client must add per-user sessions and authorization checks.
    """
    expected = settings.healthos_api_key.get_secret_value()
    if not api_key or not hmac.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
