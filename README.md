# juizi.dashboard

An activity record for Plone 6 sites, and a dashboard in Volto's Site Setup
that shows site administrators what happened: content actions and people's
account activity in one list, filtered by date range, with a CSV download.

Plain Volto: no Volto Light Theme or kitconcept dependency. See
[scope.md](scope.md) for what it records and how it's stored, and
[DECISIONS.md](DECISIONS.md) for the choices made while building it.

Alpha. Not released.

## Installing

1. **Backend:** add `juizi.dashboard` to the backend's requirements, then
   install it on the site in Site Setup → Add-ons.
2. **Frontend:** add `volto-juizi-dashboard` (this repo's `frontend/`) to
   the Volto project's add-ons.
3. Open Site Setup → **Activity**. Its settings (recording on or off, IP
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

`erase` handles a person's erasure request. It removes the account entries
about them and replaces their name with "Erased user" in everything else.

## What isn't recorded

Plone fires no event for these:
- failed logins;
- role changes made in classic Users and Groups or the ZMI;
- password reset requests.

Global role changes made in Volto's Users screen *are* recorded.

## Development

    uv venv --python 3.12 .venv
    uv pip install --python .venv/bin/python \
      -c https://dist.plone.org/release/6.1.5/constraints.txt \
      Products.CMFPlone plone.restapi plone.app.contenttypes zope.testrunner \
      horse-with-no-namespace -e ".[test]"
    .venv/bin/zope-testrunner --test-path src

Browser scenarios run on the payments test bench: `make -C e2e dashboard`,
on the `dashboard-test` site with the frontend on :3004.
