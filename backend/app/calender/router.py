from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta
from middleware.auth import verify_token
from models.schemas import(
    CalendarConnectResponse,
    CalendarDisconnectResponse,
    CalendarEventsResponse,
    CalendarTodayResponse,
    FreeSlotsResponse,
    FreeSlot,
)

from calender.oauth_handler import ( 
    get_authorization_url,
    handle_oauth_callback,
    get_stored_credentials,
    disconnect_calendar,
)
from calender.calender_client import GoogleCalendarClient
from calender.utils import decrypt_token

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/connect", response_model=CalendarConnectResponse)
async def connect_calendar(user=Depends(verify_token)):
  #oauth clander link geenral user clicks and permits connection
    try:
        uid = user["uid"]
        
        auth_url = get_authorization_url(uid)
        
        return CalendarConnectResponse(authorization_url=auth_url)
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")


@router.get("/callback")
async def calendar_callback(code: str = Query(None), state: str = Query(None)):
    # OAuth callback — Google redirects here with code & state (uid).
    # No Firebase auth header is present; we identify the user via the state param.
    try:
        
        if not code:
            
            return RedirectResponse(url="http://localhost:5173/calendar?error=missing_code")

        if not state:
            
            return RedirectResponse(url="http://localhost:5173/calendar?error=missing_state")

        uid=state

        credentials = handle_oauth_callback(uid, code)
        
        return RedirectResponse(
            url=f"http://localhost:5173/calendar?calendar_connected=true&email={credentials.google_account_email}"
        )

    except Exception as e:
        
        return RedirectResponse(url=f"http://localhost:5173/calendar?error={str(e)}")


@router.get("/events", response_model=CalendarEventsResponse)#get upcoming calendar events.
async def get_events(
    #max_results: Max events to return (default: 10), days_ahead: How many days into future (default: 30)
    max_results: int = Query(10, ge=1, le=100),
    days_ahead: int = Query(30, ge=1, le=365),
    user=Depends(verify_token),
):
    
    try:
        uid = user["uid"]
       
       
        creds = get_stored_credentials(uid)
        if not creds or not creds.connected:
            
            raise HTTPException(status_code=404, detail="Calendar not connected")
       
        
        client = GoogleCalendarClient(creds, uid)
        events = client.get_events(max_results=max_results, days_ahead=days_ahead)
        
        
        return CalendarEventsResponse(events=events, count=len(events))
    
    except HTTPException:
        raise
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}")


@router.get("/today", response_model=CalendarTodayResponse)
async def get_today_events(user=Depends(verify_token)):

    try:
        uid = user["uid"]
        print(f"=== ROUTER DEBUG: /today request for UID: {uid} ===")
   
        creds = get_stored_credentials(uid)
        if not creds or not creds.connected:
            
            raise HTTPException(status_code=404, detail="Calendar not connected")
      
        
        client = GoogleCalendarClient(creds, uid)
        events = client.get_today_events()
        
        
        return CalendarTodayResponse(events=events, count=len(events))
    
    except HTTPException:
        raise
    except Exception as e:
        
        raise HTTPException(status_code=500, detail=f"Failed to fetch today's events: {str(e)}")


@router.get("/free-slots", response_model=FreeSlotsResponse)
async def get_free_slots(user=Depends(verify_token)):
    #working hours as per user already set in the profile
   
    
    try:
        uid = user["uid"]
        
        # Get stored credentials
        creds = get_stored_credentials(uid)
        if not creds or not creds.connected:
            raise HTTPException(status_code=404, detail="Calendar not connected")
        
        from firebase_admin import firestore
        db = firestore.client()
        
        user_doc = db.collection("users").document(uid).get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        user_data = user_doc.to_dict()
        profile = user_data.get("profile", {})
        
        working_hours_start = profile.get("working_hours_start", "09:00")
        working_hours_end = profile.get("working_hours_end", "18:00")

        client = GoogleCalendarClient(creds, uid) #fetch  events for today
        events = client.get_today_events()

        free_slots = _calculate_free_slots(events, working_hours_start, working_hours_end)
        
        total_free_minutes = sum(slot.duration_minutes for slot in free_slots)
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        return FreeSlotsResponse(
            date=today_str,
            free_slots=free_slots,
            total_free_minutes=total_free_minutes,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate free slots: {str(e)}")


@router.post("/disconnect", response_model=CalendarDisconnectResponse)
async def disconnect_calendar_access(user=Depends(verify_token)):

    try:
        uid = user["uid"]

        if disconnect_calendar(uid):
            return CalendarDisconnectResponse(message="Calendar disconnected successfully")
        else:
            raise HTTPException(status_code=500, detail="Failed to disconnect calendar")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disconnect failed: {str(e)}")



def _calculate_free_slots(events, working_hours_start: str, working_hours_end: str) -> list[FreeSlot]:
    
    
    
    
    try:
        start_hour, start_min = map(int, working_hours_start.split(":"))
        end_hour, end_min = map(int, working_hours_end.split(":"))
    except:
     
        start_hour, start_min = 9, 0
        end_hour, end_min = 18, 0
    
    today = datetime.now().date()
    work_start = datetime.combine(today, datetime.min.time()).replace(hour=start_hour, minute=start_min)
    work_end = datetime.combine(today, datetime.min.time()).replace(hour=end_hour, minute=end_min)
    
   
    sorted_events = sorted(events, key=lambda e: e.start)
    
    free_slots = []
    current_time = work_start
    
    for event in sorted_events:
        # Skip all-day events and events outside working hours
        if event.is_all_day or event.start >= work_end:
            continue
        
        # If there's a gap before this event
        if current_time < event.start and current_time < work_end:
            gap_start = max(current_time, work_start)
            gap_end = min(event.start, work_end)
            
            if gap_end > gap_start:
                duration_minutes = int((gap_end - gap_start).total_seconds() / 60)
                if duration_minutes > 0:
                    free_slots.append(
                        FreeSlot(
                            start=gap_start,
                            end=gap_end,
                            duration_minutes=duration_minutes,
                        )
                    )
        
        current_time = max(current_time, event.end)
    
    # Add remaining time until work_end
    if current_time < work_end:
        duration_minutes = int((work_end - current_time).total_seconds() / 60)
        if duration_minutes > 0:
            free_slots.append(
                FreeSlot(
                    start=current_time,
                    end=work_end,
                    duration_minutes=duration_minutes,
                )
            )
    
    return free_slots

