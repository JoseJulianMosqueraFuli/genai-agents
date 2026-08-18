# Deploying on Amazon Bedrock AgentCore

Amazon Bedrock AgentCore is AWS's managed platform for running agents in production
(GA October 2025). It is framework- and model-agnostic — you keep your LangGraph
graph and provider strategy, and AgentCore owns the operational surface: runtime,
memory, identity, gateway, observability. This repo integrates the two services that
matter most for a RAG agent: **Runtime** and **Memory**.

> Sources: [AgentCore is now GA](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-is-now-generally-available/),
> [Runtime starter toolkit](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-getting-started-toolkit.html),
> [Using any agent framework](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/using-any-agent-framework.html).
> Content was rephrased for compliance with licensing restrictions.

## AgentCore capabilities (state of the art)

| Service           | What it gives you                                                                                                     | Used here                                     |
| ----------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| **Runtime**       | Per-session microVM isolation, session affinity, fast cold starts, extended/async runtimes, OTel traces to CloudWatch | ✅ `app/runtime/agentcore_app.py`             |
| **Memory**        | Managed short-term (session) + long-term (cross-session) context                                                      | ✅ `app/agents/memory.py` (`AgentCoreMemory`) |
| **Gateway**       | Turns APIs/Lambdas into MCP tools with auth in front                                                                  | roadmap                                       |
| **Identity**      | OAuth / workload identity for agents and tools                                                                        | roadmap                                       |
| **Observability** | Built-in OTel; traces/metrics in CloudWatch (ADOT)                                                                    | inherited via Runtime                         |

Two serving paths ship in this repo, and both run the _same_ `AgentPipeline`
(`app/pipeline.py`) so behaviour is identical:

- **ECS Fargate** (`app/main.py` + `infra/terraform`) — you own the container/ALB/scaling.
- **AgentCore Runtime** (`app/runtime/agentcore_app.py`) — AWS owns the runtime.

## Runtime: the contract

An AgentCore Runtime agent must either use the SDK's `@app.entrypoint` decorator or
implement `/invocations` (POST) and `/ping` (GET), listening on port **8080**. We use
the decorator; `BedrockAgentCoreApp.run()` serves both endpoints. The entrypoint
receives the invocation `payload` (`{"prompt": "..."}`) and a runtime `context` (which
carries the session id used for memory affinity).

## Deploy with the starter toolkit

```bash
uv sync --extra agentcore

# 1. Configure (points at the entrypoint module + builds an ARM64 image)
agentcore configure --entrypoint app/runtime/agentcore_app.py

# 2. Launch to AgentCore Runtime (creates the agent runtime + IAM role)
agentcore launch

# 3. Invoke
agentcore invoke '{"prompt": "What is Kubernetes?"}'
```

Set provider credentials as runtime env/secrets (`LLM_PROVIDER=bedrock` avoids an
OpenAI key; the execution role needs `bedrock:InvokeModel`).

## Enable AgentCore Memory

Create a memory store once (console, CLI, or CloudFormation), then flip config:

```env
MEMORY_BACKEND=agentcore
AGENTCORE_MEMORY_ID=mem-xxxxxxxx
AGENTCORE_ACTOR_ID=user
BEDROCK_REGION=us-east-1
```

`get_memory()` (in `app/agents/memory.py`) swaps `InMemoryConversationMemory` for
`AgentCoreMemory` with no code change — same pattern as the LLM provider strategy.
Local dev and CI keep the in-memory backend, so tests never touch AWS.

## Manual container build

```bash
docker build -f Dockerfile.agentcore -t genai-agents-agentcore .
docker run -p 8080:8080 --env-file .env genai-agents-agentcore
curl -s localhost:8080/ping
curl -s localhost:8080/invocations -d '{"prompt":"What is Kubernetes?"}'
```

## Fargate vs Runtime — when to use which

- **Fargate**: you need a plain HTTP/REST service, custom middleware, or already run
  an ECS platform. Full control, more ops.
- **AgentCore Runtime**: you want managed session isolation, long-running/async agent
  turns, built-in identity and observability, and less infrastructure to own.
