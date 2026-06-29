from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


#user profile
class ProfileCreate(BaseModel):
    """User profile data on signup"""
    name: str
    profession: str  # "student" or "professional"
    working_hours_start: str  # "09:00"
    working_hours_end: str    # "18:00"
    productive_hours: List[str]  # ["09:00-11:00", "14:00-16:00"]
    preferred_session_duration: int  # minutes (e.g., 60)
    timezone: str  # "UTC", "IST"

class PreferencesCreate(BaseModel):
    """Notification preferences"""
    email_reminders: bool
    push_notifications: bool
    daily_summary: bool

class UserResponse(BaseModel):
    """User data response"""
    uid: str
    email: str
    profile: dict
    preferences: dict
    created_at: datetime


from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

#task schemas

class TaskCreate(BaseModel):
    """Create new task"""
    title: str
    description: Optional[str] = None
    deadline: str 
    priority: str  
    estimated_hours: float
    tags: Optional[List[str]] = []

class TaskUpdate(BaseModel):
    """Update task"""
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None
    estimated_hours: Optional[float] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

class TaskResponse(BaseModel):
    """Task response"""
    id: str
    uid: str
    title: str
    description: Optional[str]
    deadline: str
    priority: str
    estimated_hours: float
    status: str  # "todo", "in_progress", "completed"
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

# ============ CALENDAR OAUTH ============

class GoogleCalendarCredentials(BaseModel):
    """Stored Google Calendar OAuth credentials (encrypted in Firestore)"""
    google_account_email: str
    access_token: str  #ye dono tokens encrypted
    refresh_token: str  
    expires_at: int
    token_type: str  
    connected: bool = True
    created_at: Optional[int] = None
    updated_at: Optional[int] = None

class CalendarConnectResponse(BaseModel):
    """Response from /api/calendar/connect"""
    authorization_url: str

class CalendarCallbackResponse(BaseModel):
    """Response from /api/calendar/callback"""
    message: str
    google_email: str

class CalendarDisconnectResponse(BaseModel):
    """Response from /api/calendar/disconnect"""
    message: str


class CalendarEvent(BaseModel):
    """Single calendar event from Google Calendar"""
    event_id: str
    title: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    is_all_day: bool = False
    attendees: List[str] = []

class CalendarEventsResponse(BaseModel):
    """Response from /api/calendar/events"""
    events: List[CalendarEvent]
    count: int

class CalendarTodayResponse(BaseModel):
    """Response from /api/calendar/today"""
    events: List[CalendarEvent]
    count: int



class FreeSlot(BaseModel):
    """Available time slot between calendar events"""
    start: datetime
    end: datetime
    duration_minutes: int

class FreeSlotsResponse(BaseModel):
    """Response from /api/calendar/free-slots"""
    date: str 
    free_slots: List[FreeSlot]
    total_free_minutes: int