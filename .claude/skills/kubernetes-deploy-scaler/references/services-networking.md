# Kubernetes Services and Networking

## Service Types

### 1. ClusterIP (Default)
Exposes the service on a cluster-internal IP:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: app-clusterip
spec:
  selector:
    app: my-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: ClusterIP
```

### 2. NodePort
Exposes the service on each Node's IP at a static port:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: app-nodeport
spec:
  selector:
    app: my-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
      nodePort: 30080  # Optional: specify port (30000-32767)
  type: NodePort
```

### 3. LoadBalancer
Exposes the service externally using a cloud provider's load balancer:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: app-loadbalancer
spec:
  selector:
    app: my-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: LoadBalancer
```

### 4. ExternalName
Maps the service to the contents of the externalName field:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: external-service
spec:
  type: ExternalName
  externalName: my.database.example.com
```

## Headless Services

Services without a cluster IP (useful for StatefulSets):
```yaml
apiVersion: v1
kind: Service
metadata:
  name: headless-service
spec:
  selector:
    app: my-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  clusterIP: None  # Makes it headless
```

## Ingress Configuration

### Basic Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: basic-ingress
spec:
  rules:
  - host: myapp.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-service
            port:
              number: 80
```

### TLS Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - secure.example.com
    secretName: tls-secret
  rules:
  - host: secure.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: app-service
            port:
              number: 80
```

### Multiple Paths Ingress
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: multi-path-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  rules:
  - host: example.com
    http:
      paths:
      - path: /api(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /web(/|$)(.*)
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

## Advanced Ingress Features

### Rate Limiting
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rate-limit-ingress
  annotations:
    nginx.ingress.kubernetes.io/rate-limit-connections: "10"
    nginx.ingress.kubernetes.io/rate-limit-requests-per-second: "5"
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
```

### Authentication
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: auth-ingress
  annotations:
    nginx.ingress.kubernetes.io/auth-type: basic
    nginx.ingress.kubernetes.io/auth-secret: basic-auth
    nginx.ingress.kubernetes.io/auth-realm: 'Authentication Required'
spec:
  rules:
  - host: protected.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: protected-service
            port:
              number: 80
```

## Network Policies

Control traffic flow at the IP address or port level:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: app-netpol
spec:
  podSelector:
    matchLabels:
      app: my-app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          role: frontend
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: TCP
      port: 53
```

## Service Mesh Integration (Istio Example)

### Virtual Service
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: my-app-vs
spec:
  hosts:
  - my-app.example.com
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: my-app
        subset: v2
      weight: 100
  - route:
    - destination:
        host: my-app
        subset: v1
      weight: 90
    - destination:
        host: my-app
        subset: v2
      weight: 10
```

### Destination Rule
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: DestinationRule
metadata:
  name: my-app-dr
spec:
  host: my-app
  subsets:
  - name: v1
    labels:
      version: v1
  - name: v2
    labels:
      version: v2
```

## Load Balancing Configuration

### Session Affinity
```yaml
apiVersion: v1
kind: Service
metadata:
  name: session-affinity-service
spec:
  selector:
    app: my-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: LoadBalancer
  sessionAffinity: ClientIP
  sessionAffinityConfig:
    clientIP:
      timeoutSeconds: 10800
```

## Multi-Cluster Services

Cross-cluster service discovery:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: multi-cluster-service
  annotations:
    service.alpha.kubernetes.io/tolerate-unready-endpoints: "true"
spec:
  type: ClusterIP
  clusterIP: None
  publishNotReadyAddresses: true
  ports:
    - port: 80
      protocol: TCP
      targetPort: 8080
  selector:
    app: my-app
```

## Best Practices

### 1. Service Naming Convention
Use consistent naming patterns:
- `{app-name}-service` for main services
- `{app-name}-{environment}-svc` for environment-specific services

### 2. Port Management
- Use standard port ranges for internal services
- Document custom port assignments
- Consider using named ports for clarity

### 3. Health Checks
Configure health checks for services:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: monitored-service
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-protocol: HTTP
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-port: "8080"
    service.beta.kubernetes.io/aws-load-balancer-healthcheck-path: /health
spec:
  # ... service spec
```

### 4. Traffic Splitting
For gradual rollouts:
```yaml
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: traffic-splitting
spec:
  hosts:
  - my-service
  http:
  - route:
    - destination:
        host: my-service
        subset: stable
      weight: 80
    - destination:
        host: my-service
        subset: canary
      weight: 20
```

### 5. Monitoring and Observability
Include monitoring annotations:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: monitored-service
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8080"
    prometheus.io/path: "/metrics"
spec:
  # ... service spec
```

## Common Commands

```bash
# List services
kubectl get svc

# Describe a service
kubectl describe svc my-service

# Get service endpoints
kubectl get endpoints my-service

# Port forward to a service
kubectl port-forward service/my-service 8080:80

# Check service connectivity
kubectl run test-connection --image=nicolaka/netshoot -it --rm -- curl my-service:80
```