
from fastapi.middleware import cors

from fastapi import FastAPI, Depends
from api import user_profile, tasks
from api.inbox import router as inbox_router
from api.planning import router as planning_router
from api.schedule import router as schedule_router
from calender import router
from middleware.auth import verify_token

# Import agents package — triggers auto-registration of InboxIntelligenceAgent
# and all IIA tools into AgentRegistry + ToolRegistry on startup.
import agents  # noqa: F401
import agents.planning



app=FastAPI(
    tile="vibe2ship MY PA",
    summary="will add summary"
)

#cors
app.add_middleware(
    cors.CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "https://vibe2ship-863e5.web.app",
        "https://vibe2ship-863e5.firebaseapp.com",
        "https://YOUR_DEPLOYED_FIREBASE_HOSTING_URL",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def force_https_scheme_middleware(request, call_next):
    if request.headers.get("x-forwarded-proto") == "https":
        request.scope["scheme"] = "https"
    response = await call_next(request)
    return response

"""
#auth routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
@app.get("/api/profile")
async def get_profiile(user=Depends(verify_token)):
    return {
        "uid": user['uid'],
        "email": user['email']
    } 
"""
@app.get("/"
         )
async def root():
    return {"message": "PA's root docs"}



app.include_router(user_profile.router, prefix="/api/users", tags=["Users"])

#all task routes
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])

#calender router- in calender/router.py -added hte whole router here it contains all endpoints
app.include_router(router.router)

#agent endpoints
app.include_router(inbox_router)
app.include_router(planning_router)
app.include_router(schedule_router)

