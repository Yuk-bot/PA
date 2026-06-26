from firebase_admin import firestore
from db.firebase import firebase_db
from models.schemas import ProfileCreate, PreferencesCreate

async def create_user_profile(uid: str, email: str, profile_data: ProfileCreate, pref_data: PreferencesCreate):
    """Store user profile in Firestore"""
    try:
        user_ref = firebase_db.collection("users").document(uid)
        
        user_ref.set({
            "email": email,
            "profile": {
                "name": profile_data.name,
                "profession": profile_data.profession,
                "working_hours": {
                    "start": profile_data.working_hours_start,
                    "end": profile_data.working_hours_end
                },
                "productive_hours": profile_data.productive_hours,
                "preferred_session_duration": profile_data.preferred_session_duration,
                "timezone": profile_data.timezone
            },
            "preferences": {
                "email_reminders": pref_data.email_reminders,
                "push_notifications": pref_data.push_notifications,
                "daily_summary": pref_data.daily_summary
            },
            "created_at": firestore.SERVER_TIMESTAMP
        })
        
        return {"uid": uid, "message": "Profile created"}
    
    except Exception as e:
        raise Exception(f"Error creating profile: {str(e)}")

async def get_user_profile(uid: str):
    #fetch user profile
    try:
        user_doc = firebase_db.collection("users").document(uid).get()
        if user_doc.exists:
            return user_doc.to_dict()
        else:
            raise Exception("User not found")
    except Exception as e:
        raise Exception(f"Error fetching profile: {str(e)}")