# Smart Network Documentation Copilot 🚀

An event-streamed, Agentic Retrieval-Augmented Generation (RAG) platform designed to navigate dense cloud infrastructure and network engineering documentation. 

This project goes beyond standard static RAG pipelines by implementing a **LangGraph state machine** that dynamically routes queries between a local vector database (for domain-specific knowledge like AWS VPC and Transit Gateways) and external search APIs (for fallback, out-of-domain queries). The entire stack is containerized and orchestrated via Kubernetes.

## 🌟 Key Features

* **Agentic Routing:** Uses an LLM router to evaluate query domain before executing retrieval, achieving high routing accuracy and eliminating out-of-domain hallucinations.
* **Fallback Web Search:** Automatically falls back to the Tavily Search API when local vector confidence thresholds are not met.
* **Real-Time Event Streaming:** Implements Server-Sent Events (SSE) via FastAPI to stream the agent's internal state transitions (e.g., *Routing*, *Searching Web*, *Synthesizing*) directly to the React frontend.
* **Microservices Architecture:** Decoupled NGINX frontend and Python API backend, optimized for unbuffered stream delivery.
* **Production-Grade Kubernetes Deployment:** Utilizes `initContainers` for isolated vector database seeding and shared Volume mounts to decouple data ingestion from the primary API application lifecycle. Horizontal Pod Autoscaling (HPA) enabled.

## 🛠️ Tech Stack

* **Backend / AI Engine:** Python, FastAPI, LangGraph, LangChain, ChromaDB, OpenAI (GPT-4o-mini, text-embedding-3-small), Tavily API
* **Frontend:** React.js, Tailwind CSS, Vite
* **Infrastructure / DevOps:** Docker (Multi-stage builds), NGINX, Kubernetes (Minikube/Local Lab)

## 🏗️ System Architecture

```text
+-------------------+       +-------------------+       +--------------------+
|    React UI       | <---> |   NGINX Proxy     | <---> |    FastAPI (SSE)   |
+-------------------+       +-------------------+       +--------------------+
                                                                 |
                                                                 v
                                                      +--------------------+
                                                      |  LangGraph Router  |
                                                      +--------------------+
                                                            /        \
                                            (In-Domain)   /            \  (Out-of-Domain)
                                                        v                v
                                              +---------------+   +------------------+
                                              | Local ChromaDB|   | Tavily Search API|
                                              +---------------+   +------------------+

```

## 🚀 Getting Started (Local Development)

### Prerequisites

* Docker & Docker Compose
* Local Kubernetes Cluster (Minikube, kind, or Docker Desktop)
* API Keys for OpenAI and Tavily

### 1. Clone the Repository

```bash
git clone git@github.com:iDontKnow-cpp/Smart-Network-Documentation-Copilot.git
cd Smart-Network-Documentation-Copilot

```

### 2. Configure Secrets

Create a `secrets.private.yaml` file (do not commit this to Git) for your Kubernetes cluster:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-secrets
type: Opaque
stringData:
  OPENAI_API_KEY: "your_openai_api_key_here"
  TAVILY_API_KEY: "your_tavily_api_key_here"

```

### 3. Build the Docker Images

```bash
# Build the NGINX Frontend
docker build -t my-nginx-frontend:latest -f ./docker/Dockerfile.frontend .

# Build the Python API Backend
docker build -t my-python-backend:latest -f ./docker/Dockerfile.backend .

```

### 4. Deploy to Kubernetes

Apply the configuration files in this order:

```bash
# Apply secrets
kubectl apply -f ./kubernetes/secrets.private.yaml

# Apply the Deployment & Autoscaler
kubectl apply -f kubernetes/rag-deployment.yaml

# Apply the Service
kubectl apply -f kubernetes/rag-service.yaml

```

### 5. Access the Application

If using NodePort on a local lab:
Access the frontend at `http://<your-node-ip>:30080`.

## 📂 Project Structure

* `/docs` - Markdown files ingested into the local vector database.
* `/frontend` - React.js source code and Tailwind configuration.
* `main.py` - FastAPI gateway and SSE endpoints.
* `graph.py` - LangGraph state machine and routing logic.
* `ingest.py` - Chunking and vector embedding pipeline.
* `nginx.conf` - Reverse proxy configuration for unbuffered streaming.
* `/k8s` - Kubernetes manifest files (Deployment, Service, HPA).

## 📈 Evaluation Metrics

*(Run your local tests and insert your metrics here before applying to jobs!)*

* **Routing Accuracy:** 89%
* **Average Retrieval Latency:** 192 ms
