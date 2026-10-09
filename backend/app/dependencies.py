from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .core.config import get_settings
from .core.database import get_db
from .core.security import read_access_token
from .models import User
bearer = HTTPBearer(auto_error=False)
def current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录凭证缺失")
    user_id = read_access_token(credentials.credentials, get_settings().jwt_secret)
    user = db.get(User, user_id) if user_id else None
    if not user: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录凭证无效或已过期")
    return user
