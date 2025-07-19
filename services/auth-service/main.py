"""
Authentication Service for AI Planner
Provides JWT token-based authentication for microservices
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import bcrypt
import redis
import json
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = "ai-planner-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Redis for session management
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

security = HTTPBearer()

class UserCredentials(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class UserInfo(BaseModel):
    username: str
    email: Optional[str] = None
    roles: list = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize demo users
    demo_users = {
        "admin": {
            "username": "admin",
            "email": "admin@ai-planner.com",
            "password_hash": bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            "roles": ["admin", "user"]
        },
        "user": {
            "username": "user",
            "email": "user@ai-planner.com", 
            "password_hash": bcrypt.hashpw("user123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            "roles": ["user"]
        }
    }
    
    # Store demo users in Redis
    for username, user_data in demo_users.items():
        redis_client.hset(f"user:{username}", mapping=user_data)
    
    logger.info("Authentication service initialized with demo users")
    yield
    # Shutdown
    logger.info("Authentication service shutting down")

app = FastAPI(
    title="AI Planner Authentication Service",
    description="JWT token-based authentication for AI Planner microservices",
    version="1.0.0",
    lifespan=lifespan
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_user(username: str) -> Optional[Dict[str, Any]]:
    """Get user from Redis"""
    user_data = redis_client.hgetall(f"user:{username}")
    return user_data if user_data else None

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user credentials"""
    user = get_user(username)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if token is blacklisted
        if redis_client.get(f"blacklist:{credentials.credentials}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = get_user(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "auth-service", "timestamp": datetime.utcnow()}

@app.post("/auth/login", response_model=Token)
async def login(credentials: UserCredentials):
    """Authenticate user and return access token"""
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "roles": user.get("roles", [])},
        expires_delta=access_token_expires
    )
    
    # Store session info
    session_data = {
        "username": user["username"],
        "login_time": datetime.utcnow().isoformat(),
        "roles": user.get("roles", [])
    }
    redis_client.setex(f"session:{access_token}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, json.dumps(session_data))
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@app.post("/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout user and blacklist token"""
    # Add token to blacklist
    redis_client.setex(f"blacklist:{credentials.credentials}", ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
    
    # Remove session
    redis_client.delete(f"session:{credentials.credentials}")
    
    return {"message": "Successfully logged out"}

@app.get("/auth/me", response_model=UserInfo)
async def get_current_user(current_user: Dict[str, Any] = Depends(verify_token)):
    """Get current user information"""
    return UserInfo(
        username=current_user["username"],
        email=current_user.get("email"),
        roles=current_user.get("roles", [])
    )

@app.post("/auth/verify")
async def verify_user_token(current_user: Dict[str, Any] = Depends(verify_token)):
    """Verify token validity"""
    return {
        "valid": True,
        "username": current_user["username"],
        "roles": current_user.get("roles", [])
    }

@app.get("/auth/sessions")
async def active_sessions(current_user: Dict[str, Any] = Depends(verify_token)):
    """Get active sessions (admin only)"""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    sessions = []
    for key in redis_client.scan_iter(match="session:*"):
        session_data = redis_client.get(key)
        if session_data:
            sessions.append(json.loads(session_data))
    
    return {"active_sessions": len(sessions), "sessions": sessions}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
