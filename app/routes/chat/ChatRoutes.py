from fastapi import APIRouter, HTTPException, status
from typing import List
from app.controllers.chat.ChatController import ChatController
from app.models.chat.ChatModel import ChatCreate, ChatUpdate, ChatResponse
from app.models.ingest.IngestModel import ChatMessageRequest, ChatMessageResponse

router = APIRouter(prefix="/chats", tags=["chats"])

# Initialize controller
chat_controller = ChatController()

@router.post("/message", response_model=ChatMessageResponse)
async def process_message(request: ChatMessageRequest):
    """
    Process user message using RAG (Retrieval-Augmented Generation)
    
    This endpoint uses vector search to find relevant context and generates
    intelligent responses about products, categories, and promotions.
    """
    try:
        result = await chat_controller.process_message(
            message=request.message,
            user_id=request.user_id
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
        
        return ChatMessageResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando mensaje: {str(e)}"
        )

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
def create_chat(chat: ChatCreate):
    """Create a new chat"""
    try:
        return ChatController.create_chat(chat)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/", response_model=List[ChatResponse])
def get_all_chats():
    """Get all chats"""
    return ChatController.get_all_chats()

@router.get("/{chat_id}", response_model=ChatResponse)
def get_chat(chat_id: int):
    """Get chat by ID"""
    chat = ChatController.get_chat_by_id(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return chat

@router.get("/usuario/{usuario_id}", response_model=List[ChatResponse])
def get_chats_by_usuario(usuario_id: int):
    """Get chats by usuario"""
    return ChatController.get_chats_by_usuario(usuario_id)

@router.put("/{chat_id}", response_model=ChatResponse)
def update_chat(chat_id: int, chat: ChatUpdate):
    """Update chat"""
    updated_chat = ChatController.update_chat(chat_id, chat)
    if not updated_chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return updated_chat

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: int):
    """Delete chat"""
    if not ChatController.delete_chat(chat_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
