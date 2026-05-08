# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Claude Code **plugin** that ships ten markdown-only skills for contributing to [Koha ILS](https://koha-community.org/). There is no application code, no build, no test suite, and no lint config — every file under `skills/<name>/SKILL.md` is shipped verbatim to end users via the plugin marketplace.

Plugin manifest: `.claude-plugin/plugin.json` (single source of truth for `version`). Marketplace entry: `.claude-plugin/marketplace.json` (must be kept in sync with `plugin.json` — same `version`, `description`, `keywords`).

## How the skills compose

The skills are deliberately split rather than bundled into one mega-skill, and several call into each other. When editing one, check whether peers reference it:

- `koha-review` references `koha-qa` and `koha-prove` in its workflow, and **soft-depends** on the `pr-review-toolkit` plugin (Anthropic) for the specialist review agents (`code-reviewer`, `silent-failure-hunter`, `pr-test-analyzer`, `comment-analyzer`, `type-design-analyzer`). If `pr-review-toolkit` isn't installed, `koha-review` falls back to direct review — keep that fallback path working when editing.
- `koha-schema-apply` is the follow-up step after `atomicupdate` has scaffolded a `.pl` file and the SQL has been filled in.
- `koha-syspref` writes both an atomicupdate `INSERT` and the matching `admin/preferences/*.pref` YAML — both edits are required for the syspref to appear in the staff UI.
- `koha-build` reminds about `restart_all` after swagger YAML changes — `yarn build` alone is not enough. Don't drop that reminder.

## Container vs host commands (the central design constraint)

Almost every Koha CLI tool runs **inside the KTD container** (`kohadev-koha-1`), but Cypress runs on the **host** because KTD exposes the staff/OPAC UI on localhost. Encoding this split correctly is the main reason these skills exist — the model otherwise tends to run `prove` on the host or Cypress in the container.

| Runs in KTD container | Runs on host |
|-----------------------|--------------|
| `prove` (koha-prove) | `cypress` (koha-cypress, with container fallback) |
| `koha-qa.pl` (koha-qa) | `git bz` (koha-bz, koha-bz-fetch) |
| `yarn build` (koha-build) | file scaffolding (atomicupdate, koha-syspref) |
| `updatedatabase.pl`, `dbic --force` (koha-schema-apply) | |

## Vendored handbook (`references/koha-handbook/`)

The [koha-handbook](https://github.com/thekesolutions/koha-handbook) (design patterns, naming conventions, REST API architecture, testing framework, etc.) is vendored into this repo as a `git subtree` so it ships with the plugin and is available offline. **Do not edit files under `references/koha-handbook/` directly** — they are upstream content. Fix issues upstream, then re-sync.

Sync mechanism: `.github/workflows/sync-handbook.yml` runs weekly (Monday 06:00 UTC) and on `workflow_dispatch`, doing `git subtree pull --squash` from upstream `main` and opening a PR if anything changed. Manual sync from a local checkout:

```bash
git subtree pull --prefix=references/koha-handbook \
  https://github.com/thekesolutions/koha-handbook.git main --squash
```

When citing handbook content from a skill, link to the vendored path (e.g. `references/koha-handbook/koha_design_patterns.md`) — that's the copy the user has locally; URLs would require network.

## SKILL.md conventions

Every skill is a single markdown file with YAML frontmatter. Required fields: `name` (matching the directory) and `description`. The `description` is what the agent matches against when deciding whether to invoke the skill — write it as a behavioural specification: include trigger phrases ("Use when the user says X"), expected arguments, and what the skill actually does. Examples to model new skills on:

- `skills/koha-bz/SKILL.md` — argument-driven, encodes a non-interactive CLI invocation that otherwise hangs.
- `skills/koha-review/SKILL.md` — orchestrator, fans out to specialist agents based on file types in the diff.

Keep skill bodies short and prescriptive. They are loaded into the user's context every time the skill triggers, so verbosity is a real cost.

## Editing rules of thumb

- **Bumping version**: edit `plugin.json` and `marketplace.json` together, then commit.
- **Adding a skill**: create `skills/<name>/SKILL.md` with frontmatter, then add a row to the table in `README.md` (the table is the human-facing skill index — if it falls out of sync the plugin looks broken).
- **`koha-bz` component list** is intentionally a hint, not authoritative — Bugzilla is case- and spelling-strict, so the skill tells the model to ask the user when unsure rather than guess. Don't "fix" this by making the list authoritative.
- The `koha-bz` `-y` flag and required-field flags are the most common failure mode (interactive prompts hang the agent). Don't remove them.

## Testing changes locally

There is no automated test harness. To dogfood a change, install the plugin locally:

```bash
cp -r ~/Projects/koha-contributor/skills/* ~/.claude/skills/
```

Or via the plugin marketplace (`/plugin marketplace add ...`, `/plugin install koha-contributor`) once changes are pushed.
