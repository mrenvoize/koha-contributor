---
name: koha-build
description: Build Koha frontend assets (CSS, JS, OpenAPI spec) inside the KTD container. Use after editing SCSS, Vue components, or api/v1/swagger/*.yaml. After swagger changes you must also run restart_all to reload services — yarn build alone is not enough.
---

Build Koha assets inside KTD.

Arguments: $ARGUMENTS (optional — `css`, `js`, `prod`, or omit for full build)

## Decide which build to run

| Changed | Command |
|---------|---------|
| `*.scss` only | `yarn css:build` (faster) |
| `*.vue` / `*.js` only | `yarn js:build` (faster) |
| `api/v1/swagger/*.yaml` (OpenAPI) | `yarn build` then `restart_all` (mandatory — see below) |
| Mixed or unsure | `yarn build` |
| Production / packaging | `yarn build:prod` |

If the user didn't specify and edited several file types, default to
`yarn build`.

## Run

```bash
docker exec --user kohadev-koha --workdir /kohadevbox/koha -i kohadev-koha-1 \
  bash -c 'yarn build'
```

Substitute `yarn css:build`, `yarn js:build`, or `yarn build:prod` as needed.

## After Swagger / OpenAPI changes — REQUIRED

Edits to `api/v1/swagger/*.yaml` are not picked up by `yarn build` alone —
the running Mojolicious workers cache the compiled spec. Restart services
after the build:

```bash
docker exec --user kohadev-koha --workdir /kohadevbox/koha -i kohadev-koha-1 \
  bash -c 'yarn build && restart_all'
```

Without `restart_all` the API will still serve the old spec and your tests
will fail with confusing schema-mismatch errors. This is the single most
common "build looks fine but tests fail" trap.

## Watch mode (during iteration)

For tight feedback loops while editing SCSS or JS, run in the background:

```bash
docker exec --user kohadev-koha --workdir /kohadevbox/koha -i kohadev-koha-1 \
  bash -c 'yarn css:watch'   # or yarn js:watch
```

The user should run watch mode in a separate terminal — don't background it
from a skill invocation.

## Output

Report: which target ran, build duration if surfaced, and whether
`restart_all` was triggered. If the build failed, surface the first error
(usually a missing import, syntax error, or YAML parse error in swagger).
