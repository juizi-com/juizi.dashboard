# Decisions

Made while building, where scope.md doesn't settle the question. Each one
says what was chosen, why, and the alternative, so the user can confirm or
overturn it.

## D1. Settled with the user before building (2026-10-10)

- **Admins only:** Site Administrator and Manager. No "own record" view for
  other users.
- **Uninstall keeps the record,** dormant. Only the server script deletes it.
- **No failed logins.** Core fires nothing for them, and this add-on doesn't
  patch core.
- **Private repo juizi-com/juizi.dashboard,** with the Volto add-on in
  `frontend/`, built on branches with PRs.
- **Plain Volto,** with no VLT or kitconcept dependencies.

## D2. No dependency on collective.auditlog, collective.fingerpointing or Products.LoginLockout

The user allowed the PLIP's add-ons as dependencies. None of them fits:

- **collective.auditlog** stores entries in SQL through SQLAlchemy <2 and is
  driven by content rules. The agreed storage is the ZODB, with no extra
  database to run.
- **collective.fingerpointing** writes log files, which can't be read or
  filtered from inside Plone. Its last release was in 2022.
- **Products.LoginLockout** is only useful for failed logins, which are out
  (D1).

What we used instead: fingerpointing's list of subscribers served as a
checklist of which core events to catch. LoginLockout can sit alongside
this add-on unchanged.

*Alternative:* auditlog as the store, with our own view on top. Rejected
because of the SQL server and an old SQLAlchemy pin.

**Review 2026-10-11: confirmed, no dependencies for now.**

**Option for later: failed logins through LoginLockout.** Make LoginLockout
an optional integration, not a dependency. When it's installed, the
dashboard would show its failed login attempts, for example as "Login
failed" entries under People. This reopens D1's "no failed logins", and
it's the realistic way to get them before the PLIP's core event exists,
without patching Plone.

## D3. Name, layout and versions

- Python package `juizi.dashboard`; Volto add-on `volto-juizi-dashboard` in
  `frontend/`.
- `juizi`, not `collective`, for the same reason as juizi.aichatbot: it's
  Juizi's short-term tool, and `collective` is left free for the PLIP's
  eventual add-on.
- Plone 6.1.5 and Volto 18, as on the test bench.

**Review 2026-10-11: confirmed** (`juizi.dashboard`, not renamed to `juizi.activity`).

## D4. The record lives in the site root's annotations

The record is one persistent object under the annotation key
`juizi.dashboard.record`:

- an `LOBTree` of entries, keyed by time;
- `LLTreeSet` indexes by category, and by person (whoever did it or whom
  it concerns);
- a `BTrees.Length` count.

Annotations aren't touched by uninstalling a profile. That's what keeps the
record dormant (D1). They're also invisible to the catalog, search and the
ZMI's object listings, and they're included in the normal ZODB backup.

*Alternative:* a separate ZODB mount point, as the PLIP allows for busy
sites. Not needed at client scale, and it can be added later without
changing the record's code.

**Review 2026-10-11: confirmed.** Raised in the review: show each item's
content type, so an admin helping an editor can see what kind of item it
was. Entries already stored the type's id. The dashboard and CSV now show
its name as editors see it ("Page", not "Document"), looked up when the
list is read. A type removed since shows its id.

## D5. Keys are microseconds × 1000 plus a random 0–999

An entry's key is its UTC time in microseconds, times 1000, plus a random
suffix. This is the PLIP's "timestamp with a random suffix": concurrent
writes land in different BTree buckets, and a date range is a plain key range.
The largest key, around 1.8 × 10¹⁸, fits a signed 64-bit `LOBTree` key until
the year 2262. If a key is already taken, the next free one is used.

**Review 2026-10-11: confirmed.**

## D6. One entry per action, not one per child

Deleting or moving a folder fires Plone's event once for every item inside
it. The record keeps only the entry for the item that was actually moved or
deleted, and notes how many items were inside it. Otherwise one folder
delete could bury a day's activity under hundreds of entries.

The same goes for creating an item: Volto's create fires "added" and then
"modified" in the same request. Only "created" is kept. One request records
at most one entry per item for each kind of action.

**Review 2026-10-11: confirmed.** Added in the review: deleting, moving,
copying or renaming a folder notes how many items it took with it, as a
separate note under the change ("With 4 items inside"). In the CSV the
note is added to the Details cell. So an admin knows there were items
inside, even though those items have no entries of their own.

## D7. Sharing changes show what was given and taken away

Plone's Sharing event says only that local roles changed, not what
changed. The record therefore remembers each item's local roles at its
last Sharing change (Owner left out), in a small lookup table by UID
(`last_sharing`). The next Sharing change on that item is compared with
them:

> Given: Eddie Editor (Editor); Taken away: Eddie Editor (Reviewer)
> *Roles now: Eddie Editor (Editor)*

- **Inheritance:** blocking or restoring inherited roles is shown too.
- **The first change the record sees on an item** can't be compared with
  anything. It shows "Roles now: …", with a note that the earlier roles
  weren't recorded.
