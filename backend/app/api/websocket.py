import json
import logging
import uuid
from typing import Dict, Set, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Store active connections: user_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Store pending call invitations
        self.pending_invitations: Dict[str, dict] = {}
        # Store active calls: call_id -> {participants: [], room_id: str}
        self.active_calls: Dict[str, dict] = {}
        # Track user status: user_id -> {"is_online": bool, "current_call": call_id or None}
        self.user_status: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_status[user_id] = {"is_online": True, "current_call": None}
        logger.info(f"✅ User {user_id} connected. Total: {len(self.active_connections)}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "welcome",
            "user_id": user_id,
            "is_online": True,
            "timestamp": datetime.now().isoformat()
        }, user_id)

    def disconnect(self, user_id: str):
        """Clean up when user disconnects"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        if user_id in self.user_status:
            self.user_status[user_id]["is_online"] = False
            # Notify others in same call
            current_call = self.user_status[user_id]["current_call"]
            if current_call and current_call in self.active_calls:
                participants = self.active_calls[current_call]["participants"]
                for participant in participants:
                    if participant != user_id and participant in self.active_connections:
                        asyncio.create_task(
                            self.send_personal_message({
                                "type": "user_left_call",
                                "user_id": user_id,
                                "call_id": current_call,
                                "timestamp": datetime.now().isoformat()
                            }, participant)
                        )
                # Remove from active call
                if user_id in participants:
                    participants.remove(user_id)
        
        logger.info(f"❌ User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                logger.debug(f"📤 Sent {message.get('type')} to {user_id}")
                return True
            except Exception as e:
                logger.error(f"❌ Error sending to {user_id}: {e}")
                self.disconnect(user_id)
                return False
        logger.warning(f"⚠️ User {user_id} not connected")
        return False

    async def send_call_invite(self, from_user_id: str, to_user_id: str, call_id: str, caller_name: str = None):
        """Simple call invite notification (used by /api/calls/invite endpoint)"""
        logger.info(f"📞 Sending call invite from {from_user_id} to {to_user_id} for call {call_id}")
        
        # Check if receiver is actually online
        if to_user_id not in self.active_connections:
            logger.warning(f"⚠️ User {to_user_id} is not connected via WebSocket")
            return False
        
        # Send notification to receiver
        success = await self.send_personal_message({
            "type": "call_invite",
            "from_user_id": from_user_id,
            "call_id": call_id,
            "caller_name": caller_name or "Someone",
            "timestamp": datetime.now().isoformat()
        }, to_user_id)
        
        if success:
            logger.info(f"✅ Call invite sent to {to_user_id}")
        else:
            logger.warning(f"⚠️ Failed to send call invite to {to_user_id} - user not connected")
        
        return success
    
    async def broadcast_transcription(self, call_id: str, speaker_id: str, speaker_role: str, text: str):
        """Broadcast real-time transcription to all participants in a call"""
        if call_id not in self.active_calls:
            return False
        
        participants = self.active_calls[call_id]["participants"]
        
        message = {
            "type": "transcription",
            "call_id": call_id,
            "speaker_id": speaker_id,
            "speaker_role": speaker_role,  # "caller" or "receiver"
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all participants
        for participant in participants:
            if participant in self.active_connections:
                await self.send_personal_message(message, participant)

    async def send_call_invitation(self, from_user: str, to_user: str, call_id: str, call_data: dict):
        """Send call invitation to receiver (legacy method for WebSocket messages)"""
        logger.info(f"📞 Sending call invitation from {from_user} to {to_user} for call {call_id}")
        
        # Store invitation
        invitation_id = str(uuid.uuid4())
        self.pending_invitations[invitation_id] = {
            "from_user": from_user,
            "to_user": to_user,
            "call_id": call_id,
            "call_data": call_data,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        # Send notification to receiver
        success = await self.send_personal_message({
            "type": "call_invitation",
            "invitation_id": invitation_id,
            "from_user": from_user,
            "call_id": call_id,
            "call_data": call_data,
            "timestamp": datetime.now().isoformat()
        }, to_user)
        
        if success:
            logger.info(f"✅ Call invitation sent to {to_user}")
            # Also notify caller that invitation was sent
            await self.send_personal_message({
                "type": "invitation_sent",
                "to_user": to_user,
                "call_id": call_id,
                "timestamp": datetime.now().isoformat()
            }, from_user)
        
        return success

    async def accept_call_invitation(self, invitation_id: str, user_id: str):
        """Accept a call invitation"""
        if invitation_id not in self.pending_invitations:
            return {"error": "Invitation not found"}
        
        invitation = self.pending_invitations[invitation_id]
        
        if invitation["to_user"] != user_id:
            return {"error": "Not authorized"}
        
        if invitation["status"] != "pending":
            return {"error": f"Invitation already {invitation['status']}"}
        
        # Update invitation status
        invitation["status"] = "accepted"
        invitation["accepted_at"] = datetime.now().isoformat()
        
        # Create active call record
        call_id = invitation["call_id"]
        from_user = invitation["from_user"]
        
        self.active_calls[call_id] = {
            "participants": [from_user, user_id],
            "room_id": f"room_{call_id}",
            "started_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        # Update user status
        self.user_status[from_user]["current_call"] = call_id
        self.user_status[user_id]["current_call"] = call_id
        
        # Notify both users
        await self.send_personal_message({
            "type": "call_accepted",
            "invitation_id": invitation_id,
            "call_id": call_id,
            "room_id": f"room_{call_id}",
            "partner_id": user_id,
            "timestamp": datetime.now().isoformat()
        }, from_user)
        
        await self.send_personal_message({
            "type": "call_started",
            "invitation_id": invitation_id,
            "call_id": call_id,
            "room_id": f"room_{call_id}",
            "partner_id": from_user,
            "timestamp": datetime.now().isoformat()
        }, user_id)
        
        logger.info(f"✅ Call {call_id} started between {from_user} and {user_id}")
        
        return {
            "call_id": call_id,
            "room_id": f"room_{call_id}",
            "partner_id": from_user,
            "status": "accepted"
        }

    async def reject_call_invitation(self, invitation_id: str, user_id: str):
        """Reject a call invitation"""
        if invitation_id not in self.pending_invitations:
            return {"error": "Invitation not found"}
        
        invitation = self.pending_invitations[invitation_id]
        
        if invitation["to_user"] != user_id:
            return {"error": "Not authorized"}
        
        invitation["status"] = "rejected"
        invitation["rejected_at"] = datetime.now().isoformat()
        
        # Notify caller
        await self.send_personal_message({
            "type": "call_rejected",
            "invitation_id": invitation_id,
            "call_id": invitation["call_id"],
            "by_user": user_id,
            "timestamp": datetime.now().isoformat()
        }, invitation["from_user"])
        
        logger.info(f"❌ Call invitation {invitation_id} rejected by {user_id}")
        
        return {"status": "rejected"}

    async def handle_webrtc_signal(self, from_user: str, signal_data: dict):
        """Handle WebRTC signaling messages"""
        try:
            signal_type = signal_data.get("type")
            to_user = signal_data.get("to_user_id")
            call_id = signal_data.get("call_id")
            
            logger.debug(f"🔧 WebRTC {signal_type} from {from_user} to {to_user}")
            
            # Validate both users are in the same call
            if call_id not in self.active_calls:
                return {"error": "Call not found"}
            
            if from_user not in self.active_calls[call_id]["participants"]:
                return {"error": "User not in call"}
            
            if to_user not in self.active_calls[call_id]["participants"]:
                return {"error": "Target not in call"}
            
            # Forward the signal
            success = await self.send_personal_message({
                "type": "webrtc_signal",
                "signal": signal_data,
                "from_user": from_user,
                "timestamp": datetime.now().isoformat()
            }, to_user)
            
            if success:
                return {"status": f"{signal_type}_forwarded"}
            else:
                return {"error": "user_not_connected"}
                
        except Exception as e:
            logger.error(f"❌ Error handling WebRTC signal: {e}")
            return {"error": str(e)}

    async def end_call(self, call_id: str, user_id: str):
        """End a call"""
        if call_id not in self.active_calls:
            return {"error": "Call not found"}
        
        if user_id not in self.active_calls[call_id]["participants"]:
            return {"error": "User not in call"}
        
        # Notify all participants
        for participant in self.active_calls[call_id]["participants"]:
            if participant != user_id:
                await self.send_personal_message({
                    "type": "call_ended",
                    "call_id": call_id,
                    "ended_by": user_id,
                    "timestamp": datetime.now().isoformat()
                }, participant)
        
        # Update user status
        for participant in self.active_calls[call_id]["participants"]:
            if participant in self.user_status:
                self.user_status[participant]["current_call"] = None
        
        # Remove call from active calls
        del self.active_calls[call_id]
        
        logger.info(f"📞 Call {call_id} ended by {user_id}")
        
        return {"status": "call_ended"}

# Global connection manager instance
manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """Main WebSocket endpoint for signaling"""
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            logger.debug(f"📨 {message_type} from {user_id}")
            
            if message_type == "ping":
                # Keep-alive ping
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, user_id)
                
            elif message_type == "send_call_invitation":
                # Send call invitation
                to_user = data.get("to_user")
                call_id = data.get("call_id")
                call_data = data.get("call_data", {})
                
                success = await manager.send_call_invitation(user_id, to_user, call_id, call_data)
                await manager.send_personal_message({
                    "type": "invitation_result",
                    "success": success,
                    "to_user": to_user,
                    "call_id": call_id,
                    "timestamp": datetime.now().isoformat()
                }, user_id)
                
            elif message_type == "accept_call_invitation":
                # Accept call invitation
                invitation_id = data.get("invitation_id")
                result = await manager.accept_call_invitation(invitation_id, user_id)
                await manager.send_personal_message({
                    "type": "accept_result",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }, user_id)
                
            elif message_type == "reject_call_invitation":
                # Reject call invitation
                invitation_id = data.get("invitation_id")
                call_id = data.get("call_id")
                from_user_id = data.get("from_user_id")
                
                result = await manager.reject_call_invitation(invitation_id, user_id)
                
                # Send confirmation to rejector
                await manager.send_personal_message({
                    "type": "reject_result",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }, user_id)
                
                # Notify sender that call was rejected
                if from_user_id and from_user_id in manager.active_connections:
                    # Get rejector's name
                    from backend.app.database import Database
                    from bson import ObjectId
                    db = Database.get_db()
                    rejector = db.users.find_one({"_id": ObjectId(user_id)})
                    rejector_name = rejector.get("name", "User") if rejector else "User"
                    
                    await manager.send_personal_message({
                        "type": "call_rejected",
                        "call_id": call_id,
                        "rejected_by": user_id,
                        "rejected_by_name": rejector_name,
                        "message": f"{rejector_name} declined your call",
                        "timestamp": datetime.now().isoformat()
                    }, from_user_id)
                    logger.info(f"✅ Notified {from_user_id} that call was rejected by {user_id}")
                
            elif message_type == "webrtc_signal":
                # Handle WebRTC signaling
                signal_data = data.get("signal", {})
                call_id = data.get("call_id") or signal_data.get("call_id")
                
                # Ensure call is in active_calls for transcription broadcasting
                if call_id and call_id not in manager.active_calls:
                    # Get call info to determine participants
                    from backend.app.database import Database
                    from bson import ObjectId
                    db = Database.get_db()
                    try:
                        call_data = db.calls.find_one({"_id": ObjectId(call_id)})
                        if call_data:
                            manager.active_calls[call_id] = {
                                "participants": [str(call_data["caller_id"]), str(call_data["receiver_id"])],
                                "room_id": call_data["jitsi_room_id"],
                                "started_at": datetime.now().isoformat(),
                                "status": "active"
                            }
                            logger.info(f"✅ Added call {call_id} to active calls")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not add call to active_calls: {e}")
                
                result = await manager.handle_webrtc_signal(user_id, signal_data)
                await manager.send_personal_message({
                    "type": "signal_result",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }, user_id)
            
            elif message_type == "transcription":
                # Handle incoming transcription to broadcast to partner
                call_id = data.get("call_id")
                text = data.get("text")
                speaker_role = data.get("speaker_role")
                
                if call_id and call_id in manager.active_calls:
                    await manager.broadcast_transcription(
                        call_id=call_id,
                        speaker_id=user_id,
                        speaker_role=speaker_role,
                        text=text
                    )
                
            elif message_type == "end_call":
                # End a call
                call_id = data.get("call_id")
                result = await manager.end_call(call_id, user_id)
                await manager.send_personal_message({
                    "type": "end_call_result",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }, user_id)
                
            elif message_type == "check_online":
                # Check if user is online
                target_user = data.get("target_user")
                is_online = target_user in manager.active_connections
                await manager.send_personal_message({
                    "type": "online_status",
                    "user_id": target_user,
                    "is_online": is_online,
                    "timestamp": datetime.now().isoformat()
                }, user_id)
                
            else:
                logger.warning(f"⚠️ Unknown message type: {message_type}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": datetime.now().isoformat()
                }, user_id)
                
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected: {user_id}")
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"❌ WebSocket error for {user_id}: {e}")
        manager.disconnect(user_id)

@router.get("/online-users")
async def get_online_users():
    """Get list of online users"""
    return {
        "online_users": list(manager.active_connections.keys()),
        "total": len(manager.active_connections)
    }