from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import bcrypt

from app.db.database import get_db
from app.models.models import User
from app.api.deps import get_current_user

router = APIRouter()

class UpgradeRequest(BaseModel):
    premium_key: str

class UpdateProfileRequest(BaseModel):
    name: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.get("/me")
async def get_profile(current_user: User = Depends(get_current_user)):
    """
    Returns the currently logged-in user's profile details.
    """
    return {
        "name": current_user.name, 
        "email": current_user.email, 
        "is_premium": current_user.is_premium
    }

@router.put("/update")
async def update_profile(
    request: UpdateProfileRequest, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates the current user's display name.
    """
    current_user.name = request.name
    await db.commit()
    return {"message": "Profile updated successfully"}

@router.post("/password")
async def change_password(
    request: ChangePasswordRequest, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Securely changes the current user's password using bcrypt validation.
    """
    if not bcrypt.checkpw(request.old_password.encode('utf-8'), current_user.hashed_password.encode('utf-8')):
        raise HTTPException(status_code=400, detail="Invalid old password")
    
    hashed = bcrypt.hashpw(request.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    current_user.hashed_password = hashed
    await db.commit()
    return {"message": "Password changed successfully"}

@router.post("/upgrade")
async def upgrade_to_premium(
    request: UpgradeRequest, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upgrades the current user to Premium based on a valid key.
    """
    key_found = False
    try:
        with open("premium_key.txt", "r") as f:
            if request.premium_key in [line.strip() for line in f.readlines()]:
                key_found = True
    except FileNotFoundError:
        pass
        
    if not key_found:
        raise HTTPException(status_code=400, detail="Invalid premium key")
        
    if current_user.is_premium:
        return {"message": "Already premium."}
        
    current_user.is_premium = True
    await db.commit()
    return {"message": "Successfully upgraded!"}
