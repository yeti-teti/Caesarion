# Caesarion

Python code execution in Kubernetes-based sandboxes.

## Demo Video
[![Demo Video](https://img.shields.io/badge/▶️_Watch_Demo-Google_Drive-blue?style=for-the-badge)](https://drive.google.com/file/d/1ZVXjrfha_-rzlIYy3VYYABKv0qtxRhJC/view?usp=sharing)



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

## Backend Architecture

### Application Structure
The backend is built with **FastAPI** and provides several key components:

#### Core Modules
- **`index.py`**: Main application entry point with chat endpoints and session management
- **`routers/sandbox.py`**: Kubernetes pod management and code execution orchestration
- **`utils/tools.py`**: Tool implementations (weather API, Python interpreter)
- **`utils/prompt.py`**: Message formatting and OpenAI integration

#### Key Features
- **Async/Await Support**: Full asynchronous request handling for concurrent operations
- **Streaming Responses**: Real-time code execution output via Server-Sent Events
- **Session Management**: Persistent sandbox environments tied to user sessions
- **File Upload Support**: Direct file transfer to sandbox environments
- **Error Handling**: Comprehensive timeout and error recovery mechanisms

### API Endpoints
```
POST /api/chat                          # Main chat interface with streaming
POST /api/sessions/{session_id}/initialize  # Proactive sandbox creation
POST /api/sandboxes                     # Create new sandbox pods
GET  /api/sandboxes                     # List active sandboxes
POST /api/sandboxes/{id}/execute        # Execute code in specific sandbox
POST /api/sandboxes/upload              # Upload files to sandbox
DELETE /api/sandboxes/{id}              # Cleanup sandbox resources
```

## Kubernetes Integration & RBAC

### Service Account & Permissions
The system uses a dedicated service account with specific RBAC permissions for dynamic pod management:

```yaml
# Service Account
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api-service-account
  namespace: app
```

### RBAC Permissions
The backend requires comprehensive Kubernetes permissions to manage sandbox lifecycle:

#### Pod Management
```yaml
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["create", "get", "list", "delete", "watch", "update", "patch"]
```
- **Create**: Spawn new sandbox pods for each session
- **Get/List**: Monitor pod status and readiness
- **Delete**: Cleanup idle or terminated sandboxes
- **Watch**: Real-time pod state monitoring
- **Update/Patch**: Modify pod configurations if needed

#### Pod Execution
```yaml
- apiGroups: [""]
  resources: ["pods/exec"]
  verbs: ["create", "get", "list", "delete", "watch", "update", "patch"]
```
- **Execute Commands**: File uploads via `kubectl exec` equivalent
- **Interactive Access**: Direct command execution in sandbox containers

#### Pod Logging
```yaml
- apiGroups: [""]
  resources: ["pods/log"]
  verbs: ["get", "list"]
```
- **Log Access**: Retrieve container logs for debugging
- **Output Streaming**: Real-time log monitoring

#### Service Management
```yaml
- apiGroups: [""]
  resources: ["services"]
  verbs: ["create", "get", "list", "delete"]
```
- **Service Creation**: ClusterIP services for pod networking
- **Internal Communication**: Service discovery for sandbox access
- **Cleanup**: Service removal during sandbox termination

### Dynamic Pod Creation Process

1. **Session Initialization**
   ```python
   # Create pod manifest with resource limits and security context
   pod_manifest = {
       "spec": {
           "containers": [{
               "image": "backend-api:latest",
               "resources": {
                   "limits": {"memory": "5Gi", "cpu": "500m"},
                   "requests": {"memory": "2Gi", "cpu": "100m"}
               }
           }]
       }
   }
   ```

2. **Service Creation**
   ```python
   # Create ClusterIP service for internal communication
   service_manifest = {
       "spec": {
           "selector": {"pod-name": pod_name},
           "ports": [{"port": 8000, "targetPort": 8000}]
       }
   }
   ```

3. **Networking & Communication**
   - **Service DNS**: `{sandbox-id}-service.app.svc.cluster.local:8000`
   - **Internal Routing**: ClusterIP for secure pod-to-pod communication
   - **Health Checks**: Readiness and liveness probes for reliability

### Security & Isolation

#### Resource Constraints
- **Memory Limits**: 5Gi maximum, 2Gi requests
- **CPU Limits**: 500m maximum, 100m requests
- **Execution Timeout**: 5-minute maximum per code execution

#### Network Isolation
- **Namespace Separation**: All components in dedicated `app` namespace
- **Service-based Communication**: No direct pod IP access
- **Egress Control**: Controlled outbound network access

#### File System Isolation
```yaml
volumeMounts:
  - name: "uploaded-files"
    mountPath: "/uploaded_files"
volumes:
  - name: "uploaded-files"
    emptyDir: {}
```
- **EmptyDir Volumes**: Ephemeral storage that dies with the pod
- **No Persistent Storage**: Prevents data leakage between sessions
- **Isolated Upload Directory**: Separate mount point for user files

## Infrastructure Details

### Kubernetes Cluster Configuration
- **Platform**: Google Kubernetes Engine (GKE)
- **Node Configuration**: Auto-scaling node pools with preemptible instances
- **Networking**: VPC-native cluster with private nodes
- **Security**: Workload Identity for secure service account mapping

### Deployment Strategy
- **Blue-Green Deployments**: Zero-downtime updates via Jenkins CI/CD
- **Health Checks**: Kubernetes health probes ensure service availability
- **Auto-scaling**: Horizontal Pod Autoscaler based on CPU/memory usage
- **Resource Management**: ResourceQuotas prevent resource exhaustion

### Monitoring & Observability
- **Metrics**: Prometheus for cluster and application metrics
- **Visualization**: Grafana dashboards for real-time monitoring
- **Logging**: Centralized logging with structured log collection
- **Alerting**: PrometheusAlerts for critical system events

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
- **Framework**: Next.js 14 with App Router
- **UI Components**: Tailwind CSS with custom components
- **Real-time Communication**: Server-Sent Events for streaming
- **File Handling**: Drag-and-drop upload with progress tracking

### Backend
- **Framework**: FastAPI with async/await support
- **LLM**: OpenAI GPT-4.1 with streaming responses
- **Orchestration**: Kubernetes Python client
- **Code Execution**: Jupyter kernels in isolated pods

### Infrastructure
- **Container Runtime**: Docker with multi-stage builds
- **Orchestration**: Kubernetes with RBAC
- **Networking**: Cluster DNS with service discovery
- **Storage**: EmptyDir volumes for sandbox isolation
- **CI/CD**: Jenkins with GitOps workflows
- **Infrastructure as Code**: Terraform for GCP resources

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

### RBAC Security Model
- **Principle of Least Privilege**: Service accounts with minimal required permissions
- **Namespace Isolation**: All resources scoped to specific namespace
- **Pod Security Standards**: Enforced security contexts and resource limits
- **Network Policies**: Controlled ingress/egress traffic rules


## Infrastructure & DevOps Pipeline
**Complete Infrastructure Repository**: [GitOps-Jen](https://github.com/yeti-teti/GitOps-Jen)

The complete infrastructure setup including Terraform, Jenkins CI/CD, Ansible automation, and monitoring stack is available in the GitOps-Jen repository. This includes:
- **Terraform**: GCP infrastructure provisioning (GKE, VPC, NAT, Firewall rules)
- **Jenkins**: CI/CD pipelines for automated deployment
- **Ansible**: Configuration management and automation
- **Monitoring**: Prometheus, Grafana, and logging setup