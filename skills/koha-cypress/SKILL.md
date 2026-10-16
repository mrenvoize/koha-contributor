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

1. Work out the UI URLs. Koha's `cypress.config.ts` reads
   `KOHA_INTRANET_URL` (default `http://localhost:8081`) and
   `KOHA_OPAC_URL` (default `http://localhost:8080`). A KTD instance
   started with `--proxy` is not on those ports — its UI is at
   `http://<name>-intra.localhost` (staff) and `http://<name>.localhost`
   (OPAC); `ktd --list` shows running instances. For a proxied instance:
   ```bash
   export KOHA_INTRANET_URL=http://<name>-intra.localhost
   export KOHA_OPAC_URL=http://<name>.localhost
   ```

2. Verify KTD is up and the staff interface responds:
   ```bash
   STAFF_URL="${KOHA_INTRANET_URL:-http://localhost:8081}"
   curl -sf -o /dev/null "$STAFF_URL/" && echo OK || echo "KTD not responding at $STAFF_URL"
   ```
   If that fails, tell the user to start KTD (`ktd up`) and stop.

3. Normalise the spec path. Strip any leading absolute path so it's
   repo-relative (e.g. `t/cypress/integration/Biblio/bookingsModal_spec.ts`).

4. Run Cypress headlessly from the host (Koha repo root):
   ```bash
   npx cypress run --spec "<path>"
   ```

   For a whole directory:
   ```bash
   npx cypress run --spec "t/cypress/integration/Acquisitions/"
   ```

5. Container fallback (only if host Cypress fails):
   ```bash
   ktd --name "${KTD_INSTANCE:-kohadev}" --shell --run 'yarn cypress run --spec <path>'
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
- **`Failed to connect to localhost`** — KTD is down, on a different port,
  or running behind the proxy. Check `docker ps` for the port mapping
  (default 8081 staff, 8080 OPAC) or `ktd --list` for proxied instances,
  and set `KOHA_INTRANET_URL` / `KOHA_OPAC_URL` accordingly.
- **Authentication tests failing locally but passing in CI** — Koha test
  database fixtures may be stale; run `ktd --restart` or rebuild KTD.

## Output

Report pass/fail counts and the failing spec(s). For failures, include the
first error stack from the Cypress output — the user usually doesn't need
the full screenshot path.
