import json
import datetime
from typing import List, Dict, Optional
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request, Form, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import Message, Order, User
from app.auth import get_current_user_optional, get_current_user, decode_token
from app.services.jitsi import generate_jitsi_room
from app.config import settings

router = APIRouter(tags=["Chat & Calls"])

# Connection Manager for WebSocket rooms
class ConnectionManager:
    def __init__(self):
        # order_id -> list of active WebSockets
        self.active_rooms: Dict[int, List[WebSocket]] = {}

    async def connect(self, order_id: int, websocket: WebSocket):
        await websocket.accept()
        if order_id not in self.active_rooms:
            self.active_rooms[order_id] = []
        self.active_rooms[order_id].append(websocket)

    def disconnect(self, order_id: int, websocket: WebSocket):
        if order_id in self.active_rooms:
            if websocket in self.active_rooms[order_id]:
                self.active_rooms[order_id].remove(websocket)
            if not self.active_rooms[order_id]:
                del self.active_rooms[order_id]

    async def broadcast(self, order_id: int, message_data: dict):
        if order_id in self.active_rooms:
            payload = json.dumps(message_data)
            for connection in self.active_rooms[order_id]:
                try:
                    await connection.send_text(payload)
                except Exception:
                    pass

manager = ConnectionManager()

@router.websocket("/ws/orders/{order_id}")
async def websocket_chat_endpoint(websocket: WebSocket, order_id: int):
    # Retrieve cookie from websocket headers
    token = websocket.cookies.get("gigly_session")
    payload = decode_token(token) if token else None
    
    if not payload:
        await websocket.close(code=1008)
        return

    user_id = int(payload.get("sub"))
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or user_id not in [order.buyer_id, order.seller_id]:
            await websocket.close(code=1008)
            return

        user = db.query(User).filter(User.id == user_id).first()
        await manager.connect(order_id, websocket)

        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            content = data.get("content", "").strip()
            
            if content:
                msg = Message(
                    order_id=order_id,
                    sender_id=user.id,
                    content=content,
                    is_system_message=False
                )
                db.add(msg)
                db.commit()
                db.refresh(msg)

                broadcast_payload = {
                    "id": msg.id,
                    "sender_id": user.id,
                    "sender_name": user.full_name,
                    "sender_avatar": user.avatar_url,
                    "content": msg.content,
                    "is_system_message": False,
                    "created_at": msg.created_at.strftime("%H:%M"),
                    "jitsi_meeting_url": None
                }
                await manager.broadcast(order_id, broadcast_payload)

    except WebSocketDisconnect:
        manager.disconnect(order_id, websocket)
    except Exception as e:
        manager.disconnect(order_id, websocket)
    finally:
        db.close()

@router.get("/api/orders/{order_id}/messages")
async def get_messages(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or user.id not in [order.buyer_id, order.seller_id]:
        return JSONResponse({"success": False, "error": "No autorizado"}, status_code=403)

    messages = db.query(Message).filter(Message.order_id == order_id).order_by(Message.created_at.asc()).all()
    results = []
    for m in messages:
        sender_name = "Sistema Gigly" if m.is_system_message else (m.sender.full_name if m.sender else "Usuario")
        sender_avatar = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150" if not m.sender else m.sender.avatar_url
        results.append({
            "id": m.id,
            "sender_id": m.sender_id,
            "sender_name": sender_name,
            "sender_avatar": sender_avatar,
            "content": m.content,
            "is_system_message": m.is_system_message,
            "jitsi_meeting_url": m.jitsi_meeting_url,
            "attachment_url": m.attachment_url,
            "created_at": m.created_at.strftime("%H:%M")
        })

    return JSONResponse({"success": True, "messages": results})

@router.post("/api/orders/{order_id}/messages")
async def send_rest_message(
    order_id: int,
    content: str = Form(...),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or user.id not in [order.buyer_id, order.seller_id]:
        return JSONResponse({"success": False, "error": "No autorizado"}, status_code=403)

    attachment_url = None
    if attachment and attachment.filename:
        filename = f"chat_{order_id}_{user.id}_{attachment.filename}"
        filepath = settings.UPLOAD_DIR / filename
        with open(filepath, "wb") as f:
            f.write(await attachment.read())
        attachment_url = f"/uploads/{filename}"

    msg = Message(
        order_id=order_id,
        sender_id=user.id,
        content=content.strip(),
        attachment_url=attachment_url,
        is_system_message=False
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # Broadcast via websocket if room is open
    await manager.broadcast(order_id, {
        "id": msg.id,
        "sender_id": user.id,
        "sender_name": user.full_name,
        "sender_avatar": user.avatar_url,
        "content": msg.content,
        "attachment_url": attachment_url,
        "is_system_message": False,
        "created_at": msg.created_at.strftime("%H:%M"),
        "jitsi_meeting_url": None
    })

    return JSONResponse({"success": True, "message_id": msg.id})

@router.post("/api/orders/{order_id}/start-call")
async def start_jitsi_videocall(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order or user.id not in [order.buyer_id, order.seller_id]:
        return JSONResponse({"success": False, "error": "No autorizado"}, status_code=403)

    jitsi_info = generate_jitsi_room(order.order_number)

    msg = Message(
        order_id=order_id,
        sender_id=user.id,
        content=f"📹 {user.full_name} ha iniciado una videollamada para el pedido #{order.order_number}. Haz clic para unirte a la reunión segura de Jitsi Meet.",
        jitsi_meeting_url=jitsi_info["meeting_url"],
        is_system_message=True
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    await manager.broadcast(order_id, {
        "id": msg.id,
        "sender_id": user.id,
        "sender_name": "Sistema Gigly",
        "sender_avatar": user.avatar_url,
        "content": msg.content,
        "is_system_message": True,
        "created_at": msg.created_at.strftime("%H:%M"),
        "jitsi_meeting_url": jitsi_info["meeting_url"]
    })

    return JSONResponse({
        "success": True,
        "meeting_url": jitsi_info["meeting_url"],
        "room_name": jitsi_info["room_name"]
    })
