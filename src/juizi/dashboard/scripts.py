"""The record's server-side tools. Nothing on the website can do these.

    juizi-dashboard-record ZOPE_CONF SITE COMMAND [options]

    info                             counts, oldest and newest entry, retention
    export --to FILE [--from D --to-date D]
                                     every entry in the range as JSON Lines
    clear  (--before D | --from D --to-date D) [--export-to FILE] --yes
                                     remove content and account entries in
                                     the range; leaves a permanent note
    erase  --user ID --yes           remove a person's account entries and
                                     anonymise them elsewhere; leaves a note
    purge  --yes                     delete the whole record, only once the
                                     add-on is uninstalled

Stop the instance first, or run this against a ZEO client: the script opens
the database itself. Dates are YYYY-MM-DD in the site's time zone and both
days are included.
"""
from datetime import date
from datetime import timedelta

from juizi.dashboard.present import date_range
from juizi.dashboard.present import site_zone
from juizi.dashboard.record import ACCOUNT
from juizi.dashboard.record import ANNOTATION_KEY
from juizi.dashboard.record import CONTENT
from juizi.dashboard.record import get_record
from juizi.dashboard.record import RECORD
from juizi.dashboard.record import when

import argparse
import getpass
import json
import socket
import sys

ERASED_ID = 'erased-user'
ERASED_NAME = 'Erased user'


def operator():
    try:
        return f'{getpass.getuser()}@{socket.gethostname()}'
    except Exception:
        return 'the server operator'


def _note(record, event, detail):
    """A permanent entry: category "record", which clearing never removes."""
    record.add({'category': RECORD, 'event': event, 'actor': None, 'actor_name': '',
                'subject': None, 'subject_name': '', 'detail': detail, 'ip': ''})


def export_entries(record, out, lo=None, hi=None):
    count = 0
    for key in reversed(record.select(lo, hi)):
        entry = dict(record.entries[key])
        entry['key'] = key
        entry['when'] = when(key).isoformat().replace('+00:00', 'Z')
        out.write(json.dumps(entry, sort_keys=True, default=str) + '\n')
        count += 1
    return count


def clear(record, lo, hi, first, last, by=None):
    """Remove content and account entries in [lo, hi). Returns the count."""
    removed = 0
    for category in (CONTENT, ACCOUNT):
        for key in record.select(lo, hi, category=category):
            record.remove(key)
            removed += 1
    _note(record, 'record.cleared', {'from': first, 'to': last, 'removed': removed,
                                     'operator': by or operator()})
    return removed


def erase(record, person, by=None):
    """A person's erasure request (D18). Their own account activity goes:
    logins, logouts, their own password and profile changes, anonymous steps
    such as a reset link. Everything else stays with their name replaced:
    what they did, and what others did to their account. Returns
    (removed, anonymised)."""
    removed = anonymised = 0
    for key in record.select(person=person):
        entry = record.entries[key]
        # Their own account activity goes; what someone else did to their
        # account stays, anonymised, so admins' actions keep their trail.
        if (entry['category'] == ACCOUNT and entry.get('subject') == person
                and entry.get('actor') in (person, None)):
            record.remove(key)
            removed += 1
            continue
        changed = dict(entry)
        for field, name in (('actor', 'actor_name'), ('subject', 'subject_name')):
            if changed.get(field) == person:
                changed[field], changed[name] = ERASED_ID, ERASED_NAME
        record.replace(key, changed)
        anonymised += 1
    # Sharing entries name people in their detail, not as actor or subject,
    # and the record remembers each item's last roles (D7).
    def scrub(people):
        return [dict(r, id=ERASED_ID, title=ERASED_NAME) if r.get('id') == person else r
                for r in people]

    for key in record.select(category=ACCOUNT):
        entry = record.entries[key]
        detail = entry.get('detail') or {}
        lists = {f: detail[f] for f in ('roles', 'given', 'taken') if detail.get(f)}
        if any(r.get('id') == person for people in lists.values() for r in people):
            record.replace(key, dict(entry, detail=dict(
                detail, **{f: scrub(people) for f, people in lists.items()})))
            anonymised += 1
    record.person_names().pop(person, None)
    names = record.person_names()
    if ERASED_ID in record.by_person:
        names[ERASED_ID] = ERASED_NAME
    memory = record.sharing_memory()
    for uid, last in list(memory.items()):
        if person in last['roles']:
            roles = dict(last['roles'])
            roles[ERASED_ID] = roles.pop(person)
            memory[uid] = dict(last, roles=roles)
    _note(record, 'record.erased', {'removed': removed, 'anonymised': anonymised,
                                    'operator': by or operator()})
    return removed, anonymised


