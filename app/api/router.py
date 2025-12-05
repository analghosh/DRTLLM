from fastapi import APIRouter
from pydantic import BaseModel
from app.shared_resources import chatbot_instances

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    chat_history: list | None = None


@router.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    bot = chatbot_instances["DefaultBot"]
    history = payload.chat_history or []
    result = await bot.process_query(payload.question, chat_history=history)
    return result
