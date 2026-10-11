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

## Decisions review (2026-10-11): done

All decisions (D2–D25) were reviewed with the user. Changes made during the
review:
- **D4:** each item's content type is shown, as the Add-menu name.
- **D6:** folder moves, copies and renames note the items inside.
- **D7:** Sharing changes show what was given and taken away.
- **D11:** the list shows times in the site's time zone.
- **D18:** erasure keeps admins' actions on the person's account,
  anonymised.
- **D21:** a Person box suggests people from the record.
- **D24:** collective.membership stays Manager-only (membership#25).

Also done after the first build:
- the layout (Type, When, Who with IP, What, Details);
- the 800px width;
- numbered pagination;
- links that open in a new tab;
- phone cards;
- WCAG 2.2 AA checks with axe.

Possible extensions are in the README: failed logins through LoginLockout,
and site activity.

## Waiting for the user

- Test PR #1 on the bench (http://localhost:3004/controlpanel/activity),
  then merge.
- Decide about a release and the first client install.
- The shared dashboard style's active-tab contrast (#007bff, 3.97:1) and
  numbered pagination in the other dashboards were raised, not changed.
