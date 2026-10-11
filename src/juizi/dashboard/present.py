"""Entries as the dashboard and the CSV show them: labels, details, dates.

Times are stored in UTC. Date ranges are read in the site's time zone, so
"today" is the site's today (D11)."""
from datetime import date
from datetime import datetime
from datetime import timedelta
from plone.registry.interfaces import IRegistry
from zope.component import queryUtility
from zoneinfo import ZoneInfo

from juizi.dashboard.record import key_for
from juizi.dashboard.record import when

import csv
import io

CATEGORY_LABELS = {'content': 'Content', 'account': 'People', 'record': 'The record'}

LABELS = {
    'login': 'Logged in',
    'logout': 'Logged out',
    'password.changed': 'Password changed',
    'account.created': 'Account created',
    'account.deleted': 'Account deleted',
    'group.created': 'Group created',
    'group.deleted': 'Group deleted',
    'group.member_added': 'Added to a group',
    'group.member_removed': 'Removed from a group',
    'profile.changed': 'Profile changed',
    'roles.changed': 'Roles changed',
    'sharing.changed': 'Sharing changed',
    'content.created': 'Created',
    'content.copied': 'Copied',
    'content.edited': 'Edited',
    'content.transition': 'State changed',
    'content.renamed': 'Renamed',
    'content.moved': 'Moved',
    'content.deleted': 'Deleted',
    'recording.on': 'Recording switched on',
    'recording.off': 'Recording switched off',
    'settings.changed': 'Setting changed',
    'addon.installed': 'Activity record started',
    'addon.reinstalled': 'Add-on reinstalled: recording resumed',
    'addon.uninstalled': 'Add-on uninstalled: recording stopped',
    'record.cleared': 'Entries cleared on the server',
    'record.erased': "A person's entries erased on the server",
}

SETTING_LABELS = {'ip_addresses': 'IP addresses', 'comment_text': 'Workflow comment text'}

PASSWORD_HOW = {
    'self': 'Changed by the account holder',
    'admin': 'Changed by an administrator',
    'reset': 'Set through a password reset link',
}

CSV_LIMIT = 100000


def _fields(names):
    return 'Fields: ' + ', '.join(names) if names else ''


def detail_text(entry):
    event, d = entry['event'], entry.get('detail') or {}
    if event == 'password.changed':
        return PASSWORD_HOW.get(d.get('how'), '')
    if event in ('group.member_added', 'group.member_removed'):
        return 'Group: ' + (d.get('group_title') or d.get('group') or '')
    if event in ('profile.changed', 'content.edited'):
        return _fields(d.get('fields'))
    if event == 'roles.changed':
        parts = []
        if d.get('added'):
            parts.append('Given: ' + ', '.join(d['added']))
        if d.get('removed'):
            parts.append('Taken away: ' + ', '.join(d['removed']))
        return '; '.join(parts)
    if event == 'sharing.changed':
        if 'given' not in d:
            # The first change the record saw on this item: roles as they are.
            return 'Roles now: ' + _sharing_now(d)
        parts = []
        if d['given']:
            parts.append('Given: ' + _roles(d['given']))
        if d['taken']:
            parts.append('Taken away: ' + _roles(d['taken']))
        if d.get('inherit_changed'):
            parts.append('Inherited roles ' + ('restored' if d.get('inherit', True)
                                               else 'blocked'))
        return '; '.join(parts) or 'No change to roles'
    if event == 'content.transition':
        text = f"{d.get('transition_title')}: {d.get('from')} → {d.get('to')}"
        if 'comment' in d:
            text += (f' — “{d["comment"]}”' if d['comment']
                     else ' — with a comment (text not recorded)')
        return text
    if event == 'content.renamed':
        return f"{d.get('from')} → {d.get('to')}"
    if event == 'content.moved':
        return 'From ' + (d.get('from') or '')
    if event == 'content.copied':
        return 'Copy of ' + (d.get('from') or '')
    if event == 'settings.changed':
        name = SETTING_LABELS.get(d.get('setting'), d.get('setting'))
        return f"{name}: {_value(d.get('old'))} → {_value(d.get('new'))}"
    if event == 'record.cleared':
        return (f"{d.get('removed', 0)} entries from {d.get('from') or 'the start'} to "
                f"{d.get('to')}, by {d.get('operator') or 'the server operator'}")
    if event == 'record.erased':
        return (f"{d.get('removed', 0)} entries removed and {d.get('anonymised', 0)} "
                f"anonymised, by {d.get('operator') or 'the server operator'}")
    return ''


def _roles(changes):
    return '; '.join(f"{r['title'] or r['id']} ({', '.join(r['roles'])})"
                     for r in changes)


