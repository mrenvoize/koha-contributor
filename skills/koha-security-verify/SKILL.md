---
name: koha-security-verify
description: "Prove a Koha security fix works, in a disposable KTD instance: a fail-then-pass regression test, and a browser or curl test plan with setup, reproduce before the fix, repeat after, and a control. Covers the traps that give false confirmations (Basic Auth ignored on CGI scripts, stale Plack code, timing noise in blind SQLi, a test that passes on both reverted and patched code). Use when fixing or QAing a patch for a restricted Koha security bug, XSS, SQL injection, IDOR, auth or 2FA bypass, SSRF, or when security QA says the test plan isn't sufficient. Arguments (optional): bug number."
---

Verify a Koha security fix empirically. Work only against your own KTD instance
with throwaway fixtures; never aim an exploit at a real or shared system.

Arguments: $ARGUMENTS - optional bug number.

## Handling the bug

- Security bugs are restricted. Read them with `git bz show` (`koha-bz-fetch`);
  the public REST API returns 401. Keep every detail inside restricted bugs and
  the user's own notes; never copy exploit detail into a public place.
- Before starting, re-read the bug (status and comments may have changed). If
  the user wants it, assign it to them with
  `git bz edit --non-interactive --assignee <email> NNNNN` (check who it is
  assigned to first; don't assume).
- A fix goes at most to **Needs Signoff**, only with the user's confirmation
  (`koha-bz`). Don't change status on related or omnibus bugs without being
  asked; a cross-link comment is the default (and see `koha-bz` before touching
  `--depends`).
- Prefer the narrowest fix that closes the finding; broader redesigns discussed
  on the bug get their own bug.

## 1. Fail-then-pass regression test

Write the test first (Cypress spec that drives the **real crafted request**, or
a `prove` subtest). Then show that it fails without the fix:

1. Revert only the fix (`git stash`, or check out the parent of the fix commit).
2. `restart_all` in the instance (Plack caches `.pm` **and** `.pl`; see
   `koha-workflow`).
3. Run the test: it must **fail** for the right reason.
4. Restore the fix, `restart_all`, run again: it must **pass**.

A test that passes on both reverted and patched code is worse than none. The
usual causes: Plack still running the old code, or a missing hidden form field
(e.g. `nodouble=1` on the patron edit form) that makes the whole request a
silent no-op. Confirm the live effect with a direct `curl` or a look at the
real response body, not only a green run.

XSS tests: assert with `cy.on('window:alert', stub)` using the reported
payload, and check the context (a bare JS argument is not protected by an
`html` filter; validate at the source, e.g. cast an id to an integer).

## 2. Live reproduction: Setup, Reproduce, Fix, Control

Security QA does not accept a `prove`-only test plan; give a browser or `curl`
plan in this shape and run it yourself first:

1. **Setup:** fixtures through the UI, a Perl one-liner or SQL (e.g. patrons at
   two different libraries, a permission grant, the resource under test).
2. **Reproduce (pre-fix):** check out the parent commit, `restart_all`, show the
   exploit succeeding.
3. **Apply the fix**, `restart_all`, repeat the same request: now blocked
   (403/404/validation error, as designed).
4. **Control:** the same attacking account against an in-scope resource, or a
   harmless payload of the same shape, still behaves normally. This proves the
   fix scopes rather than blanket-denies.
5. **Clean up everything**, including syspreferences you toggled
   (`IndependentBranches` and similar). Leftover settings leak into later `prove`
   runs; re-run the affected suites afterwards.

## Authentication recipes (where false results come from)

- **REST API:** `curl -u user:pass .../api/v1/...` works when `RESTBasicAuth=1`
  (set it on a fresh KTD DB).
- **Staff/OPAC CGI scripts (`/cgi-bin/koha/...pl`):** Basic Auth is **silently
  ignored** and you get the HTML login page with HTTP 200. A fast 200 is not
  evidence of anything. Build a real session: GET a page to a cookie jar and
  read the `csrf_token` hidden input, then POST
  `login_op=cud-login&koha_login_context=intranet&login_userid=...&login_password=...&csrf_token=...`
  (the fields are `login_userid`/`login_password`, not `userid`/`password`) to
  the same jar, and reuse it (`-b jar -c jar`). Confirm success by a page title
  such as `Koha staff interface` in the body, not by the status code.
- Never print credentials or tokens. If you build a `rest/login` URL by hand,
  URL-encode the password (a `&` in it truncates the request and returns a 401
  that looks like a wrong password).

## Blind and time-based injection

Never conclude "fixed" from "the request returned fast". Run a **control** of the
same shape with a harmless payload alongside the exploit attempt. Identical
timing on both is the confirmation; only the exploit being slow means it still
works. (On bug 42946 a patched request was still ~5.7 s because the unfiltered
export was itself slow, close to a 5 s `SLEEP` payload.) For SQLi also check
that values are bound, and that any identifier taken from user input (column,
alias, attribute-type code) is validated against an allow-list.

## 3. Write it up

Put the Setup, Reproduce, Fix, Control steps in the commit message test plan
(plain text, `koha-bz` formatting) and in your notes with the observed output.
Report what was verified and what was not (for example, behaviour that needs a
production-like proxy). Before attaching, run `koha-clean-series` and
`koha-qa`, then show the user the patch and wait (`koha-bz`).
