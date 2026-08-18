# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Amazon Bedrock AgentCore Runtime entrypoint (`app/runtime/agentcore_app.py`) and
  AgentCore Memory backend (`MEMORY_BACKEND=agentcore`).
- Full-AWS model stack: Amazon Nova via the Bedrock Converse API + Titan Text
  Embeddings V2.
- Amazon S3 Vectors RAG backend (`VECTOR_BACKEND=s3_vectors`), managed via SDK.
- Document ingestion endpoint `POST /v1/documents`.
- `ruff` lint/format wired into CI; `flake8` available as an optional local check.
- Community/governance files: `LICENSE`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, issue/PR templates, `CODEOWNERS`, Dependabot.

### Changed

- Dependency management migrated to **uv** (`pyproject.toml` + `uv.lock`); removed
  `requirements*.txt`.
- Docker files consolidated under `docker/`.
- Model tiering now routes the selected model to generation (previously only used as
  a cache key).

### Fixed

- ECS service now actually runs on **Fargate Spot** (was pinned to on-demand via
  `launch_type`).
- Response cache is invalidated on document ingestion (was serving stale answers).
- `LLMProviderError` returns a clean HTTP 502 instead of a raw 500.

## [0.2.0]

Model tiering, response caching, and the eval release gate. See
[`releases/v0.2.0.md`](releases/v0.2.0.md) for the measured report.

[Unreleased]: https://github.com/JoseJulianMosqueraFuli/genai-agents/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/JoseJulianMosqueraFuli/genai-agents/releases/tag/v0.2.0
