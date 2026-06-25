from fastapi import APIRouter
from pydantic import BaseModel

router=APIRouter()

class GoogleLoginRequest(BaseModel):
    id_token: str  #from google sign thru frontend

class EmailSignupRequest(BaseModel):
    email: str
    password: str

class EmailLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login/google", summary="google signin",
             description=""" Body: { "id_token": "..." }
    Returns: { "uid": "...", "email": "..." }""")
async def google_login():
    return



@router.post("/signup/email", summary="email signup",
             description=""" Body: { "email": "...", "password": "..." }
    Returns: { "uid": "...", "email": "..." }""")
async def email_signup(request: emailsignup):
    return


@router.post("/login/email", summary="emailsignin",
             description=""" Body: { "email": "...", "password": "..." }
    Returns: { "uid": "...", "email": "..." }""")
async def email_signin():
    return

@router.post("/logout",
             description="""
    POST /api/auth/logout
    (Optional: for frontend cleanup. Backend doesn't track sessions)
    """)
async def logout(user=Depends(verify_token)):
    
    return {"message": "logged out"}






