from fastapi import APIRouter, HTTPException, Depends
from models.schemas import TaskCreate, TaskUpdate
from services.task_service import (
    create_task, get_all_tasks, get_task_by_id, 
    update_task, delete_task
)
from middleware.auth import verify_token

router = APIRouter()

@router.post("/")
async def create_new_task(
    task_data: TaskCreate,
    user=Depends(verify_token)
):
    
    try:
        uid = user['uid']
        result = await create_task(uid, task_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_tasks(user=Depends(verify_token)): #get all tasks from current user
   
    try:
        uid = user['uid']
        tasks = await get_all_tasks(uid)
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}")
async def get_task(task_id: str, user=Depends(verify_token)):
#get a single task from the user
    print(f"✅ User authenticated: {user['uid']}")
    try:
        uid = user['uid']
        task = await get_task_by_id(uid, task_id)
        return task
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{task_id}")
async def update_single_task(
    task_id: str,
    update_data: TaskUpdate,
    user=Depends(verify_token)
):
    """
    PUT /api/tasks/{task_id}
    Update task
    """
    try:
        uid = user['uid']
        result = await update_task(uid, task_id, update_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{task_id}")
async def delete_single_task(task_id: str, user=Depends(verify_token)):
  
    try:
        uid = user['uid']
        result = await delete_task(uid, task_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))