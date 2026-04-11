# Standard library
import logging

# Third-party
from fastapi import APIRouter, Cookie, Response
from fastapi.responses import JSONResponse

# Internal — dependencies
from app.constants.values import OTP_EXPIRE_MINUTES
from app.dependencies import DbSession
from app.rbac.dependencies import AuthenticatedUser

# Internal — service
from app.services.auth_service import AuthService
from app.services.otp_service import OtpService

# Internal — schemas
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    ForgotPasswordRequest,
    VerifyOtpRequest,
    ResetPasswordRequest
)
from app.schemas.common import SuccessResponse

# Internal — exceptions
from app.core.exceptions import AuthException
from app.constants.messages import REFRESH_TOKEN_MISSING, REFRESH_TOKEN_INVALID

# Constants
from app.constants.messages import OtpPurpose

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

@router.post("/forgot-password", response_model=SuccessResponse[None])
async def forgot_password(body: ForgotPasswordRequest, db: DbSession) -> JSONResponse:
    """
    Initiate password reset flow by sending an OTP to the user's email.
    Always returns success to prevent email enumeration.
    """
    if body.purpose != OtpPurpose.PASSWORD_RESET.value:
        raise AuthException(
            code=REFRESH_TOKEN_INVALID,
            message="Invalid OTP purpose.",
        )
    service = OtpService(db)
    await service.send_otp(body.email, OtpPurpose.PASSWORD_RESET)
    return JSONResponse(content={
        "success": True,
        "message": f"If email exists, an OTP has been sent",
        "data": None,
    })

@router.post("/verify-otp", response_model=SuccessResponse[str])
async def verify_otp(body: VerifyOtpRequest, db: DbSession) -> JSONResponse:
    """
    Verify the OTP provided by the user. If valid, issue a short-lived reset token for password reset.
    """
    if body.purpose == OtpPurpose.PASSWORD_RESET.value:
        service = OtpService(db)
        reset_token = await service.verify_otp_and_issue_token(body.email, OtpPurpose.PASSWORD_RESET, otp_plain=body.otp)
    elif body.purpose == OtpPurpose.REGISTER.value:
        return JSONResponse(content={
            "success": True,
            "message": "Currently we are not onboarding users via online registration. Please contact support to create an account.",
            "data": None,
        })
    else:
        raise AuthException(
            code=REFRESH_TOKEN_INVALID,
            message="Invalid OTP purpose.",
        )
    return JSONResponse(content={
        "success": True,
        "message": "OTP verified. Use the reset token to set a new password.",
        "data": reset_token,
    })

@router.post("/reset-password", response_model=SuccessResponse[None])
async def reset_password(body: ResetPasswordRequest, db: DbSession) -> JSONResponse:
    """
    Reset the user's password using the reset token obtained from OTP verification.
    """
    service = OtpService(db)
    await service.reset_password(body.reset_token, body.new_password)
    return JSONResponse(content={
        "success": True,
        "message": "Password has been reset successfully.",
        "data": None,
    })