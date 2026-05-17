# Contributing to media-os

Thanks for your interest. This repo IS a Claude Code plugin + marketplace — the deliverable is the directory tree. There's no build step, no service, no API.

Before doing anything, read [CLAUDE.md](CLAUDE.md) — it documents directory invariants, skill structure rules, and script standards. The CI workflow at `.github/workflows/validate.yml` enforces a subset of those rules on every push and PR.

## Quickest contributions

| You want to… | Open this issue |
|---|---|
| Report a broken skill / hook / CLI | [Bug report](https://github.com/damionrashford/media-os/issues/new?template=bug.yml) |
| Propose a new tool-and-technique skill | [Skill request](https://github.com/damionrashford/media-os/issues/new?template=skill_request.yml) |
| Propose a new end-to-end workflow skill | [Workflow request](https://github.com/damionrashford/media-os/issues/new?template=workflow_request.yml) |
| Show what you built / ask a question | [Discussions](https://github.com/damionrashford/media-os/discussions) |

## Adding a skill

1. Pick a layer (1–9 — see [README](README.md#whats-in-it)).
2. Create `skills/<kebab-name>/SKILL.md` with frontmatter (`name:` must match folder), then body ≤ 500 lines.
3. Put any helper scripts in `skills/<kebab-name>/scripts/` — stdlib-only Python 3, PEP 723 inline-dep header, `--dry-run` + `--verbose`, no `input()`.
4. Put deep reference material in `skills/<kebab-name>/references/<topic>.md` and reference it from SKILL.md.
5. Skill folder must be sealed — no cross-skill imports. Copying the folder to any other plugin must yield a working skill.
6. For AI skills (Layer 9), every model must be Apache-2 / MIT / BSD / GPL. NC / research-only / commercial-restricted models go in `references/LICENSES.md` as documented-and-dropped.
7. Run the validator: `gh workflow run validate.yml` (or push and watch CI).

## Adding a workflow skill

Workflow skills (`skills/workflow-*`) are orchestrators with no scripts. They document a step-by-step chain across existing skills. Use one of the existing 13 (`skills/workflow-broadcast-delivery/SKILL.md`) as a template.

## Renaming or removing a skill

Run the `readme-curator` dev agent (`.claude/agents/readme-curator.md`) — it keeps README counts, the layer breakdown, and the install section in sync. Then run `repo-maintainer` to scrub artifacts and verify GitHub topics + description.

## Releases

Use `.claude/agents/release-manager.md` — it bumps the version in `plugin.json` + `marketplace.json` in lockstep, updates CHANGELOG, tags, and creates the GitHub release.

## License

By contributing you agree your contribution is MIT-licensed under [LICENSE](LICENSE).
