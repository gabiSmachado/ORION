# mcp-server Helm Chart

Deploy the MCP Server component to Kubernetes.

## Installing

Package and install directly from this directory:

```bash
helm install my-mcp ./helm/mcp-server \
  --set image.repository=docker.io/gabiminz/mcp_server \
  --set image.tag=latest
```

## Values Overview

| Key | Description | Default |
|-----|-------------|---------|
| image.repository | Image repository (including registry) | docker.io/gabiminz/mcp_server |
| image.tag | Image tag | latest |
| service.port | Service & container port | 8000 |
| env | Extra environment variables | {} |
| config.enabled | Mount generated config.yaml | true |
| probes.enabled | Enable liveness/readiness HTTP probes | true |
| replicaCount | Number of pod replicas | 1 |

## Configuration File
The chart renders a `config.yaml` from `values.yaml` under `.Values.config` into a ConfigMap and mounts it at `/app/config/config.yaml` if `config.enabled` is true.

## Upgrading
```bash
helm upgrade my-mcp ./helm/mcp-server -f my-values.yaml
```

## Uninstall
```bash
helm uninstall my-mcp
```
