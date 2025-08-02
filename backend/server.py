from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import uuid
import requests
from datetime import datetime, timedelta
import json

# Initialize FastAPI app
app = FastAPI(title="LessonHub API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = MongoClient(MONGO_URL)
db = client.lessonhub

# Collections
users_collection = db.users
sessions_collection = db.sessions
classes_collection = db.classes
lessons_collection = db.lessons
slides_collection = db.slides
messages_collection = db.messages
notifications_collection = db.notifications

# Google OAuth credentials
GOOGLE_CLIENT_ID = "613974911032-ffmhap5o4pbnasca0f5cpsd17oplvdssps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

# Pydantic models
class User(BaseModel):
    id: str
    email: str
    name: str
    picture: str
    role: str = "teacher"  # teacher or student
    created_at: datetime

class Session(BaseModel):
    session_id: str
    user_id: str
    session_token: str
    expires_at: datetime

class ClassRoom(BaseModel):
    id: str
    name: str
    description: str
    teacher_id: str
    students: List[str] = []
    created_at: datetime

class Lesson(BaseModel):
    id: str
    title: str
    description: str
    class_id: str
    teacher_id: str
    slides_url: Optional[str] = None
    google_slides_id: Optional[str] = None
    google_docs_id: Optional[str] = None
    audio_url: Optional[str] = None
    video_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class Message(BaseModel):
    id: str
    sender_id: str
    recipient_id: str
    class_id: Optional[str] = None
    message: str
    created_at: datetime

class Notification(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    type: str  # lesson, message, assignment
    read: bool = False
    created_at: datetime

# Authentication helper
async def get_current_user(x_session_id: Optional[str] = Header(None)):
    if not x_session_id:
        raise HTTPException(status_code=401, detail="Session ID required")
    
    session = sessions_collection.find_one({"session_id": x_session_id})
    if not session or session["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    user = users_collection.find_one({"id": session["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user

# Root endpoint
@app.get("/")
async def root():
    return {"message": "LessonHub API is running"}

# Authentication endpoints
@app.post("/api/auth/profile")
async def create_profile(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")
    
    # Call Emergent auth API
    headers = {"X-Session-ID": session_id}
    response = requests.get(
        "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
        headers=headers
    )
    
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    auth_data = response.json()
    
    # Check if user exists
    existing_user = users_collection.find_one({"email": auth_data["email"]})
    
    if not existing_user:
        # Create new user
        user_data = {
            "id": str(uuid.uuid4()),
            "email": auth_data["email"],
            "name": auth_data["name"],
            "picture": auth_data["picture"],
            "role": "teacher",  # Default role
            "created_at": datetime.utcnow()
        }
        users_collection.insert_one(user_data)
        user_id = user_data["id"]
    else:
        user_id = existing_user["id"]
    
    # Create session
    session_data = {
        "session_id": session_id,
        "user_id": user_id,
        "session_token": auth_data["session_token"],
        "expires_at": datetime.utcnow() + timedelta(days=7)
    }
    sessions_collection.insert_one(session_data)
    
    return {"success": True, "user_id": user_id, "session_token": auth_data["session_token"]}

@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "picture": current_user["picture"],
        "role": current_user["role"]
    }

# Classroom endpoints
@app.post("/api/classes")
async def create_class(class_data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create classes")
    
    new_class = {
        "id": str(uuid.uuid4()),
        "name": class_data["name"],
        "description": class_data.get("description", ""),
        "teacher_id": current_user["id"],
        "students": [],
        "created_at": datetime.utcnow()
    }
    
    classes_collection.insert_one(new_class)
    return new_class

@app.get("/api/classes")
async def get_classes(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == "teacher":
        classes = list(classes_collection.find({"teacher_id": current_user["id"]}))
    else:
        classes = list(classes_collection.find({"students": current_user["id"]}))
    
    # Remove MongoDB _id field
    for class_item in classes:
        class_item.pop("_id", None)
    
    return classes

@app.get("/api/classes/{class_id}")
async def get_class(class_id: str, current_user: dict = Depends(get_current_user)):
    class_data = classes_collection.find_one({"id": class_id})
    if not class_data:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Check if user has access
    if (current_user["role"] == "teacher" and class_data["teacher_id"] != current_user["id"]) or \
       (current_user["role"] == "student" and current_user["id"] not in class_data["students"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    class_data.pop("_id", None)
    return class_data

# Lesson endpoints
@app.post("/api/lessons")
async def create_lesson(lesson_data: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can create lessons")
    
    # Verify class ownership
    class_data = classes_collection.find_one({"id": lesson_data["class_id"]})
    if not class_data or class_data["teacher_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    new_lesson = {
        "id": str(uuid.uuid4()),
        "title": lesson_data["title"],
        "description": lesson_data.get("description", ""),
        "class_id": lesson_data["class_id"],
        "teacher_id": current_user["id"],
        "slides_url": lesson_data.get("slides_url"),
        "google_slides_id": lesson_data.get("google_slides_id"),
        "google_docs_id": lesson_data.get("google_docs_id"),
        "audio_url": lesson_data.get("audio_url"),
        "video_url": lesson_data.get("video_url"),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    lessons_collection.insert_one(new_lesson)
    
    # Create notification for students
    if class_data["students"]:
        for student_id in class_data["students"]:
            notification = {
                "id": str(uuid.uuid4()),
                "user_id": student_id,
                "title": "New Lesson Available",
                "message": f"New lesson '{new_lesson['title']}' has been added to {class_data['name']}",
                "type": "lesson",
                "read": False,
                "created_at": datetime.utcnow()
            }
            notifications_collection.insert_one(notification)
    
    new_lesson.pop("_id", None)
    return new_lesson

@app.get("/api/lessons")
async def get_lessons(class_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if class_id:
        # Verify access to class
        class_data = classes_collection.find_one({"id": class_id})
        if not class_data:
            raise HTTPException(status_code=404, detail="Class not found")
        
        if (current_user["role"] == "teacher" and class_data["teacher_id"] != current_user["id"]) or \
           (current_user["role"] == "student" and current_user["id"] not in class_data["students"]):
            raise HTTPException(status_code=403, detail="Access denied")
        
        query["class_id"] = class_id
    else:
        if current_user["role"] == "teacher":
            query["teacher_id"] = current_user["id"]
        else:
            # Get student's classes
            student_classes = classes_collection.find({"students": current_user["id"]})
            class_ids = [c["id"] for c in student_classes]
            query["class_id"] = {"$in": class_ids}
    
    lessons = list(lessons_collection.find(query).sort("created_at", -1))
    
    for lesson in lessons:
        lesson.pop("_id", None)
    
    return lessons

# Google integration endpoints
@app.post("/api/google/import-slides")
async def import_google_slides(data: dict, current_user: dict = Depends(get_current_user)):
    # This will be implemented with Google Slides API
    # For now, return a placeholder
    return {"message": "Google Slides import will be implemented", "slides_id": data.get("slides_id")}

@app.post("/api/google/import-docs")
async def import_google_docs(data: dict, current_user: dict = Depends(get_current_user)):
    # This will be implemented with Google Docs API
    # For now, return a placeholder
    return {"message": "Google Docs import will be implemented", "docs_id": data.get("docs_id")}

# Messaging endpoints
@app.post("/api/messages")
async def send_message(message_data: dict, current_user: dict = Depends(get_current_user)):
    new_message = {
        "id": str(uuid.uuid4()),
        "sender_id": current_user["id"],
        "recipient_id": message_data["recipient_id"],
        "class_id": message_data.get("class_id"),
        "message": message_data["message"],
        "created_at": datetime.utcnow()
    }
    
    messages_collection.insert_one(new_message)
    
    # Create notification
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": message_data["recipient_id"],
        "title": "New Message",
        "message": f"You have a new message from {current_user['name']}",
        "type": "message",
        "read": False,
        "created_at": datetime.utcnow()
    }
    notifications_collection.insert_one(notification)
    
    new_message.pop("_id", None)
    return new_message

@app.get("/api/messages")
async def get_messages(recipient_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {
        "$or": [
            {"sender_id": current_user["id"]},
            {"recipient_id": current_user["id"]}
        ]
    }
    
    if recipient_id:
        query = {
            "$or": [
                {"sender_id": current_user["id"], "recipient_id": recipient_id},
                {"sender_id": recipient_id, "recipient_id": current_user["id"]}
            ]
        }
    
    messages = list(messages_collection.find(query).sort("created_at", -1))
    
    for message in messages:
        message.pop("_id", None)
    
    return messages

# Notifications endpoints
@app.get("/api/notifications")
async def get_notifications(current_user: dict = Depends(get_current_user)):
    notifications = list(notifications_collection.find({"user_id": current_user["id"]}).sort("created_at", -1))
    
    for notification in notifications:
        notification.pop("_id", None)
    
    return notifications

@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    result = notifications_collection.update_one(
        {"id": notification_id, "user_id": current_user["id"]},
        {"$set": {"read": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)