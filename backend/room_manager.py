import json
import time
import redis.asyncio as redis
from fakeredis.aioredis import FakeRedis
from typing import Optional, Dict

class RoomManager:
    def __init__(self, redis_url: str = "redis://localhost"):
        try:
            self.redis = FakeRedis(decode_responses=True)
        except Exception:
            pass

    async def create_room(self, room_id: str) -> None:
        """Create a room with 12 hours expiry."""
        room_data = {
            "is_playing": False,
            "current_time": 0.0,
            "updated_at": time.time(),
            "video_url": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4" # Mock video source
        }
        await self.redis.setex(
            f"room:{room_id}", 
            12 * 60 * 60, # 12 hours in seconds
            json.dumps(room_data)
        )
        # We also need a chat list
        await self.redis.delete(f"chat:{room_id}")

    async def get_room_state(self, room_id: str) -> Optional[Dict]:
        data = await self.redis.get(f"room:{room_id}")
        if data:
            state = json.loads(data)
            if state.get("is_playing"):
                elapsed = time.time() - state.get("updated_at", time.time())
                state["current_time"] += elapsed
            return state
        return None

    async def update_room_state(self, room_id: str, is_playing: bool, current_time: float) -> None:
        state = await self.get_room_state(room_id)
        if state:
            state["is_playing"] = is_playing
            state["current_time"] = current_time
            state["updated_at"] = time.time()
            # update expiry to keep it alive or just keep original? let's just update value
            ttl = await self.redis.ttl(f"room:{room_id}")
            if ttl > 0:
                await self.redis.setex(f"room:{room_id}", ttl, json.dumps(state))

    async def add_chat_message(self, room_id: str, username: str, text: str) -> Dict:
        msg = {"username": username, "text": text}
        msg_str = json.dumps(msg)
        await self.redis.rpush(f"chat:{room_id}", msg_str)
        # expire chat when room expires
        ttl = await self.redis.ttl(f"room:{room_id}")
        if ttl > 0:
            await self.redis.expire(f"chat:{room_id}", ttl)
        return msg

    async def get_chat_history(self, room_id: str) -> list:
        msgs = await self.redis.lrange(f"chat:{room_id}", 0, -1)
        return [json.loads(m) for m in msgs]

room_manager = RoomManager()
