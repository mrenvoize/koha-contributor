# koha-contributor

Claude Code skills for contributing to [Koha ILS](https://koha-community.org/).

Bundles ten skills:

| Skill | Triggers | What it does |
|-------|----------|--------------|
| `koha-bz` | "file a Koha bug", "submit patch to bugzilla", "git bz" | Creates a Bugzilla bug on `bugs.koha-community.org` and attaches commits non-interactively via `git bz`. Encodes the `-y` flag and required-field workflow that otherwise hangs the agent. |
| `koha-bz-fetch` | "fetch bug NNNNN", "what does bug NNNNN say" | Pulls a bug's summary, description, test plan, and recent comments from bugs.koha-community.org by bug number. |
| `koha-prove` | "run koha tests", "prove t/..." | Runs Perl tests inside the KTD container (`kohadev-koha-1`). Never runs `prove` on the host. |
| `koha-cypress` | "run cypress", "e2e tests" | Runs Cypress E2E tests from the host (KTD exposes the UI on localhost). Container fallback included. |
| `koha-qa` | "run qa", "qa script", "before submit" | Runs `koha-qa.pl` inside KTD with `-v 2 --more-tests`. Triages real failures vs known KTD limitations. |
| `koha-build` | "yarn build", "rebuild", "after editing swagger" | Builds CSS / JS / OpenAPI inside KTD. Reminds about `restart_all` after swagger YAML changes (the #1 trap). |
| `atomicupdate` | "create atomicupdate", "scaffold a DB change for bug NNNNN" | Scaffolds a Koha atomicupdate `.pl` file, makes it executable, and reminds about the wider workflow. |
| `koha-schema-apply` | "apply schema change", "regenerate dbic" | End-to-end DB workflow: runs `updatedatabase.pl`, `dbic --force`, and reminds about manual `is_boolean` / relation edits below the marker line. |
| `koha-syspref` | "add a system preference", "new syspref" | Generates the atomicupdate INSERT and the matching `.pref` YAML entry so the syspref shows up in the admin UI. |
| `koha-review` | "QA this patchset", "review my branch", "review last N commits" | Auto-detects patchset scope, fans out specialist review agents in parallel, applies a Koha-specific checklist, and synthesises Critical / Important / Suggestion findings with file:line citations. |

## Requirements

- **Claude Code** with plugin support
- **`git bz`** installed and authenticated (`git bz --help` once interactively to populate `~/.git-bz`) — for `koha-bz` and `koha-bz-fetch`
- **KTD** ([Koha Testing Docker](https://gitlab.com/koha-community/koha-testing-docker)) running, with container name `kohadev-koha-1` — for `koha-prove`, `koha-cypress`, `koha-qa`, `koha-build`, `koha-schema-apply`
- A local Koha checkout — for `atomicupdate`, `koha-syspref`, `koha-review` (run from the repo root)

### Recommended companion plugins

`koha-review` orchestrates specialist review agents in parallel. It works
without these, but is significantly more thorough when they're installed:

- **`pr-review-toolkit`** (Anthropic, on the `claude-code-plugins`
  marketplace) — provides `code-reviewer`, `silent-failure-hunter`,
  `pr-test-analyzer`, `comment-analyzer`, and `type-design-analyzer`
  agents that `koha-review` fans out to based on what's in the diff.

  ```
  /plugin marketplace add anthropics/claude-code-plugins
  /plugin install pr-review-toolkit
  ```

If `pr-review-toolkit` isn't installed, `koha-review` falls back to direct
review by the model — you lose the parallel speedup but still get the
Koha-specific checklist.

## Installation

### Via marketplace (recommended)

Inside Claude Code:

```
/plugin marketplace add mrenvoize/koha-contributor
/plugin install koha-contributor
```

The marketplace name and plugin name are both `koha-contributor`.

### Local install (for development)

Clone, then point your `~/.claude/settings.json` at the local path:

```bash
git clone <repo-url> ~/Projects/koha-contributor
```

Then in Claude Code:

```
/plugin marketplace add ~/Projects/koha-contributor
/plugin install koha-contributor
```

### Manual install (without the plugin system)

Copy the skills into your user-global skills dir:

```bash
cp -r ~/Projects/koha-contributor/skills/* ~/.claude/skills/
```

This gets the skills working but skips version tracking via the plugin manager.

## Verifying

After install, run `/help` inside Claude Code and confirm the skills
appear under "Skills" (namespaced as `koha-contributor:<skill>`). Trigger
one with a phrase like:

> Please file a Koha bug for the changes on this branch.

The `koha-bz` skill should activate.

## Skill design notes

- **Why skills, not MCP servers?** Every skill here wraps an existing CLI tool (`git bz`, `prove`, `cypress`, `koha-qa.pl`, `yarn build`, file scaffolding) or orchestrates other agents. Skills are markdown + workflow guidance with no process to run; MCP would be heavier with no capability gain.
- **Why split into many skills rather than one mega-skill?** Each has a distinct trigger surface and operates independently. Splitting keeps each skill's instructions short and targeted, and lets them compose (e.g. `koha-review` references `koha-qa` and `koha-prove`).
- **Component list in `koha-bz`** — the inline list is a hint, not authoritative. Bugzilla is case- and spelling-strict; the skill explicitly tells the model to ask the user when unsure rather than guess.
- **Soft dependency on `pr-review-toolkit`** for `koha-review` — see the Recommended companion plugins section. Hard-coding the agents into this plugin would duplicate maintenance; depending on a published plugin keeps responsibilities separate.

## Contributing

Issues and patches welcome on the bug tracker (this repo, not bugs.koha-community.org).

## License

GPL-3.0-or-later, matching Koha itself.
