from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.firebase import firebase_auth, firebase_db
import re
from firebase_admin import firestore
import os
import requests
from google.auth.transport import requests as google_requests

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

router=APIRouter()

class GoogleLoginRequest(BaseModel):
    id_token: str  #from google sign thru frontend

class EmailSignupRequest(BaseModel):
    email: str
    password: str

class EmailLoginRequest(BaseModel):
    email: str
    password: str

#reponse model
class AuthResponse(BaseModel):
    uid: str
    email: str
    message: str


async def create_user_in_firestore(uid: str, email: str): #create user if doesnt exist in firestore
    
    user_ref = firebase_db.collection("users").document(uid)
    
    try:
        user_ref.get()
        if not user_ref.get().exists:
            user_ref.set({
                "email": email,
                "created_at": firestore.SERVER_TIMESTAMP,
                "profile": {
                    "interests": [],
                    "timezone": "UTC"
                },
                "settings": {
                    "notifications_enabled": True
                }
            })
        return True
    except Exception as e:
        print(f"Error creating user in Firestore: {e}")
        return False
 

"""@router.post("/login/google", summary="google signin",
             description= Body: { "id_token": "..." }
    Returns: { "uid": "...", "email": "..." })
async def google_login(request: GoogleLoginRequest):
    try:
        access_token = request.id_token
        
        # Exchange access token for user info
        userinfo_endpoint = "https://www.googleapis.com/oauth2/v2/userinfo"
        response = requests.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")
        
        userinfo = response.json()
        email = userinfo.get('email')
        name = userinfo.get('name', '')
        
        if not email:
            raise HTTPException(status_code=401, detail="Could not retrieve email from Google")
        
        #create user in firebase only if he doesnt exist check first otherwise errors
        try:
            user = firebase_auth.get_user_by_email(email)
            uid = user.uid
        except firebase_auth.UserNotFoundError:
            #user not found so create
            user = firebase_auth.create_user(email=email, display_name=name)
            uid = user.uid
        
        #same user creation and chencking logic
        user_ref = firebase_db.collection("users").document(uid)
        if not user_ref.get().exists:
            user_ref.set({
                "email": email,
                "profile": {
                    "name": name,
                    "interests": [],
                    "timezone": "UTC"
                },
                "preferences": {
                    "notifications_enabled": True
                },
                "created_at": firestore.SERVER_TIMESTAMP
            })
        
        #for frontend
        custom_token = firebase_auth.create_custom_token(uid)
        
        return {
            "uid": uid,
            "email": email,
            "message": "Google login successful",
            "token": custom_token.decode()
        }
    
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=401, detail="Failed to verify Google token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google login failed: {str(e)}")
    

@router.post("/signup/email")
async def email_signup(request: EmailSignupRequest):
    try:
        # create firebase user
        user = firebase_auth.create_user(
            email=request.email,
            password=request.password
        )

        uid = user.uid

        # create firestore profile
        user_ref = firebase_db.collection("users").document(uid)
        if not user_ref.get().exists:
            user_ref.set({
                "email": request.email,
                "profile": {
                    "interests": [],
                    "timezone": "UTC"
                },
                "preferences": {
                    "notifications_enabled": True
                },
                "created_at": firestore.SERVER_TIMESTAMP
            })

        return {
            "uid": uid,
            "email": request.email,
            "message": "Signup successful"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    


@router.post("/login/email", summary="emailsignin",
             description= Body: { "email": "...", "password": "..." }
    Returns: { "uid": "...", "email": "..." })
async def email_signin(request: EmailLoginRequest):
    try:
        user = firebase_auth.get_user_by_email(request.email)
        uid = user.uid

        custom_token = firebase_auth.create_custom_token(uid) #creating custom token for exchange with frontend
        
        return AuthResponse(
            uid=uid,
            email=request.email,
            message=f"Logged in using Email. Use this token: {custom_token.decode()}"
        )
    except firebase_auth.UserNotFoundError:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")
    
"""
@router.post("/logout",
             description="""
    POST /api/auth/logout
    (Optional: for frontend cleanup. Backend doesn't track sessions)
    """)
async def logout():
    
    return {"message": "logged out"}






