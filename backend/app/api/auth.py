from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from db.firebase import firebase_auth, firebase_db
import re
from firebase_admin import firestore

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
 

@router.post("/login/google", summary="google signin",
             description=""" Body: { "id_token": "..." }
    Returns: { "uid": "...", "email": "..." }""")
async def google_login(request: GoogleLoginRequest):
    try:
        decoded=firebase_auth.verify_id_token(request.id_token)
        
        uid=decoded['uid']
        email=decoded['email']

        await create_user_in_firestore(uid, email) #if first login
    
        return AuthResponse(
            uid=uid,
            email=email,
            message="Logged in by Google"
        )

    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid ID token")
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="ID token expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    


@router.post("/signup/email", summary="email signup",
             description=""" Body: { "email": "...", "password": "..." }
    Returns: { "uid": "...", "email": "..." }""")
async def email_signup(request: EmailSignupRequest):
    try:
        if len(request.password)<6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 character")
                                
        user = firebase_auth.create_user(
            email=request.email,
            password=request.password
        )

        uid=user.uid
        await create_user_in_firestore(uid, request.email)
        
        return AuthResponse(
            uid=uid,
            email=request.email,
            message="Signup successful. Please login."
        )
    
    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Email arleady registered")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail="Signup failed due to: Password criteria not fullfiled(capital letter+special character equired), or {str(e)}")

    


@router.post("/login/email", summary="emailsignin",
             description=""" Body: { "email": "...", "password": "..." }
    Returns: { "uid": "...", "email": "..." }""")
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
    

@router.post("/logout",
             description="""
    POST /api/auth/logout
    (Optional: for frontend cleanup. Backend doesn't track sessions)
    """)
async def logout():
    
    return {"message": "logged out"}






