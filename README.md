# juizi.dashboard

An activity record for Plone 6 sites, and a dashboard in Volto's Site Setup
that shows site administrators what happened: content actions and people's
account activity in one list, filtered by date range, with a CSV download.

Plain Volto: no Volto Light Theme or kitconcept dependency. See
[scope.md](scope.md) for what it records and how it's stored, and
[DECISIONS.md](DECISIONS.md) for the choices made while building it.

Alpha. Not released.

Works on Plone 6.0 with Python 3.10 or newer, and on Plone 6.1, with
Volto 18. CI tests both Plone 6.0.15 on Python 3.10 and Plone 6.1.5 on
Python 3.12, the two setups Juizi runs (p22 and p24).

## Installing

1. **Backend:** add `juizi.dashboard` to the backend's requirements. With
   mxdev, as in p22 and p24:

       [juizi.dashboard]
       url = git@github.com:juizi-com/juizi.dashboard.git
       branch = main

   It's picked up through `z3c.autoinclude`, so the instance's
   `zcml_package_includes` needn't list it.
2. **Frontend:** add `volto-juizi-dashboard` (this repo's `frontend/`) to
   the Volto project's add-ons. In a pnpm project, with mrs-developer:
   - in `mrs.developer.json`, check the repository out into `packages/`
     with `"path": "frontend"`;
   - in `pnpm-workspace.yaml`, list `'packages/*/frontend'`;
   - add `volto-juizi-dashboard` to the site add-on's `addons`, and
     `"volto-juizi-dashboard": "workspace:*"` to its `dependencies`;
   - also add `"volto-juizi-dashboard": "workspace:*"` to the frontend's
     root `package.json` `dependencies`, next to the site add-on. Volto
     looks add-ons up from `core/packages/volto`. Some pnpm versions
     (9.15) don't hoist workspace packages where it can find them, and
     Volto then stops with "Cannot find module 'volto-juizi-dashboard'".
   Then install **Juizi Dashboard** on the site in Site Setup → Add-ons.
   It's only listed on a frontend that includes `volto-juizi-dashboard`:
   the backend leaves it out of its add-ons list until it's installed on
   the site (`setuphandlers.HiddenProfiles`), because one backend can serve
   several sites and only those with the frontend part can use it, so that
   frontend adds it to the list itself (`frontend/src/offerAddon.js`). Once
   installed it's listed as usual, for upgrades and uninstalling.
3. Set the site's time zone in Site Setup → Date and Time, if it hasn't
   been set. Plone defaults to UTC. The dashboard's dates, times and date
   ranges all follow it.
4. Open Site Setup → **Activity**. Its settings (recording on or off, IP
   addresses, comment text) are under Site Setup → Activity record settings.

Who can see it: Manager and Site Administrator, through the permissions
"juizi.dashboard: View site activity" and "juizi.dashboard: Manage activity
record settings".

## Uninstalling

Uninstall in Site Setup → Add-ons. That removes the settings, the
permissions' roles and the settings tile, and stops recording. The record
itself stays in the ZODB, dormant, and nobody can read it from the website
until the add-on is reinstalled, when recording resumes. Rebuild Volto
without `volto-juizi-dashboard` to remove the Activity tile as well.

To delete the record for good, use the server script's `purge`.

## Retention

Set in the backend's environment, never on the website:

| Variable | Default | |
|---|---|---|
| `JUIZI_DASHBOARD_ACCOUNT_RETENTION_DAYS` | 365 | logins and account changes |
| `JUIZI_DASHBOARD_CONTENT_RETENTION_DAYS` | 1825 | content actions |

`0` keeps entries forever. Expired entries are removed a few at a time as
new ones are written. The record's own entries (install, settings, clears)
are kept forever. The dashboard shows both periods but can't change them.

## The server script

Clearing, erasing and purging are only possible from the server, so nobody
can use the website to cover their tracks. Every clear and erasure leaves a
permanent note in the record. Stop the instance first, or run the script on
a ZEO client.

    juizi-dashboard-record etc/zope.conf SITE info
    juizi-dashboard-record etc/zope.conf SITE export --to all.jsonl [--from 2026-01-01 --to-date 2026-03-31]
    juizi-dashboard-record etc/zope.conf SITE clear --before 2025-01-01 [--export-to archive.jsonl] --yes
    juizi-dashboard-record etc/zope.conf SITE clear --from 2026-01-01 --to-date 2026-01-31 --yes
    juizi-dashboard-record etc/zope.conf SITE erase --user USERID --yes
    juizi-dashboard-record etc/zope.conf SITE purge --yes     # only once uninstalled

`erase` handles a person's erasure request:
- it removes their own account activity (logins, their own password and
  profile changes);
- it replaces their name with "Erased user" everywhere else, including what
  admins did to their account, which stays in the trail.

It can't reach their name in site content (page titles, comments), which the
site owner handles separately.

## What isn't recorded

Content types hidden from search (Site Setup → Search) aren't recorded: those
are add-ons' internal records, such as collective.membership's. Sharing
changes are recorded for every type. A recording error never blocks what
someone is doing. It's written to the server log, and that action has no
entry.

Plone fires no event for these, so they aren't recorded either:
- failed logins;
- role changes made in classic Users and Groups or the ZMI;
- password reset requests;
- permission changes in the ZMI, including who may see this dashboard.

Global role changes made in Volto's Users screen *are* recorded.

## Possible extensions

- **Failed logins** through Products.LoginLockout, as an optional
  integration (DECISIONS.md, D2). When LoginLockout is installed, its
  failed login attempts would appear on the dashboard.
- **Site activity** (DECISIONS.md, D8). Plone already fires events for
  these, so no patches are needed:
  - control panel changes, for example "Site setting changed: Mail → SMTP
    server", with names only and never values, because some settings are
    secrets such as the mail password. One entry per save.
  - other add-ons installed or uninstalled;
  - content types and workflows changed in Site Setup.

  These would answer questions like "who switched on self-registration?" or
  "who installed that add-on?".

## Development

    uv venv --python 3.12 .venv
    uv pip install --python .venv/bin/python \
      -c https://dist.plone.org/release/6.1.5/constraints.txt \
      Products.CMFPlone plone.restapi plone.app.contenttypes zope.testrunner \
      horse-with-no-namespace -e ".[test]"
    .venv/bin/zope-testrunner --test-path src

For Plone 6.0, use `--python 3.10` and the 6.0.15 constraints. CI runs
both. Keep the code to Python 3.10 syntax: no `type` aliases, PEP 695
generics, `except*`, or f-strings that reuse their own quotes inside.

Browser scenarios run on the payments test bench: `make -C e2e dashboard`,
on the `dashboard-test` site with the frontend on :3004.
