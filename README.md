# koha-contributor

Claude Code skills for contributing to [Koha ILS](https://koha-community.org/).

Bundles three skills:

| Skill | Triggers | What it does |
|-------|----------|--------------|
| `koha-bz` | "file a Koha bug", "submit patch to bugzilla", "git bz" | Creates a Bugzilla bug on `bugs.koha-community.org` and attaches commits non-interactively via `git bz`. Encodes the `-y` flag and required-field workflow that otherwise hangs the agent. |
| `koha-prove` | "run koha tests", "prove t/..." | Runs Perl tests inside the KTD container (`kohadev-koha-1`). Never runs `prove` on the host. |
| `atomicupdate` | "create atomicupdate", "scaffold a DB change for bug NNNNN" | Scaffolds a Koha atomicupdate `.pl` file with the standard skeleton, marks it executable, and reminds about the wider DBIC schema workflow. |

## Requirements

- **Claude Code** with plugin support
- **`git bz`** installed and authenticated (`git bz --help` once interactively to populate `~/.git-bz`) — for `koha-bz`
- **KTD** ([Koha Testing Docker](https://gitlab.com/koha-community/koha-testing-docker)) running, with container name `kohadev-koha-1` — for `koha-prove`
- A local Koha checkout — for `atomicupdate` (run from the repo root)

## Installation

### Via marketplace (recommended)

Inside Claude Code:

```
/plugin marketplace add <git-url-of-this-repo>
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

After install, run `/help` inside Claude Code and confirm the three skills
appear under "Skills". Trigger one with a phrase like:

> Please file a Koha bug for the changes on this branch.

The `koha-bz` skill should activate.

## Skill design notes

- **Why a skill, not an MCP server?** All three wrap existing CLI tools (`git bz`, `prove`, file scaffolding). A skill is markdown + workflow guidance, no process to run. MCP would be heavier with no capability gain.
- **Why three skills, not one?** Each has a distinct trigger surface and operates independently. Splitting keeps each skill's instructions short and targeted.
- **Component list in `koha-bz`** — the inline list is a hint, not authoritative. Bugzilla is case- and spelling-strict; the skill explicitly tells the model to ask the user when unsure rather than guess.

## Contributing

Issues and patches welcome on the bug tracker (this repo, not bugs.koha-community.org).

## License

GPL-3.0-or-later, matching Koha itself.
