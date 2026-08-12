# Deploy genai-agents on AWS ECS Fargate (Spot)

This Terraform configuration deploys the `genai-agents` FastAPI service on **Amazon ECS Fargate with FARGATE_SPOT capacity** (on-demand not used), behind an ALB, with VPC + NAT, ECR, CloudWatch and IAM.

## Architecture

```
        Internet
           │
        [ALB :80] ──────────────► public subnets
           │
        [ECS Service]  FARGATE_SPOT capacity provider (weight 100)
           │  task: genai-agents (port 8000)
           ├─ ECR image
           ├─ CloudWatch Logs
           ├─ IAM execution role (ECR pull, logs, Secrets Manager)
           └─ IAM task role (Amazon Bedrock invoke)
                in private subnets via NAT
```

## Deploy

### 1. Prereqs

- AWS CLI configured with credentials
- Terraform >= 1.5
- Docker (to build & push the image)

### 2. Choose your LLM provider

Two options:

**Option A — AWS Bedrock (recommended, no secrets):**

```bash
cp terraform.tfvars.example terraform.tfvars
# keep llm_provider = "bedrock"; the task role already has bedrock:InvokeModel
```

**Option B — OpenAI:**

```bash
cp terraform.tfvars.example terraform.tfvars
# set llm_provider = "openai" and openai_api_key = "sk-..."
# (key goes to AWS Secrets Manager, never to the image)
```

### 3. Apply

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

Outputs:

- `alb_dns` — the public ALB endpoint, e.g. `genai-agents-dev-alb-XXXX.elb.amazonaws.com`
- `ecr_repository_url` — repository to push the image

### 4. Build & push the image

```bash
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REPO=$(cd infra/terraform && terraform output -raw ecr_repository_url)

aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com"

docker build -t "$REPO:latest" .
docker push "$REPO:latest"
```

### 5. Verify

```bash
ALB=$(cd infra/terraform && terraform output -raw alb_dns)
curl -s "http://$ALB/health"
# {"status":"ok","app":"genai-agents","provider":"bedrock","guardrails":true}

curl -s -X POST "http://$ALB/v1/agents/chat" \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is Kubernetes?"}'
```

> The ECS service only starts running the new image after the push. If the task was already
> running, force a new deployment: `aws ecs update-service --cluster <cluster> --service <service> --force-new-deployment`.

## FARGATE_SPOT

- The cluster uses `FARGATE_SPOT` as the **default capacity provider strategy (weight 100)**.
- Spot interruption on Fargate is graceful: ECS scales the task down with a warning, which is fine for a stateless API.
- The ALB health check (`/health`) routes traffic away from an interrupted task before removal.

## Teardown

```bash
cd infra/terraform
terraform destroy
```

## Notes

- The vector store is **in-memory** per task — replace with Amazon OpenSearch Serverless / pgvector for a persistent RAG store (see the project roadmap).
- Bedrock model access must be enabled in the AWS console for the chosen model ID.
