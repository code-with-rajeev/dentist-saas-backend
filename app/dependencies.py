# Standard library
from typing import Annotated

# Third-party
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from app.database.session import get_db

# Reusable type alias for DB session in route signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]

# HTTP Bearer scheme — extracts "Authorization: Bearer <token>" header
_bearer_scheme = HTTPBearer(auto_error=False)
BearerToken = Annotated[
    HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
]
