from pydantic import BaseModel

class GoogleLoginRequest(BaseModel):
    credential: str

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    user_id: int
