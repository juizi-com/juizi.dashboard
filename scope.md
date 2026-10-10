# juizi.dashboard: scope

A short-term activity dashboard for Juizi's client sites, while the full
editorial oversight dashboard (the PLIP in `~/plone-projects/plone-dashboard`)
takes its long road. It takes one piece of that PLIP: the activity record,
shown to site administrators as one list.

## What it does

- **One list of what happened on the site,** newest first: content actions
  and people's account activity together.
- **Filtered by date range:** last 7, 28 or 90 days, or a custom range.
  The default is the last 28 days. The list can also be narrowed to content or
  people, and to one person.
- **CSV download** of exactly what the filters select.
- **Site administrators only:** Site Administrator and Manager. There's no
  dashboard for other users in this version.
- **Plone 6 with plain Volto.** It doesn't depend on Volto Light Theme or any
  kitconcept package.
- **Installs and uninstalls cleanly** from Site Setup → Add-ons.

## What it records

Only events Plone core already fires. There are no patches.

**People:**
- logins and logouts (Volto and Classic UI);
- password changes;
- accounts created and deleted;
- groups created and deleted, and people added to or removed from a group;
- profile changes (field names only, never the values);
- Sharing changes.

**Content:**
- created, edited, workflow transitions (with the comment), moved or
  renamed, deleted.

**The record itself:** switched on or off, settings changed, add-on
installed or uninstalled.

**Not recorded, because core fires nothing:** failed logins, global role
changes, password reset requests. These need the PLIP's new core events.

## Storage and security (as agreed for the PLIP)

- ZODB BTrees on the site, with indexes, so queries never walk the whole
  record.
- Entries are written in the same transaction as the action. A rolled-back
  action leaves no entry.
- No password, reset token or login name as typed is ever stored. Profile
  changes store field names, not values.
- IP addresses on account events are stored full, shortened or not at all,
  as the site admin chooses.
- Retention is set by whoever runs the server, never on the website:
  1 year for account events and 5 years for content actions by default.
  Old entries are pruned a few at a time as new ones are written.
- **Clearing is only possible from the server,** with a script. Every clear
  leaves a permanent note. No web screen, the ZMI included, can clear it.
- **Uninstalling keeps the record,** dormant. Reinstalling brings it back. Only
  the server script deletes it for good. That way an admin can't uninstall
  the add-on to cover their tracks.
- Every settings change is itself recorded.

## Out of scope (in the PLIP, not here)

- Content tab with workflow groups, Access tab, Mine / Other people's.
- Dashboards for editors and reviewers, and per-item visibility rules.
- Failed logins and the other events core doesn't fire.
- Classic UI dashboard.
