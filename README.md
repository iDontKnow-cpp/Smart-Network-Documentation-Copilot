# Smart Network Documentation Copilot 🚀

An event-streamed, Agentic Retrieval-Augmented Generation (RAG) platform designed to navigate dense cloud infrastructure and network engineering documentation (AWS VPCs, Transit Gateways, BGP routing, and telemetry architectures).

This platform goes beyond static RAG pipelines by combining a **LangGraph state machine** for dynamic query routing with a **memory-optimized, streaming vector ingestion pipeline** running on Kubernetes.

---

## 🌟 Key Features

*   **Agentic Routing:** Uses an LLM router to evaluate query domains prior to execution, dynamically directing requests between a local vector database and external search APIs to reduce out-of-domain hallucinations.
*   **Fallback Web Search:** Routes to the **Tavily Search API** when the router classifies a query as out-of-domain, or when a local-context synthesis attempt returns an explicit "cannot answer from retrieved data" result — at which point local and web context are compared to produce a final answer.
*   **Semantic Response Caching:** A Redis-backed `RedisSemanticCache` sits in front of the LLM calls (distance threshold `0.15`, 24h TTL), so semantically similar questions can return a cached answer instead of triggering a fresh generation call. Initialization fails soft — if Redis is unreachable, the app logs a warning and continues without caching instead of crashing.
*   **Universal Chat-Scoped Retrieval:** Handled in `graph.py` (`_retrieve_chat_scoped_docs`), chunks from PDFs uploaded in the current chat are retrieved regardless of which branch the router picks. This ensures a query like "skills in my resume" still surfaces the uploaded PDF even when routed to web search.
*   **Bounded Conversation Memory:** The generation node only forwards the most recent 5 user/assistant exchanges (10 messages) into the LLM prompt, regardless of how long the chat has grown — keeping prompt size and cost predictable in long-running conversations.
*   **Real-Time Event Streaming (SSE):** Implements Server-Sent Events via FastAPI to stream internal agent state transitions (*Routing* → *Searching Vector DB / Web* → *Synthesizing*) directly to the React frontend.
*   **Memory-Safe File-by-File Ingestion Engine:** Processes each source file (Markdown + PDF) individually — load, chunk, embed, persist, then explicitly garbage-collect — before moving to the next file, rather than holding the entire corpus in memory at once. This replaced an earlier all-at-once approach that reliably caused Kubernetes `OOMKilled` failures once the real corpus size (26,748 PDF pages) was ingested.
*   **Chat File Uploads:** `POST /api/upload` accepts PDFs and images. PDFs are classified into vendor subdirectories under `tmp/chats/<chat_id>/docs/`, chunked and embedded into ChromaDB as a **background task** (`background_tasks.add_task`), and removed with the chat. Images are kept under `tmp/chats/<chat_id>` for the chat lifetime and are sent to the vision-capable chat model with the next question; abandoned chat files expire after 24 hours by default.
*   **Unbuffered NGINX Reverse Proxy:** `/api/` location configured with `proxy_buffering off` and `proxy_cache off` so SSE tokens aren't held back by proxy-level buffering.
*   **Kubernetes Deployment:** Uses explicit CPU/memory/ephemeral-storage limits on every container and Horizontal Pod Autoscaling (HPA, requires `metrics-server` installed in-cluster).

---

## 🛠️ Tech Stack

| Category | Technology Stack |
| --- | --- |
| **Backend & Agent Core** | Python 3.10-slim, FastAPI, LangGraph, LangChain, ChromaDB |
| **AI Models & Search** | OpenAI (`gpt-4.1`, `text-embedding-3-small`), Tavily API |
| **Caching** | Redis (`redis:alpine`) via LangChain's `RedisSemanticCache` |
| **Frontend UI** | React.js, Tailwind CSS, Vite, Lucide Icons |
| **Proxy & Streaming** | NGINX (unbuffered SSE proxying) |
| **Container & Orchestration** | Docker (Buildx), Kubernetes (`kubeadm`), HPA |

---

## 🏗️ System Architecture

