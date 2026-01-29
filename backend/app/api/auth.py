from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests
from pydantic import BaseModel
import os
from datetime import datetime, timedelta
from jose import jwt

from app.core.database import get_db
from app.models.base import User

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

class GoogleLoginRequest(BaseModel):
    credential: str # The ID token from Google

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    user_id: int

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/google", response_model=Token)
async def login_google(request: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        # Verify Google Token
        idinfo = id_token.verify_oauth2_token(
            request.credential, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        email = idinfo['email']
        # Use email prefix as username if not provided (or full name)
        # Google returns 'name' and 'picture' too
        
        # Check if user exists
        result = await db.execute(select(User).where(User.username == email))
        user = result.scalars().first()
        
        if not user:
            # Create new user (Auto Registration)
            # Note: We don't have password, so we store a dummy or empty string
            # In real schema, hashed_password should be nullable if using OAuth
            # For now we put a placeholder
            new_user = User(
                username=email,
                hashed_password="google_auth_user", 
                elo_rating=1200
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            user = new_user
            
        # Create JWT
        access_token = create_access_token(data={"sub": str(user.id), "username": user.username})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "username": user.username,
            "user_id": user.id
        }
        
    except ValueError as e:
        # Invalid token
        raise HTTPException(status_code=401, detail=f"Invalid Google Token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
