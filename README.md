---

# Smart Network Documentation Copilot 🚀

An event-streamed, Agentic Retrieval-Augmented Generation (RAG) platform designed to navigate dense cloud infrastructure and network engineering documentation (AWS VPCs, Transit Gateways, BGP routing, and telemetry architectures).

This platform goes beyond static RAG pipelines by combining a **LangGraph state machine** for dynamic query routing with a **memory-optimized, streaming vector ingestion pipeline** running on Kubernetes.

---

## 🌟 Key Features

* **Agentic Routing:** Uses an LLM router to evaluate query domains prior to execution, dynamically directing requests between a local vector database and external search APIs to prevent out-of-domain hallucinations.
* **Fallback Web Search:** Automatically routes queries to the **Tavily Search API** when local vector similarity confidence thresholds are not met.
* **Real-Time Event Streaming (SSE):** Implements Server-Sent Events via FastAPI to stream internal agent state transitions (*Routing* $\rightarrow$ *Searching Vector DB / Web* $\rightarrow$ *Synthesizing*) directly to the React frontend.
* **Memory-Safe File-by-File Ingestion Engine:** Handles large document sets (380 MB+ / 26,000+ PDF pages) using a streaming file-by-file loader with explicit garbage collection and chunk batching—preventing Kubernetes `OOMKilled` spikes.
* **Unbuffered NGINX Reverse Proxy:** Configured with `proxy_buffering off` and `X-Accel-Buffering: no` headers to ensure zero latency jitter during token and state streaming.
* **Production Kubernetes Deployment:** Utilizes `initContainers` for decoupled vector database seeding onto shared `emptyDir` volumes, backed by tuned Ephemeral Storage limits (`6Gi`) and Horizontal Pod Autoscaling (HPA).

---

## 🛠️ Tech Stack

| Category | Technology Stack |
| --- | --- |
| **Backend & Agent Core** | Python 3.11, FastAPI, LangGraph, LangChain, ChromaDB |
| **AI Models & Search** | OpenAI (`gpt-4o-mini`, `text-embedding-3-small`), Tavily API |
| **Frontend UI** | React.js, Tailwind CSS, Vite, Lucide Icons |
| **Proxy & Streaming** | NGINX (Unbuffered SSE Proxying) |
| **Container & Orchestration** | Docker (Multi-stage & Multi-arch Buildx), Kubernetes (`kubeadm`), HPA |

---

## 🏗️ System Architecture

```text
+-------------------+       +-------------------+       +--------------------+
|  React UI (Vite)  | <---> |  NGINX Proxy      | <---> |  FastAPI (SSE)     |
+-------------------+       +-------------------+       +--------------------+
                                                                  |
                                                                  v
                                                        +--------------------+
                                                        |  LangGraph Router  |
                                                        +--------------------+
                                                               /      \
                                                 (In-Domain)  /        \  (Out-of-Domain)
                                                             v          v
                                                    +---------------+  +------------------+
                                                    | Local ChromaDB|  | Tavily Search API|
                                                    +---------------+  +------------------+

```

---

## 🐳 Kubernetes Ingestion & Storage Design

To prevent cgroup RAM limit breaches during large PDF parsing, the architecture decouples vector processing into a dedicated `initContainer` with isolated lifecycle constraints:

```text
+---------------------------------------------------------------------------------+
| Pod: rag-deployment                                                             |
|                                                                                 |
|  +-----------------------------------+                                          |
|  | [initContainer] data-ingestion    |                                          |
|  | - Streams 380MB+ PDFs file-by-file  | ---> Writes to /app/chroma_db           |
|  | - Batched Chroma inserts          |          |                               |
|  +-----------------------------------+          | (Shared emptyDir Volume)      |
|                    |                            v                               |
|                    +-------------------> [container] api-server                 |
|                   (Completes)            - Mounts ready vector DB index         |
|                                          - Serves FastAPI + SSE streams         |
+---------------------------------------------------------------------------------+

```

---

## 🚀 Getting Started (Deployment Guide)

### Prerequisites

* Docker with Buildx enabled (for multi-platform builds)
* A running Kubernetes cluster (`kubeadm`, Minikube, or Docker Desktop)
* `kubectl` configured with cluster access
* API Keys for **OpenAI** and **Tavily**

---

### 1. Clone the Repository

```bash
git clone git@github.com:iDontKnow-cpp/Smart-Network-Documentation-Copilot.git
cd Smart-Network-Documentation-Copilot

```

---

### 2. Configure Kubernetes Secrets

Create `kubernetes/secrets.private.yaml` (*do not commit to source control*):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-secrets
  namespace: default
type: Opaque
stringData:
  OPENAI_API_KEY: "your_openai_api_key_here"
  TAVILY_API_KEY: "your_tavily_api_key_here"

```

---

### 3. Build & Push Multi-Arch Docker Images

Build backend and frontend images using `docker buildx`:

```bash
# Build & Push Backend (Includes Ingestion Engine & API Server)
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ujjwalrajpurohit/smart-network-documentation-copilot-backend:v7 \
  -f docker/Dockerfile.backend --push .

# Build & Push Frontend
docker buildx build --platform linux/amd64,linux/arm64 \
  -t ujjwalrajpurohit/smart-network-documentation-copilot-frontend:v1 \
  -f docker/Dockerfile.frontend --push .

```

---

### 4. Deploy to Kubernetes

Apply the manifests in sequential order:

```bash
# 1. Apply secrets
kubectl apply -f kubernetes/secrets.private.yaml

# 2. Deploy application (Deployment, Service, HPA)
kubectl apply -f kubernetes/rag-deployment.yaml
kubectl apply -f kubernetes/rag-service.yaml

```

---

### 5. Monitor Vector Ingestion

Track the data ingestion init container as it streams PDFs and populates ChromaDB:

```bash
kubectl logs -n default -l app=rag-agent -c data-ingestion -f

```

---

### 6. Access the Application

Access the application via the configured NodePort on your cluster node:

```text
URL: http://<your-node-ip>:30080

```

---

## 📂 Project Structure

```text
Smart-Network-Documentation-Copilot/
├── docs/                      # Documentation PDFs and Markdown files for ingestion
├── docker/
│   ├── Dockerfile.backend     # Python backend runtime container
│   └── Dockerfile.frontend    # Multi-stage NGINX + React build container
├── kubernetes/
│   ├── rag-deployment.yaml    # Deployment manifest (initContainers, limits, volumes)
│   ├── rag-service.yaml       # NodePort / ClusterIP service definition
│   └── secrets.private.yaml   # API credentials (Git-ignored)
├── frontend/                  # React.js SPA source code
│   ├── src/                   # EventSource streaming components & UI
│   └── tailwind.config.js     # Tailwind CSS design system configuration
├── main.py                    # FastAPI app entrypoint & SSE stream endpoint
├── graph.py                   # LangGraph state machine & routing workflow
├── ingest.py                  # File-by-file batching vector ingestion script
├── nginx.conf                 # Reverse proxy configuration for unbuffered SSE streaming
└── requirements.txt           # Python dependencies

```

---

## 📈 Engineering Performance Metrics

* **Agentic Routing Accuracy:** 93.88% on benchmark domain query sets.
* **Vector Indexing Footprint:** 391.4 MB source docs $\rightarrow$ ~140,000 chunks indexed under **< 600 MB peak RAM**.
* **Streaming Latency:** First SSE state event delivered in **< 120 ms**.
* **Average Retrieval Latency:** 806.5 ms across local vector store queries.