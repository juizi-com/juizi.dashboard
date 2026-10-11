"""Through the REST API, as Volto uses it."""
from datetime import date
from datetime import timedelta
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import SITE_OWNER_NAME
from plone.app.testing import SITE_OWNER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.testing.zope import Browser

from juizi.dashboard.record import get_record
from juizi.dashboard.testing import DASHBOARD_FUNCTIONAL_TESTING

import csv
import io
import transaction
import unittest


class Response:

    def __init__(self, response):
        self.status_code = response.status_int
        self.headers = response.headers
        self.content = response.body
        self.text = response.text

    def json(self):
        import json
        return json.loads(self.text)


class Session:
    """Volto-style requests: JSON in and out, a Bearer token once logged in.
    webtest under plone.testing's Browser, so PATCH works and errors don't
    raise."""

    def __init__(self, app, base):
        self.app = Browser(app).testapp
        self.base = base
        self.headers = {'Accept': 'application/json'}

    def _url(self, path):
        return self.base + '/' + path.lstrip('/') if path != '/' else self.base

    def request(self, method, path, json=None, params=None):
        from urllib.parse import urlencode
        url = self._url(path) + ('?' + urlencode(params) if params else '')
        kwargs = dict(headers=self.headers, expect_errors=True,
                      extra_environ={'REMOTE_ADDR': '198.51.100.7'})
        if method == 'GET':
            return Response(self.app.get(url, **kwargs))
        call = getattr(self.app, method.lower() + '_json')
        return Response(call(url, json if json is not None else {}, **kwargs))

    def get(self, path, params=None):
        return self.request('GET', path, params=params)

    def post(self, path, json=None):
        return self.request('POST', path, json=json)

    def patch(self, path, json=None):
        return self.request('PATCH', path, json=json)


