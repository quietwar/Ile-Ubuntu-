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
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
google_tokens_collection = db.google_tokens

# Google OAuth credentials
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.readonly'
]

# Google OAuth flow configuration
def create_google_flow():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:3000/auth/google/callback"]
            }
        },
        scopes=GOOGLE_SCOPES
    )
    flow.redirect_uri = "http://localhost:3000/auth/google/callback"
    return flow

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
@app.get("/api/google/auth-url")
async def get_google_auth_url(current_user: dict = Depends(get_current_user)):
    """Get Google OAuth authorization URL"""
    try:
        flow = create_google_flow()
        auth_url, _ = flow.authorization_url(prompt='consent')
        
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create auth URL: {str(e)}")

@app.post("/api/google/callback")
async def google_oauth_callback(request: Request, current_user: dict = Depends(get_current_user)):
    """Handle Google OAuth callback"""
    try:
        data = await request.json()
        authorization_code = data.get("code")
        
        if not authorization_code:
            raise HTTPException(status_code=400, detail="Authorization code required")
        
        flow = create_google_flow()
        flow.fetch_token(code=authorization_code)
        
        credentials = flow.credentials
        
        # Store Google credentials
        token_data = {
            "user_id": current_user["id"],
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "created_at": datetime.utcnow(),
            "expires_at": credentials.expiry
        }
        
        # Update or insert Google token
        google_tokens_collection.replace_one(
            {"user_id": current_user["id"]},
            token_data,
            upsert=True
        )
        
        return {"success": True, "message": "Google account connected successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")

@app.get("/api/google/slides")
async def list_google_slides(current_user: dict = Depends(get_current_user)):
    """List user's Google Slides presentations"""
    try:
        # Get user's Google credentials
        token_data = google_tokens_collection.find_one({"user_id": current_user["id"]})
        if not token_data:
            raise HTTPException(status_code=401, detail="Google account not connected")
        
        # Create credentials object
        credentials = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data["scopes"]
        )
        
        # Refresh credentials if needed
        if credentials.expired:
            credentials.refresh(GoogleRequest())
            # Update stored credentials
            google_tokens_collection.update_one(
                {"user_id": current_user["id"]},
                {"$set": {
                    "access_token": credentials.token,
                    "expires_at": credentials.expiry
                }}
            )
        
        # Build Drive service to list presentations
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Search for Google Slides presentations
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.presentation'",
            pageSize=50,
            fields="nextPageToken, files(id, name, createdTime, modifiedTime, thumbnailLink)"
        ).execute()
        
        presentations = results.get('files', [])
        
        return {"presentations": presentations}
        
    except HttpError as error:
        raise HTTPException(status_code=400, detail=f"Google API error: {error}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list slides: {str(e)}")

@app.get("/api/google/docs")
async def list_google_docs(current_user: dict = Depends(get_current_user)):
    """List user's Google Docs documents"""
    try:
        # Get user's Google credentials
        token_data = google_tokens_collection.find_one({"user_id": current_user["id"]})
        if not token_data:
            raise HTTPException(status_code=401, detail="Google account not connected")
        
        # Create credentials object
        credentials = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data["scopes"]
        )
        
        # Refresh credentials if needed
        if credentials.expired:
            credentials.refresh(GoogleRequest())
            # Update stored credentials
            google_tokens_collection.update_one(
                {"user_id": current_user["id"]},
                {"$set": {
                    "access_token": credentials.token,
                    "expires_at": credentials.expiry
                }}
            )
        
        # Build Drive service to list documents
        drive_service = build('drive', 'v3', credentials=credentials)
        
        # Search for Google Docs documents
        results = drive_service.files().list(
            q="mimeType='application/vnd.google-apps.document'",
            pageSize=50,
            fields="nextPageToken, files(id, name, createdTime, modifiedTime, thumbnailLink)"
        ).execute()
        
        documents = results.get('files', [])
        
        return {"documents": documents}
        
    except HttpError as error:
        raise HTTPException(status_code=400, detail=f"Google API error: {error}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list docs: {str(e)}")

