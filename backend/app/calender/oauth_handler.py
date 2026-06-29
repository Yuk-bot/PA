import os
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from firebase_admin import firestore
from models.schemas import GoogleCalendarCredentials
from calender.utils import encrypt_token, decrypt_token


CLIENT_ID = os.getenv("GOOGLE_CALENDAR_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_CALENDAR_REDIRECT_URI")


SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"] #calender scopes- auth/calender scope added already so all permssions exist

db = firestore.client()


def get_authorization_url(uid: str) -> str:
    """google OAuth authorization URL will be generated
    User will be redirected to this URL to grant calendar access- perm grant karna padega .
    """
    flow = Flow.from_client_config(
        {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    
    
    auth_url, state = flow.authorization_url(
        access_type="offline", #get refresh token
        prompt="consent", #force consent screen for gcalander every time
    )
    

    
    return auth_url


def handle_oauth_callback(uid: str, auth_code: str) -> GoogleCalendarCredentials:
  
    #exchange auth code for access/refresh tokens.
    #Store encrypted tokens in Firestore.

    flow = Flow.from_client_config(
        {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    
  
    flow.fetch_token(code=auth_code)#exchange tokens
    credentials = flow.credentials
    
    
    google_email = credentials.token_info.get("email", "unknown@gmail.com")
    
  
    expires_at = int((datetime.now() + timedelta(seconds=credentials.expiry.timestamp() if credentials.expiry else 3600)).timestamp())
    
  
    creds_to_store = GoogleCalendarCredentials(
        google_account_email=google_email,
        access_token=encrypt_token(credentials.token),
        refresh_token=encrypt_token(credentials.refresh_token or ""),
        expires_at=expires_at,
        token_type="Bearer",
        connected=True,
        created_at=int(datetime.now().timestamp()),
        updated_at=int(datetime.now().timestamp()),
    )
    
    user_ref = db.collection("users").document(uid)
    user_ref.collection("integrations").document("google_calendar").set(
        creds_to_store.model_dump()
    )
    
    return creds_to_store


def get_stored_credentials(uid: str) -> GoogleCalendarCredentials | None:
    #get credentialsn decrypt and use
    try:
        doc = (
            db.collection("users")
            .document(uid)
            .collection("integrations")
            .document("google_calendar")
            .get()
        )
        
        if not doc.exists:
            return None
        
        data = doc.to_dict()
        
    
        data["access_token"] = decrypt_token(data["access_token"])
        data["refresh_token"] = decrypt_token(data["refresh_token"])
        
        return GoogleCalendarCredentials(**data)
    
    except Exception as e:
        print(f"Error retrieving credentials: {e}")
        return None


def disconnect_calendar(uid: str) -> bool:
  
    try:
        db.collection("users").document(uid).collection("integrations").document(
            "google_calendar"
        ).delete()
        return True
    except Exception as e:
        print(f"Error disconnecting calendar: {e}")
        return False