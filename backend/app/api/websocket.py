from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
import json
import asyncio
from datetime import datetime
from bson import ObjectId

from app.database import Database
from app.auth import AuthHandler

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_to_connection: Dict[str, str] = {}
        self.connection_to_user: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        connection_id = str(id(websocket))
        
        self.active_connections[connection_id] = websocket
        self.user_to_connection[user_id] = connection_id
        self.connection_to_user[connection_id] = user_id
        
        # Update user online status
        db = Database.get_db()
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_online": True, "last_seen": datetime.utcnow()}}
        )
        
        # Notify all users about online status change
        await self.broadcast_user_status(user_id, True)
    
    def disconnect(self, connection_id: str):
        if connection_id in self.connection_to_user:
            user_id = self.connection_to_user[connection_id]
            
            # Clean up mappings
            if user_id in self.user_to_connection:
                del self.user_to_connection[user_id]
            del self.connection_to_user[connection_id]
            
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
            
            # Update user offline status
            db = Database.get_db()
            db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_online": False, "last_seen": datetime.utcnow()}}
            )
            
            # Notify all users about offline status change
            asyncio.create_task(self.broadcast_user_status(user_id, False))
    
    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.user_to_connection:
            connection_id = self.user_to_connection[user_id]
            websocket = self.active_connections.get(connection_id)
            if websocket:
                await websocket.send_json(message)
    
    async def broadcast_user_status(self, user_id: str, is_online: bool):
        """Broadcast user online/offline status to all connected users"""
        message = {
            "type": "user_status",
            "user_id": user_id,
            "is_online": is_online,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(message, exclude_user=user_id)
    
    async def send_call_invite(self, from_user_id: str, to_user_id: str, call_id: str):
        """Send call invitation to specific user"""
        db = Database.get_db()
        
        # Get caller info
        caller = db.users.find_one({"_id": ObjectId(from_user_id)})
        if not caller:
            return
        
        message = {
            "type": "call_invite",
            "call_id": call_id,
            "caller_id": from_user_id,
            "caller_name": caller.get("name", "User"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_personal_message(message, to_user_id)
    
    async def send_call_response(self, call_id: str, from_user_id: str, to_user_id: str, accepted: bool, room_id: str = None):
        """Send call acceptance/rejection response"""
        message = {
            "type": "call_response",
            "call_id": call_id,
            "from_user_id": from_user_id,
            "accepted": accepted,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if accepted and room_id:
            message["room_id"] = room_id
        
        await self.send_personal_message(message, to_user_id)
    
    async def broadcast(self, message: dict, exclude_user: str = None):
        """Broadcast message to all connected users"""
        disconnected = []
        
        for connection_id, websocket in self.active_connections.items():
            try:
                user_id = self.connection_to_user.get(connection_id)
                if user_id != exclude_user:
                    await websocket.send_json(message)
            except:
                disconnected.append(connection_id)
        
        # Clean up disconnected sockets
        for connection_id in disconnected:
            self.disconnect(connection_id)

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Respond to ping to keep connection alive
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                
                elif message_type == "call_invite":
                    # Forward call invite to recipient
                    to_user_id = message.get("to_user_id")
                    call_id = message.get("call_id")
                    if to_user_id and call_id:
                        await manager.send_call_invite(user_id, to_user_id, call_id)
                
                elif message_type == "call_response":
                    # Forward call response to caller
                    call_id = message.get("call_id")
                    to_user_id = message.get("to_user_id")
                    accepted = message.get("accepted", False)
                    room_id = message.get("room_id")
                    
                    if call_id and to_user_id:
                        await manager.send_call_response(
                            call_id, user_id, to_user_id, accepted, room_id
                        )
                
            except json.JSONDecodeError:
                # Invalid JSON, ignore
                pass
            except Exception as e:
                print(f"WebSocket error: {e}")
    
    except WebSocketDisconnect:
        manager.disconnect(str(id(websocket)))