---
name: kubernetes-deploy-scaler
description: |
  This skill helps deploy and scale containerized applications on Kubernetes from hello world to professional production systems. It provides best practices for Deployments, Services, Ingress, ConfigMaps, Secrets, and scaling strategies. Use when users need to deploy and scale applications on Kubernetes.
allowed-tools: Read, Grep, Glob, Bash
---

# Kubernetes Deploy & Scale

This skill helps deploy and scale containerized applications on Kubernetes from hello world to professional production systems, following Kubernetes best practices and production-ready configurations.

## What This Skill Does

- Creates optimized Kubernetes manifests for Deployments, Services, and Ingress
- Implements ConfigMaps and Secrets for configuration and sensitive data
- Sets up scaling strategies (HPA/VPA) for automatic resource management
- Provides production-ready configurations with proper resource limits
- Offers deployment strategies for zero-downtime updates

## When to Use This Skill

Use when users need to deploy and scale containerized applications on Kubernetes with proper configuration management, security, and auto-scaling capabilities.

## Before Implementation

Gather context to ensure successful implementation:

| Source | Gather |
|--------|--------|
| **Codebase** | Containerized application structure, Docker image location, environment variables |
| **Conversation** | User's specific deployment requirements, scaling needs, security constraints |
| **Skill References** | Kubernetes best practices from `references/` (deployments, services, scaling) |
| **User Guidelines** | Team-specific conventions, namespace policies, security policies |

Ensure all required context is gathered before implementing.
Only ask user for THEIR specific requirements (domain expertise is in this skill).

## Kubernetes Deployment Patterns

### 1. Hello World Deployment

Basic deployment for getting started:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello-world
  labels:
    app: hello-world
spec:
  replicas: 2
  selector:
    matchLabels:
      app: hello-world
  template:
    metadata:
      labels:
        app: hello-world
    spec:
      containers:
      - name: hello-world
        image: nginx:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
```

### 2. Production Deployment with ConfigMap and Secrets

Advanced deployment with configuration management:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: production-app
  labels:
    app: production-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: production-app
  template:
    metadata:
      labels:
        app: production-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        ports:
        - containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: database-url
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: log-level
        volumeMounts:
        - name: config-volume
          mountPath: /app/config
        - name: secret-volume
          mountPath: /app/secrets
          readOnly: true
        resources:
          requests:
            memory: "256Mi"
            cpu: "500m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: config-volume
        configMap:
          name: app-config
      - name: secret-volume
        secret:
          secretName: db-secret
```

## Service Configuration

### 1. ClusterIP Service (Internal Access)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: app-service
spec:
  selector:
    app: production-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: ClusterIP
```

### 2. LoadBalancer Service (External Access)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: app-loadbalancer
spec:
  selector:
    app: production-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: LoadBalancer
```

## Ingress Configuration

### Basic Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: app-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
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

### TLS-Enabled Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tls-app-ingress
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

## Scaling Strategies

### 1. Horizontal Pod Autoscaler (HPA)

Scale based on CPU/memory usage:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: production-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 2. Vertical Pod Autoscaler (VPA)

Adjust resource requests based on actual usage:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: app-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: production-app
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: app
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 2
        memory: 4Gi
      controlledResources:
      - cpu
      - memory
```

## Configuration Management

### ConfigMap

Store non-sensitive configuration data:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  log-level: "info"
  max-connections: "100"
  timeout: "30s"
```

### Secret

Store sensitive data (credentials, certificates):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  database-url: <base64-encoded-value>
  username: <base64-encoded-value>
  password: <base64-encoded-value>
```

## Production Deployment Workflow

### Step 1: Prepare Application
- Containerize application with proper Dockerfile
- Push image to registry
- Define resource requirements

### Step 2: Create Configuration
- Create ConfigMaps for configuration data
- Create Secrets for sensitive data
- Define proper resource limits

### Step 3: Deploy Application
- Create Deployment with appropriate replica count
- Set up health checks (liveness/readiness probes)
- Configure proper service accounts and RBAC

### Step 4: Expose Application
- Create Service for internal communication
- Set up Ingress for external access
- Configure TLS if needed

### Step 5: Enable Scaling
- Implement HPA for horizontal scaling
- Consider VPA for vertical scaling
- Set up monitoring and alerting

## Quality Checklist

Before deploying to production, ensure:

- [ ] Resource requests and limits defined
- [ ] Health checks configured (liveness/readiness)
- [ ] Proper service account and RBAC setup
- [ ] ConfigMaps and Secrets properly configured
- [ ] Rolling update strategy configured
- [ ] HPA/VPA implemented for scaling
- [ ] Service and Ingress configured
- [ ] Network policies applied (if needed)
- [ ] Monitoring and logging configured
- [ ] Backup and recovery strategy in place