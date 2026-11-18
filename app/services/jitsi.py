import uuid
import hashlib

def generate_jitsi_room(order_number: str) -> dict:
    """
    Generates a secure, unique Jitsi Meet video conference room for a specific order.
    Integrates directly with meet.jit.si without needing API keys.
    """
    # Create an obfuscated room name using order number and a short hash
    salt = "gigly_secure_meeting_2026"
    raw = f"{order_number}-{salt}"
    room_hash = hashlib.sha256(raw.encode()).hexdigest()[:12]
    room_name = f"GiglyOrder-{order_number}-{room_hash}"
    
    meeting_url = f"https://meet.jit.si/{room_name}"
    
    return {
        "room_name": room_name,
        "meeting_url": meeting_url,
        "domain": "meet.jit.si"
    }