class TestActivityService(unittest.TestCase):

    layer = DASHBOARD_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.base = '/' + self.portal.getId()
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        for name, roles in (('siteadmin', ['Site Administrator']), ('editor', ['Editor'])):
            api.user.create(email=f'{name}@example.com', username=name,
                            password='Secret-pass-1', roles=roles,
                            properties={'fullname': name.title()})
        transaction.commit()

    def session(self, login=None, password='Secret-pass-1'):
        s = Session(self.layer['app'], self.base)
        if login:
            r = s.post('@login', json={'login': login, 'password': password})
            self.assertEqual(r.status_code, 200, r.text)
            s.headers.update({'Authorization': 'Bearer ' + r.json()['token']})
        return s

    def admin(self):
        return self.session(SITE_OWNER_NAME, SITE_OWNER_PASSWORD)

    def events(self, **params):
        # One login for the whole test: each login is itself an entry.
        if not hasattr(self, '_reader'):
            self._reader = self.session('siteadmin')
        r = self._reader.get('@activity', params=params)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_only_site_admins(self):
        self.assertEqual(self.session().get('@activity').status_code, 401)
        self.assertEqual(self.session('editor').get('@activity').status_code, 401)
        self.assertEqual(self.session('siteadmin').get('@activity').status_code, 200)

    def test_volto_login_and_logout_with_address(self):
        s = self.session('editor')
        r = s.post('@logout')
        self.assertEqual(r.status_code, 204, r.text)
        found = self.events(category='account', person='editor')
        events = [i['label'] for i in found['items']]
        self.assertEqual(events[:2], ['Logged out', 'Logged in'])
        self.assertEqual(found['items'][1]['actor_name'], 'Editor')
        self.assertEqual(found['items'][1]['ip'], '198.51.100.7')

    def test_failed_login_records_nothing_and_no_typed_name(self):
        r = self.session().post('@login', json={'login': 'editor-typo', 'password': 'x'})
        self.assertEqual(r.status_code, 401)
        transaction.begin()
        self.assertNotIn('editor-typo', repr(list(get_record(self.portal).entries.values())))

    def test_volto_create_is_one_entry_and_sharing(self):
        s = self.admin()
        r = s.post('/', json={'@type': 'Document', 'id': 'news', 'title': 'News'})
        self.assertEqual(r.status_code, 201, r.text)
        r = s.patch('news', json={'title': 'Latest news'})
        self.assertEqual(r.status_code, 204, r.text)
        r = s.post('news/@sharing', json={'entries': [
            {'id': 'editor', 'type': 'user', 'roles': {'Editor': True}}]})
        self.assertEqual(r.status_code, 204, r.text)
        items = [i for i in self.events()['items'] if i['event'] != 'login']
        self.assertEqual([i['label'] for i in items[:3]],
                         ['Sharing changed', 'Edited', 'Created'])
        # The first change the record sees on an item: roles as they are.
        self.assertEqual(items[0]['detail'], 'Roles now: Editor (Editor)')
        self.assertIn("Earlier roles on this item weren't recorded", items[0]['note'])
        self.assertEqual(items[1]['detail'], 'Fields: title')
        self.assertEqual(items[2]['path'], '/news')
        self.assertEqual(items[2]['type'], 'Document')
        self.assertEqual(items[2]['type_title'], 'Page')

    def test_sharing_shows_what_changed(self):
        s = self.admin()
        s.post('/', json={'@type': 'Document', 'id': 'minutes', 'title': 'Minutes'})
        s.post('minutes/@sharing', json={'entries': [
            {'id': 'editor', 'type': 'user', 'roles': {'Editor': True}}]})
        r = s.post('minutes/@sharing', json={'inherit': False, 'entries': [
            {'id': 'editor', 'type': 'user', 'roles': {'Editor': False}},
            {'id': 'siteadmin', 'type': 'user', 'roles': {'Reviewer': True}}]})
        self.assertEqual(r.status_code, 204, r.text)
        latest = [i for i in self.events(category='account')['items']
                  if i['event'] == 'sharing.changed'][0]
        self.assertEqual(latest['detail'], 'Given: Siteadmin (Reviewer); '
                         'Taken away: Editor (Editor); Inherited roles blocked')
        self.assertEqual(latest['note'],
                         'Roles now: Siteadmin (Reviewer), inherited roles blocked')

    def test_date_range_and_category(self):
        api.content.create(container=self.portal, type='Document', id='p', title='P')
        transaction.commit()
        today = date.today()
        self.assertEqual(self.events(category='content')['total'], 1)
        old = self.events(**{'from': (today - timedelta(days=60)).isoformat(),
                             'to': (today - timedelta(days=30)).isoformat()})
        self.assertEqual(old['total'], 0)
        week = self.events(days=7)
        self.assertEqual(week['from'], (today - timedelta(days=6)).isoformat())
        default = self.events()
        self.assertEqual(default['from'], (today - timedelta(days=27)).isoformat())
        self.assertEqual(default['to'], today.isoformat())

    def test_bad_input(self):
        s = self.session('siteadmin')
        self.assertEqual(s.get('@activity', params={'from': 'yesterday'}).status_code, 400)
        self.assertEqual(s.get('@activity', params={'from': '2026-10-10',
                                                    'to': '2026-10-01'}).status_code, 400)
        self.assertEqual(s.get('@activity', params={'category': 'x'}).status_code, 400)
        self.assertEqual(s.get('@activity', params={'page': 'x'}).status_code, 400)
        self.assertEqual(s.get('@activity', params={'days': '0'}).status_code, 400)

    def test_pagination(self):
        for i in range(7):
            api.content.create(container=self.portal, type='Document', id=f'p{i}', title='P')
        transaction.commit()
        page = self.events(category='content', size=5, page=2)
        self.assertEqual(page['total'], 7)
        self.assertEqual(len(page['items']), 2)

    def test_csv(self):
        api.content.create(container=self.portal, type='Document', id='f',
                           title='=HYPERLINK("http://evil.example","x")')
        transaction.commit()
        r = self.session('siteadmin').get('@activity', params={'format': 'csv',
                                                               'category': 'content'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.headers['Content-Type'].startswith('text/csv'))
        self.assertIn('attachment; filename="activity-', r.headers['Content-Disposition'])
        rows = list(csv.reader(io.StringIO(r.content.decode('utf-8-sig'))))
        self.assertEqual(rows[0][0], 'When (UTC)')
        self.assertEqual(rows[1][2], 'Created')
        self.assertEqual(rows[1][8], '\'=HYPERLINK("http://evil.example","x")')
        self.assertEqual(rows[1][10], 'Page')

    def test_csv_needs_the_permission(self):
        r = self.session('editor').get('@activity', params={'format': 'csv'})
        self.assertEqual(r.status_code, 401)

    def test_settings_control_panel(self):
        s = self.session('siteadmin')
        listed = [p['@id'].rsplit('/', 1)[-1] for p in s.get('@controlpanels').json()]
        self.assertIn('juizi-dashboard-settings', listed)  # site admins see the tile
        r = s.get('@controlpanels/juizi-dashboard-settings')
        self.assertEqual(r.status_code, 200, r.text)
        r = s.patch('@controlpanels/juizi-dashboard-settings', json={'ip_addresses': 'off'})
        self.assertEqual(r.status_code, 204, r.text)
        items = self.events(category='record')['items']
        self.assertEqual(items[0]['detail'], 'IP addresses: full → off')
        self.assertEqual(items[0]['actor'], 'siteadmin')

    def test_role_change_from_volto_users_panel(self):
        s = self.session('siteadmin')
        r = s.patch('@users/editor', json={'roles': {'Reviewer': True, 'Editor': False}})
        self.assertEqual(r.status_code, 204, r.text)
        items = self.events(category='account', person='editor')['items']
        self.assertEqual(items[0]['label'], 'Roles changed')
        self.assertEqual(items[0]['detail'], 'Given: Reviewer; Taken away: Editor')
        self.assertEqual(items[0]['actor'], 'siteadmin')
        self.assertNotIn('Profile changed', [i['label'] for i in items])

    def test_refused_role_change_records_nothing(self):
        r = self.session('siteadmin').patch('@users/editor', json={'roles': {'Manager': True}})
        self.assertEqual(r.status_code, 403, r.text)
        items = self.events(category='account', person='editor')['items']
        self.assertNotIn('Roles changed', [i['label'] for i in items])

    def test_person_suggestions(self):
        # An account with no activity in the record: created while recording
        # was off.
        api.portal.set_registry_record('juizi.dashboard.recording', False)
        api.user.create(email='quiet@example.com', username='quiet-editor')
        api.portal.set_registry_record('juizi.dashboard.recording', True)
        transaction.commit()
        self.session('editor')  # a login: Editor is now in the record
        reader = self.session('siteadmin')
        found = reader.get('@activity-people', params={'q': 'edi'})
        self.assertEqual(found.status_code, 200, found.text)
        self.assertEqual(found.json()['items'], [{'id': 'editor', 'name': 'Editor'}])
        self.assertEqual(reader.get('@activity-people', params={'q': 'e'}).json()['items'],
                         [])  # two letters at least
        self.assertEqual(self.session('editor').get(
            '@activity-people', params={'q': 'edi'}).status_code, 401)

    def test_uninstalled_record_is_not_served_even_to_manager(self):
        self.portal.restrictedTraverse('@@installer').uninstall_product('juizi.dashboard')
        transaction.commit()
        r = self.admin().get('@activity')
        self.assertEqual(r.status_code, 404)
        self.assertIn('not installed', r.text)


class TestSafeWrites(unittest.TestCase):
    """A logged-in GET whose only write is the entry keeps it (D16)."""

    layer = DASHBOARD_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        api.user.create(email='editor@example.com', username='editor',
                        password='Secret-pass-1', roles=['Editor'])
        transaction.commit()

    def logouts(self):
        transaction.begin()
        record = get_record(self.portal)
        return [e for e in record.entries.values() if e['event'] == 'logout']

    def classic_logout(self):
        browser = Browser(self.layer['app'])
        browser.handleErrors = False
        browser.addHeader('Authorization', 'Basic editor:Secret-pass-1')
        browser.open(self.portal.absolute_url() + '/logout')

    def test_classic_logout_on_get_is_kept(self):
        self.classic_logout()
        self.assertEqual(len(self.logouts()), 1)

    def test_without_marking_plone_protect_discards_it(self):
        from unittest import mock
        from juizi.dashboard import recorder
        with mock.patch.object(recorder, '_add_marked_safe',
                               lambda record, entry: record.add(entry)):
            self.classic_logout()
        self.assertEqual(self.logouts(), [])
