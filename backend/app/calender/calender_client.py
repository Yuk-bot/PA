from datetime import datetime, timedelta, timezone
from typing import List
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from models.schemas import CalendarEvent, GoogleCalendarCredentials
from calender.utils import encrypt_token, decrypt_token
from firebase_admin import firestore
import os

db = firestore.client()


class GoogleCalendarClient:
    
    
    def __init__(self, credentials: GoogleCalendarCredentials, uid: str): #inintialize calender
      
        self.uid = uid
        self.credentials_obj = credentials
        self.service = self._create_service()
    
    def _create_service(self):  #_- the strating/leading underscore- for private method functions- use inside the class
  
        # Build Credentials object from stored data
        creds = Credentials(
            token=self.credentials_obj.access_token,
            refresh_token=self.credentials_obj.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("OAUTH_CLIENT_ID"),
            client_secret=os.getenv("CLIENT_SECRET"),
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            expiry=datetime.fromtimestamp(self.credentials_obj.expires_at, tz=timezone.utc),
        )
        

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update tokens in Firestore
            self._update_tokens_in_firestore(creds)
        
        return build("calendar", "v3", credentials=creds)
    
    def _update_tokens_in_firestore(self, creds):
        
        try:
            expires_at = int(creds.expiry.timestamp()) if creds.expiry else int((datetime.now() + timedelta(hours=1)).timestamp())
            
            db.collection("users").document(self.uid).collection("integrations").document(
                "google_calendar"
            ).update({
                "access_token": encrypt_token(creds.token),
                "refresh_token": encrypt_token(creds.refresh_token or ""),
                "expires_at": expires_at,
                "updated_at": int(datetime.now().timestamp()),
            })
        except Exception as e:
            print(f"Error updating tokens in Firestore: {e}")
    
    def get_events(self, max_results: int = 10, days_ahead: int = 30) -> List[CalendarEvent]:
        
        try:
            now = datetime.now().isoformat() + "Z"
            end_date = (datetime.now() + timedelta(days=days_ahead)).isoformat() + "Z"
            
            events_result = self.service.events().list(
                calendarId="primary",
                timeMin=now,
                timeMax=end_date,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            
            events = events_result.get("items", [])
            return self._parse_events(events)
        
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []
    
    def get_today_events(self) -> List[CalendarEvent]:
        """Fetch only today's events"""
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            today_start_iso = today_start.isoformat() + "Z"
            today_end_iso = today_end.isoformat() + "Z"
            
            events_result = self.service.events().list(
                calendarId="primary",
                timeMin=today_start_iso,
                timeMax=today_end_iso,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            
            events = events_result.get("items", [])
            return self._parse_events(events)
        
        except Exception as e:
            print(f"Error fetching today's events: {e}")
            return []
    
    def _parse_events(self, events: List[dict]) -> List[CalendarEvent]:
        
        parsed = []
        
        for event in events:
            try:
            
                start_data = event.get("start", {})
                end_data = event.get("end", {})
                
                
                is_all_day = "date" in start_data
                
                if is_all_day:
                    start = datetime.strptime(start_data["date"], "%Y-%m-%d")
                    end = datetime.strptime(end_data["date"], "%Y-%m-%d")
                else:
                   
                    start = datetime.fromisoformat(start_data["dateTime"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(end_data["dateTime"].replace("Z", "+00:00"))

                attendees = [att.get("email", "") for att in event.get("attendees", [])]
                
                cal_event = CalendarEvent(
                    event_id=event.get("id", ""),
                    title=event.get("summary", "Untitled"),
                    start=start,
                    end=end,
                    description=event.get("description", ""),
                    location=event.get("location", ""),
                    is_all_day=is_all_day,
                    attendees=attendees,
                )
                parsed.append(cal_event)
            
            except Exception as e:
                print(f"Error parsing event: {e}")
                continue
        
        return parsed