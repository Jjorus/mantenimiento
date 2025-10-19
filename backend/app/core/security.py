from passlib.hash import argon2
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings

pwd_hasher = argon2.using(type="ID", time_cost=3, memory_cost=64*1024, parallelism=2)
def hash_password(p: str) -> str: return pwd_hasher.hash(p)
def verify_password(p: str, h: str) -> bool: return pwd_hasher.verify(p, h)

def _now(): return datetime.now(timezone.utc)

def make_access_token(sub: str, role: str):
    exp = _now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"iss":settings.ISSUER,"aud":settings.AUDIENCE,"sub":sub,"role":role,"exp":exp}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
