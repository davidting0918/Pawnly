from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2 import id_token
from google.auth.transport import requests
from pydantic import BaseModel
import os
from datetime import datetime, timedelta
from jose import jwt

from app.core.database import get_db
from app.services import user_service
from app.schemas.auth import Token, GoogleLoginRequest # Need to create this schema
from app.core.security import create_access_token

router = APIRouter()

@router.post("/google", response_model=Token)
async def login_google(request: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    try:
        # Verify Google Token
        idinfo = id_token.verify_oauth2_token(
            request.credential, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        email = idinfo['email']
        
        # Check if user exists
        user = await user_service.get_user_by_username(db, username=email)
        
        if not user:
            # Create new user
            user = await user_service.create_user(
                db, 
                username=email, 
                hashed_password="google_auth_user" # Placeholder
            )
            
        # Create JWT
        access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username,
            "user_id": user.id
        }
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google Token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
