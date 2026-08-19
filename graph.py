import os
import re
import chromadb
from typing import TypedDict, Literal, List, Dict, Any
from dotenv import load_dotenv
from openai import RateLimitError
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

# Load environment variables (OpenAI and Tavily keys)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if OPENAI_API_KEY is None:
    raise EnvironmentError(
        "OPENAI_API_KEY is not set. Please set it in your environment or .env file."
    )

# --- 1. Define the State ---
class GraphState(TypedDict):
    """
    This dictionary is passed between nodes. Each node reads from it and updates it.
    """
    question: str
    context: str
    source: str  # Tracks if we used 'local_db' or 'web_search'
    answer: str
    history: List[Dict[str, Any]]

# --- 2. Initialize Core Components ---
# We use a higher-quality model for the backend routing and generation
llm = ChatOpenAI(model="gpt-4.1", temperature=0)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Connect to the Chroma server over HTTP
chroma_client = chromadb.HttpClient(
    host=os.getenv("CHROMA_HOST", "chroma-service"),
    port=int(os.getenv("CHROMA_PORT", 8000)),
)

db = Chroma(
    client=chroma_client,
    embedding_function=embeddings,
)
retriever = db.as_retriever(search_kwargs={"k": 6})

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
    The local vectorstore contains documentation on AWS, GCP, Azure, Nutanix, VMware, Transit Gateways, RoCEv2, Arista networking, and storage architecture.
    If the question is about these core enterprise infrastructure topics or vendor-specific docs, route to 'local_db'.
    If the question asks for general internet knowledge, current events, or topics outside infrastructure, route to 'web_search'."""
    
    route_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{question}")
    ])
    
    # Force the LLM to output a clean JSON structure
    router = route_prompt | llm.with_structured_output(RouteDecision)
    try:
        decision = router.invoke({"question": question})
    except RateLimitError as e:
        print("   ⚠️ OpenAI rate limit / quota error while routing query:", e)
        print("   ↳ Falling back to local_db route.")
        return {"source": "local_db"}
    except Exception as e:
        print("   ⚠️ Router error:", type(e).__name__, e)
        print("   ↳ Falling back to local_db route.")
        return {"source": "local_db"}
    
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

def retrieve_web(state):
    question = state["question"]
    
    # Execute Tavily search
    docs = web_search_tool.invoke({"query": question})
    
    # 1. If Tavily returned a plain string
    if isinstance(docs, str):
        return {"context": docs}
    
    # 2. If Tavily returned a list of items (dicts or strings)
    context_list = []
    if isinstance(docs, list):
        for doc in docs:
            if isinstance(doc, dict):
                # Safely extract 'content' or fallback to string representation
                context_list.append(doc.get("content", str(doc)))
            elif isinstance(doc, str):
                context_list.append(doc)
            else:
                context_list.append(str(doc))
    
    context = "\n\n".join(context_list)
    return {"context": context}


def retrieve_any_source(state: GraphState):
    if state["source"] == "local_db":
        return retrieve_local(state)
    return retrieve_web(state)

def generate_response(state: GraphState):
    print("✍️  [Generation Node] Synthesizing final answer...")
    
    history_text = "\n".join([
        f"{message['role'].capitalize()}: {message['content']}" for message in state.get("history", [])
    ])

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a senior Systems Reliability Engineer. Use the provided context to answer the question clearly and directly. Do not output any plan, internal workflow, or reasoning steps. Never label any part of the answer with words like 'Local:', 'Web:', 'Source:', or similar attribution tags — write plain prose or bullets describing the actual content instead. Return only the final answer in README.md style markdown. If the question asks you to compare or contrast items and the context describes each item individually, synthesize a comparison from what is described rather than refusing — only say 'I cannot answer this based on the retrieved data.' if the context is genuinely unrelated to the question's topic."),
        ("human", "Conversation history:\n{history}\n\nContext:\n{context}\n\nQuestion:\n{question}")
    ])
    
    fallback_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a senior Systems Reliability Engineer and an agentic RAG assistant. Internally compare local documentation and web search results, but do not expose any plan, evaluation, or evidence workflow in the final response. Never label any part of the answer with words like 'Local:', 'Web:', 'Source:', or similar attribution tags — write plain prose or bullets describing the actual content instead. Output only the final answer in README-style markdown with this structure:\n\n# <Short title>\n\n## Introduction\n- One short sentence describing the task.\n\n## Conclusion\n- One concise sentence stating the final answer.\n\nDo not mention evidence sources, web/local, plans, scores, or internal reasoning. Keep the answer direct and factual."),
        ("human", "Conversation history:\n{history}\n\nLocal Context:\n{local_context}\n\nWeb Context:\n{web_context}\n\nQuestion:\n{question}")
    ])

    chain = prompt | llm
    fallback_chain = fallback_prompt | llm
    refusal_text = "I cannot answer this based on the retrieved data."

    def synthesize(context: str, question: str, history: str):
        result = chain.invoke({
            "history": history,
            "context": context,
            "question": question
        })
        return getattr(result, "content", str(result)).strip()

    def synthesize_with_web(local_context: str, web_context: str, question: str, history: str):
        result = fallback_chain.invoke({
            "history": history,
            "local_context": local_context,
            "web_context": web_context,
            "question": question
        })
        return getattr(result, "content", str(result)).strip()

    def clean_answer(answer: str):
        # Remove any residual lines that look like internal planning or evidence sections.
        lines = answer.splitlines()
        filtered = [line for line in lines if not re.match(r'^(Plan|Evidence|Evaluation|References|Source|Scoring):', line.strip(), re.IGNORECASE)]
        cleaned = '\n'.join(filtered).strip()
        return cleaned if cleaned else answer

    try:
        answer = synthesize(state["context"], state["question"], history_text)
    except RateLimitError as e:
        print("   ⚠️ OpenAI rate limit / quota error while generating response:", e)
        return {"answer": "OpenAI quota/rate limit error occurred. Please check your API quota and try again.", "source": state["source"]}
    except Exception as e:
        print("   ⚠️ Generation error:", type(e).__name__, e)
        return {"answer": "An internal error occurred while generating the response.", "source": state["source"]}

    if refusal_text.lower() in answer.lower() and state["source"] == "local_db":
        print("   ↳ Local DB did not contain an answer; falling back to web search and comparing sources.")
        web_context = retrieve_web(state)["context"]
        state["source"] = "web_search"
        try:
            answer = synthesize_with_web(state["context"], web_context, state["question"], history_text)
        except RateLimitError as e:
            print("   ⚠️ OpenAI rate limit / quota error while generating fallback response:", e)
            return {"answer": "OpenAI quota/rate limit error occurred during fallback. Please check your API quota and try again.", "source": "web_search"}
        except Exception as e:
            print("   ⚠️ Fallback generation error:", type(e).__name__, e)
            return {"answer": "An internal error occurred while generating the fallback response.", "source": "web_search"}

    answer = clean_answer(answer)
    return {"answer": answer, "source": state["source"]}

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
    print("OPENAI_API_KEY set:", bool(OPENAI_API_KEY))
    print("TAVILY_API_KEY set:", bool(TAVILY_API_KEY))
    
    # Test 1: Should hit local ChromaDB
    q1 = "What is the maximum MTU for AWS Transit Gateway VPC attachments?"
    print(f"\nUser: {q1}")
    try:
        result1 = app.invoke({
            "question": q1,
            "context": "",
            "source": "local_db",
            "answer": "",
            "history": [],
        })
        print(f"\nFinal Output:\n{result1['answer']}\n")
    except Exception as e:
        print("\n⚠️ Diagnostics failed:", type(e).__name__, e)
    print("-" * 40)
    
    # Test 2: Should hit external Tavily Search
    q2 = "What are the latest trackside server hardware specs used in Formula 1?"
    print(f"User: {q2}")
    try:
        result2 = app.invoke({
            "question": q2,
            "context": "",
            "source": "web_search",
            "answer": "",
            "history": [],
        })
        print(f"\nFinal Output:\n{result2['answer']}")
    except Exception as e:
        print("\n⚠️ Diagnostics failed:", type(e).__name__, e)