- **Deleting** an item drops it from the lookup table.
- **Erasing a person** replaces them there too (D18).
- **Records made before this existed** get the table the first time it's
  used. No upgrade step is needed.

*Alternative 1, the original build:* store only the roles as they stand
afterwards, and leave admins to compare two entries by eye.

*Alternative 2:* snapshot the roles before each change, by hooking into
the Sharing view and `@sharing` before they save. That's a patch.

**Review 2026-10-11: changed to this middle way** (the user's choice: "the
most helpful").

## D8. Only content is recorded, and only where the add-on is installed

- Only content (`IContentish`) is recorded, not tools, registry records or
  other objects in the ZODB.
- The add-on's code runs for every site in a Zope instance once it's in
  the environment. Each handler first checks that the add-on is installed
  on the current site, and does nothing otherwise, including when no site
  is set at all, for example while another site is being created. The test
  bench found this: creating a second site crashed until the check came
  first.

**Review 2026-10-11: confirmed, content only for now.** Site activity
(control panel changes, other add-ons installed or uninstalled, types and
workflows changed) is noted in the README as a possible extension.

## D9. Settings live in plone.registry; retention lives on the server

**Registry settings (Site Setup → Activity record settings):**
- recording on or off (on when installed);
- IP addresses: full, shortened or off (default full, as in the PLIP);
- review comment text: on or off (default on).

**Server settings (environment variables):**
- `JUIZI_DASHBOARD_ACCOUNT_RETENTION_DAYS` (default 365);
- `JUIZI_DASHBOARD_CONTENT_RETENTION_DAYS` (default 1825);
- `0` means keep forever.

Retention isn't on the website for the same reason clearing isn't. The
dashboard shows both values, read-only.

**Review 2026-10-11: confirmed as is**, including full IP addresses by
default. Raised and left open: shortened might suit client sites better
(POPIA/GDPR), since most admins won't change the default.

## D10. Every settings change and install change is recorded

Switching recording off writes "Recording switched off" before it stops.
Switching it back on writes "Recording switched on". Changes to the IP and
comment settings are recorded with their old and new values.

The add-on writes "Add-on installed", "Add-on uninstalled" and "Add-on
reinstalled" entries. Between an uninstall and a reinstall the record
shows a visible gap.

**Review 2026-10-11: confirmed.** Known gap, documented: granting the
dashboard's permission to another role in the ZMI isn't recorded, because
Plone fires no event for permission changes. It needs Manager access.

## D11. Times are stored in UTC and shown in the site's time zone

- Entries are stored in UTC.
- The dashboard shows times in the site's time zone, not the browser's, so
  the list, the date filter and the CSV agree. (As first built it used the
  browser's, which disagreed with the filter whenever the two zones
  differed.)
- The CSV has a "When (UTC)" column and a column in the site's time zone
  (`plone.portal_timezone`), so a spreadsheet sorts correctly and still
  reads naturally.
- The date range filter uses the site's time zone, so "today" means the
  site's today.

**Review 2026-10-11: confirmed, with the list changed to the site's time
zone.** The README tells installers to set the site's time zone (Plone
defaults to UTC).

## D12. CSV cells that look like formulas are made safe

A cell that starts with `=`, `+`, `-`, `@`, a tab or a carriage return gets a
leading `'`, so a spreadsheet doesn't run it as a formula. Titles and
profile names are typed by users, and an admin opening the file is exactly
the person such a formula would target.

**Review 2026-10-11: confirmed.** Accepted cost: harmless titles that start
with -, + or @ show a leading apostrophe in the CSV (not on screen).

## D13. A CSV download stops at 100,000 rows

- A download includes at most 100,000 rows, newest first.
- The dashboard warns before downloading when the range holds more.
- The file's last line says it was cut off.
- The server script exports everything, with no limit.

This keeps one request's memory bounded.

**Review 2026-10-11: confirmed.**

## D14. Who did it, and their name at the time

- Each entry stores the actor's user id and their full name at the time.
- The dashboard shows the stored name, so a deleted account's actions still
  read clearly. A person with no full name has their id stored as the name.
- After a name change, older entries keep the old name. The person filter
  works by user id, so it shows all of their activity either way.
- Anonymous actions (self-registration, for example) show as "Anonymous".

**Review 2026-10-11: confirmed.**

## D15. The dashboard's address

- Site Setup → **Activity** opens `/controlpanel/activity`.
- Its settings are a generic Volto control panel,
  `/controlpanel/juizi-dashboard-settings`, linked from the dashboard.
- The REST endpoint is `GET @activity`. `?format=csv` gives the download.
- The dashboard and `@activity` need `juizi.dashboard: View site activity`.
  The settings tile needs `juizi.dashboard: Manage activity record
  settings` (D24). Both go to Manager and Site Administrator.
- Both tiles are under Add-on Configuration, like membership and donations.

