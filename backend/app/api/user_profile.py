from fastapi import APIRouter, HTTPException, Depends
from models.schemas import ProfileCreate, PreferencesCreate
from services.user_service import create_user_profile, get_user_profile
from middleware.auth import verify_token

router = APIRouter()

@router.post("/profile") #create/update user profile after signup
async def create_profile(
    profile_data: ProfileCreate,
    pref_data: PreferencesCreate,
    user=Depends(verify_token)
):
    try:
        uid = user['uid']
        email = user['email']
        
        result = await create_user_profile(uid, email, profile_data, pref_data)
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/profile")
async def get_profile(user=Depends(verify_token)):
    
    try:
        uid = user['uid']
        profile = await get_user_profile(uid)
        return profile
    
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))