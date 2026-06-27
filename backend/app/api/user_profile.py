from fastapi import APIRouter, HTTPException, Depends
from models.schemas import ProfileCreate, PreferencesCreate
from services.user_service import create_user_profile, get_user_profile
from middleware.auth import verify_token
from db.firebase import firebase_db
from firebase_admin import firestore


router = APIRouter()



@router.post("/profile") #set up profile while signing up
async def create_profile(
    profile_data: ProfileCreate,
    pref_data: PreferencesCreate,
    user=Depends(verify_token)
):
    try:
        uid = user['uid']
        email = user['email']
        
        # Store in Firestore
        user_ref = firebase_db.collection("users").document(uid)
        user_ref.set({
            "email": email,
            "created_at": firestore.SERVER_TIMESTAMP,
            "profile": {
                "name": profile_data.name,
                "profession": profile_data.profession,
                "working_hours_start": profile_data.working_hours_start,
                "working_hours_end": profile_data.working_hours_end,
                "productive_hours": profile_data.productive_hours,
                "preferred_session_duration": profile_data.preferred_session_duration,
                "timezone": profile_data.timezone,
            },
            "preferences": {
                "email_reminders": pref_data.email_reminders,
                "push_notifications": pref_data.push_notifications,
                "daily_summary": pref_data.daily_summary,
            }
        })
        
        return {
            "uid": uid,
            "message": "Profile created successfully"
        }
    
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