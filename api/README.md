# jAnus-Next API Backend

FastAPI-based backend service that orchestrates AI conversations and manages secure Python code execution in Kubernetes sandboxes.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                          │
├─────────────────────────────────────────────────────────────────┤
│  index.py          │ Main application, AI streaming, tool routing│
│  tools.py          │ Tool implementations (weather, code exec)  │
│  sandbox.py        │ Kubernetes pod lifecycle management       │
│  prompt.py         │ Message conversion and prompt handling     │
├─────────────────────────────────────────────────────────────────┤
│           Kubernetes Python Client Integration                  │
├─────────────────────────────────────────────────────────────────┤
│                     Sandbox Pods                               │
│  • Jupyter kernels  • File storage  • Isolated execution      │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Component Architecture

### Core Components

#### 1. **index.py** - Main Application
- **FastAPI Application**: ASGI server with async request handling
- **AI Integration**: OpenAI GPT-4 streaming with tool calling
- **Session Management**: User session tracking and sandbox assignment
- **Request Routing**: Chat endpoints and file upload handling

#### 2. **tools.py** - Tool System
- **Weather Tool**: Real-time weather data via Open-Meteo API
- **Python Interpreter**: Secure code execution orchestration
- **Session Tracking**: Container lifecycle and session mapping

#### 3. **sandbox.py** - Kubernetes Orchestration
- **Pod Management**: Dynamic sandbox creation and cleanup
- **Service Networking**: Cluster DNS-based pod communication
- **File Upload**: Kubernetes exec-based file transfer
- **Resource Management**: CPU/memory limits and health monitoring

#### 4. **prompt.py** - Message Processing
- **Format Conversion**: Client messages to OpenAI format
- **Attachment Handling**: File and image processing
- **Tool Invocation**: Tool call serialization and result handling

## 🛠️ Technical Implementation

### FastAPI Application Structure

```python
# Main application with lifespan management
app = FastAPI()
app.include_router(sandbox.router)

# Streaming response with tool execution
async def stream_text(session_id: str, messages: List[ChatCompletionMessageParam])

# Session initialization and sandbox creation
@app.post("/api/sessions/{session_id}/initialize")
async def initialize_session(session_id: str)
```

### Kubernetes Integration

#### Pod Specification
```yaml
apiVersion: v1
kind: Pod
metadata:
  labels:
    app: sandbox
    sbx: "1"
spec:
  containers:
  - name: jupyter-sandbox
    image: us-central1-docker.pkg.dev/exalted-crane-459000-g5/backend/backend-api:17
    resources:
      limits:
        memory: "5Gi"
        cpu: "500m"
      requests:
        memory: "2Gi" 
        cpu: "100m"
    volumeMounts:
    - name: uploaded-files
      mountPath: /uploaded_files
```

#### Service Networking
```python
# Service DNS resolution for inter-pod communication
service_url = f"http://{sandbox_id}-service.{namespace}.svc.cluster.local:8000/execute"
```

### Tool System Design

#### Tool Registration
```python
available_tools = {
    "get_current_weather": get_current_weather,
    "python_interpreter": python_interpreter
}
```

#### Async Tool Execution
```python
async def python_interpreter(code, session_id=None):
    # 1. Validate session and create sandbox if needed
    # 2. Execute code via HTTP to sandbox pod
    # 3. Stream results back to client
    # 4. Handle errors and timeouts
```

## 🔒 Security Implementation

### Sandbox Isolation
- **Process Isolation**: Each user session in separate Kubernetes pods
- **Resource Limits**: Memory (5Gi) and CPU (500m) constraints prevent resource exhaustion
- **Network Segmentation**: Pods communicate only through Kubernetes services
- **File System Isolation**: EmptyDir volumes with no persistent storage

### Input Validation
```python
# File type restrictions
allowed_extensions = {'.csv', '.xlsx', '.json', '.txt', '.parquet'}

# Code execution timeout
tool_result = await asyncio.wait_for(
    tool_function(**json.loads(tool_call["arguments"])),
    timeout=300.0  # 5 minutes max execution time
)
```

### Error Handling
- **Timeout Protection**: Automatic termination of long-running operations
- **Resource Cleanup**: Automatic pod termination after idle timeout
- **Error Propagation**: Structured error responses with debugging info

## 🚀 API Endpoints

### Chat Endpoints
```http
POST /api/chat
Content-Type: application/json

{
  "messages": [{"role": "user", "content": "Analyze this data"}],
  "session_id": "unique-session-id"
}
```

