# Kubernetes ConfigMaps and Secrets Management

## ConfigMaps

### 1. Basic ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  log-level: "info"
  max-connections: "100"
  timeout: "30s"
  config.json: |
    {
      "database": {
        "host": "db.example.com",
        "port": 5432
      },
      "logging": {
        "level": "info"
      }
    }
```

### 2. Creating ConfigMap from Files
```bash
# From a properties file
kubectl create configmap app-properties --from-file=application.properties

# From multiple files
kubectl create configmap app-config --from-file=config1.properties --from-file=config2.properties

# From directory
kubectl create configmap app-config --from-file=./config/
```

### 3. Using ConfigMap as Environment Variables
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-with-env
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        env:
        - name: LOG_LEVEL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: log-level
        - name: MAX_CONNECTIONS
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: max-connections
        - name: TIMEOUT
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: timeout
```

### 4. Using ConfigMap as Volume Mounts
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-with-volume
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        volumeMounts:
        - name: config-volume
          mountPath: /app/config
          readOnly: true
        env:
        - name: CONFIG_PATH
          value: "/app/config"
      volumes:
      - name: config-volume
        configMap:
          name: app-config
          # Optional: Specify specific keys to mount
          items:
          - key: "config.json"
            path: "config.json"
          - key: "log-level"
            path: "log-level"
```

### 5. Using Entire ConfigMap as Environment Variables
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-all-env
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        envFrom:
        - configMapRef:
            name: app-config
```

## Secrets

### 1. Basic Secret
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  # Values must be base64 encoded
  username: YWRtaW4=  # admin
  password: MWYyZDFlMmU2N2Rm  # 1f2d1e2e67df
  database-url: cG9zdGdyZXNxbDovL2FkbWluOjFmMmQxZTJlNjdkZkBkYi5leGFtcGxlLmNvbTo1NDMyL215ZGI=  # postgresql://admin:1f2d1e2e67df@db.example.com:5432/mydb
```

### 2. Creating Secrets from Files
```bash
# From literal values
kubectl create secret generic db-secret \
  --from-literal=username=admin \
  --from-literal=password=securepassword \
  --from-literal=database-url=postgresql://admin:securepassword@db.example.com:5432/mydb

# From files
kubectl create secret generic tls-secret \
  --from-file=tls.crt=path/to/tls.crt \
  --from-file=tls.key=path/to/tls.key

# From environment file
kubectl create secret generic app-secret --from-env-file=.env
```

### 3. Using Secrets as Environment Variables
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-with-secret-env
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        env:
        - name: DB_USERNAME
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: username
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
```

### 4. Using Secrets as Volume Mounts
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-with-secret-volume
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        volumeMounts:
        - name: secret-volume
          mountPath: "/app/secrets"
          readOnly: true
        env:
        - name: SECRET_PATH
          value: "/app/secrets"
      volumes:
      - name: secret-volume
        secret:
          secretName: db-secret
          # Optional: Specify specific keys to mount
          items:
          - key: "username"
            path: "db-username"
          - key: "password"
            path: "db-password"
          # Optional: Set file permissions
          defaultMode: 0400
```

### 5. Using TLS Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tls-secret
type: kubernetes.io/tls
data:
  tls.crt: LS0tLS1CRUdJTi...
  tls.key: LS0tLS1CRUdJTi...
```

### 6. Using Docker Config Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: regcred
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: eyJhdXRocyI6eyJuYW1lIjp7InVzZXIiOiJhZG1pbiIsInBhc3N3b3JkIjoicGFzc3dvcmQifX19
```

## Best Practices for ConfigMaps and Secrets

### 1. Security Best Practices for Secrets
```yaml
# Use memory-based volumes for secrets when possible
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: app
    image: my-app:latest
    volumeMounts:
    - name: secret-volume
      mountPath: "/etc/secret-volume"
  volumes:
  - name: secret-volume
    emptyDir:
      medium: Memory  # Store in memory, not disk
    - name: my-secret
      secret:
        secretName: my-secret-name
