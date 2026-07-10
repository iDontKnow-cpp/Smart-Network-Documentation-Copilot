import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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
class ChatRequest(BaseModel):
    message: str

@api.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    This endpoint takes the user's message, feeds it into LangGraph, 
    and streams the agent's internal state transitions back to the client.
    """
    async def event_stream():
        # Yield an initial acknowledgement
        yield f"data: {json.dumps({'type': 'status', 'message': 'Agent initialized. Analyzing domain...'})}\n\n"
        
        # Stream the graph execution step-by-step
        # astream() yields the output of each node as it completes
        async for output in agent_app.astream({"question": request.message}):
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