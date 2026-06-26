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
    timezone: str  # "UTC", "IST", etc.

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