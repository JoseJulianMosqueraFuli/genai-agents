# RAG on Amazon S3 Vectors (managed via SDK)

The full-AWS RAG path uses **Amazon S3 Vectors** — a purpose-built S3 bucket type
that stores and queries embeddings through a dedicated API, with no cluster to
provision. You pay for storage + queries instead of a standing OpenSearch/Aurora
instance, which makes it the cheapest option for a document-grounded agent with
moderate, infrequent query volume.

We manage it **via the SDK** (`boto3.client("s3vectors")`), not the console or
Bedrock Knowledge Bases: the app owns the vector bucket, index, embeddings and
queries. This keeps RAG behaviour in code and under test.

> Sources: [Amazon S3 Vectors](https://aws.amazon.com/s3/features/vectors),
> [Working with S3 Vectors](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors.html),
> [boto3 s3vectors](https://docs.aws.amazon.com/boto3/latest/reference/services/s3vectors.html).
> Content was rephrased for compliance with licensing restrictions.

## The model stack (all Amazon)

| Function                 | Model                                                                | Notes                             |
| ------------------------ | -------------------------------------------------------------------- | --------------------------------- |
| Generation (strong tier) | Amazon **Nova Pro** (`us.amazon.nova-pro-v1:0`)                      | via Converse API                  |
| Generation (cheap tier)  | Amazon **Nova Micro** (`us.amazon.nova-micro-v1:0`)                  | `ComplexityRouter` tiering        |
| Embeddings               | Amazon **Titan Text Embeddings V2** (`amazon.titan-embed-text-v2:0`) | 1024 dims; Nova has no embeddings |

Nova is invoked through the **Converse API** (`bedrock.Converse`), which is
model-agnostic, so swapping Nova ↔ Claude ↔ Llama is a config change.

## How it maps to the code

`S3VectorStore` (`app/rag/s3_vectors.py`) implements the same `VectorStore` contract
as the in-memory store, so the LangGraph agent and pipeline are unchanged:

- `add_documents(texts)` → `provider.embed()` (Titan v2) → `put_vectors` (batched at 500).
  Document text is stored as **non-filterable** metadata under `text`.
- `search(query)` → `provider.embed([query])` → `query_vectors(topK, returnMetadata, returnDistance)`.
  Cosine distance is converted to a higher-is-better score (`1 - distance`).
- `ensure_index()` creates the vector bucket + index if missing (idempotent).

Backend selection is by config (`app/rag/factory.py`), mirroring the LLM/memory
strategy — no agent code changes when you flip it on.

## Enable it

```env
LLM_PROVIDER=bedrock
BEDROCK_REGION=us-east-1
BEDROCK_MODEL_ID=us.amazon.nova-pro-v1:0
BEDROCK_CHEAP_MODEL=us.amazon.nova-micro-v1:0
EMBEDDING_PROVIDER=bedrock
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
EMBEDDING_DIMENSION=1024

VECTOR_BACKEND=s3_vectors
S3_VECTORS_BUCKET=genai-agents-vectors
S3_VECTORS_INDEX=docs
```

The index dimension must match the embedding dimension (Titan v2 default 1024).

## Bootstrapping the index

Because we manage S3 Vectors via SDK, the index is created on first ingest. The
simplest path is the ingestion endpoint (`AgentPipeline.ingest` calls `ensure_index()`
once, then `add_documents`):

```bash
curl -s -X POST http://localhost:8000/v1/documents \
  -H 'Content-Type: application/json' \
  -d '{"documents":[{"text":"<your document chunk>","metadata":{"src":"docs"}}]}'
```

Or directly in code:

```python
from app.providers.factory import get_provider
from app.rag.factory import get_vector_store

store = get_vector_store(get_provider())
store.ensure_index()  # idempotent: bucket + index
await store.add_documents(["<your document chunks>"])
```

## IAM (Terraform)

When `s3_vectors_bucket` is set, `infra/terraform` attaches an `s3vectors:*`
policy to the ECS task role (create bucket/index, put/query/get/list/delete
vectors) alongside the Bedrock `InvokeModel`/`Converse` permissions. Nothing is
created in the console.

## When S3 Vectors is not the right fit

S3 Vectors targets cost and infrequent queries. If you need consistently high QPS
with strict low-latency p99, use OpenSearch Serverless (vector engine) instead — the
`VectorStore` abstraction means that would be another backend behind the same API.