```

### 2. Environment-Specific ConfigMaps
```yaml
# Development config
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config-dev
data:
  log-level: "debug"
  debug-mode: "true"

---
# Production config
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config-prod
data:
  log-level: "error"
  debug-mode: "false"
```

### 3. Immutable ConfigMaps and Secrets (Performance)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: immutable-config
immutable: true  # Improves performance for large numbers of pods
data:
  config-key: "config-value"

---
apiVersion: v1
kind: Secret
metadata:
  name: immutable-secret
immutable: true  # Improves performance for large numbers of pods
data:
  secret-key: c2VjcmV0LXZhbHVl
```

### 4. Pod Configuration with Both ConfigMap and Secret
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: full-config-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: full-config-app
  template:
    metadata:
      labels:
        app: full-config-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        ports:
        - containerPort: 8080
        # Environment variables from ConfigMap
        envFrom:
        - configMapRef:
            name: app-config
        # Individual secret environment variables
        env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
        # Volume mounts for config files
        volumeMounts:
        - name: config-volume
          mountPath: /app/config
        - name: secret-volume
          mountPath: /app/secrets
          readOnly: true
      volumes:
      - name: config-volume
        configMap:
          name: app-config
      - name: secret-volume
        secret:
          secretName: db-secret
```

## Secret Encryption at Rest

### Enable encryption at rest in Kubernetes cluster
```yaml
# EncryptionConfig.yaml
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
- resources:
  - secrets
  providers:
  - aescbc:
      keys:
      - name: key1
        secret: <KEY_IN_BASE64>
  - identity: {}
```

## Best Practices Summary

### ConfigMap Best Practices
- Use ConfigMaps for non-sensitive configuration data
- Organize configuration by application or environment
- Use volume mounts for configuration files
- Use environment variables for simple key-value pairs
- Consider using subPath for specific file mounting

### Secret Best Practices
- Use Secrets for sensitive data only
- Encode values in base64 (automatically done by kubectl create)
- Use volume mounts instead of environment variables when possible (to prevent process dumps)
- Enable encryption at rest for secrets
- Rotate secrets regularly
- Use Kubernetes RBAC to control access to secrets
- Don't store secrets in plain text in version control

### Common Commands
```bash
# Create ConfigMap
kubectl create configmap app-config --from-literal=key=value

# Create Secret
kubectl create secret generic my-secret --from-literal=key=value

# View ConfigMap
kubectl get configmap app-config -o yaml

# View Secret (decode base64 values)
kubectl get secret my-secret -o jsonpath='{.data.password}' | base64 -d

# Update ConfigMap
kubectl patch configmap app-config -p '{"data":{"new-key":"new-value"}}'

# Check if pod can access config
kubectl exec -it my-pod -- ls /etc/config
```

## Advanced Patterns

### 1. Sidecar for Dynamic Config Updates
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dynamic-config-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: dynamic-config-app
  template:
    metadata:
      labels:
        app: dynamic-config-app
    spec:
      containers:
      - name: app
        image: my-app:latest
        volumeMounts:
        - name: shared-config
          mountPath: /app/config
      - name: config-reloader
        image: busybox
        command: ['sh', '-c', 'while true; do inotifyd /app/reload-config /app/config:wm; sleep 1; done']
        volumeMounts:
        - name: shared-config
          mountPath: /app/config
      volumes:
      - name: shared-config
        configMap:
          name: app-config
```

### 2. External Secrets Operator Pattern
```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
spec:
  provider:
    vault:
      server: "https://vault.example.com"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "my-role"
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: db-secret
    creationPolicy: Owner
  data:
  - secretKey: username
    remoteRef:
      key: database
      property: username
  - secretKey: password
    remoteRef:
      key: database
      property: password
```