**Review 2026-10-11: confirmed as is** (two tiles, Add-on Configuration).

## D16. Writes go through even when a request is read-only

A login is a GET-like action as far as plone.protect is concerned. Because
the record is a plain BTree, a logged-in request without a form token would
have its write discarded, and the login wouldn't be recorded.

After writing, the record compares the connection's registered objects
before and after its write, and marks only the new ones (its own buckets
and indexes) as safe writes for that request. Nothing else in the request
gets a pass: if the action itself writes without a token, plone.protect
still aborts the whole transaction, and the entry goes with it.

plone.protect's own `safeWrite(btree)` walks every bucket of the tree, so it
would get slower as the record grows. It isn't used.

*Alternative:* `IDisableCSRFProtection` for the whole request. Rejected,
because it would also switch the check off for whatever else that request
writes.

## D17. The record's own entries are never pruned

Entries in the "record" category (add-on installed, uninstalled or
reinstalled, recording switched on or off, settings changed, entries
cleared, a person erased) are kept forever, and clearing never removes
them. There are few of them, and they're the trail that shows whether
anyone has interfered with the record.

## D18. What erasing a person removes

`erase --user ID`:
- **Removes** account entries about the person: their logins and logouts,
  their password and profile changes, their account's creation, and their
  group memberships.
- **Keeps, anonymised as "Erased user",** anything they did to other
  accounts, to content or to the record, for example sharing changes they
  made or another account they deleted.
- **Anonymises** sharing entries that name them in their roles.
- **Writes** a permanent note with the counts, without the person's id.

*Alternative:* the PLIP's wording ("removes a person's account events").
Read literally, that would also delete what an administrator did to other
people's accounts, which is exactly the trail an audit needs to keep.

## D19. Gaps, stated on the dashboard

Core fires nothing for these, so they aren't recorded:
- failed logins;
- global role changes made in classic Users and Groups or the ZMI (those
  made in Volto's Users screen are recorded: see D25);
- password reset requests;
- permission changes made in the ZMI.

The dashboard says so under the list. A password set through a reset link
*is* recorded, as "Password changed: set through a password reset link",
because Plone fires its credentials event then.

## D20. Presets send a number of days, not dates

The dashboard sends `days=7|28|90`. The server works out the range from
today in the site's time zone, so a browser in another time zone, or one
just past midnight, still gets the site's "last 7 days". A custom range
sends dates.

## D21. A person filter is a click on a name

- Clicking a person's name, in "Who" or as the account concerned, narrows
  the list to entries they did or that concern them. A chip with × clears
  it.
- There's no person search box. Most people a site admin wants to look at
  are already in the list.
- This avoids an endpoint that lists every account name.

## D22. Test bench: a `dashboard-test` site on payments-testbed

juizi.dashboard isn't part of the payments family. But the bench is where
Juizi's add-ons are tested on plain Volto, and one more site there costs
nothing. The bench's changes are on its branch `feat/juizi-dashboard`. The
site has juizi.dashboard only. Its frontend runs on :3004, one dev server at
a time, as for the other sites.

## D23. Uninstalled means unreadable from the website

Once the add-on is uninstalled, `@activity` answers 404 to everyone,
Manager included. The record is dormant: kept in the ZODB and readable only
with the server script, or after reinstalling.

The Volto add-on's Site Setup tile stays until the frontend is rebuilt
without it, which is how Volto add-ons work:
- a site administrator who opens it sees Volto's Unauthorized page, because
  uninstalling takes their permission away;
- Manager sees "The activity record is not installed on this site".

*Alternative:* let Manager keep reading it. Rejected, because "uninstalled"
should mean the website no longer shows it.

## D24. Settings have their own permission, so site admins see the tile

The settings configlet first used "Manage portal", which Site
Administrator doesn't have in Plone 6. Site admins couldn't see the
settings in Site Setup, even though plone.restapi let them save the form,
because `@controlpanels` only asks for the Site Setup overview permission.
The test bench found this.

The configlet now uses its own permission, "juizi.dashboard: Manage
activity record settings", given to Manager and Site Administrator.
Uninstalling resets it to Manager only.

collective.membership's settings tile uses "Manage portal" too, so site
admins don't see it either. That's for the user to decide; it hasn't been
changed.

## D25. Global role changes from Volto's Users screen are recorded

The test bench showed that plone.restapi's `@users` PATCH passes `roles`
through `setMemberProperties`, which fires Plone's "properties updated"
event, before it sets the roles. Without handling, that showed up as
"Profile changed: Fields: roles".

When that event carries `roles`:
1. The recorder notes the user's directly given global roles.
2. It compares them again in a before-commit hook.
3. Only if they actually changed, it records "Roles changed" with what
   was given and what was taken away.

A change `@users` refuses (403, for example a site admin trying to give
Manager) changes nothing, so nothing is recorded. "roles" is never listed
as a profile field.

Roles that come through groups aren't part of this. Group membership
changes are recorded on their own.
