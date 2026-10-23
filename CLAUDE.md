# Cryptia — Agent Instructions

## Project Guidelines

**You must always read `.agents/rules/project-guidelines.md` at the start of every task.**

This file contains the canonical reference for:
- Project architecture, structure, and file locations.
- Tooling conventions (`uv`, Podman, `act`, Nginx).
- Supported cryptocurrencies and ML pipeline details.
- Branching, CI/CD, and deployment strategy.
- Coding standards and secret hygiene rules.

## Update Requirement

**You must keep `.agents/rules/project-guidelines.md` up to date.**

After completing any task that introduces changes to:
- Project structure (new files, renamed modules, removed directories)
- Dependencies (`pyproject.toml` / `uv.lock`)
- Infrastructure (Podman services, Nginx configuration, Quadlet units)
- API endpoints or application behavior
- CI/CD workflow or branching strategy
- Coding conventions or ML pipeline

...you **must update** `.agents/rules/project-guidelines.md` to reflect those changes before finishing.

Do not leave the guidelines file stale or out of sync with the actual codebase.
