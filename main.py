import json
import os
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Any
from uploads import IMAGE_TYPES, chat_image_path, cleanup_expired_chat_uploads, delete_chat_uploads, image_data_url, save_image, save_pdf

# Import the compiled LangGraph app from Phase 2
from graph import app as agent_app

# Initialize FastAPI
api = FastAPI(title="Agentic RAG API")

# Configure CORS so your React frontend can communicate with this API
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the request schema
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    chat_id: str = "anonymous"
    images: list[str] = Field(default_factory=list)


@api.post("/api/upload")
async def upload_file(file: UploadFile = File(...), chat_id: str = Form("anonymous")):
    cleanup_expired_chat_uploads()
    content_type = (file.content_type or "").lower()
    filename = file.filename or "upload"
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        try:
            return save_pdf(file, filename, chat_id)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Could not ingest PDF: {exc}") from exc
    if content_type in IMAGE_TYPES or Path(filename).suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return save_image(file, filename, chat_id)
    raise HTTPException(status_code=415, detail="Only PDF, JPEG, PNG, GIF, and WebP files are supported.")


@api.delete("/api/chat/{chat_id}/uploads")
async def delete_uploads(chat_id: str):
    delete_chat_uploads(chat_id)
    return {"status": "ok"}

@api.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Use POST /api/chat with JSON body {'message': '<your question>'}"
    }

@api.get("/api/chat")
async def chat_info():
    return {
        "detail": "This endpoint requires POST. Send JSON body {'message': '<your question>'} to /api/chat or use /api/chat/json for a plain JSON response."
    }

@api.post("/api/chat/json")
async def chat_endpoint_json(request: ChatRequest):
    """
    This endpoint returns the final result as JSON for clients that do not support SSE.
    """
    result = agent_app.invoke({
        "question": request.message,
        "context": "",
        "source": "local_db",
        "answer": "",
        "history": [msg.dict() for msg in request.history],
        "images": [image_data_url(str(chat_image_path(request.chat_id, filename))) for filename in request.images],
    })
    return {
        "answer": result.get("answer"),
        "source": result.get("source"),
        "context": result.get("context"),
    }

@api.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    This endpoint takes the user's message, feeds it into LangGraph, 
    and streams the agent's internal state transitions back to the client.
    """
    async def event_stream():
        # Yield an initial acknowledgement
        yield f"data: {json.dumps({'type': 'status', 'message': 'Agent initialized. Analyzing domain...'})}\n\n"

        request_history = [msg.dict() for msg in request.history]
        images = []
        for filename in request.images:
            path = chat_image_path(request.chat_id, filename)
            if path.is_file():
                images.append(image_data_url(str(path)))
        
        # Stream the graph execution step-by-step
        # astream() yields the output of each node as it completes
        async for output in agent_app.astream({
            "question": request.message,
            "context": "",
            "source": "local_db",
            "answer": "",
            "history": request_history,
            "images": images,
        }):
            for node_name, state_update in output.items():
                
                # Intercept the Router Node
                if node_name == "route_query":
                    decision = state_update.get("source")
                    if decision == "local_db":
                        msg = "Domain Match: Routing to Local VPC Documentation."
                    else:
                        msg = "Out of Domain: Routing to External Web Search."
                    yield f"data: {json.dumps({'type': 'status', 'message': msg})}\n\n"
                
                # Intercept the Local Vector Retrieval Node
                elif node_name == "retrieve_local":
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Querying ChromaDB for architectural context...'})}\n\n"
                
                # Intercept the Web Search Node
                elif node_name == "retrieve_web":
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Querying Tavily API for external context...'})}\n\n"
                
                # Intercept the Generation Node and send the final answer
                elif node_name == "generate_response":
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Synthesizing final response...'})}\n\n"
                    final_answer = state_update.get("answer")
                    # Send the actual payload
                    yield f"data: {json.dumps({'type': 'result', 'message': final_answer})}\n\n"
        
        # Close the stream
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    # Run the server on port 8000
    uvicorn.run("main:api", host="0.0.0.0", port=8000, reload=True)