# kubectl exec -it api-994695959-4q8c4 -n app -- python -c "
# import sys
# sys.path.append('/app')
# import os
# import uuid
# from kubernetes import client, config

# try:
#     # Initialize the client
#     config.load_incluster_config()
#     k8s_v1 = client.CoreV1Api()
#     print('✓ Kubernetes client initialized')
    
#     # Test basic API access
#     nodes = k8s_v1.list_node()
#     print(f'✓ Can list nodes: {len(nodes.items)} nodes found')
    
#     # Test pod creation (dry run)
#     pod_name = f'sandbox-test-{str(uuid.uuid4())[:8]}'
#     namespace = 'app'
    
#     pod_manifest = {
#         'apiVersion': 'v1',
#         'kind': 'Pod',
#         'metadata': {
#             'name': pod_name,
#             'namespace': namespace,
#         },
#         'spec': {
#             'containers': [{
#                 'name': 'test-container',
#                 'image': 'nginx:alpine',
#                 'ports': [{'containerPort': 80}],
#             }],
#             'restartPolicy': 'Never'
#         }
#     }
    
#     # Try dry-run pod creation
#     result = k8s_v1.create_namespaced_pod(
#         namespace=namespace,
#         body=pod_manifest,
#         dry_run='All'
#     )
#     print('✓ Pod creation dry-run successful')
    
# except Exception as e:
#     print(f'✗ Error: {e}')
#     import traceback
#     traceback.print_exc()
# "

# kubectl exec -it api-994695959-4q8c4 -n app -- python -c "
# import sys
# sys.path.append('/app')
# import os
# import uuid
# from kubernetes import client, config

# try:
#     # Initialize the client
#     config.load_incluster_config()
#     k8s_v1 = client.CoreV1Api()
#     print('✓ Kubernetes client initialized')
    
#     # Test pod listing in the app namespace (this should work)
#     pods = k8s_v1.list_namespaced_pod(namespace='app')
#     print(f'✓ Can list pods in app namespace: {len(pods.items)} pods found')
    
#     # Test service listing in the app namespace
#     services = k8s_v1.list_namespaced_service(namespace='app')
#     print(f'✓ Can list services in app namespace: {len(services.items)} services found')
    
#     # Test pod creation (dry run) - this is what sandbox creation actually does
#     pod_name = f'sandbox-test-{str(uuid.uuid4())[:8]}'
#     namespace = 'app'
    
#     pod_manifest = {
#         'apiVersion': 'v1',
#         'kind': 'Pod',
#         'metadata': {
#             'name': pod_name,
#             'namespace': namespace,
#             'labels': {
#                 'app': 'sandbox',
# "   traceback.print_exc())reation operations work correctly')100m'}459000-g5/backend/backend-api:13',


# kubectl exec -it <api-pod-name> -n app -- python -c "
# import sys
# sys.path.append('/app')
# from utils.tools import session_containers
# print('Session containers:', session_containers)
# "