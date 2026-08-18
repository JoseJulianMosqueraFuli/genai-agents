# Contributing to genai-agents

Thanks for your interest in contributing! This project is a production-grade GenAI
agent platform, and it's developed **test-first (TDD)**: write the failing test, then
implement.

## Prerequisites

- Python 3.12 (see `.python-version`)
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- (Optional) Docker, Terraform ≥ 1.5 for the infra paths

## Getting started

```bash
git clone https://github.com/JoseJulianMosqueraFuli/genai-agents.git
cd genai-agents
uv sync                 # installs runtime + dev deps from uv.lock
cp .env.example .env    # fill OPENAI_API_KEY, or switch to bedrock
```

## Development workflow

1. Create a branch: `git checkout -b feat/short-description` (never push to `main`).
2. Write a failing test first (see `tests/`), then implement.
3. Keep changes scoped and add tests for new behaviour — all providers/SDKs are mocked,
   so tests need no network or credentials.
4. Run the full local gate before opening a PR:

```bash
uv run ruff format .        # format
uv run ruff check .         # lint (enforced in CI)
uv run pytest tests/ -v     # 53 tests, must stay green
```

If you touch `infra/terraform/`:

```bash
terraform -chdir=infra/terraform fmt -recursive
terraform -chdir=infra/terraform test
```

## Conventions

- **Style**: ruff (line-length 100). `ruff format` is the source of truth; don't hand-format.
- **Commits**: use [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `ci:`).
- **Architecture**: read `AGENTS.md` for the project map and gotchas (lazy provider
  init, guarded optional imports, single-pipeline source of truth).
- **Dependencies**: managed with uv. Add with `uv add <pkg>` (or `uv add --group dev`
  / `--optional agentcore`), and commit the updated `pyproject.toml` + `uv.lock`.

## Pull requests

- Keep PRs focused; one logical change per PR.
- Fill in the PR template (summary, testing, breaking changes).
- CI must pass (lint + tests, and Terraform checks if infra changed).
- Update docs (`README.md`, `docs/`, `AGENTS.md`) when behaviour or commands change.

## Reporting bugs / requesting features

Open an issue using the templates in `.github/ISSUE_TEMPLATE/`. For security issues,
**do not** open a public issue — see [`SECURITY.md`](SECURITY.md).
