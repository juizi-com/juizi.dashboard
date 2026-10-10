# Progress

Built from 2026-10-10, as membership was: decisions the scope leaves open
are made and logged in DECISIONS.md, and work goes on a branch with a PR,
not merged until the user has tested it. After a pause, read this file and
DECISIONS.md first, then continue from the first unfinished item.

- [x] Repo skeleton on `main`: scope, decisions, packaging, CI
- [x] Backend (`feat/activity-dashboard`): 42 tests
  - [x] The record: storage, indexes, retention pruning, safe writes (D4, D5, D16)
  - [x] Recording: account events, content actions, settings and install changes;
        global role changes from Volto's Users screen (D25)
  - [x] Query and CSV: date range in the site's time zone, presets in days,
        filters, pagination, formula-safe cells
  - [x] `@activity` endpoint, permissions, settings control panel
  - [x] Install and uninstall profiles (record kept dormant, 404 while uninstalled)
  - [x] Server script: info, export, clear (with permanent note), erase, purge
- [x] Volto dashboard (`frontend/`, same branch): Site Setup → Activity
- [x] Test bench (payments-testbed branch `feat/juizi-dashboard`, local only):
      `dashboard-test` site, frontend on :3004, 10 browser scenarios
      (`make -C e2e dashboard`), audit in `e2e/reports/dashboard-*/audit.md`.
      Server script run by hand on the bench: export, clear, purge.

## Waiting for the user

- Review DECISIONS.md (D2–D25) and the browser audit.
- Merge the PR once tested, then decide about a release and installing on
  the first client site.
