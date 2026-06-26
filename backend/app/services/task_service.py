from firebase_admin import firestore
from db.firebase import firebase_db
from models.schemas import TaskCreate, TaskUpdate
from datetime import datetime

async def create_task(uid: str, task_data: TaskCreate):

    try:
        task_ref = firebase_db.collection("tasks").document()
        
        task_ref.set({
            "uid": uid,
            "title": task_data.title,
            "description": task_data.description or "",
            "deadline": task_data.deadline,
            "priority": task_data.priority,
            "estimated_hours": task_data.estimated_hours,
            "status": "todo",  # Default status
            "tags": task_data.tags or [],
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP
        })
        
        return {"id": task_ref.id, "message": "Task created"}
    
    except Exception as e:
        raise Exception(f"Error creating task: {str(e)}")

async def get_all_tasks(uid: str):
    """Get all tasks for user"""
    try:
        tasks = firebase_db.collection("tasks").where("uid", "==", uid).stream()
        
        task_list = []
        for doc in tasks:
            task_data = doc.to_dict()
            task_data['id'] = doc.id
            task_list.append(task_data)
        
        return task_list
    
    except Exception as e:
        raise Exception(f"Error fetching tasks: {str(e)}")

async def get_task_by_id(uid: str, task_id: str):
    """Get single task"""
    try:
        doc = firebase_db.collection("tasks").document(task_id).get()
        
        if not doc.exists:
            raise Exception("Task not found")
        
        task_data = doc.to_dict()
        
        # Verify ownership
        if task_data['uid'] != uid:
            raise Exception("Unauthorized")
        
        task_data['id'] = doc.id
        return task_data
    
    except Exception as e:
        raise Exception(f"Error fetching task: {str(e)}")

async def update_task(uid: str, task_id: str, update_data: TaskUpdate):
    """Update task"""
    try:
        doc = firebase_db.collection("tasks").document(task_id).get()
        
        if not doc.exists:
            raise Exception("Task not found")
        
        task_data = doc.to_dict()
        
        # Verify ownership
        if task_data['uid'] != uid:
            raise Exception("Unauthorized")
        
      
        update_dict = {}
        for field, value in update_data.dict().items():
            if value is not None:
                update_dict[field] = value
        
        update_dict['updated_at'] = firestore.SERVER_TIMESTAMP
        
        firebase_db.collection("tasks").document(task_id).update(update_dict)
        
        return {"id": task_id, "message": "Task updated"}
    
    except Exception as e:
        raise Exception(f"Error updating task: {str(e)}")

async def delete_task(uid: str, task_id: str):
    
    try:
        doc = firebase_db.collection("tasks").document(task_id).get()
        
        if not doc.exists:
            raise Exception("Task not found")
        
        task_data = doc.to_dict()
        
        # Verify ownership
        if task_data['uid'] != uid:
            raise Exception("Unauthorized")
        
        firebase_db.collection("tasks").document(task_id).delete()
        
        return {"message": "Task deleted"}
    
    except Exception as e:
        raise Exception(f"Error deleting task: {str(e)}")