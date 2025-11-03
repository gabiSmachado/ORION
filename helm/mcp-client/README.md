```markdown
# mcp-client Helm Chart

Deploy the MCP Client component to Kubernetes. The client connects to the MCP server (default service name `mcp-server`) and invokes tools via OpenAI function calling.

> Note: The provided Python client is interactive (reads an intent from STDIN). In a Kubernetes Pod you typically `kubectl exec` into the container to provide input, or you can extend the image to watch a queue / API. This chart focuses on packaging & configuration; adapt runtime behavior as needed.

## Installing

From repository root (where `helm/` lives):

```bash
helm install my-mcp-client ./helm/mcp-client \
  --set image.repository=docker.io/gabiminz/mcp_client \
  --set image.tag=latest \
  --set openai.existingSecret=my-openai-secret
```

Or (NOT recommended for production) pass the key inline to auto-create a Secret:

```bash
helm install my-mcp-client ./helm/mcp-client \
  --set openai.apiKey="$OPENAI_API_KEY"
```

## Values Overview

| Key | Description | Default |
|-----|-------------|---------|
| image.repository | Image repository | docker.io/gabiminz/mcp_client |
| image.tag | Image tag | latest |
| replicaCount | Number of pod replicas | 1 |
| env | Extra non-secret env vars | {} |
| openai.existingSecret | Use an existing secret for OPENAI_API_KEY | "" |
| openai.apiKey | Inline API key to create a Secret (dev only) | "" |
| openai.secretKey | Key within Secret | OPENAI_API_KEY |
| config.enabled | Mount generated config.yaml | true |
| config.mcp_server.host | MCP server hostname/service | mcp-server |
| config.mcp_server.port | MCP server port | 8000 |
| probes.enabled | Enable liveness/readiness probes | false |

## Configuration File
`values.yaml` under `.Values.config` renders to `/app/config/config.yaml` when `config.enabled` is true.

## Providing OpenAI API Key
Preferred: create a secret yourself:
```bash
kubectl create secret generic my-openai-secret \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY"
```
Then install with `--set openai.existingSecret=my-openai-secret`.

## Upgrading
```bash
helm upgrade my-mcp-client ./helm/mcp-client -f my-values.yaml
```

## Uninstall
```bash
helm uninstall my-mcp-client
```

## Next Steps
Consider adapting the client to consume intents from a message queue or CRD for unattended operation.
```
