import os
from typing import TypedDict, Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

# Load environment variables (OpenAI and Tavily keys)
load_dotenv()

# --- 1. Define the State ---
class GraphState(TypedDict):
    """
    This dictionary is passed between nodes. Each node reads from it and updates it.
    """
    question: str
    context: str
    source: str  # Tracks if we used 'local_db' or 'web_search'
    answer: str

# --- 2. Initialize Core Components ---
# We use a fast, low-cost model for the backend routing and generation
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0) 
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Connect to the local vector store created in Phase 1
db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
retriever = db.as_retriever(search_kwargs={"k": 3})

# Initialize the fallback web search tool
web_search_tool = TavilySearchResults(max_results=3)

# --- 3. Build the Nodes ---

class RouteDecision(BaseModel):
    datasource: Literal["local_db", "web_search"] = Field(
        description="Choose whether to route the query to a local vector store or web search."
    )

def route_query(state: GraphState):
    print("🚦 [Router Node] Analyzing query domain...")
    question = state["question"]
    
    # We prime the router with strict system engineering contexts
    system_prompt = """You are an expert routing assistant for an SRE and Network Infrastructure team. 
    The local vectorstore contains documentation on AWS VPC, Transit Gateways, RoCEv2, Arista networking, and storage architecture.
    If the question is about these core technical infrastructure topics, route to 'local_db'.
    If the question asks for general internet knowledge, current events, or topics outside infrastructure, route to 'web_search'."""
    
    route_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}")
    ])
    
    # Force the LLM to output a clean JSON structure
    router = route_prompt | llm.with_structured_output(RouteDecision)
    decision = router.invoke({"question": question})
    
    if decision.datasource == "local_db":
        print("   ↳ Decision: Local Infrastructure Docs")
        return {"source": "local_db"}
    else:
        print("   ↳ Decision: External Web Search")
        return {"source": "web_search"}

def retrieve_local(state: GraphState):
    print("🔍 [Local Search Node] Querying ChromaDB...")
    docs = retriever.invoke(state["question"])
    context = "\n\n".join([doc.page_content for doc in docs])
    return {"context": context}

def retrieve_web(state: GraphState):
    print("🌐 [Web Search Node] Querying Tavily API...")
    docs = web_search_tool.invoke({"query": state["question"]})
    context = "\n\n".join([doc["content"] for doc in docs])
    return {"context": context}

def generate_response(state: GraphState):
    print("✍️  [Generation Node] Synthesizing final answer...")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a senior Systems Reliability Engineer. Answer the question using ONLY the provided context. If the context does not contain the answer, say 'I cannot answer this based on the retrieved data.'\n\nContext:\n{context}"),
        ("human", "{question}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({
        "context": state["context"],
        "question": state["question"]
    })
    
    return {"answer": response.content}

# --- 4. Define Edge Logic ---
def decide_route(state: GraphState) -> str:
    """Reads the state to determine which path the graph should take."""
    return state["source"]

# --- 5. Compile the LangGraph ---
workflow = StateGraph(GraphState)

# Register the nodes
workflow.add_node("route_query", route_query)
workflow.add_node("retrieve_local", retrieve_local)
workflow.add_node("retrieve_web", retrieve_web)
workflow.add_node("generate_response", generate_response)

# Set the starting point
workflow.set_entry_point("route_query")

# Add conditional routing
workflow.add_conditional_edges(
    "route_query",
    decide_route,
    {
        "local_db": "retrieve_local",
        "web_search": "retrieve_web",
    }
)

# Funnel both retrieval paths back to the generator
workflow.add_edge("retrieve_local", "generate_response")
workflow.add_edge("retrieve_web", "generate_response")
workflow.add_edge("generate_response", END)

# Compile into a runnable application
app = workflow.compile()

# --- 6. Quick Local Test ---
if __name__ == "__main__":
    print("\n--- Running Graph Diagnostics ---")
    
    # Test 1: Should hit local ChromaDB
    q1 = "What is the maximum MTU for AWS Transit Gateway VPC attachments?"
    print(f"\nUser: {q1}")
    result1 = app.invoke({"question": q1})
    print(f"\nFinal Output:\n{result1['answer']}\n")
    print("-" * 40)
    
    # Test 2: Should hit external Tavily Search
    q2 = "What are the latest trackside server hardware specs used in Formula 1?"
    print(f"\nUser: {q2}")
    result2 = app.invoke({"question": q2})
    print(f"\nFinal Output:\n{result2['answer']}")