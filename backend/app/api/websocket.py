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
        # Random matching queue: list of {user_id, joined_at, user_name}
        self.random_queue: List[dict] = []
        # Pending offline tasks: user_id -> asyncio.Task (grace period before marking offline)
        self._offline_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        
        # Cancel any pending offline task for this user (they reconnected!)
        if user_id in self._offline_tasks:
            self._offline_tasks[user_id].cancel()
            del self._offline_tasks[user_id]
            logger.info(f"✅ Cancelled offline timer for {user_id} (reconnected)")
        
        self.active_connections[user_id] = websocket
        self.user_status[user_id] = {"is_online": True, "current_call": None}
        logger.info(f"✅ User {user_id} connected. Total: {len(self.active_connections)}")
        
        # Update database to set user online
        try:
            from backend.app.database import Database
            from bson import ObjectId
            db = Database.get_db()
            db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_online": True, "last_seen": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"Failed to update user online status in DB: {e}")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "welcome",
            "user_id": user_id,
            "is_online": True,
            "timestamp": datetime.now().isoformat()
        }, user_id)
        
        # Broadcast online status to ALL other connected users
        await self._broadcast_status_change(user_id, True)

    def disconnect(self, user_id: str):
        """Clean up when user disconnects - uses grace period to avoid flicker on page navigation"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Remove from random queue if present
        self.random_queue = [q for q in self.random_queue if q["user_id"] != user_id]
        
        if user_id in self.user_status:
            # Notify others in same call immediately
            current_call = self.user_status[user_id].get("current_call")
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
        
        # Start grace period before marking offline
        # This prevents flicker when user navigates between pages
        # (e.g. users.html -> call.html causes disconnect then reconnect)
        if user_id in self._offline_tasks:
            self._offline_tasks[user_id].cancel()
        
        self._offline_tasks[user_id] = asyncio.create_task(
            self._delayed_offline(user_id)
        )
        
        logger.info(f"⏳ User {user_id} disconnected, 8s grace period started")
    
    async def _delayed_offline(self, user_id: str):
        """Wait before marking user offline to allow page navigation reconnects"""
        try:
            await asyncio.sleep(8)  # 8 second grace period
            
            # Check if user reconnected during grace period
            if user_id in self.active_connections:
                logger.info(f"✅ User {user_id} reconnected during grace period, staying online")
                return
            
            # User did NOT reconnect - mark offline
            if user_id in self.user_status:
                self.user_status[user_id]["is_online"] = False
            
            # Update database to set user offline
            try:
                from backend.app.database import Database
                from bson import ObjectId
                db = Database.get_db()
                db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {"is_online": False, "last_seen": datetime.utcnow()}}
                )
            except Exception as e:
                logger.error(f"Failed to update user offline status in DB: {e}")
            
            # Broadcast offline status to ALL other connected users
            await self._broadcast_status_change(user_id, False)
            
            logger.info(f"❌ User {user_id} confirmed offline after grace period")
            
        except asyncio.CancelledError:
            # Grace period was cancelled (user reconnected)
            pass
        finally:
            # Clean up the task reference
            self._offline_tasks.pop(user_id, None)

    async def _broadcast_status_change(self, user_id: str, is_online: bool):
        """Broadcast a user's online/offline status to all other connected users"""
        status_message = {
            "type": "user_online" if is_online else "user_offline",
            "user_id": user_id,
            "is_online": is_online,
            "timestamp": datetime.now().isoformat()
        }
        for other_id, ws in list(self.active_connections.items()):
            if other_id != user_id:
                try:
                    await ws.send_json(status_message)
                except Exception:
                    pass  # Don't fail broadcast if one send fails
        logger.info(f"📢 Broadcast: {user_id} is now {'ONLINE' if is_online else 'OFFLINE'} (notified {len(self.active_connections) - 1} users)")

    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user has an active WebSocket connection (real-time check)"""
        return user_id in self.active_connections

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
        """Handle WebRTC signaling messages - forward directly to target user"""
        try:
            signal_type = signal_data.get("type")
            to_user = signal_data.get("to_user_id")
            call_id = signal_data.get("call_id")
            
            logger.info(f"🔧 WebRTC {signal_type} from {from_user} to {to_user}")
            
            if not to_user:
                return {"error": "No target user specified"}
            
            # Forward the signal directly - don't require active_calls validation
            # This ensures signals always get through for call establishment
            success = await self.send_personal_message({
                "type": "webrtc_signal",
                "signal": {**signal_data, "from": from_user},
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

    async def join_random_queue(self, user_id: str, user_name: str):
        """Join the random matching queue"""
        # Check if user is already in queue
        for queued in self.random_queue:
            if queued["user_id"] == user_id:
                logger.info(f"⚠️ User {user_id} already in random queue")
                return {"status": "already_in_queue"}
        
        # Check if there's someone already waiting
        if len(self.random_queue) > 0:
            # Match with first person in queue
            partner = self.random_queue.pop(0)
            partner_id = partner["user_id"]
            partner_name = partner["user_name"]
            
            logger.info(f"🎲 Random match: {user_id} ({user_name}) matched with {partner_id} ({partner_name})")
            
            # Create a call between them
            try:
                from backend.app.database import Database
                from bson import ObjectId
                db = Database.get_db()
                
                # Create call record
                call_data = {
                    "caller_id": partner_id,  # First person who joined queue is caller
                    "receiver_id": user_id,
                    "jitsi_room_id": f"random_{uuid.uuid4().hex[:12]}",
                    "status": "accepted",
                    "created_at": datetime.utcnow(),
                    "started_at": datetime.utcnow(),
                    "is_random_match": True
                }
                result = db.calls.insert_one(call_data)
                call_id = str(result.inserted_id)
                
                # Add to active calls
                self.active_calls[call_id] = {
                    "participants": [partner_id, user_id],
                    "room_id": call_data["jitsi_room_id"],
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Update user status
                if partner_id in self.user_status:
                    self.user_status[partner_id]["current_call"] = call_id
                if user_id in self.user_status:
                    self.user_status[user_id]["current_call"] = call_id
                
                # Notify both users about the match
                match_message = {
                    "type": "random_match_found",
                    "call_id": call_id,
                    "room_id": call_data["jitsi_room_id"],
                    "timestamp": datetime.now().isoformat()
                }
                
                # Send to partner (first person in queue)
                await self.send_personal_message({
                    **match_message,
                    "partner_id": user_id,
                    "partner_name": user_name
                }, partner_id)
                
                # Send to current user
                await self.send_personal_message({
                    **match_message,
                    "partner_id": partner_id,
                    "partner_name": partner_name
                }, user_id)
                
                return {"status": "matched", "call_id": call_id, "partner_id": partner_id}
                
            except Exception as e:
                logger.error(f"❌ Failed to create random match call: {e}")
                return {"status": "error", "message": str(e)}
        else:
            # No one waiting, add to queue
            self.random_queue.append({
                "user_id": user_id,
                "user_name": user_name,
                "joined_at": datetime.utcnow().isoformat()
            })
            logger.info(f"🎲 User {user_id} ({user_name}) joined random queue. Queue size: {len(self.random_queue)}")
            
            return {"status": "waiting", "position": len(self.random_queue)}

    def leave_random_queue(self, user_id: str):
        """Leave the random matching queue"""
        self.random_queue = [q for q in self.random_queue if q["user_id"] != user_id]
        logger.info(f"🎲 User {user_id} left random queue. Queue size: {len(self.random_queue)}")
        return {"status": "left_queue"}

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
                # Keep-alive ping - also update database last_seen for cross-instance online status
                try:
                    from backend.app.database import Database
                    from bson import ObjectId
                    db = Database.get_db()
                    db.users.update_one(
                        {"_id": ObjectId(user_id)},
                        {"$set": {"is_online": True, "last_seen": datetime.utcnow()}}
                    )
                except Exception as e:
                    logger.error(f"Failed to update last_seen on ping: {e}")
                
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
                # Accept call invitation (legacy with invitation_id)
                invitation_id = data.get("invitation_id")
                result = await manager.accept_call_invitation(invitation_id, user_id)
                await manager.send_personal_message({
                    "type": "accept_result",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }, user_id)
            
            elif message_type == "accept_call":
                # Accept call (new direct call_id based)
                call_id = data.get("call_id")
                from_user_id = data.get("from_user_id")
                
                logger.info(f"✅ User {user_id} accepting call {call_id} from {from_user_id}")
                
                # Get acceptor's name and update call in database
                from backend.app.database import Database
                from bson import ObjectId
                db = Database.get_db()
                acceptor = db.users.find_one({"_id": ObjectId(user_id)})
                acceptor_name = acceptor.get("name", "User") if acceptor else "User"
                
                # Update call status to 'accepted' in database (for cross-instance)
                if call_id:
                    try:
                        db.calls.update_one(
                            {"_id": ObjectId(call_id)},
                            {"$set": {
                                "status": "active",
                                "start_time": datetime.utcnow(),
                                "accepted_at": datetime.utcnow()
                            }}
                        )
                        logger.info(f"✅ Updated call {call_id} to active in database")
                    except Exception as e:
                        logger.error(f"Failed to update call status: {e}")
                
                # Notify the caller that the call was accepted
                if from_user_id and from_user_id in manager.active_connections:
                    await manager.send_personal_message({
                        "type": "call_accepted",
                        "call_id": call_id,
                        "partner_id": user_id,
                        "partner_name": acceptor_name,
                        "message": f"{acceptor_name} accepted your call",
                        "timestamp": datetime.now().isoformat()
                    }, from_user_id)
                    logger.info(f"✅ Notified {from_user_id} that call was accepted by {user_id}")
                
                # Send confirmation to acceptor
                await manager.send_personal_message({
                    "type": "accept_result",
                    "success": True,
                    "call_id": call_id,
                    "timestamp": datetime.now().isoformat()
                }, user_id)
                
            elif message_type == "reject_call_invitation":
                # Reject call invitation
                invitation_id = data.get("invitation_id")
                call_id = data.get("call_id")
                from_user_id = data.get("from_user_id")
                
                # Get rejector's name
                from backend.app.database import Database
                from bson import ObjectId
                db = Database.get_db()
                rejector = db.users.find_one({"_id": ObjectId(user_id)})
                rejector_name = rejector.get("name", "User") if rejector else "User"
                
                # Update call status in database to "rejected" so new invites can be sent
                if call_id:
                    try:
                        db.calls.update_one(
                            {"_id": ObjectId(call_id)},
                            {"$set": {
                                "status": "rejected",
                                "rejected_at": datetime.utcnow(),
                                "rejected_by": user_id
                            }}
                        )
                        logger.info(f"✅ Updated call {call_id} to rejected in database")
                    except Exception as e:
                        logger.error(f"Failed to update call rejection status: {e}")
                
                # If we have an invitation_id, use the original flow
                if invitation_id:
                    result = await manager.reject_call_invitation(invitation_id, user_id)
                else:
                    result = {"status": "rejected"}
                
                # Send confirmation to rejector
                await manager.send_personal_message({
                    "type": "reject_result",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }, user_id)
                
                # Notify sender that call was rejected
                if from_user_id and from_user_id in manager.active_connections:
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
                # Handle WebRTC signaling - forward directly without strict validation
                signal_data = data.get("signal", {})
                call_id = data.get("call_id") or signal_data.get("call_id")
                
                # Register call in active_calls for transcription broadcasting  
                if call_id and call_id not in manager.active_calls:
                    try:
                        from backend.app.database import Database
                        from bson import ObjectId
                        db = Database.get_db()
                        call_data = db.calls.find_one({"_id": ObjectId(call_id)})
                        if call_data:
                            manager.active_calls[call_id] = {
                                "participants": [str(call_data["caller_id"]), str(call_data["receiver_id"])],
                                "room_id": call_data.get("jitsi_room_id", ""),
                                "started_at": datetime.now().isoformat(),
                                "status": "active"
                            }
                            logger.info(f"✅ Added call {call_id} to active calls")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not add call to active_calls: {e}")
                
                # Forward signal directly
                result = await manager.handle_webrtc_signal(user_id, signal_data)
                if result.get("error"):
                    logger.warning(f"⚠️ Signal forwarding: {result}")
                
            
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
            
            elif message_type == "join_random_queue":
                # Join random matching queue
                user_name = data.get("user_name", "Anonymous")
                result = await manager.join_random_queue(user_id, user_name)
                await manager.send_personal_message({
                    "type": "random_queue_status",
                    "data": result,
                    "timestamp": datetime.now().isoformat()
                }, user_id)
            
            elif message_type == "leave_random_queue":
                # Leave random matching queue
                result = manager.leave_random_queue(user_id)
                await manager.send_personal_message({
                    "type": "random_queue_left",
                    "data": result,
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

@router.get("/random-queue-status")
async def get_random_queue_status():
    """Get random queue status (for debugging)"""
    return {
        "queue_length": len(manager.random_queue),
        "users_waiting": [q["user_id"] for q in manager.random_queue]
    }