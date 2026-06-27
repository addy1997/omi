"""JWT-based auth for the platform API."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from ..config import settings

_bearer = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class TokenData(BaseModel):
    sub: str
    role: str = "user"


def create_token(sub: str, role: str = "user") -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": sub, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return TokenData(sub=payload["sub"], role=payload.get("role", "user"))
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    api_key: str | None = Security(_api_key_header),
) -> TokenData:
    # Accept either Bearer JWT or X-API-Key header
    if creds:
        return decode_token(creds.credentials)
    if api_key:
        # Simple API key check — extend with DB lookup for production
        if api_key == settings.secret_key:
            return TokenData(sub="api-key-user", role="admin")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


# Optional — use as a dependency where auth is not required but is useful if present
async def optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    api_key: str | None = Security(_api_key_header),
) -> TokenData | None:
    try:
        return await get_current_user(creds, api_key)
    except HTTPException:
        return None
