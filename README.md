# juizi.dashboard

[![PyPI](https://img.shields.io/pypi/v/juizi.dashboard?label=PyPI)](https://pypi.org/project/juizi.dashboard/)
[![npm (beta)](https://img.shields.io/npm/v/volto-juizi-dashboard/beta?label=npm%20beta)](https://www.npmjs.com/package/volto-juizi-dashboard)
[![Try It in Plone in a Box](https://img.shields.io/badge/Try%20It-Plone%20in%20a%20Box-0083be)](#try-it)

An activity record for Plone 6 sites, and a dashboard in Volto's Site Setup
that shows site administrators what happened: content actions and people's
account activity in one list, filtered by date range, with a CSV download.

Plain Volto: no Volto Light Theme or kitconcept dependency. See
[scope.md](scope.md) for what it records and how it's stored, and
[DECISIONS.md](DECISIONS.md) for the choices made while building it.

Beta: being readied for live sites. Releases are on
[PyPI](https://pypi.org/project/juizi.dashboard/) and
[npm](https://www.npmjs.com/package/volto-juizi-dashboard) (npm tag `beta`).

![The Activity dashboard in Site Setup: filtering by date range, content or people](https://github.com/user-attachments/assets/f745ddf4-d7b5-44bf-9df6-f747f09c2375)

## Try It

[![Launch Stack on AWS](https://s3.amazonaws.com/cloudformation-examples/cloudformation-launch-stack.png)](https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?templateURL=https%3A%2F%2Fplone-in-a-box-templates.s3.us-east-1.amazonaws.com%2Flatest%2Fcloudformation.yaml&stackName=juizi-dashboard-demo&param_FrontendImage=ghcr.io%2Fcollective%2Fplone-in-a-box-frontend%3A19-juizi-dashboard&param_DemoUser=demo)
[![Deploy on Linode](https://img.shields.io/badge/Deploy%20on-Linode-00a95c?logo=akamai&logoColor=white&style=for-the-badge)](https://cloud.linode.com/stackscripts/2318969)

Get your own Plone 6 site with Juizi Dashboard in about 10 minutes, set up by
[Plone in a Box](https://github.com/tkimnguyen/plone-in-a-box) on your own
cloud account. A small server costs a few cents an hour; delete it when
you're done.

1. Click a button and sign in. Fill in an admin password and a **Demo login
   password** (each at least 12 characters), and create the server.
2. Open the server's address. When the site appears, log in as `demo` with
   your demo password, and open **Activity** in the user menu.

The `demo` login is an Editor and a Site Activity Viewer: it can add and
change content and watch it appear on the dashboard, but isn't an
administrator. Share it with whoever you want to try it.

<details>
<summary>Step by step, DigitalOcean and Hetzner, and finding the password</summary>

- **Linode:** the button opens the StackScript; click **Deploy New Linode**.
  Choose **Ubuntu 26.04 LTS**, a region, a 1 GB Nanode and **No firewall**,
  set a root password, and click **Create Linode**.
- **AWS:** the button opens a Launch Stack form with Juizi Dashboard and the
  demo login filled in. Set the passwords, click **Create stack**, and open
  the **SiteURL** on its **Outputs** tab. A `t3.small` server costs more
  than the other providers' 1 GB ones.
- **DigitalOcean or Hetzner** (no button): create an Ubuntu 26.04 server
  (1 GB) and paste this into **Startup scripts** (DigitalOcean) or **Cloud
  config** (Hetzner), replacing `CHANGE-ME` with an admin password and
  `CHANGE-ME-TOO` with a demo password, each at least 12 characters:

      #!/bin/bash
      export ADMIN_PASSWORD='CHANGE-ME'
      export FRONTEND_IMAGE='ghcr.io/collective/plone-in-a-box-frontend:19-juizi-dashboard'
      export DEMO_USER='demo'
      export DEMO_PASSWORD='CHANGE-ME-TOO'
      curl -fsSL --retry 10 --retry-all-errors -o /root/plone-in-a-box.sh https://raw.githubusercontent.com/tkimnguyen/plone-in-a-box/2.14/src/StackScript && bash /root/plone-in-a-box.sh

**Left the demo password empty, or forgot it?** Setup made one up, which
isn't shown anywhere on the website. Either:
- **read it on the server:** open your provider's browser console (Linode's
  **Launch LISH Console**, DigitalOcean's **Access → Launch Droplet
  Console**, AWS's **Connect → EC2 Instance Connect**, or Hetzner's **>_
  Console**) and run `sudo cat /root/plone-credentials.txt`. The demo line
  has the password after the `/`:

      Demo login: demo / 7Gq2v8xRmT4pLwZs9KcN (Editor, Site Activity Viewer)

- **or set a new one as admin:** log in as `admin`, open Site Setup →
  **Users**, click `demo`, and change its password.

The dashboard also shows everyone's logins on the demo site, so share the
demo login only with people you trust.

</details>

## Installing

1. **Backend:** add `juizi.dashboard` to the backend's requirements
   (`pip install --pre juizi.dashboard` while it's in beta).
2. **Frontend:** add `volto-juizi-dashboard` (this repo's `frontend/`) to
   the Volto project's add-ons (`pnpm add volto-juizi-dashboard@beta`).
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

Who can see it:
- **Manager and Site Administrator** see the dashboard and can change its
  settings.
- **Site Activity Viewer**, a role this add-on adds, sees the dashboard and
  nothing else: no settings, no Site Setup, no editing. Give it in Site
  Setup → Users to someone who should see what happened without being an
  administrator, such as an auditor, or a demo login. They open the dashboard
  from **Activity** in their user menu (the toolbar's person icon), and can
  hold it alongside other roles, such as Editor.

The permissions are "juizi.dashboard: View site activity" (all three roles)
and "juizi.dashboard: Manage activity record settings" (Manager and Site
Administrator). Uninstalling removes the Site Activity Viewer role and
everyone's assignments of it.

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

Browser scenarios run on the payments test bench: `make -C e2e dashboard`,
on the `dashboard-test` site with the frontend on :3004.

Releases to PyPI and npm are published from the
[tkimnguyen/juizi.dashboard](https://github.com/tkimnguyen/juizi.dashboard) fork; see its
[RELEASING.md](https://github.com/tkimnguyen/juizi.dashboard/blob/main/RELEASING.md).