```text
+-------------------+       +-------------------+       +--------------------+
|  React UI (Vite)  | <---> |  NGINX Proxy      | <---> |  FastAPI (SSE)     |
+-------------------+       +-------------------+       +--------------------+
                                                                  |
                                                                  v
                                                    +--------------------------+
                                                    |   LangGraph Agent Core   | <---> Redis Semantic Cache
                                                    |     (Router + Gen)       |
                                                    +--------------------------+
                                                               /      \
                                                 (In-Domain)  /        \  (Out-of-Domain)
                                                             v          v
                                                    +---------------+  +------------------+
                                                    | Local ChromaDB|  | Tavily Search API|
                                                    +---------------+  +------------------+

```

---

## 🐳 Kubernetes Ingestion & Storage Design

### Pre-Ingestion Pipeline

The pipeline for getting documents onto the system before ingestion involves two steps:

1. `setup_docs.sh` pulls vendor PDF guides and writes `LINKS.md` into `docs/{aws,azure,...}`.
2. These files are served via `docs.conf` (an NGINX autoindex+WebDAV server on your control-plane node at `<CONTROL_PLANE_IP>`) that `ingest.py`'s `fetch_docs()` mirrors from before ingestion begins.

### Isolated Job Execution & Storage

To avoid cgroup memory limit breaches during large PDF parsing, vector processing and serving are decoupled into distinct Kubernetes components:

* **`chroma-server.yaml`**: A standalone Chroma `Deployment` utilizing a `PersistentVolume` (hostPath) and exposed via a `ClusterIP Service`.
* **`chroma-ingestion-job.yaml`**: A one-shot `Job` that executes `ingest.py` against the standalone Chroma service over HTTP.
* **`redis.yaml`**: A Redis `Deployment` + `Service` providing the semantic response cache used by the API server.
* **`rag-deployment.yaml`**: Contains exactly two containers (`nginx-frontend` and `api-server`), with no `initContainer` involved.

```text
+---------------------------------------------------------------------------------+
| Kubernetes Cluster                                                              |
|                                                                                 |
|  +-----------------------------------+       +-------------------------------+  |
|  | [Job] chroma-ingestion            |       | [Deployment] chroma-server    |  |
|  | - Runs ingest.py as a one-shot    | --->  | - Standalone Vector Database  |  |
|  | - Batched Chroma inserts + gc()   | HTTP  | - Mounted PersistentVolume    |  |
|  +-----------------------------------+       +-------------------------------+  |
|                                                             ^                   |
|                                                             |                   |
|  +-----------------------------------+                      |    +-----------------------------+
|  | [Deployment] rag-deployment       | <--------------------+    | [Deployment] redis           |
|  | - api-server container            | <-------------------------| - Semantic response cache   |
|  | - nginx-frontend container        |                            | - Exposed via redis Service |
|  +-----------------------------------+                            +-----------------------------+
+---------------------------------------------------------------------------------+

```

---

## 🚀 Getting Started (Deployment Guide)

### Prerequisites

* Docker with Buildx enabled

* A running Kubernetes cluster (`kubeadm`, Minikube, or Docker Desktop)

* `kubectl` configured with cluster access

* `metrics-server` installed in-cluster if you want the HPA to actually scale (not included by default on `kubeadm` clusters)

* API keys for **OpenAI** and **Tavily**


---

### 1. Clone the Repository

```bash
git clone git@github.com:<your-organization-or-username>/Smart-Network-Documentation-Copilot.git
cd Smart-Network-Documentation-Copilot

```

To pull the pre-built images from Docker Hub (Multi-platform Linux build for both arm64 and amd64):

```bash
docker pull ujjwalrajpurohit/smart-network-documentation-copilot-backend:v8
docker pull ujjwalrajpurohit/smart-network-documentation-copilot-frontend:v4

```

> If you're pulling the frontend at `:v4`, make sure `kubernetes/rag-deployment.yaml`'s `nginx-frontend` image tag is bumped to match.

---

### 2. Configure Kubernetes Secrets

Create `kubernetes/secret.private.yaml` (*do not commit to source control*):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-secrets
  namespace: default
type: Opaque
stringData:
  OPENAI_API_KEY: "<YOUR_OPENAI_API_KEY>"
  TAVILY_API_KEY: "<YOUR_TAVILY_API_KEY>"
  REDIS_URL: "redis://redis:6379"   # match this to the Service name defined in kubernetes/redis.yaml