@app.post("/api/google/import-slides")
async def import_google_slides(data: dict, current_user: dict = Depends(get_current_user)):
    """Import Google Slides presentation"""
    try:
        slides_id = data.get("slides_id")
        lesson_id = data.get("lesson_id")
        
        if not slides_id:
            raise HTTPException(status_code=400, detail="Slides ID required")
        
        # Get user's Google credentials
        token_data = google_tokens_collection.find_one({"user_id": current_user["id"]})
        if not token_data:
            raise HTTPException(status_code=401, detail="Google account not connected")
        
        # Create credentials object
        credentials = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data["scopes"]
        )
        
        # Build Slides service
        slides_service = build('slides', 'v1', credentials=credentials)
        
        # Get presentation details
        presentation = slides_service.presentations().get(presentationId=slides_id).execute()
        
        # Import slides data
        imported_slides = {
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "google_slides_id": slides_id,
            "lesson_id": lesson_id,
            "title": presentation.get('title', 'Untitled Presentation'),
            "slides_data": presentation,
            "imported_at": datetime.utcnow()
        }
        
        slides_collection.insert_one(imported_slides)
        
        # Update lesson if lesson_id provided
        if lesson_id:
            lessons_collection.update_one(
                {"id": lesson_id, "teacher_id": current_user["id"]},
                {"$set": {"google_slides_id": slides_id}}
            )
        
        imported_slides.pop("_id", None)
        return imported_slides
        
    except HttpError as error:
        raise HTTPException(status_code=400, detail=f"Google API error: {error}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import slides: {str(e)}")

@app.post("/api/google/import-docs")
async def import_google_docs(data: dict, current_user: dict = Depends(get_current_user)):
    """Import Google Docs document"""
    try:
        docs_id = data.get("docs_id")
        lesson_id = data.get("lesson_id")
        
        if not docs_id:
            raise HTTPException(status_code=400, detail="Docs ID required")
        
        # Get user's Google credentials
        token_data = google_tokens_collection.find_one({"user_id": current_user["id"]})
        if not token_data:
            raise HTTPException(status_code=401, detail="Google account not connected")
        
        # Create credentials object
        credentials = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data["scopes"]
        )
        
        # Build Docs service
        docs_service = build('docs', 'v1', credentials=credentials)
        
        # Get document details
        document = docs_service.documents().get(documentId=docs_id).execute()
        
        # Update lesson if lesson_id provided
        if lesson_id:
            lessons_collection.update_one(
                {"id": lesson_id, "teacher_id": current_user["id"]},
                {"$set": {"google_docs_id": docs_id}}
            )
        
        return {
            "success": True,
            "docs_id": docs_id,
            "title": document.get('title', 'Untitled Document'),
            "message": "Google Docs imported successfully"
        }
        
    except HttpError as error:
        raise HTTPException(status_code=400, detail=f"Google API error: {error}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import docs: {str(e)}")

@app.get("/api/google/slides/{slides_id}")
async def get_slides_content(slides_id: str, current_user: dict = Depends(get_current_user)):
    """Get Google Slides content"""
    try:
        # Get user's Google credentials
        token_data = google_tokens_collection.find_one({"user_id": current_user["id"]})
        if not token_data:
            raise HTTPException(status_code=401, detail="Google account not connected")
        
        # Create credentials object
        credentials = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data["scopes"]
        )
        
        # Build Slides service
        slides_service = build('slides', 'v1', credentials=credentials)
        
        # Get presentation content
        presentation = slides_service.presentations().get(presentationId=slides_id).execute()
        
        return {"presentation": presentation}
        
    except HttpError as error:
        raise HTTPException(status_code=400, detail=f"Google API error: {error}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get slides content: {str(e)}")

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