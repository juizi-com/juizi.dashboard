# volto-juizi-dashboard

The Volto screen for juizi.dashboard, on plain Volto (no theme add-on).

It also offers juizi.dashboard in Site Setup → Add-ons (`src/offerAddon.js`): the backend leaves it out of the list until it is installed on the site, because one backend can serve several sites and only those with this frontend add-on can use it. It wraps any add-ons reducer configured before it, so other add-ons that offer themselves the same way stay in the list. The offered entry names the add-on's uninstall profile (`juizi.dashboard:uninstall`, set in `src/index.js`), so Volto doesn't say before installing that it can't be uninstalled.

**Site Setup → Activity** (`/controlpanel/activity`) is for Manager and Site
Administrator. It shows one list of what happened on the site, newest first:

- **Columns:** type (Content, People, Record), when, who (with the IP
  address for account events, if the site records it), what, and details:
  the item or account concerned, then the change itself.
- **Filters:**
  - the last 7, 28 or 90 days, or chosen dates, in the site's time zone;
  - everything, content, people or the record's own entries;
  - one person: click their name, or type it in the Person box, which
    suggests people who have activity in the record. Use × to clear it.
- **Download CSV:** exactly what the filters select, up to 100,000 rows.
- **Pagination:**
  - 50 entries a page;
  - numbered pages in a "Pages" navigation landmark, the current page
    marked;
  - after a page change, focus moves to the top of the list.
- **Links:** items and settings open in a new tab, so the dashboard stays
  open, and they say so to screen readers.
- **Phones:** each entry becomes a card with every field labelled. Buttons
  and links are at least 24px tall.

The note under the list gives only how long entries are kept, and a link to
the settings (Site Setup → Activity record settings).

## Kept out of the screen, on purpose

- **Retention:** how long entries are kept is set on the server, with
  `JUIZI_DASHBOARD_ACCOUNT_RETENTION_DAYS` and
  `JUIZI_DASHBOARD_CONTENT_RETENTION_DAYS`, never on the website. Entries
  can only be cleared there too, with the `juizi-dashboard-record` script.
  See the main README.
- **What Plone doesn't report, so isn't recorded:**
  - failed logins;
  - role changes made in classic Users and Groups or the ZMI (changes made
    in Volto's Users screen are recorded);
  - password reset requests.

## Accessibility

Checked with axe-core (WCAG 2.2 A and AA) at desktop and phone widths in the
test bench's browser scenarios (`make -C e2e dashboard`).

The shared Juizi dashboard style colours the active tab #007bff, which is
3.97:1 on white, below AA's 4.5:1. This add-on overrides it with #0a5ea8.
The shared stylesheet itself is unchanged.
