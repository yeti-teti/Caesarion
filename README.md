# jAnus-Next

An AI-powered interactive coding assistant with secure Python code execution in Kubernetes-based sandboxes.

## 🚀 Overview

jAnus-Next is a sophisticated chat application that combines conversational AI with secure code execution capabilities. Users can interact with "Cesarion," an advanced AI assistant that can execute Python code in isolated Kubernetes pods, upload files, perform data analysis, and provide real-time results with Jupyter-style output rendering.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Backend   │    │  K8s Sandboxes  │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (Python)      │
│                 │    │                 │    │                 │
│ • Chat UI       │    │ • Session Mgmt  │    │ • Code Exec     │
│ • File Upload   │    │ • Tool Routing  │    │ • File Storage  │
│ • Jupyter Output│    │ • AI Integration│    │ • Jupyter Kernel│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Flow
1. **Frontend Request** → Chat interface sends user messages to API
2. **index.py** → Routes requests and manages AI conversation flow
3. **tools.py** → Handles tool execution (weather, code execution)
4. **sandbox.py** → Manages Kubernetes pod lifecycle for code execution
5. **Kubernetes** → Creates isolated sandbox pods for secure code execution
6. **Sandbox Pod** → Executes Python code and returns structured output

## ✨ Features

### 🤖 AI Assistant
- **Cesarion**: Advanced AI assistant powered by OpenAI GPT-4
- Specialized in systematic reasoning and code execution
- Context-aware conversations with tool integration

### 🔒 Secure Code Execution
- **Kubernetes Sandboxes**: Isolated pods for each user session
- **Resource Limits**: Memory (5Gi) and CPU (500m) constraints
- **Auto-cleanup**: Idle timeout management (1 hour)
- **Network Isolation**: Pod-to-pod communication via Kubernetes services

### 📁 File Management
- **Upload Support**: CSV, TXT, JSON, Python files
- **Session Persistence**: Files stored in `/uploaded_files/` within sandbox
- **Automatic Discovery**: AI automatically lists and inspects uploaded files

### 🎨 Modern UI
- **Responsive Design**: Mobile-first with Tailwind CSS
- **Real-time Chat**: Streaming responses with tool execution status
- **Jupyter Output**: Rich rendering of code execution results
- **File Preview**: Attachment previews with upload progress

## 🛠️ Technology Stack

### Frontend
- **Framework**: Next.js 13.4.4 with App Router
- **Styling**: Tailwind CSS with Radix UI components
- **State Management**: React hooks with AI SDK
- **Type Safety**: TypeScript with strict configuration

### Backend
- **Framework**: FastAPI with async/await support
- **AI Integration**: OpenAI GPT-4 with streaming responses
- **Orchestration**: Kubernetes Python client
- **Code Execution**: Jupyter kernels in isolated pods

### Infrastructure
- **Container Runtime**: Docker with multi-stage builds
- **Orchestration**: Kubernetes with RBAC
- **Networking**: Cluster DNS with service discovery
- **Storage**: EmptyDir volumes for sandbox isolation

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Kubernetes cluster (local or cloud)
- OpenAI API key
- Node.js 18+ and Python 3.8+

### 1. Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd jAnus-Next

# Set up environment variables
cp api/.env.local.example api/.env.local
# Add your OPENAI_API_KEY to api/.env.local
```

### 2. Local Development

#### Option A: Docker Compose (Recommended)
```bash
# Build and run all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:3000
# API: http://localhost:8000
```

#### Option B: Manual Setup
```bash
# Terminal 1: API
cd api
pip install -r requirements.txt
uvicorn index:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

### 3. Kubernetes Deployment
```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Verify deployment
kubectl get pods -n app
kubectl get services -n app
```

## 📚 Component Documentation

### 📱 [Frontend README](./frontend/README.md)
- Next.js application architecture
- UI component system
- State management patterns
- Build and deployment process

### 🔧 [API README](./api/README.md)
- FastAPI service architecture
- Kubernetes integration details
- Tool system and AI routing
- Sandbox lifecycle management

## 🔧 Configuration

### Environment Variables

#### API Configuration
```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional
KUBERNETES_NAMESPACE=app                    # Default namespace
SANDBOX_IMAGE=your_custom_sandbox_image    # Custom sandbox image
IS_SANDBOX=1                               # Set in sandbox containers
```

#### Frontend Configuration
```bash
# API endpoint (automatically configured)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🔐 Security Features

### Sandbox Isolation
- **Process Isolation**: Each session runs in separate Kubernetes pods
- **Resource Limits**: CPU and memory constraints prevent resource exhaustion
- **Network Segmentation**: Pods communicate only through defined services
- **File System Isolation**: EmptyDir volumes ensure no persistent data leakage

### Input Validation
- **File Type Restrictions**: Only allowed file extensions accepted
- **Code Sanitization**: Input validation before execution
- **Session Management**: Unique session IDs with cleanup

## 📊 Monitoring and Observability

### Health Checks
- **API Health**: `/health` endpoint for service monitoring
- **Pod Readiness**: Kubernetes readiness and liveness probes
- **Resource Monitoring**: Built-in Kubernetes metrics

### Logging
- **Structured Logging**: JSON format for easy parsing
- **Error Tracking**: Comprehensive error handling and reporting
- **Execution Tracing**: Tool execution and sandbox lifecycle logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow TypeScript/Python type annotations
- Add tests for new features
- Update documentation for API changes
- Ensure Kubernetes manifests are valid

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues and questions:
1. Check the [Issues](./issues) page
2. Review component-specific READMEs
3. Check Kubernetes logs: `kubectl logs -n app deployment/api`

## 🗺️ Roadmap

- [ ] Multi-language sandbox support (JavaScript, R, etc.)
- [ ] Persistent file storage with volume claims
- [ ] Advanced visualization capabilities
- [ ] Collaborative sessions
- [ ] API rate limiting and authentication
- [ ] Performance monitoring dashboard
