import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
import bcrypt

load_dotenv()

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")
JWT_SECRET = os.environ.get("JWT_SECRET")

# MongoDB setup
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Collections
users_col = db["users"]
messages_col = db["messages"]
conversations_col = db["conversations"]

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, data: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(user_id)

    def is_online(self, user_id: str) -> bool:
        return user_id in self.active_connections

manager = ConnectionManager()

# Pydantic models
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    about: str = "Hey there! I am using WhatsApp"

class LoginRequest(BaseModel):
    email: str
    password: str

class SendMessageRequest(BaseModel):
    conversation_id: str
    content: str
    message_type: str = "text"

class CreateConversationRequest(BaseModel):
    participant_ids: list[str]
    is_group: bool = False
    group_name: Optional[str] = None

class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    about: Optional[str] = None
    avatar: Optional[str] = None

class MarkReadRequest(BaseModel):
    conversation_id: str

# Seed data
SEED_USERS = [
    {"username": "Saswata", "email": "saswata@whatsapp2.com", "password": "password123", "avatar": "/img/109316527.jpg", "about": "Building cool stuff!"},
    {"username": "Ananya", "email": "ananya@whatsapp2.com", "password": "password123", "avatar": "/img/girl-profile.jpg", "about": "Living my best life"},
    {"username": "Arjun Mehta", "email": "arjun@whatsapp2.com", "password": "password123", "avatar": "/img/arjun-profile.jpg", "about": "Coffee & Code"},
    {"username": "Priya Sharma", "email": "priya@whatsapp2.com", "password": "password123", "avatar": "/img/79feb1611dddcbce7910e0c1081df6e2.jpg", "about": "Traveler at heart"},
    {"username": "Vikram Patel", "email": "vikram@whatsapp2.com", "password": "password123", "avatar": "/img/e5wnacz2aaaa.jpg", "about": "Foodie & Explorer"},
    {"username": "Neha Gupta", "email": "neha@whatsapp2.com", "password": "password123", "avatar": "/img/neha-profile.jpg", "about": "Bookworm"},
    {"username": "Amit Kumar", "email": "amit@whatsapp2.com", "password": "password123", "avatar": "/img/amit-profile.jpg", "about": "Gym & Gains"},
    {"username": "Rohan Singh", "email": "rohan@whatsapp2.com", "password": "password123", "avatar": "/img/rohan-profile.jpg", "about": "Music is life"},
    {"username": "Kavita Reddy", "email": "kavita@whatsapp2.com", "password": "password123", "avatar": "/img/kavita-profile.jpg", "about": "Art & Design"},
    {"username": "Dev Team", "email": "devteam@whatsapp2.com", "password": "password123", "avatar": "/img/devteam-profile.jpg", "about": "We build things"},
    {"username": "Sanjay Iyer", "email": "sanjay@whatsapp2.com", "password": "password123", "avatar": "/img/sanjay-profile.jpg", "about": "Photography enthusiast"},
]

