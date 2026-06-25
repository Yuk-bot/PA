from fastapi import FastAPI

app=FastAPI(
    tile="vibe2ship MY PA",
    summary="will add summary"
)

from fastapi import FastAPI

from app.routers import auth
from app.routers import tasks
from app.routers import agents

app = FastAPI()

#auth routes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
@app.get("/api/profile")
async def get_profiile():
    return 

@app.get("/"
         )
async def root():
    return {"message": "PA's root docs"}

app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])

app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])