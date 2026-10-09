from pydantic import BaseModel, Field
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=120, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)
class LoginRequest(RegisterRequest): pass
class UserResponse(BaseModel):
    id: str; username: str; timezone: str
class TokenResponse(BaseModel):
    access_token: str; token_type: str = "bearer"; user: UserResponse
