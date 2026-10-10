"""GET @activity: the record for site administrators (D15).

Read-only. Parameters: from, to (YYYY-MM-DD, the site's time zone),
category (content, account, record), person (a user or group id), page,
size, and format=csv for the download."""
from plone.restapi.services import Service

from juizi.dashboard.present import CSV_LIMIT
from juizi.dashboard.present import date_range
from juizi.dashboard.present import RangeError
from juizi.dashboard.present import row
from juizi.dashboard.present import site_zone
from juizi.dashboard.present import to_csv
from juizi.dashboard.record import CATEGORIES
from juizi.dashboard.record import get_record
from juizi.dashboard.record import retention_days
from juizi.dashboard.recorder import setting

import json

MAX_SIZE = 200


class Activity(Service):

    def render(self):
        self.check_permission()
        response = self.request.response
        try:
            result = self.handle()
        except RangeError as e:
            response.setStatus(400)
            result = {'error': {'type': 'BadRequest', 'message': str(e)}}
        if isinstance(result, tuple):
            body, filename = result
            response.setHeader('Content-Type', 'text/csv; charset=utf-8')
            response.setHeader('Content-Disposition', f'attachment; filename="{filename}"')
            return body
        response.setHeader('Content-Type', 'application/json')
        return json.dumps(result)

    def handle(self):
        form = self.request.form
        zone = site_zone()
        first, last, lo, hi = date_range(form.get('from'), form.get('to'), zone=zone)
        category = form.get('category') or None
        if category and category not in CATEGORIES:
            raise RangeError('Unknown category.')
        person = form.get('person') or None
        record = get_record(self.context)
        keys = record.select(lo, hi, category=category, person=person) if record else []

        if form.get('format') == 'csv':
            return to_csv(record, keys, zone), f'activity-{first}-to-{last}.csv'

        try:
            size = min(max(int(form.get('size', 50)), 1), MAX_SIZE)
            page = max(int(form.get('page', 1)), 1)
        except ValueError:
            raise RangeError('page and size must be numbers.')
        start = (page - 1) * size
        items = [row(k, record.entries[k]) for k in keys[start:start + size]]
        return {
            'from': first.isoformat(),
            'to': last.isoformat(),
            'timezone': zone.key,
            'category': category,
            'person': person,
            'person_name': _person_name(record, person),
            'total': len(keys),
            'page': page,
            'size': size,
            'items': items,
            'csv_limit': CSV_LIMIT,
            'recording': bool(setting('recording', False)),
            'retention': {'account_days': retention_days('account'),
                          'content_days': retention_days('content')},
            'started': _started(record),
        }


def _person_name(record, person):
    """The filtered person's name as the record has it, for the filter chip."""
    if not record or not person:
        return ''
    keys = record.by_person.get(person)
    if not keys:
        return person
    entry = record.entries[keys.maxKey()]
    if entry.get('actor') == person and entry.get('actor_name'):
        return entry['actor_name']
    return entry.get('subject_name') or person


def _started(record):
    if not record or not len(record.entries):
        return None
    from juizi.dashboard.record import when
    return when(record.entries.minKey()).isoformat().replace('+00:00', 'Z')
