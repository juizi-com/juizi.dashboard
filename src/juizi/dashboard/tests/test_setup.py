"""Install, uninstall, reinstall, and the server script's operations."""
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.registry.interfaces import IRegistry
from zope.component import getUtility

from juizi.dashboard import scripts
from juizi.dashboard.record import get_record
from juizi.dashboard.testing import DASHBOARD_INTEGRATION_TESTING

import io
import json
import unittest

PERMISSION = 'juizi.dashboard: View site activity'
SETTINGS = 'juizi.dashboard: Manage activity record settings'


class TestSetup(unittest.TestCase):

    layer = DASHBOARD_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.installer = self.portal.restrictedTraverse('@@installer')

    def roles(self, permission=PERMISSION):
        return sorted(r['name'] for r in self.portal.rolesOfPermission(permission)
                      if r['selected'])

    def events(self):
        record = get_record(self.portal)
        return [record.entries[k]['event'] for k in record.entries.keys()]

    def test_installed(self):
        self.assertTrue(self.installer.is_product_installed('juizi.dashboard'))
        self.assertEqual(self.roles(), ['Manager', 'Site Administrator'])
        self.assertEqual(self.roles(SETTINGS), ['Manager', 'Site Administrator'])
        self.assertTrue(api.portal.get_registry_record('juizi.dashboard.recording'))
        self.assertEqual(self.events(), ['addon.installed'])
        self.assertIn('juizi-dashboard-settings',
                      [a.getId() for a in self.portal.portal_controlpanel.listActions()])

    def test_uninstall_keeps_the_record_dormant_and_reinstall_resumes(self):
        api.content.create(container=self.portal, type='Document', id='p', title='P')
        self.installer.uninstall_product('juizi.dashboard')
        self.assertFalse(self.installer.is_product_installed('juizi.dashboard'))
        registry = getUtility(IRegistry)
        self.assertFalse([k for k in registry.records.keys() if k.startswith('juizi.dashboard')])
        self.assertEqual(self.roles(), ['Manager'])
        self.assertEqual(self.roles(SETTINGS), ['Manager'])
        self.assertNotIn('juizi-dashboard-settings',
                         [a.getId() for a in self.portal.portal_controlpanel.listActions()])
        # Dormant: kept, and nothing more is written.
        api.content.create(container=self.portal, type='Document', id='q', title='Q')
        self.assertEqual(self.events(), ['addon.installed', 'content.created',
                                         'addon.uninstalled'])
        self.installer.install_product('juizi.dashboard')
        self.assertEqual(self.events()[-1], 'addon.reinstalled')
        self.assertEqual(len(self.events()), 4)

    def test_purge_refused_while_installed(self):
        with self.assertRaises(SystemExit):
            scripts.purge(self.portal)
        self.installer.uninstall_product('juizi.dashboard')
        self.assertEqual(scripts.purge(self.portal), 2)
        self.assertIsNone(get_record(self.portal))


class TestServerScript(unittest.TestCase):

    layer = DASHBOARD_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.record = get_record(self.portal)

    def test_clear_leaves_a_permanent_note(self):
        api.content.create(container=self.portal, type='Document', id='p', title='P')
        api.user.create(email='jane@example.com', username='jane')
        removed = scripts.clear(self.record, None, None, None, '2026-10-10', by='ops@host')
        self.assertEqual(removed, 2)
        events = [e['event'] for e in self.record.entries.values()]
        self.assertEqual(events, ['addon.installed', 'record.cleared'])
        note = list(self.record.entries.values())[-1]
        self.assertEqual(note['detail']['operator'], 'ops@host')

    def test_erase(self):
        api.user.create(email='jane@example.com', username='jane',
                        properties={'fullname': 'Jane Doe'})
        page = api.content.create(container=self.portal, type='Document', id='p', title='P')
        page.manage_setLocalRoles('jane', ['Editor'])
        from plone.app.workflow.events import LocalrolesModifiedEvent
        from zope.event import notify
        notify(LocalrolesModifiedEvent(page, self.layer['request']))
        removed, anonymised = scripts.erase(self.record, 'jane', by='ops@host')
        self.assertEqual(removed, 1)  # account created
        self.assertEqual(anonymised, 1)  # the sharing entry names her
        dump = repr(list(self.record.entries.values()))
        self.assertNotIn('jane', dump)
        self.assertNotIn('Jane Doe', dump)
        self.assertEqual(list(self.record.entries.values())[-1]['event'], 'record.erased')

    def test_export_json_lines(self):
        api.content.create(container=self.portal, type='Document', id='p', title='P')
        out = io.StringIO()
        self.assertEqual(scripts.export_entries(self.record, out), 2)
        lines = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual([e['event'] for e in lines], ['addon.installed', 'content.created'])
        self.assertTrue(lines[0]['when'].endswith('Z'))