```

> ⚠️ `graph.py` defaults to `redis://redis-service:6379` if `REDIS_URL` isn't set. Confirm the actual Service name inside your merged `redis.yaml` and set `REDIS_URL` to match it — otherwise the semantic cache silently no-ops instead of failing loudly.

---

### 3. Build & Push Docker Images

```bash
# Backend — built multi-platform.
docker buildx build --platform linux/amd64,linux/arm64 \
  -t <your-docker-hub-username>/<docker_repository_name>:<tag> \
  -f docker/dockerfile.backend --push .

# Frontend — built multi-platform.
docker buildx build --platform linux/amd64,linux/arm64 \
  -t <your-docker-hub-username>/<docker_repository_name>:<tag> \
  -f docker/dockerfile.frontend --push .

```

---

### 4. Deploy to Kubernetes

Note: Order matters.

```bash
kubectl apply -f kubernetes/secret.private.yaml
kubectl apply -f kubernetes/redis.yaml
kubectl wait --for=condition=available deployment/redis --timeout=60s
kubectl apply -f kubernetes/chroma-server.yaml
kubectl wait --for=condition=available deployment/chroma-server --timeout=60s
kubectl apply -f kubernetes/chroma-ingestion-job.yaml
kubectl wait --for=condition=complete job/chroma-ingestion --timeout=600s
kubectl apply -f kubernetes/rag-deployment.yaml
kubectl apply -f kubernetes/rag-service.yaml

```

---

### 5. Monitor Vector Ingestion

The ingestion Job prints progress per file (fetch → per-file load/chunk/embed → completion):

```bash
kubectl logs -l job-name=chroma-ingestion -f

```

Ingestion time scales with corpus size — expect this to take a meaningful amount of wall-clock time on a real documentation set (tens of thousands of PDF pages), since embedding is a sequential API-bound step.

---

### 6. Access the Application

```text
URL: http://<your-node-ip>:30080

```

---

## 📂 Project Structure

```text
.
├── docker/
│   ├── dockerfile.backend
│   └── dockerfile.frontend
├── docs/                          # Local corpus mirror (generated by setup_docs.sh; gitignored)
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── vite.config.js
├── kubernetes/
│   ├── chroma-ingestion-job.yaml  # Job for ingesting data to Chroma
│   ├── chroma-server.yaml         # ChromaDB deployment
│   ├── rag-deployment.yaml        # Main application deployment
│   ├── rag-service.yaml           # Service routing for the RAG app
│   └── redis.yaml                 # Redis Deployment + Service (semantic response cache)
├── nginx/
│   ├── docs.conf                  # NGINX configuration for docs
│   └── nginx.conf                 # Main NGINX configuration
├── entrypoint.sh                  # Container initialization script
├── eval_router.py                 # Router accuracy evaluation harness
├── graph.py                       # Agentic workflow and graph definition
├── ingest.py                      # Document ingestion and processing
├── main.py                        # Application entry point
├── requirements.txt
├── setup_docs.sh                  # Initial documentation setup
└── uploads.py                     # File upload handling logic

```

---

## 📈 Evaluation Results

Measured with `eval_router.py` against a 49-query test set (real run output, not simulated):

| Category | Result |
| --- | --- |
| Out-of-Domain routing | 100.0% (5/5) |
| General Knowledge routing | 100.0% (5/5) |
| General Coding routing | 100.0% (5/5) |
| Edge Case routing | 76.9% (10/13) |
| **Overall** | **93.88% (46/49)** |
| Avg. router latency (LLM routing decision only) | 806.5 ms |

Edge cases are the current weak point in routing accuracy and the most likely area to improve next.

Corpus scale actually ingested and confirmed via ingestion logs: 42 source files (8 Markdown, 34 PDF), split into **90691 vector chunks** at the current `chunk_size=1000` / `chunk_overlap=200` splitter settings.

---

## 🗺️ Roadmap

* **Accessibility**: Can be accessed from anywhere.

* **Improve edge-case routing accuracy** (currently 76.9%, the weakest category in the eval set above).

* **PostgreSQL**: add SQL for metadata storage and caching, so the model can remember previous queries in the chat.