SEED_MESSAGES = [
    {"from_idx": 1, "to_idx": 0, "content": "Hey! How are you?", "minutes_ago": 120},
    {"from_idx": 0, "to_idx": 1, "content": "I'm great! Working on a project", "minutes_ago": 118},
    {"from_idx": 1, "to_idx": 0, "content": "That sounds exciting! What project?", "minutes_ago": 115},
    {"from_idx": 0, "to_idx": 1, "content": "Building a WhatsApp clone 😄", "minutes_ago": 110},
    {"from_idx": 1, "to_idx": 0, "content": "Wow that's so cool! Can I see it?", "minutes_ago": 5},
    {"from_idx": 2, "to_idx": 0, "content": "Bro, let's meet for coffee tomorrow", "minutes_ago": 60},
    {"from_idx": 0, "to_idx": 2, "content": "Sure! What time works?", "minutes_ago": 55},
    {"from_idx": 2, "to_idx": 0, "content": "How about 11am at the usual place?", "minutes_ago": 50},
    {"from_idx": 3, "to_idx": 0, "content": "Did you see the photos from the trip?", "minutes_ago": 300},
    {"from_idx": 0, "to_idx": 3, "content": "Not yet! Send them over", "minutes_ago": 295},
    {"from_idx": 3, "to_idx": 0, "content": "Will share on the group 📸", "minutes_ago": 290},
    {"from_idx": 4, "to_idx": 0, "content": "Found an amazing restaurant near your place", "minutes_ago": 1440},
    {"from_idx": 5, "to_idx": 0, "content": "Have you read the new book by Harari?", "minutes_ago": 2880},
    {"from_idx": 6, "to_idx": 0, "content": "Gym session at 6am?", "minutes_ago": 4320},
    {"from_idx": 7, "to_idx": 0, "content": "Check out this playlist 🎵", "minutes_ago": 5000},
    {"from_idx": 8, "to_idx": 0, "content": "I made a new design, want feedback!", "minutes_ago": 7000},
    {"from_idx": 9, "to_idx": 0, "content": "Sprint review at 3pm today", "minutes_ago": 8000},
    {"from_idx": 10, "to_idx": 0, "content": "Great photos from the hackathon!", "minutes_ago": 10000},
]


