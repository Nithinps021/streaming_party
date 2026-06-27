from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import json
import time
import httpx
from typing import Dict, List

from room_manager import room_manager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        # room_id -> list of websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def broadcast(self, message: str, room_id: str, exclude: WebSocket = None):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                if connection != exclude:
                    await connection.send_text(message)

manager = ConnectionManager()

class RoomResponse(BaseModel):
    room_id: str
    admin_token: str

@app.post("/api/room", response_model=RoomResponse)
async def create_room():
    room_id = str(uuid.uuid4())[:8]
    admin_token = str(uuid.uuid4())
    
    await room_manager.create_room(room_id)
    # Store admin token mapping temporarily in redis or just in memory?
    # Better in redis:
    await room_manager.redis.setex(f"admin:{room_id}", 12 * 3600, admin_token)
    
    return RoomResponse(room_id=room_id, admin_token=admin_token)

@app.get("/api/room/{room_id}")
async def get_room(room_id: str):
    state = await room_manager.get_room_state(room_id)
    if not state:
        raise HTTPException(status_code=404, detail="Room not found or expired")
    return state

@app.get("/api/stream/{room_id}/{file_id}")
async def stream_video(room_id: str, file_id: str, request: Request):
    # Retrieve the stored Google Drive access token for this room
    access_token = await room_manager.redis.get(f"drive_token:{room_id}")

    if access_token:
        # Use Google Drive API v3 with Bearer auth for authenticated downloads
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
        headers = {"Authorization": f"Bearer {access_token}"}
    else:
        # Fallback for public files
        url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
        headers = {}

    if "range" in request.headers:
        headers["Range"] = request.headers["range"]

    client = httpx.AsyncClient(follow_redirects=True, timeout=30.0)
    req = client.build_request("GET", url, headers=headers)

    r = await client.send(req, stream=True)

    async def stream_generator():
        try:
            async for chunk in r.aiter_bytes(chunk_size=1024 * 1024):
                yield chunk
        finally:
            await r.aclose()
            await client.aclose()

    response_headers = {
        "Accept-Ranges": "bytes",
    }
    for h in ["Content-Type", "Content-Range", "Content-Length"]:
        if h.lower() in r.headers:
            response_headers[h] = r.headers[h.lower()]

    return StreamingResponse(
        stream_generator(),
        status_code=r.status_code,
        headers=response_headers
    )

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, admin_token: str = None, username: str = "Anonymous"):
    state = await room_manager.get_room_state(room_id)
    if not state:
        await websocket.close(code=1008)
        return
        
    actual_admin_token = await room_manager.redis.get(f"admin:{room_id}")
    is_admin = (admin_token == actual_admin_token)

    await manager.connect(websocket, room_id)
    
    # Send current state and chat history on connect
    chat_history = await room_manager.get_chat_history(room_id)
    await websocket.send_text(json.dumps({
        "type": "init",
        "state": state,
        "chat_history": chat_history,
        "is_admin": is_admin
    }))

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type in ["play", "pause", "seek"]:
                if not is_admin:
                    continue # Only admin can control playback
                    
                current_state = await room_manager.get_room_state(room_id)
                if current_state:
                    state = current_state
                    
                is_playing = (msg_type == "play") or (state["is_playing"] if msg_type == "seek" else False)
                current_time = message.get("time", state["current_time"])
                
                await room_manager.update_room_state(room_id, is_playing, current_time)
                # broadcast to everyone else
                await manager.broadcast(data, room_id, exclude=websocket)
                
            elif msg_type == "change_video":
                if not is_admin:
                    continue
                new_url = message.get("url")
                drive_access_token = message.get("access_token")
                if new_url:
                    # Store Google Drive access token for this room so the
                    # proxy endpoint can authenticate downloads
                    if drive_access_token:
                        ttl_token = await room_manager.redis.ttl(f"room:{room_id}")
                        if ttl_token > 0:
                            await room_manager.redis.setex(
                                f"drive_token:{room_id}", ttl_token, drive_access_token
                            )

                    state = await room_manager.get_room_state(room_id)
                    state["video_url"] = new_url
                    state["is_playing"] = False
                    state["current_time"] = 0.0
                    state["updated_at"] = time.time()

                    ttl = await room_manager.redis.ttl(f"room:{room_id}")
                    if ttl > 0:
                        await room_manager.redis.setex(f"room:{room_id}", ttl, json.dumps(state))

                    # broadcast sync to everyone (including admin to confirm)
                    await manager.broadcast(json.dumps({
                        "type": "sync",
                        "state": state
                    }), room_id)
                    
            elif msg_type == "chat":
                text = message.get("text", "")
                if text:
                    msg = await room_manager.add_chat_message(room_id, username, text)
                    broadcast_msg = json.dumps({
                        "type": "chat",
                        "message": msg
                    })
                    await manager.broadcast(broadcast_msg, room_id)
                    
            elif msg_type == "sync_request":
                # client asks for current state
                current_state = await room_manager.get_room_state(room_id)
                await websocket.send_text(json.dumps({
                    "type": "sync",
                    "state": current_state
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
