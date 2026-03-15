# Standard library
import logging

# Third-party
from fastapi import APIRouter, Cookie, Response
from fastapi.responses import JSONResponse

# Internal — dependencies
from app.dependencies import DbSession
from app.rbac.dependencies import AuthenticatedUser

# Internal — service
from app.services.auth_service import AuthService

# Internal — schemas
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.schemas.common import SuccessResponse

# Internal — exceptions
from app.core.exceptions import AuthException
from app.constants.messages import REFRESH_TOKEN_MISSING, REFRESH_TOKEN_INVALID

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=SuccessResponse[RegisterResponse], status_code=201)
async def register(body: RegisterRequest, db: DbSession) -> JSONResponse:
    """
    Register a new clinic and its owner in a single atomic operation.
    Creates: user → clinic → clinic_member (owner).
    Returns an access token — user is immediately logged in.
    """
    service = AuthService(db)
    result = await service.register_clinic(body)
    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "message": "Clinic registered successfully",
            "data": result.model_dump(mode="json"),
        },
    )


@router.post("/login", response_model=SuccessResponse[TokenResponse])
async def login(body: LoginRequest, response: Response, db: DbSession) -> JSONResponse:
    """
    Authenticate and issue tokens.
    - Access token: returned in response body
    - Refresh token: stored in HttpOnly, Secure cookie
    """
    service = AuthService(db)
    access_token, refresh_token = await service.login(body.email, body.password)

    # Set refresh token cookie — HttpOnly (not accessible from JS)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,           # Set to True in production (HTTPS only)
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days in seconds
        path="/api/v1/auth/refresh",
    )

    return JSONResponse(
        content={
            "success": True,
            "message": "Login successful",
            "data": {"access_token": access_token, "token_type": "bearer"},
        },
        headers=dict(response.headers),
    )


@router.post("/refresh", response_model=SuccessResponse[TokenResponse])
async def refresh(db: DbSession, refresh_token: str | None = Cookie(default=None)) -> JSONResponse:
    """
    Issue a new access token using the HttpOnly refresh token cookie.
    """
    if not refresh_token:
        raise AuthException(
            code=REFRESH_TOKEN_MISSING,
            message="Refresh token not found. Please login again.",
        )

    service = AuthService(db)
    access_token = await service.refresh_access_token(refresh_token)

    return JSONResponse(content={
        "success": True,
        "message": "Token refreshed",
        "data": {"access_token": access_token, "token_type": "bearer"},
    })


@router.post("/logout", response_model=SuccessResponse[None])
async def logout(response: Response) -> JSONResponse:
    """
    Clear the refresh token cookie.
    Client should also discard the access token.
    """
    response.delete_cookie(key="refresh_token", path="/api/v1/auth/refresh")
    return JSONResponse(
        content={
            "success": True,
            "message": "Logged out successfully",
            "data": None,
        },
        headers=dict(response.headers),
    )


@router.get("/me", response_model=SuccessResponse[MeResponse])
async def me(current_user: AuthenticatedUser, db: DbSession) -> JSONResponse:
    """Return the full profile of the currently authenticated user."""
    service = AuthService(db)
    result = await service.get_me(current_user)
    return JSONResponse(content={
        "success": True,
        "message": "Profile retrieved",
        "data": result.model_dump(mode="json"),
    })
