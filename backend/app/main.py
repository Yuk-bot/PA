
from fastapi.middleware import cors

from fastapi import FastAPI, Depends
from api import user_profile, tasks
from calender import router
from middleware.auth import verify_token



app=FastAPI(
    tile="vibe2ship MY PA",
    summary="will add summary"
)

#cors
app.add_middleware(
    cors.CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  #frontend 
        "http://localhost:3000",   #alternative ports
        "http://localhost:8080",  
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

#app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])