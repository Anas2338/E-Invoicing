# Kubernetes Scaling Strategies

## Horizontal Pod Autoscaler (HPA)

### 1. Basic HPA with CPU Utilization
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa-cpu
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 2. HPA with Multiple Metrics (CPU and Memory)
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa-multi
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 15
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

### 3. HPA with Custom Metrics
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa-custom
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Pods
    pods:
      metric:
        name: packets-per-second
      target:
        type: AverageValue
        averageValue: "1k"
  - type: Object
    object:
      metric:
        name: requests-per-second
      describedObject:
        apiVersion: networking.k8s.io/v1
        kind: Ingress
        name: main-route
      target:
        type: Value
        value: "10k"
```

### 4. Advanced HPA with Behavior Configuration
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa-advanced
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Min
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 5
        periodSeconds: 60
      selectPolicy: Max
```

## Vertical Pod Autoscaler (VPA)

### 1. Basic VPA Recommendation
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: app-vpa-recommend
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Off"  # Only provide recommendations
```

### 2. VPA with Auto Update
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: app-vpa-auto
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Auto"  # Automatically update resources
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
      controlledValues: RequestsAndLimits
```

### 3. VPA with Specific Container Policy
```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: app-vpa-detailed
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: app
      minAllowed:
        cpu: 200m
        memory: 256Mi
      maxAllowed:
        cpu: 4
        memory: 8Gi
      controlledResources:
      - cpu
      - memory
      controlledValues: RequestsAndLimits
    - containerName: sidecar
      minAllowed:
        cpu: 50m
        memory: 64Mi
      maxAllowed:
        cpu: 500m
        memory: 512Mi
      controlledResources:
      - cpu
      controlledValues: RequestsOnly
```

## Cluster Autoscaler

### 1. Cluster Autoscaler Configuration
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-autoscaler-status
  namespace: kube-system
data:
  status: "ok"
```

```yaml
# Example for AWS EKS
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      containers:
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.21.0
        name: cluster-autoscaler
        resources:
          limits:
            cpu: 100m
            memory: 300Mi
          requests:
            cpu: 100m
            memory: 300Mi
        command:
        - ./cluster-autoscaler
        - --v=4
        - --stderrthreshold=info
        - --cloud-provider=aws
        - --skip-nodes-with-local-storage=false
        - --expander=least-waste
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/my-cluster
        - --balance-similar-node-groups
        - --scale-down-delay-after-add=10m
        - --scale-down-unneeded-time=10m
        - --scale-down-utilization-threshold=0.5
```

## Custom Metrics Scaling

### 1. Prometheus Adapter Configuration
```yaml
# Example Custom Metrics HPA using Prometheus
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-prometheus-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
```

### 2. KEDA (Kubernetes Event Driven Autoscaling)
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: app-keda-scaledobject
spec:
  scaleTargetRef:
    name: my-app
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
  - type: prometheus
    metadata:
      serverAddress: http://prometheus.kube-system.svc:9090
      metricName: http_requests_total
      threshold: '100'
      query: sum(rate(http_requests_total[2m]))
```

## Scaling Best Practices

### 1. Resource Requests and Limits
```yaml
# Properly configured deployment for scaling
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scalable-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scalable-app
  template:
    metadata:
      labels:
        app: scalable-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        resources:
          requests:
            # Essential for HPA calculations
            memory: "256Mi"  # Minimum guaranteed resources
            cpu: "250m"      # Minimum guaranteed CPU
          limits:
            # Prevent resource exhaustion
            memory: "512Mi"  # Maximum allowed resources
            cpu: "500m"      # Maximum allowed CPU
        ports:
        - containerPort: 8080
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

### 2. Multi-Dimensional Scaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: multi-dimensional-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 50
  metrics:
  # Scale based on CPU usage
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  # Scale based on memory pressure
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  # Scale based on custom business metrics
  - type: Pods
    pods:
      metric:
        name: queue_length
      target:
        type: AverageValue
        averageValue: "10"
```

### 3. Staged Scaling Strategy
```yaml
# Stage 1: Initial deployment with conservative scaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa-initial
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60

---
# Stage 2: Enhanced scaling with custom metrics
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa-enhanced
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      selectPolicy: Max
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
      selectPolicy: Min
```

## Scaling Monitoring and Observability

### 1. HPA Status Monitoring
```bash
# Check HPA status
kubectl get hpa
kubectl describe hpa my-app-hpa

# Monitor scaling events
kubectl get events --field-selector involvedObject.kind=HorizontalPodAutoscaler

# View current metrics
kubectl top pods
kubectl top nodes
```

### 2. Scaling Performance Tuning
```yaml
# Fine-tuned HPA for responsive scaling
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: responsive-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 3
  maxReplicas: 100
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 65
  behavior:
    scaleUp:
      # Quick scale up for traffic spikes
      stabilizationWindowSeconds: 30
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
    scaleDown:
      # Conservative scale down to avoid thrashing
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Min
```

## Scaling Troubleshooting

### Common Issues and Solutions

1. **HPA Not Scaling**:
   - Verify metrics server is running: `kubectl top nodes`
   - Check resource requests are set on containers
   - Ensure correct targetRef in HPA spec

2. **Frequent Scaling (Thrashing)**:
   - Increase stabilization windows
   - Adjust scaling policies to be more conservative
   - Review metric thresholds

3. **Scaling Too Slowly**:
   - Decrease stabilization windows
   - Increase scaling policies (percent/pods)
   - Adjust metric targets

### Diagnostic Commands
```bash
# Check metrics server
kubectl get apiservice v1beta1.metrics.k8s.io
kubectl top pods

# Check HPA events
kubectl get events --field-selector involvedObject.name=your-hpa-name

# Debug HPA
kubectl describe hpa your-hpa-name
```

## Production Scaling Patterns

### 1. Time-Based Scaling (Cron Scaling)
```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: cron-scaledobject
spec:
  scaleTargetRef:
    name: my-app
  triggers:
  - type: cron
    metadata:
      timezone: Asia/Kolkata
      start: 0 9 * * 1-5  # 9 AM on weekdays
      end: 0 17 * * 1-5   # 5 PM on weekdays
      desiredReplicas: "10"
```

### 2. Predictive Scaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: predictive-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 5  # Higher baseline during predictable peak hours
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 50  # Lower threshold during peak prediction
  behavior:
    scaleUp:
      # Aggressive scale up during predicted peaks
      policies:
      - type: Percent
        value: 200
        periodSeconds: 30
```

These scaling strategies provide a comprehensive approach to Kubernetes application scaling, from basic CPU-based scaling to advanced custom metrics and event-driven scaling patterns.