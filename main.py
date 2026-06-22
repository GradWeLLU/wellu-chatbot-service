# main.py
import json
import redis
import logging
from fastapi import FastAPI
from pydantic import BaseModel, field_validator
from chatbot import WellUChatbot
from langchain_core.messages import HumanMessage, AIMessage

# Set up basic logging so errors are clearly visible 
# in your terminal, distinct from normal request logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wellu-chatbot")

app = FastAPI()

# Connect to Redis, but don't crash the whole app 
# if Redis isn't reachable at startup
try:
    redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except redis.exceptions.ConnectionError:
    logger.warning("Redis is not reachable at startup. Sessions will not persist.")
    redis_client = None
    REDIS_AVAILABLE = False


class MessageRequest(BaseModel):
    token: str
    message: str

    @field_validator("token")
    @classmethod
    def token_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Token cannot be empty")
        return v

    @field_validator("message")
    @classmethod
    def message_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v


def _session_key(token: str):
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
    return f"history:{token_hash}"


def load_history(token: str):
    """
    Loads conversation history from Redis.
    Returns an empty list if Redis is unavailable 
    or no history exists, never crashes.
    """
    if not REDIS_AVAILABLE:
        return []

    try:
        raw_history = redis_client.get(_session_key(token))
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis read failed: {e}")
        return []

    if raw_history is None:
        return []

    try:
        history_data = json.loads(raw_history)
    except json.JSONDecodeError as e:
        logger.error(f"Corrupted history data in Redis: {e}")
        return []

    messages = []
    for item in history_data:
        if item["type"] == "human":
            messages.append(HumanMessage(content=item["content"]))
        elif item["type"] == "ai":
            messages.append(AIMessage(content=item["content"]))

    return messages


def save_history(token: str, messages: list):
    """
    Saves conversation history to Redis.
    Silently does nothing if Redis is unavailable,
    rather than crashing the whole request.
    """
    if not REDIS_AVAILABLE:
        return

    history_data = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            history_data.append({"type": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            history_data.append({"type": "ai", "content": msg.content})

    try:
        redis_client.set(_session_key(token), json.dumps(history_data))
    except redis.exceptions.RedisError as e:
        logger.error(f"Redis write failed: {e}")


@app.get("/")
def root():
    return {
        "status": "WellU Chatbot Service is running",
        "redis_available": REDIS_AVAILABLE
    }


@app.post("/chat")
def chat(request: MessageRequest):
    try:
        chatbot = WellUChatbot(request.token)
    except Exception as e:
        logger.error(f"Failed to create chatbot instance: {e}")
        return {
            "error": "We couldn't start your session right now. Please try again shortly."
        }

    chatbot.conversation_history = load_history(request.token)

    try:
        response = chatbot.chat(request.message)
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        return {
            "error": "Something went wrong while processing your message. Please try again."
        }

    save_history(request.token, chatbot.conversation_history)

    return {
        "response": response
    }


@app.get("/user-context")
def get_context(token: str):
    try:
        chatbot = WellUChatbot(token)
        return {"context": chatbot.user_context}
    except Exception as e:
        logger.error(f"Failed to build context: {e}")
        return {"error": "Could not build user context right now."}
    