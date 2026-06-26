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


from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

#task schemas

class TaskCreate(BaseModel):
    """Create new task"""
    title: str
    description: Optional[str] = None
    deadline: str  # "2024-12-31T18:00:00"
    priority: str  # "high", "medium", "low"
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