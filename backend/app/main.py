from db import firebase

from fastapi import FastAPI, Depends
from api import auth
from middleware.auth import verify_token


app=FastAPI(
    tile="vibe2ship MY PA",
    summary="will add summary"
)



#auth routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
@app.get("/api/profile")
async def get_profiile(user=Depends(verify_token)):
    return {
        "uid": user['uid'],
        "email": user['email']
    } 

@app.get("/"
         )
async def root():
    return {"message": "PA's root docs"}



#app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])

#app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])