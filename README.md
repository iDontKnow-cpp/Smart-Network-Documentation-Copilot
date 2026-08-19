---

# Smart Network Documentation Copilot 🚀

An event-streamed, Agentic Retrieval-Augmented Generation (RAG) platform designed to navigate dense cloud infrastructure and network engineering documentation (AWS VPCs, Transit Gateways, BGP routing, and telemetry architectures).

This platform goes beyond static RAG pipelines by combining a **LangGraph state machine** for dynamic query routing with a **memory-optimized, streaming vector ingestion pipeline** running on Kubernetes.

---

## 🌟 Key Features

* **Agentic Routing:** Uses an LLM router to evaluate query domains prior to execution, dynamically directing requests between a local vector database and external search APIs to reduce out-of-domain hallucinations.
* **Fallback Web Search:** Routes to the **Tavily Search API** when the router classifies a query as out-of-domain, or when a local-context synthesis attempt returns an explicit "cannot answer from retrieved data" result — at which point local and web context are compared to produce a final answer.
* **Real-Time Event Streaming (SSE):** Implements Server-Sent Events via FastAPI to stream internal agent state transitions (*Routing* → *Searching Vector DB / Web* → *Synthesizing*) directly to the React frontend.
* **Memory-Safe File-by-File Ingestion Engine:** Processes each source file (Markdown + PDF) individually — load, chunk, embed, persist, then explicitly garbage-collect — before moving to the next file, rather than holding the entire corpus in memory at once. This replaced an earlier all-at-once approach that reliably caused Kubernetes `OOMKilled` failures once the real corpus size (26,748 PDF pages) was ingested.
* **Unbuffered NGINX Reverse Proxy:** `/api/` location configured with `proxy_buffering off` and `proxy_cache off` so SSE tokens aren't held back by proxy-level buffering.
* **Kubernetes Deployment:** Uses an `initContainer` for vector database seeding onto a shared `emptyDir` volume, with explicit CPU/memory/ephemeral-storage limits on every container and Horizontal Pod Autoscaling (HPA, requires `metrics-server` installed in-cluster).

---

## 🛠️ Tech Stack

| Category | Technology Stack |
| --- | --- |
| **Backend & Agent Core** | Python 3.10-slim, FastAPI, LangGraph, LangChain, ChromaDB |
| **AI Models & Search** | OpenAI (`gpt-4.1`, `text-embedding-3-small`), Tavily API |
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

To avoid the cgroup memory limit breaches seen during initial development with large PDF parsing, vector processing is isolated into a dedicated `initContainer` that runs to completion before the main containers start:

```text
+---------------------------------------------------------------------------------+
| Pod: rag-deployment                                                             |
|                                                                                 |
|  +-----------------------------------+                                          |
|  | [initContainer] data-ingestion    |                                          |
|  | - Processes files one at a time   | ---> Writes to /app/chroma_db           |
|  | - Batched Chroma inserts + gc()   |          |                               |
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

* Docker with Buildx enabled
* A running Kubernetes cluster (`kubeadm`, Minikube, or Docker Desktop)
* `kubectl` configured with cluster access
* `metrics-server` installed in-cluster if you want the HPA to actually scale (not included by default on `kubeadm` clusters)
* API keys for **OpenAI** and **Tavily**
* **At least 8 GB RAM available to the ingestion container if using the `:v6` backend tag.** The `:v8` tag's file-by-file ingestion is memory-safe on much smaller nodes — see the tag comparison in Roadmap below before choosing.

---

### 1. Clone the Repository 

```bash
git clone git@github.com:iDontKnow-cpp/Smart-Network-Documentation-Copilot.git
cd Smart-Network-Documentation-Copilot

```
To pull the pre-build images from docker hub. (Multi-platform linux build for both arm64 and amd64)
```bash
docker pull ujjwalrajpurohit/smart-network-documentation-copilot-backend:v8
docker pull ujjwalrajpurohit/smart-network-documentation-copilot-frontend:v3
```

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
  OPENAI_API_KEY: "your_openai_api_key_here"
  TAVILY_API_KEY: "your_tavily_api_key_here"

```

---

### 3. Build & Push Docker Images

```bash
# Backend — includes the ingestion engine and API server.
# Currently built for linux/amd64 only; multi-arch (arm64) is a planned
# follow-up, see Roadmap below.
docker buildx build --platform linux/amd64,linux/arm64 \
  -t <username>/<docker_repositry_name>:<tag> \
  -f docker/dockerfile.backend --push .

# Frontend — built multi-platform.
docker buildx build --platform linux/amd64,linux/arm64 \
  -t <username>/<docker_repositry_name>:<tag> \
  -f docker/dockerfile.frontend --push .

```

---

### 4. Deploy to Kubernetes 
Order matters.

```bash
kubectl apply -f kubernetes/secret.private.yaml
kubectl apply -f kubernetes/chroma-server.yaml
kubectl wait --for=condition=available deployment/chroma-server --timeout=60s
kubectl apply -f kubernetes/chroma-ingestion-job.yaml
kubectl wait --for=condition=complete job/chroma-ingestion --timeout=600s
kubectl apply -f kubernetes/rag-deployment.yaml
kubectl apply -f kubernetes/rag-service.yaml

```

---

### 5. Monitor Vector Ingestion

The `data-ingestion` initContainer prints progress per file (fetch → per-file load/chunk/embed → completion):

```bash
kubectl logs -n default -l app=rag-agent -c data-ingestion -f

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
Smart-Network-Documentation-Copilot/
├── docs/                           # Documentation PDFs and Markdown files for ingestion
├── docker/
│   ├── dockerfile.backend          # Python backend runtime container
│   └── dockerfile.frontend         # Multi-stage NGINX + React build container
├── kubernetes/
│   ├── chroma-server.yaml          # Server to access the chromaDB over HTTP for all pods
│   ├── chroma-ingestion-job.yaml   # Job to create the chromaDB
│   ├── rag-deployment.yaml         # Deployment manifest (initContainer, limits, volumes, HPA)
│   ├── rag-service.yaml            # NodePort service definition
│   └── secret.private.yaml         # API credentials (git-ignored)
├── frontend/                       # React.js SPA source code
│   ├── src/                        # SSE streaming components & UI
│   └── tailwind.config.js
├── main.py                         # FastAPI app entrypoint & SSE stream endpoint
├── graph.py                        # LangGraph state machine & routing workflow
├── ingest.py                       # File-by-file, memory-bounded vector ingestion script
├── eval_router.py                  # Router accuracy evaluation harness
├── nginx.conf                      # Reverse proxy config for unbuffered SSE streaming
└── requirements.txt

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

Edge cases are the current weak point in routing accuracy and the most likely area to improve next — see Roadmap.

Corpus scale actually ingested and confirmed via ingestion logs: **28 source files (3 Markdown, 25 PDF), 26,748 PDF pages**, split into **~63,700 vector chunks** at the current `chunk_size=1000` / `chunk_overlap=200` splitter settings.

---

## 🗺️ Roadmap

* **Accessability** : can be accessed from anywhere.
* **Improve edge-case routing accuracy** (currently 76.9%, the weakest category in the eval set above).
* **Files and Documents** Adding the feature to upload images, docs and pdf.
* **PostgreSQL**: add SQL for metadata storage and caching, so model can remember the previous queries in the chat. 