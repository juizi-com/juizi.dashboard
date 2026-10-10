# Progress

Built from 2026-10-10, as membership was: decisions the scope leaves open
are made and logged in DECISIONS.md, and work goes on a branch with a PR,
not merged until the user has tested it. After a pause, read this file and
DECISIONS.md first, then continue from the first unfinished item.

- [x] Repo skeleton on `main`: scope, decisions, packaging, CI
- [ ] Backend (`feat/activity-dashboard`)
  - [ ] The record: storage, indexes, retention pruning, safe writes
  - [ ] Recording: account events, content actions, settings and install changes
  - [ ] Query and CSV: date range in the site's time zone, filters, pagination, formula-safe cells
  - [ ] `@activity` endpoint, permission, settings control panel
  - [ ] Install and uninstall profiles (record kept dormant), upgrade step scaffold
  - [ ] Server script: export, clear (with permanent note), erase a person, purge
  - [ ] Tests
- [ ] Volto dashboard (`frontend/`, same branch): Site Setup → Activity, list, filters, CSV
- [ ] Test bench: `dashboard-test` site on payments-testbed, browser scenarios, audit