def _sharing_now(d):
    text = _roles(d.get('roles', [])) or 'no roles given on this item'
    return text if d.get('inherit', True) else text + ', inherited roles blocked'


def note_text(entry):
    """Noted under the change: a folder's contents (D6), or a Sharing
    change's full list of roles afterwards (D7)."""
    d = entry.get('detail') or {}
    if entry['event'] == 'sharing.changed':
        if 'given' not in d:
            return 'Earlier roles on this item weren\'t recorded, so the change itself isn\'t shown.'
        return 'Roles now: ' + _sharing_now(d)
    n = d.get('inside')
    return f"With {n} item{'s' if n != 1 else ''} inside" if n else ''


def _value(value):
    if value is True:
        return 'on'
    if value is False:
        return 'off'
    return str(value)


def site_zone():
    registry = queryUtility(IRegistry)
    name = registry.get('plone.portal_timezone', None) if registry is not None else None
    try:
        return ZoneInfo(name) if name else ZoneInfo('UTC')
    except Exception:
        return ZoneInfo('UTC')


class RangeError(ValueError):
    pass


def date_range(start=None, end=None, today=None, zone=None, days=None):
    """(from date, to date, first key, key after the last day), both days
    inclusive, in the site's time zone. `days` is the last N days up to
    today. Default: the last 28 days."""
    zone = zone or site_zone()
    today = today or datetime.now(zone).date()
    try:
        days = int(days) if days else 28
        if not 1 <= days <= 3660:
            raise ValueError(days)
        last = date.fromisoformat(end) if end else today
        first = date.fromisoformat(start) if start else last - timedelta(days=days - 1)
    except (TypeError, ValueError):
        raise RangeError('Dates must look like 2026-10-31, and days must be 1 to 3660.')
    if first > last:
        raise RangeError('The start date is after the end date.')
    lo = key_for(datetime.combine(first, datetime.min.time(), zone))
    hi = key_for(datetime.combine(last + timedelta(days=1), datetime.min.time(), zone))
    return first, last, lo, hi


def type_title(portal_type):
    """The name editors see in the Add menu ("Page" for Document). A type
    removed since keeps its id."""
    if not portal_type:
        return ''
    from Products.CMFCore.utils import getToolByName
    from zope.component.hooks import getSite
    info = getToolByName(getSite(), 'portal_types').getTypeInfo(portal_type)
    return (info.Title() if info is not None else '') or portal_type


def row(key, entry):
    return {
        'id': str(key),
        'when': when(key).isoformat().replace('+00:00', 'Z'),
        'category': entry['category'],
        'event': entry['event'],
        'label': LABELS.get(entry['event'], entry['event']),
        'actor': entry.get('actor'),
        'actor_name': entry.get('actor_name') or '',
        'subject': entry.get('subject'),
        'subject_name': entry.get('subject_name') or '',
        'title': entry.get('title') or '',
        'path': entry.get('path') or '',
        'type': entry.get('type') or '',
        'type_title': type_title(entry.get('type')),
        'detail': detail_text(entry),
        'note': note_text(entry),
        'ip': entry.get('ip') or '',
    }


def _safe_cell(value):
    """No cell starts like a formula (D12)."""
    text = '' if value is None else str(value)
    return "'" + text if text[:1] in ('=', '+', '-', '@', '\t', '\r') else text


def to_csv(record, keys, zone=None):
    zone = zone or site_zone()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(['When (UTC)', f'When ({zone.key})', 'Event', 'Category',
                     'Who', 'Who (user id)', 'Account concerned', 'Account concerned (id)',
                     'Item', 'Path', 'Content type', 'Details', 'IP address'])
    for key in keys[:CSV_LIMIT]:
        r = row(key, record.entries[key])
        local = when(key).astimezone(zone).strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow([_safe_cell(v) for v in (
            r['when'], local, r['label'], CATEGORY_LABELS.get(r['category'], r['category']),
            r['actor_name'] or ('Anonymous' if not r['actor'] else r['actor']),
            r['actor'] or '', r['subject_name'], r['subject'] or '', r['title'], r['path'],
            r['type_title'], '; '.join(t for t in (r['detail'], r['note']) if t),
            r['ip'])])
    if len(keys) > CSV_LIMIT:
        writer.writerow([f'Cut off: this range holds {len(keys)} entries; the first '
                         f'{CSV_LIMIT}, newest first, are above. The server script '
                         'exports everything.'])
    # A byte-order mark, so Excel reads the UTF-8 (names, arrows) correctly.
    return '﻿' + out.getvalue()
