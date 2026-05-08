---
name: koha-cypress
description: Run Koha Cypress end-to-end tests. Cypress runs from the HOST (not the KTD container) — KTD exposes the staff/OPAC interfaces on localhost and Cypress drives a real browser. Pass a spec path or directory under t/cypress/integration/.
---

Run Cypress E2E tests against KTD.

Arguments: $ARGUMENTS

## Critical: Cypress runs from HOST, not container

KTD already exposes the web UI on `localhost`. Cypress on the host drives a
real browser against that. Running Cypress *inside* the container also works
but is slower and harder to debug — only fall back to it if Node/npx isn't
available on the host.

## Steps

1. Verify KTD is up and the staff interface responds:
   ```bash
   curl -sf -o /dev/null http://localhost:8081/ && echo OK || echo "KTD not responding on :8081"
   ```
   If that fails, tell the user to start KTD (`ktd up`) and stop.

2. Normalise the spec path. Strip any leading absolute path so it's
   repo-relative (e.g. `t/cypress/integration/Biblio/bookingsModal_spec.ts`).

3. Run Cypress headlessly from the host (Koha repo root):
   ```bash
   npx cypress run --spec "<path>"
   ```

   For a whole directory:
   ```bash
   npx cypress run --spec "t/cypress/integration/Acquisitions/"
   ```

4. Container fallback (only if host Cypress fails):
   ```bash
   docker exec --user kohadev-koha --workdir /kohadevbox/koha -i kohadev-koha-1 \
     bash -c 'yarn cypress run --spec <path>'
   ```

## Narrowing during development

To run a single test within a spec, ask the user if they want `.only` added
to the source temporarily:

```javascript
it.only("only run this one", () => { ... });
it("not this one", () => { ... });
```

Use `it.skip(...)` to skip. Remind the user to remove `.only`/`.skip` before
committing — they will fail QA / leave dead tests.

## Common failures

- **`Cypress could not verify…has not exited cleanly`** — KTD is up but the
  app errored on load. Hit the URL in a browser to see the actual error;
  fix the underlying app issue, not the Cypress invocation.
- **`Failed to connect to localhost`** — KTD is down or on a different port.
  Check `docker ps` for the actual port mapping (default 8081 staff, 8080 OPAC).
- **Authentication tests failing locally but passing in CI** — Koha test
  database fixtures may be stale; run `ktd --restart` or rebuild KTD.

## Output

Report pass/fail counts and the failing spec(s). For failures, include the
first error stack from the Cypress output — the user usually doesn't need
the full screenshot path.