### Session Management
```http
POST /api/sessions/{session_id}/initialize
# Creates sandbox pod proactively

GET /sandboxes
# Lists all active sandbox pods

DELETE /sandboxes/{sandbox_id}
# Cleanup sandbox resources
```

### File Upload
```http
POST /api/sandboxes/upload?session_id={session_id}
Content-Type: multipart/form-data

# Uploads file to sandbox /uploaded_files/ directory
```

## 🐳 Container Configuration

### Base Image
```dockerfile
FROM jupyter/scipy-notebook:latest
# Provides Python, Jupyter, and scientific computing libraries
```

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_api_key

# Optional Configuration
KUBERNETES_NAMESPACE=app
SANDBOX_IMAGE=custom_sandbox_image
IS_SANDBOX=1  # Set automatically in sandbox containers
```

## 🔄 Lifecycle Management

### Session Lifecycle
1. **Session Creation**: Frontend requests session initialization
2. **Pod Provisioning**: Kubernetes pod created with unique sandbox ID
3. **Service Registration**: ClusterIP service for pod communication
4. **Code Execution**: HTTP requests to sandbox for tool execution
5. **Idle Management**: Automatic cleanup after 1 hour of inactivity

### Resource Management
```python
# Automatic cleanup of idle sandboxes
async def terminate_idle_sandboxes():
    while True:
        await asyncio.sleep(CHECK_INTERVAL)  # 1 hour
        # Check last activity and cleanup idle pods
```

## 📊 Monitoring and Health Checks

### Health Endpoints
```python
@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}
```

### Kubernetes Probes
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 3

livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 10
```

## 🚀 Development Setup

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=your_key_here

# Run development server
uvicorn index:app --reload --host 0.0.0.0 --port 8000
```

### Docker Development
```bash
# Build container
docker build -t janus-api .

# Run with Kubernetes access
docker run -p 8000:8000 \
  -v ~/.kube:/root/.kube \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  janus-api
```

## 🧪 Testing

### Unit Testing
```bash
# Run tests
pytest tests/

# Test specific components
pytest tests/test_sandbox.py
pytest tests/test_tools.py
```

### Integration Testing
```bash
# Test Kubernetes integration
kubectl exec -it api-pod -- python -c "
from routers.sandbox import create_sandbox
print('Sandbox creation test')
"
```

## 🔧 Configuration Options

### Kubernetes Configuration
```python
# Auto-detect configuration method
try:
    config.load_incluster_config()  # In-cluster
except:
    config.load_kube_config()       # Local kubeconfig
```

### Sandbox Image Configuration
```python
IMAGE_NAME = os.environ.get(
    "SANDBOX_IMAGE", 
    "us-central1-docker.pkg.dev/exalted-crane-459000-g5/backend/backend-api:17"
)
```

## 🐛 Troubleshooting

### Common Issues

#### Pod Creation Failures
```bash
# Check RBAC permissions
kubectl auth can-i create pods --as=system:serviceaccount:app:api

# Check resource quotas
kubectl describe resourcequota -n app
```

#### Network Connectivity
```bash
# Test service DNS resolution
kubectl exec api-pod -- nslookup sandbox-service.app.svc.cluster.local

# Check pod networking
kubectl exec api-pod -- curl http://sandbox-service:8000/health
```

#### File Upload Issues
```bash
# Check pod permissions
kubectl exec sandbox-pod -- ls -la /uploaded_files/

# Verify volume mounts
kubectl describe pod sandbox-pod
```

## 📈 Performance Considerations

### Resource Optimization
- **Async Operations**: All I/O operations use async/await
- **Connection Pooling**: Shared HTTP client instances
- **Streaming Responses**: Chunked transfer for large outputs

### Scalability
- **Horizontal Scaling**: Multiple API pods with shared Kubernetes access
- **Resource Isolation**: Per-session sandbox pods prevent interference
- **Auto-cleanup**: Automatic resource reclamation prevents resource leaks

## 🔮 Future Enhancements

- [ ] **Multi-language Support**: R, JavaScript, Go sandbox images
- [ ] **Persistent Storage**: Volume claims for file persistence
- [ ] **Authentication**: JWT-based session management
- [ ] **Rate Limiting**: Per-user execution quotas
- [ ] **Metrics Collection**: Prometheus integration for monitoring
- [ ] **GPU Support**: CUDA-enabled sandbox pods for ML workloads

