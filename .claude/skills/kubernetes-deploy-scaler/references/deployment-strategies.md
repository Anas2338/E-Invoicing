# Kubernetes Deployment Strategies

## Basic Deployment Configuration

### Simple Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: simple-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: simple-app
  template:
    metadata:
      labels:
        app: simple-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
```

### Production Deployment with Resource Management
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: production-app
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Allow 1 extra pod during update
      maxUnavailable: 0  # Don't allow any downtime
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
        image: my-app:v1.0.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "256Mi"
            cpu: "500m"
          limits:
            memory: "512Mi"
            cpu: "1000m"
        env:
        - name: ENV
          value: "production"
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
```

## Deployment Update Strategies

### Rolling Update (Default)
Gradually replaces old pods with new ones:
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 25%         # Maximum number of pods above desired count
    maxUnavailable: 25%   # Maximum number of pods that can be unavailable
```

### Recreate Strategy
Terminates all old pods before creating new ones:
```yaml
strategy:
  type: Recreate
```

## Advanced Deployment Patterns

### Blue-Green Deployment
```yaml
# Blue deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
      version: blue
  template:
    metadata:
      labels:
        app: my-app
        version: blue
    spec:
      containers:
      - name: app
        image: my-app:v1.0.0
        ports:
        - containerPort: 8080

---
# Green deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-app
      version: green
  template:
    metadata:
      labels:
        app: my-app
        version: green
    spec:
      containers:
      - name: app
        image: my-app:v2.0.0
        ports:
        - containerPort: 8080
```

### Canary Deployment
```yaml
# Primary deployment (stable version)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-primary
spec:
  replicas: 10
  selector:
    matchLabels:
      app: my-app
      track: stable
  template:
    metadata:
      labels:
        app: my-app
        track: stable
    spec:
      containers:
      - name: app
        image: my-app:v1.0.0
        ports:
        - containerPort: 8080

---
# Canary deployment (new version with limited traffic)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app-canary
spec:
  replicas: 2  # Small subset for testing
  selector:
    matchLabels:
      app: my-app
      track: canary
  template:
    metadata:
      labels:
        app: my-app
        track: canary
    spec:
      containers:
      - name: app
        image: my-app:v2.0.0
        ports:
        - containerPort: 8080
```

## Deployment Best Practices

### 1. Resource Management
Always specify resource requests and limits:
```yaml
resources:
  requests:
    memory: "256Mi"  # Minimum guaranteed resources
    cpu: "500m"      # Minimum guaranteed CPU
  limits:
    memory: "512Mi"  # Maximum allowed resources
    cpu: "1000m"     # Maximum allowed CPU
```

### 2. Health Checks
Implement proper liveness and readiness probes:
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3
```

### 3. Pod Disruption Budgets
Ensure availability during voluntary disruptions:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: app-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: production-app
```

### 4. Node Affinity and Tolerations
Control pod placement:
```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: node-type
          operator: In
          values:
          - production
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app
            operator: In
            values:
            - production-app
        topologyKey: kubernetes.io/hostname
```

### 5. Security Context
Apply security best practices:
```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 2000
  containers:
  - name: app
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

## Deployment Monitoring

### Common Metrics to Monitor
- Pod availability (desired vs current replicas)
- Deployment rollout status
- Resource utilization
- Health probe success rates

### Useful Commands
```bash
# Check deployment status
kubectl rollout status deployment/my-app

# View deployment history
kubectl rollout history deployment/my-app

# Rollback to previous version
kubectl rollout undo deployment/my-app

# Pause/resume deployment
kubectl rollout pause deployment/my-app
kubectl rollout resume deployment/my-app
```