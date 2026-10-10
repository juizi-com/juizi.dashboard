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

## D3. Name, layout and versions

- Python package `juizi.dashboard`; Volto add-on `volto-juizi-dashboard` in
  `frontend/`.
- `juizi`, not `collective`, for the same reason as juizi.aichatbot: it's
  Juizi's short-term tool, and `collective` is left free for the PLIP's
  eventual add-on.
- Plone 6.1.5 and Volto 18, as on the test bench.

## D4. The record lives in the site root's annotations

The record is one persistent object under the annotation key
`juizi.dashboard.record`:

- an `LOBTree` of entries, keyed by time;
- `LLTreeSet` indexes by category, by event type and by who did it;
- a `BTrees.Length` count.

Annotations aren't touched by uninstalling a profile. That's what keeps the
record dormant (D1). They're also invisible to the catalog, search and the
ZMI's object listings, and they're included in the normal ZODB backup.

*Alternative:* a separate ZODB mount point, as the PLIP allows for busy
sites. Not needed at client scale, and it can be added later without
changing the record's code.

## D5. Keys are microseconds × 1000 plus a random 0–999

An entry's key is its UTC time in microseconds, times 1000, plus a random
suffix. This is the PLIP's "timestamp with a random suffix": concurrent
writes land in different BTree buckets, and a date range is a plain key range.
The largest key, around 1.8 × 10¹⁸, fits a signed 64-bit `LOBTree` key until
the year 2262. If a key is already taken, the next free one is used.

## D6. One entry per action, not one per child

Deleting or moving a folder fires Plone's event once for every item inside
it. The record keeps only the entry for the item that was actually moved or
deleted, and notes how many items were inside it. Otherwise one folder
delete could bury a day's activity under hundreds of entries.

The same goes for creating an item: Volto's create fires "added" and then
"modified" in the same request. Only "created" is kept. One request records
at most one entry per item for each kind of action.

## D7. Sharing changes record the roles as they stand afterwards

Plone's Sharing event says only that local roles changed, not what changed.
The entry stores the item's local roles after the change, leaving out Owner,
for example "Editors: Editor; jane: Reviewer". Admins can compare it with the
previous Sharing entry for the same item.

*Alternative:* snapshot the roles before each change. Rejected because that
means hooking into the Sharing view and `@sharing` before they save, which is
a patch.

## D8. Content actions skip the record's own housekeeping

- Only content (`IContentish`) is recorded.
- Edits made while the add-on itself is being installed or uninstalled are
  not recorded.
- Content created by the site's own setup before the record existed was
  never recorded, so there's nothing to skip there.

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

## D10. Every settings change and install change is recorded

Switching recording off writes "Recording switched off" before it stops.
Switching it back on writes "Recording switched on". Changes to the IP and
comment settings are recorded with their old and new values.

The add-on writes "Add-on installed", "Add-on uninstalled" and "Add-on
reinstalled" entries. Between an uninstall and a reinstall the record
shows a visible gap.

## D11. Times are stored in UTC and shown in the site's time zone

- Entries are stored in UTC.
- The dashboard shows times in the browser's local time.
- The CSV has a "When (UTC)" column and a column in the site's time zone
  (`plone.portal_timezone`), so a spreadsheet sorts correctly and still
  reads naturally.
- The date range filter uses the site's time zone, so "today" means the
  site's today.

## D12. CSV cells that look like formulas are made safe

A cell that starts with `=`, `+`, `-`, `@`, a tab or a carriage return gets a
leading `'`, so a spreadsheet doesn't run it as a formula. Titles and
profile names are typed by users, and an admin opening the file is exactly
the person such a formula would target.

## D13. A CSV download stops at 100,000 rows

- A download includes at most 100,000 rows, newest first.
- The dashboard warns before downloading when the range holds more.
- The file's last line says it was cut off.
- The server script exports everything, with no limit.

This keeps one request's memory bounded.

## D14. Who did it, and their name at the time

- Each entry stores the actor's user id and their full name at the time.
- The dashboard shows the stored name, so a deleted account's actions still
  read clearly. If an entry has no stored name, the dashboard shows the
  current name.
- Anonymous actions (self-registration, for example) show as "Anonymous".

## D15. The dashboard's address

- Site Setup → **Activity** opens `/controlpanel/activity`.
- Its settings are a generic Volto control panel,
  `/controlpanel/juizi-dashboard-settings`, linked from the dashboard.
- The REST endpoint is `GET @activity`. `?format=csv` gives the download.
- Both need the permission `juizi.dashboard: View site activity`, which
  goes to Manager and Site Administrator.

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
