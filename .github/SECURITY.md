# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report privately via [GitHub Security Advisories](https://github.com/JoseJulianMosqueraFuli/genai-agents/security/advisories/new)
(Security → Report a vulnerability). Include a description, reproduction steps, and
affected versions if known. We aim to acknowledge reports within a few business days.

## Scope and handling

This is a demonstrative platform; still, please flag anything that could lead to:

- leakage of secrets or credentials (API keys, AWS credentials),
- prompt-injection or guardrail bypass (`app/guards/`),
- PII exposure in responses or logs,
- insecure infrastructure defaults (`infra/terraform/`).

## Secrets and configuration

- Never commit real secrets. `.env` and `*.tfvars` are git-ignored; only the
  `.example` files are tracked.
- The OpenAI key is provisioned via AWS Secrets Manager in the Terraform stack and
  injected into the container at runtime — it is not baked into the image.
- Treat all model output as untrusted; output guardrails redact PII before returning.

## Supported versions

The latest `main` receives fixes. Tagged releases are recorded in `CHANGELOG.md`.
