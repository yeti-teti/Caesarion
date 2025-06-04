# Caesarion

Python code execution in Kubernetes-based sandboxes.

## Architecture

### System Architecture
![System Architecture](https://drive.google.com/uc?export=view&id=1uPX6vurRm4I8h3stuJ6mxLtlA7G8SEvY)

### Overall System Flow
![Overall System Flow](https://drive.google.com/uc?export=view&id=1UGf5OkHPzIpgKlNHaC9cRT_93_N9qPtD)

### Pod Creation Flow
![Pod Creation Flow](https://drive.google.com/uc?export=view&id=1xw10oMOM22ncJFy-TOlijzbmepHExmrC)

### Component Flow
1. **Frontend Request** → Chat interface sends user messages to API
2. **index.py** → Routes requests and manages AI conversation flow
3. **tools.py** → Handles tool execution (weather, code execution)
4. **sandbox.py** → Manages Kubernetes pod lifecycle for code execution
5. **Kubernetes** → Creates isolated sandbox pods for secure code execution
6. **Sandbox Pod** → Executes Python code and returns structured output

## Features
### Secure Code Execution
- **Kubernetes Sandboxes**: Isolated pods for each user session
- **Resource Limits**: Memory (2Gi) and CPU (500m) constraints
- **Auto-cleanup**: Idle timeout management (1 hour)
- **Network Isolation**: Pod-to-pod communication via Kubernetes services

### File Management
- **Upload Support**: CSV, TXT, JSON, Python files
- **Session Persistence**: Files stored in `/uploaded_files/` within sandbox
- **Automatic Discovery**: AI automatically lists and inspects uploaded files


## Technology Stack

### Frontend
- Next.js

### Backend
- **Framework**: FastAPI with async/await support
- **LLM**: OpenAI GPT-4.1 with streaming responses
- **Orchestration**: Kubernetes Python client
- **Code Execution**: Jupyter kernels in isolated pods

### Infrastructure
- **Container Runtime**: Docker
- **Orchestration**: Kubernetes with RBAC
- **Networking**: Cluster DNS with service discovery
- **Storage**: EmptyDir volumes for sandbox isolation


## Security Features

### Sandbox Isolation
- **Process Isolation**: Each session runs in separate Kubernetes pods
- **Resource Limits**: CPU and memory constraints prevent resource exhaustion
- **Network Segmentation**: Pods communicate only through defined services
- **File System Isolation**: EmptyDir volumes ensure no persistent data leakage

### Input Validation
- **File Type Restrictions**: Only allowed file extensions accepted
- **Code Sanitization**: Input validation before execution
- **Session Management**: Unique session IDs with cleanup

