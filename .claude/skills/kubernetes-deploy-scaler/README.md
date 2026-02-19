# Kubernetes Deploy & Scale Skill

This skill provides comprehensive Kubernetes support for deploying and scaling containerized applications, from basic deployments to production-ready systems with auto-scaling capabilities.

## Overview

The Kubernetes Deploy & Scale skill helps developers deploy and scale their containerized applications on Kubernetes with best practices for configuration management, security, and auto-scaling. It includes:

- Kubernetes manifest templates for Deployments, Services, and Ingress
- ConfigMap and Secret management patterns
- Horizontal and Vertical Pod Autoscaler configurations
- Production-ready deployment strategies
- Helper scripts for initialization and deployment

## Features

- **Smart Manifest Generation**: Creates optimized Kubernetes manifests based on application requirements
- **Auto-scaling Configuration**: Implements HPA and VPA for automatic resource management
- **Configuration Management**: Proper ConfigMap and Secret patterns for secure configuration
- **Production Patterns**: Ready-to-use configurations for production deployments
- **Deployment Strategies**: Support for rolling updates, blue-green, and canary deployments
- **Helper Scripts**: Automated setup and configuration tools

## Usage

### Automatic Detection and Setup

The skill provides a script to automatically generate Kubernetes configurations:

1. Navigate to your containerized application directory
2. Run the initialization script to create Kubernetes configuration files
3. Customize the generated files as needed
4. Deploy your application to Kubernetes

### Manual Configuration

Review the reference documentation for detailed patterns and best practices:
- Deployment strategies (`references/deployment-strategies.md`)
- Services and networking (`references/services-networking.md`)
- ConfigMaps and Secrets (`references/configmaps-secrets.md`)
- Scaling strategies (`references/scaling-strategies.md`)

## Components

- `SKILL.md`: Main skill documentation and usage instructions
- `references/`: Detailed documentation on Kubernetes best practices
- `scripts/init-k8s.sh`: Initialization script for creating Kubernetes configuration files
- `.yaml` templates: Sample configurations for various use cases

## Best Practices Implemented

- Proper resource requests and limits
- Health checks (liveness/readiness probes)
- Configuration management with ConfigMaps and Secrets
- Horizontal and Vertical Pod Autoscaling
- Rolling update strategies
- Security contexts and RBAC
- Network policies
- Pod Disruption Budgets
- Monitoring and observability integration

## Production Considerations

When deploying to production, consider:
- Implementing proper monitoring and alerting
- Using namespaces for environment separation
- Setting up backup and disaster recovery
- Configuring ingress controllers for external access
- Implementing network policies for security
- Regular security audits of configurations
- Using GitOps for configuration management