import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

SECRET_KEY = "energy-monitor-secret-2025"
ALGORITHM = "HS256"

# 密码规则：admin/super → bn_123456，其他 → {useraccount}123
KNOWN_PASSWORDS = {"admin": "bn_123456", "super": "bn_123456"}

def password_ok(useraccount: str, pwd: str) -> bool:
    if useraccount in KNOWN_PASSWORDS:
        return pwd == KNOWN_PASSWORDS[useraccount]
    return pwd == useraccount + "123"

def create_access_token(data: dict) -> str:
    d = data.copy()
    d["exp"] = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode(d, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try: return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError: return None