async def seed_database():
    existing = await users_col.count_documents({})
    if existing > 0:
        return

    user_ids = []
    for user_data in SEED_USERS:
        user_id = str(uuid.uuid4())
        hashed = bcrypt.hashpw(user_data["password"].encode(), bcrypt.gensalt()).decode()
        await users_col.insert_one({
            "user_id": user_id,
            "username": user_data["username"],
            "email": user_data["email"],
            "password": hashed,
            "avatar": user_data["avatar"],
            "about": user_data["about"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_seen": datetime.now(timezone.utc).isoformat(),
        })
        user_ids.append(user_id)

    # Create conversations and messages
    for msg_data in SEED_MESSAGES:
        from_id = user_ids[msg_data["from_idx"]]
        to_id = user_ids[msg_data["to_idx"]]
        sorted_ids = sorted([from_id, to_id])
        conv_id = f"{sorted_ids[0]}_{sorted_ids[1]}"

        existing_conv = await conversations_col.find_one({"conversation_id": conv_id})
        if not existing_conv:
            await conversations_col.insert_one({
                "conversation_id": conv_id,
                "is_group": False,
                "participants": [from_id, to_id],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        msg_time = datetime.now(timezone.utc) - timedelta(minutes=msg_data["minutes_ago"])
        msg_id = str(uuid.uuid4())
        await messages_col.insert_one({
            "message_id": msg_id,
            "conversation_id": conv_id,
            "sender_id": from_id,
            "content": msg_data["content"],
            "message_type": "text",
            "created_at": msg_time.isoformat(),
            "read_by": [from_id],
        })

    # Create indexes
    await users_col.create_index("user_id", unique=True)
    await users_col.create_index("email", unique=True)
    await messages_col.create_index("conversation_id")
    await messages_col.create_index("created_at")
    await conversations_col.create_index("conversation_id", unique=True)
    await conversations_col.create_index("participants")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed_database()
    yield

app = FastAPI(title="WhatsApp2 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(authorization: str = None):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    token = authorization.replace("Bearer ", "")
    user_id = verify_token(token)
    user = await users_col.find_one({"user_id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---- Auth Routes ----
@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    existing = await users_col.find_one({"email": req.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    await users_col.insert_one({
        "user_id": user_id,
        "username": req.username,
        "email": req.email,
        "password": hashed,
        "avatar": "",
        "about": req.about,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat(),
    })

    token = create_token(user_id)
    return {"token": token, "user_id": user_id, "username": req.username}


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    user = await users_col.find_one({"email": req.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not bcrypt.checkpw(req.password.encode(), user["password"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(user["user_id"])
    return {
        "token": token,
        "user_id": user["user_id"],
        "username": user["username"],
        "avatar": user.get("avatar", ""),
        "about": user.get("about", ""),
    }


@app.get("/api/auth/me")
async def get_me(authorization: str = Query(None)):
    user = await get_current_user(authorization)
    return user


# ---- Users Routes ----
@app.get("/api/users")
async def get_users(authorization: str = Query(None)):
    user = await get_current_user(authorization)
    all_users = await users_col.find(
        {"user_id": {"$ne": user["user_id"]}},
        {"_id": 0, "password": 0}
    ).to_list(100)

    for u in all_users:
        u["is_online"] = manager.is_online(u["user_id"])

    return all_users


@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    user = await users_col.find_one({"user_id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["is_online"] = manager.is_online(user_id)
    return user


@app.put("/api/users/profile")
async def update_profile(req: UpdateProfileRequest, authorization: str = Query(None)):
    user = await get_current_user(authorization)
    update_data = {}
    if req.username:
        update_data["username"] = req.username
    if req.about is not None:
        update_data["about"] = req.about
    if req.avatar is not None:
        update_data["avatar"] = req.avatar
    if update_data:
        await users_col.update_one({"user_id": user["user_id"]}, {"$set": update_data})
    return {"status": "updated"}


# ---- Conversation Routes ----
@app.get("/api/conversations")
async def get_conversations(authorization: str = Query(None)):
    user = await get_current_user(authorization)
    user_id = user["user_id"]

    convs = await conversations_col.find(
        {"participants": user_id},
        {"_id": 0}
    ).to_list(100)

    result = []
    for conv in convs:
        last_msg = await messages_col.find_one(
            {"conversation_id": conv["conversation_id"]},
            {"_id": 0},
            sort=[("created_at", -1)]
        )

        unread = await messages_col.count_documents({
            "conversation_id": conv["conversation_id"],
            "sender_id": {"$ne": user_id},
            "read_by": {"$nin": [user_id]}
        })

        other_participants = []
        for pid in conv["participants"]:
            if pid != user_id:
                p = await users_col.find_one({"user_id": pid}, {"_id": 0, "password": 0})
                if p:
                    p["is_online"] = manager.is_online(pid)
                    other_participants.append(p)

        result.append({
            "conversation_id": conv["conversation_id"],
            "is_group": conv.get("is_group", False),
            "group_name": conv.get("group_name"),
            "participants": other_participants,
            "last_message": last_msg,
            "unread_count": unread,
            "created_at": conv.get("created_at"),
        })

    result.sort(key=lambda x: x["last_message"]["created_at"] if x["last_message"] else "", reverse=True)
    return result


@app.post("/api/conversations")
async def create_conversation(req: CreateConversationRequest, authorization: str = Query(None)):
    user = await get_current_user(authorization)
    user_id = user["user_id"]

    all_participants = list(set([user_id] + req.participant_ids))

    if not req.is_group and len(all_participants) == 2:
        sorted_ids = sorted(all_participants)
        conv_id = f"{sorted_ids[0]}_{sorted_ids[1]}"
        existing = await conversations_col.find_one({"conversation_id": conv_id})
        if existing:
            return {"conversation_id": conv_id}
    else:
        conv_id = str(uuid.uuid4())

    await conversations_col.insert_one({
        "conversation_id": conv_id,
        "is_group": req.is_group,
        "group_name": req.group_name,
        "participants": all_participants,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"conversation_id": conv_id}


# ---- Messages Routes ----
@app.get("/api/messages/{conversation_id}")
async def get_messages(conversation_id: str, limit: int = 50, before: str = None, authorization: str = Query(None)):
    user = await get_current_user(authorization)

    query = {"conversation_id": conversation_id}
    if before:
        query["created_at"] = {"$lt": before}

    msgs = await messages_col.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)

    msgs.reverse()
    return msgs


@app.post("/api/messages")
async def send_message(req: SendMessageRequest, authorization: str = Query(None)):
    user = await get_current_user(authorization)
    user_id = user["user_id"]

    conv = await conversations_col.find_one({"conversation_id": req.conversation_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if user_id not in conv["participants"]:
        raise HTTPException(status_code=403, detail="Not a participant")

    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    message_doc = {
        "message_id": msg_id,
        "conversation_id": req.conversation_id,
        "sender_id": user_id,
        "content": req.content,
        "message_type": req.message_type,
        "created_at": now,
        "read_by": [user_id],
    }

    await messages_col.insert_one(message_doc)

    # Broadcast to other participants
    broadcast_data = {
        "type": "new_message",
        "message_id": msg_id,
        "conversation_id": req.conversation_id,
        "sender_id": user_id,
        "sender_name": user.get("username", ""),
        "sender_avatar": user.get("avatar", ""),
        "content": req.content,
        "message_type": req.message_type,
        "created_at": now,
        "read_by": [user_id],
    }

    for pid in conv["participants"]:
        if pid != user_id:
            await manager.send_to_user(pid, broadcast_data)

    return {
        "message_id": msg_id,
        "conversation_id": req.conversation_id,
        "sender_id": user_id,
        "content": req.content,
        "message_type": req.message_type,
        "created_at": now,
        "read_by": [user_id],
    }


@app.post("/api/messages/read")
async def mark_messages_read(req: MarkReadRequest, authorization: str = Query(None)):
    user = await get_current_user(authorization)
    user_id = user["user_id"]

    result = await messages_col.update_many(
        {
            "conversation_id": req.conversation_id,
            "sender_id": {"$ne": user_id},
            "read_by": {"$nin": [user_id]}
        },
        {"$addToSet": {"read_by": user_id}}
    )

    # Notify sender that messages are read
    conv = await conversations_col.find_one({"conversation_id": req.conversation_id})
    if conv:
        for pid in conv["participants"]:
            if pid != user_id:
                await manager.send_to_user(pid, {
                    "type": "messages_read",
                    "conversation_id": req.conversation_id,
                    "read_by": user_id,
                })

    return {"modified": result.modified_count}


# ---- WebSocket ----
@app.websocket("/api/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        user_id = verify_token(token)
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect(user_id, websocket)

    # Update last seen
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"last_seen": datetime.now(timezone.utc).isoformat()}}
    )

    # Broadcast online status
    user = await users_col.find_one({"user_id": user_id}, {"_id": 0, "password": 0})
    convs = await conversations_col.find({"participants": user_id}).to_list(100)
    online_peers = set()
    for conv in convs:
        for pid in conv["participants"]:
            if pid != user_id:
                online_peers.add(pid)

    for pid in online_peers:
        await manager.send_to_user(pid, {
            "type": "user_online",
            "user_id": user_id,
        })

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "typing":
                conv = await conversations_col.find_one({"conversation_id": msg["conversation_id"]})
                if conv:
                    for pid in conv["participants"]:
                        if pid != user_id:
                            await manager.send_to_user(pid, {
                                "type": "typing",
                                "conversation_id": msg["conversation_id"],
                                "user_id": user_id,
                            })

            elif msg.get("type") == "stop_typing":
                conv = await conversations_col.find_one({"conversation_id": msg["conversation_id"]})
                if conv:
                    for pid in conv["participants"]:
                        if pid != user_id:
                            await manager.send_to_user(pid, {
                                "type": "stop_typing",
                                "conversation_id": msg["conversation_id"],
                                "user_id": user_id,
                            })

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(user_id)
        await users_col.update_one(
            {"user_id": user_id},
            {"$set": {"last_seen": datetime.now(timezone.utc).isoformat()}}
        )
        for pid in online_peers:
            await manager.send_to_user(pid, {
                "type": "user_offline",
                "user_id": user_id,
            })


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "WhatsApp2"}
