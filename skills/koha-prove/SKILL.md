---
name: koha-prove
description: Run Koha Perl tests inside the KTD container. Pass a test file or directory path (relative to the Koha repo root, or absolute). Handles both t/ and t/db_dependent/ automatically.
---

Run the specified Koha test(s) in KTD.

Arguments: $ARGUMENTS

Steps:
1. Normalize the path: strip any leading absolute path so the result is a
   repo-relative path like `t/Koha/Foo.t` or `t/db_dependent/Circulation/`.
   Common prefixes to strip: any path ending in `/koha/`.
2. Verify the container is running:
   ```
   docker ps --filter name=kohadev-koha-1 --format '{{.Names}}'
   ```
   If empty, report: "KTD container (kohadev-koha-1) is not running. Start it with: ktd up" and stop.
3. Run the test:
   ```
   docker exec --user kohadev-koha --workdir /kohadevbox/koha -i kohadev-koha-1 bash -c 'prove -v PATH'
   ```
   where PATH is the normalized path.
4. Report the full output including pass/fail summary and any test failures.

Notes:
- Never run `prove` on the host — it lacks the Koha Perl environment and will fail.
- The container name `kohadev-koha-1` is the KTD default. If `docker ps` shows a different name, use that instead.
- `prove -r t/db_dependent/` runs the full DB-dependent suite (slow); for quick iteration, target a single file or subdirectory.