def purge(site):
    """Delete the record. Refused while the add-on is installed."""
    from zope.annotation.interfaces import IAnnotations
    installer = site.restrictedTraverse('@@installer', None)
    if installer is not None and installer.is_product_installed('juizi.dashboard'):
        raise SystemExit('Uninstall juizi.dashboard from the site first. '
                         'While it is installed, the record can only be cleared.')
    annotations = IAnnotations(site)
    record = annotations.get(ANNOTATION_KEY)
    count = len(record) if record is not None else 0
    if record is not None:
        del annotations[ANNOTATION_KEY]
    return count


def _parser():
    parser = argparse.ArgumentParser(prog='juizi-dashboard-record',
                                     description=__doc__.split('\n')[0])
    parser.add_argument('zope_conf')
    parser.add_argument('site')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('info')
    exp = sub.add_parser('export')
    exp.add_argument('--to', dest='target', required=True)
    exp.add_argument('--from', dest='start')
    exp.add_argument('--to-date', dest='end')
    clr = sub.add_parser('clear')
    clr.add_argument('--before')
    clr.add_argument('--from', dest='start')
    clr.add_argument('--to-date', dest='end')
    clr.add_argument('--export-to')
    clr.add_argument('--yes', action='store_true')
    era = sub.add_parser('erase')
    era.add_argument('--user', required=True)
    era.add_argument('--yes', action='store_true')
    prg = sub.add_parser('purge')
    prg.add_argument('--yes', action='store_true')
    return parser


def _open_site(zope_conf, site_id):
    import Zope2
    from AccessControl.SecurityManagement import newSecurityManager
    from AccessControl.users import system
    from Testing.makerequest import makerequest
    from Zope2.Startup.run import make_wsgi_app
    from zope.component.hooks import setSite
    from zope.globalrequest import setRequest

    make_wsgi_app({}, zope_conf)
    app = makerequest(Zope2.app())
    app.REQUEST['PARENTS'] = [app]
    setRequest(app.REQUEST)
    newSecurityManager(None, system)
    site = app.unrestrictedTraverse(site_id)
    setSite(site)
    return site


def main(argv=None):
    import transaction

    args = _parser().parse_args(argv)
    site = _open_site(args.zope_conf, args.site)
    record = get_record(site)
    if args.command == 'purge':
        if not args.yes:
            raise SystemExit('Deleting the whole record cannot be undone. Add --yes.')
        count = purge(site)
        transaction.get().note('juizi.dashboard: activity record purged')
        transaction.commit()
        print(f'Deleted the activity record ({count} entries).')
        return
    if record is None:
        raise SystemExit(f'No activity record on {args.site}.')

    if args.command == 'info':
        print(f'Entries: {len(record)}')
        for category in (CONTENT, ACCOUNT, RECORD):
            print(f'  {category}: {len(record.by_category.get(category) or ())}')
        if len(record.entries):
            print(f'Oldest: {when(record.entries.minKey()).isoformat()}')
            print(f'Newest: {when(record.entries.maxKey()).isoformat()}')
        from juizi.dashboard.record import retention_days
        for category in (ACCOUNT, CONTENT):
            days = retention_days(category)
            print(f'Retention, {category}: {days or "forever"}{" days" if days else ""}')
        return

    zone = site_zone()
    if args.command == 'export':
        lo = hi = None
        if args.start or args.end:
            _, _, lo, hi = date_range(args.start or '1970-01-01',
                                      args.end or date.today().isoformat(), zone=zone)
        with open(args.target, 'w', encoding='utf-8') as out:
            print(f'Exported {export_entries(record, out, lo, hi)} entries to {args.target}.')
        return

    if not args.yes:
        raise SystemExit('This removes entries for good. Add --yes.')

    if args.command == 'clear':
        if args.before:
            first, end = '1970-01-01', (date.fromisoformat(args.before)
                                        - timedelta(days=1)).isoformat()
        elif args.start and args.end:
            first, end = args.start, args.end
        else:
            raise SystemExit('Give --before DATE, or both --from and --to-date.')
        first_day, last_day, lo, hi = date_range(first, end, zone=zone)
        if args.export_to:
            with open(args.export_to, 'w', encoding='utf-8') as out:
                print(f'Exported {export_entries(record, out, lo, hi)} entries to '
                      f'{args.export_to}.')
        removed = clear(record, lo, hi, None if args.before else first_day.isoformat(),
                        last_day.isoformat())
        transaction.get().note(f'juizi.dashboard: cleared {removed} entries')
        transaction.commit()
        print(f'Removed {removed} entries. A note that this happened stays in the record.')
        return

    if args.command == 'erase':
        removed, anonymised = erase(record, args.user)
        transaction.get().note('juizi.dashboard: erased a person')
        transaction.commit()
        print(f'Removed {removed} entries and anonymised {anonymised}.')


if __name__ == '__main__':
    main(sys.argv[1:])
