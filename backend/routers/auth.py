import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from google.auth.transport import requests
from google.oauth2 import id_token
from pydantic import BaseModel

from core.security import create_access_token
from services import user_service

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


class GoogleLoginRequest(BaseModel):
    credential: str  # The ID token from Google


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    user_id: int


@router.post("/google", response_model=TokenResponse)
async def login_google(request: GoogleLoginRequest):
    try:
        # Verify Google Token
        idinfo = id_token.verify_oauth2_token(
            request.credential,
            requests.Request(),
            GOOGLE_CLIENT_ID,
        )

        email = idinfo["email"]

        # Check if user exists
        user = await user_service.get_user_by_username(email)

        if not user:
            # Auto-register
            user = await user_service.create_user(
                username=email,
                hashed_password="google_auth_user",
            )

        # Create JWT
        access_token = create_access_token(
            data={"sub": str(user["id"]), "username": user["username"]}
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user["username"],
            "user_id": user["id"],
        }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google Token: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
