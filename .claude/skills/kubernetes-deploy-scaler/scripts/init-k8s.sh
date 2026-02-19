#!/bin/bash
# Kubernetes initialization script for containerized applications

set -e

echo "Kubernetes Deploy & Scale - Initialization Script"
echo "==============================================="

# Function to detect Docker image
detect_image() {
    if [ -f "Dockerfile" ]; then
        echo "Found Dockerfile"
        # Try to extract image name from docker-compose or other sources
        if [ -f "docker-compose.yml" ]; then
            IMAGE_NAME=$(grep -o 'image: [^[:space:]]*' docker-compose.yml | head -n1 | cut -d' ' -f2)
            if [ ! -z "$IMAGE_NAME" ]; then
                echo "Detected image: $IMAGE_NAME"
                echo "$IMAGE_NAME"
                return 0
            fi
        fi
    fi

    echo "Could not detect container image. Please provide image name:"
    read -p "Enter container image name (e.g., nginx:latest, my-app:v1.0.0): " IMAGE_NAME
    echo "$IMAGE_NAME"
}

# Function to create basic Deployment
create_deployment() {
    local image_name="$1"
    local app_name="$2"
    local replicas="$3"

    cat > "${app_name}-deployment.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $app_name
  labels:
    app: $app_name
spec:
  replicas: $replicas
  selector:
    matchLabels:
      app: $app_name
  template:
    metadata:
      labels:
        app: $app_name
    spec:
      containers:
      - name: $app_name
        image: $image_name
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
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
EOF

    echo "Created $app_name-deployment.yaml"
}

# Function to create Service
create_service() {
    local app_name="$1"
    local service_type="$2"

    cat > "${app_name}-service.yaml" << EOF
apiVersion: v1
kind: Service
metadata:
  name: ${app_name}-service
  labels:
    app: $app_name
spec:
  selector:
    app: $app_name
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: $service_type
EOF

    echo "Created ${app_name}-service.yaml"
}

# Function to create basic HPA
create_hpa() {
    local app_name="$1"
    local min_replicas="$2"
    local max_replicas="$3"
    local cpu_threshold="$4"

    cat > "${app_name}-hpa.yaml" << EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ${app_name}-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: $app_name
  minReplicas: $min_replicas
  maxReplicas: $max_replicas
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: $cpu_threshold
EOF

    echo "Created ${app_name}-hpa.yaml"
}

# Function to create namespace
create_namespace() {
    local namespace="$1"

    cat > "namespace.yaml" << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: $namespace
EOF

    echo "Created namespace.yaml"
}

# Main execution
echo "Kubernetes Application Deployment Generator"
echo ""

# Get application name
read -p "Enter application name: " APP_NAME

# Get or detect image name
IMAGE_NAME=$(detect_image)

# Choose deployment type
echo ""
echo "Choose deployment complexity:"
echo "1) Basic (Deployment + Service)"
echo "2) Production (Deployment + Service + HPA)"
read -p "Enter choice (1 or 2): " DEPLOY_TYPE

# Get namespace
read -p "Enter namespace (default: $APP_NAME): " NAMESPACE
NAMESPACE=${NAMESPACE:-$APP_NAME}

# Get replica count
read -p "Enter initial replica count (default: 3): " REPLICAS
REPLICAS=${REPLICAS:-3}

if [ "$DEPLOY_TYPE" = "2" ]; then
    # Get HPA parameters
    read -p "Enter minimum replicas for HPA (default: 2): " MIN_REPLICAS
    MIN_REPLICAS=${MIN_REPLICAS:-2}

    read -p "Enter maximum replicas for HPA (default: 10): " MAX_REPLICAS
    MAX_REPLICAS=${MAX_REPLICAS:-10}

    read -p "Enter CPU utilization threshold for HPA (default: 70): " CPU_THRESHOLD
    CPU_THRESHOLD=${CPU_THRESHOLD:-70}

    echo ""
    echo "Choose service type:"
    echo "1) ClusterIP (internal access)"
    echo "2) LoadBalancer (external access)"
    echo "3) NodePort (node access)"
    read -p "Enter choice (1, 2, or 3): " SVC_CHOICE

    case $SVC_CHOICE in
        1) SVC_TYPE="ClusterIP" ;;
        2) SVC_TYPE="LoadBalancer" ;;
        3) SVC_TYPE="NodePort" ;;
        *) SVC_TYPE="ClusterIP" ;;
    esac
else
    SVC_TYPE="ClusterIP"
    MIN_REPLICAS=1
    MAX_REPLICAS=5
    CPU_THRESHOLD=70
fi

echo ""
echo "Creating Kubernetes configuration files..."

# Create namespace
create_namespace "$NAMESPACE"

# Create deployment
create_deployment "$IMAGE_NAME" "$APP_NAME" "$REPLICAS"

# Create service
create_service "$APP_NAME" "$SVC_TYPE"

if [ "$DEPLOY_TYPE" = "2" ]; then
    # Create HPA
    create_hpa "$APP_NAME" "$MIN_REPLICAS" "$MAX_REPLICAS" "$CPU_THRESHOLD"
fi

echo ""
echo "Kubernetes configuration created successfully!"
echo ""
echo "Files created:"
echo "- namespace.yaml"
echo "- ${APP_NAME}-deployment.yaml"
echo "- ${APP_NAME}-service.yaml"
if [ "$DEPLOY_TYPE" = "2" ]; then
    echo "- ${APP_NAME}-hpa.yaml"
fi
echo ""
echo "To deploy your application:"
echo "1. Review the generated YAML files"
echo "2. Run 'kubectl apply -f namespace.yaml' to create namespace"
echo "3. Run 'kubectl apply -f ${APP_NAME}-deployment.yaml' to create deployment"
echo "4. Run 'kubectl apply -f ${APP_NAME}-service.yaml' to create service"
if [ "$DEPLOY_TYPE" = "2" ]; then
    echo "5. Run 'kubectl apply -f ${APP_NAME}-hpa.yaml' to create HPA"
fi
echo ""
echo "For production deployments, consider:"
echo "- Adding ConfigMaps and Secrets"
echo "- Implementing proper health checks"
echo "- Setting up monitoring and logging"
echo "- Configuring ingress for external access"