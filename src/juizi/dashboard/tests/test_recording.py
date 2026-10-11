"""What gets recorded, inside Plone."""
from plone import api
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from zope.annotation.interfaces import IAnnotations
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from zope.lifecycleevent import Attributes

from juizi.dashboard.record import get_record
from juizi.dashboard.recorder import REQUEST_KEY
from juizi.dashboard.testing import DASHBOARD_INTEGRATION_TESTING

import unittest


class RecordingBase(unittest.TestCase):

    layer = DASHBOARD_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.record = get_record(self.portal)
        self.start = len(self.record.entries) and self.record.entries.maxKey()

    def new_request(self):
        """As if the next action came in its own request."""
        IAnnotations(self.request).pop(REQUEST_KEY, None)
        IAnnotations(self.request).pop('juizi.dashboard.copies', None)

    def entries(self, event=None):
        found = [self.record.entries[k] for k in self.record.entries.keys(self.start + 1)]
        return [e for e in found if event is None or e['event'] == event]


class TestContent(RecordingBase):

    def test_create_is_one_entry(self):
        page = api.content.create(container=self.portal, type='Document', id='p', title='P')
        notify(ObjectModifiedEvent(page))
        events = [e['event'] for e in self.entries() if e['category'] == 'content']
        self.assertEqual(events, ['content.created'])
        created = self.entries('content.created')[0]
        self.assertEqual(created['path'], '/p')
        self.assertEqual(created['title'], 'P')
        self.assertEqual(created['actor'], TEST_USER_ID)
        self.assertEqual(created['ip'], '')  # content actions never store an address

    def test_edit_records_field_names(self):
        page = api.content.create(container=self.portal, type='Document', id='p', title='P')
        self.new_request()
        page.title = 'New'
        from plone.app.contenttypes.interfaces import IDocument
        notify(ObjectModifiedEvent(page, Attributes(IDocument, 'title', 'text')))
        notify(ObjectModifiedEvent(page))  # a second one in the same request
        edits = self.entries('content.edited')
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0]['detail'], {'fields': ['text', 'title']})

    def test_transition_with_comment(self):
        page = api.content.create(container=self.portal, type='Document', id='p', title='P')
        api.content.transition(obj=page, transition='publish', comment='Looks good')
        entry = self.entries('content.transition')[0]
        self.assertEqual(entry['detail']['transition'], 'publish')
        self.assertEqual(entry['detail']['comment'], 'Looks good')
        self.assertEqual(entry['detail']['to'], 'Published')
        self.assertEqual(entry['detail']['transition_title'], 'Publish')

    def test_comment_text_can_be_left_out(self):
        api.portal.set_registry_record('juizi.dashboard.comment_text', False)
        page = api.content.create(container=self.portal, type='Document', id='p', title='P')
        api.content.transition(obj=page, transition='publish', comment='Secret reason')
        entry = self.entries('content.transition')[0]
        self.assertIsNone(entry['detail']['comment'])
        self.assertNotIn('Secret reason', repr(self.record.entries.values()))

    def test_rename_move_copy(self):
        folder = api.content.create(container=self.portal, type='Folder', id='f', title='F')
        page = api.content.create(container=self.portal, type='Document', id='p', title='P')
        self.new_request()
        api.content.rename(obj=page, new_id='q')
        self.assertEqual(self.entries('content.renamed')[0]['detail'], {'from': 'p', 'to': 'q'})
        self.new_request()
        api.content.move(source=self.portal['q'], target=folder)
        moved = self.entries('content.moved')[0]
        self.assertEqual(moved['detail'], {'from': '/q'})
        self.assertEqual(moved['path'], '/f/q')
        self.new_request()
        api.content.copy(source=folder['q'], target=self.portal)
        copied = self.entries('content.copied')[0]
        self.assertEqual(copied['detail'], {'from': '/f/q'})

    def test_deleting_a_folder_is_one_entry_with_a_count(self):
        folder = api.content.create(container=self.portal, type='Folder', id='f', title='F')
        sub = api.content.create(container=folder, type='Folder', id='s', title='S')
        api.content.create(container=sub, type='Document', id='a', title='A')
        api.content.create(container=folder, type='Document', id='b', title='B')
        self.new_request()
        api.content.delete(obj=folder, check_linkintegrity=False)
        deleted = self.entries('content.deleted')
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0]['path'], '/f')
        self.assertEqual(deleted[0]['detail'], {'inside': 3})

    def test_recording_off(self):
        api.portal.set_registry_record('juizi.dashboard.recording', False)
        api.content.create(container=self.portal, type='Document', id='p', title='P')
        self.assertEqual([e['event'] for e in self.entries()], ['recording.off'])
        api.portal.set_registry_record('juizi.dashboard.recording', True)
        self.assertEqual(self.entries()[-1]['event'], 'recording.on')


class TestAccounts(RecordingBase):

    def test_new_account_is_one_entry(self):
        api.user.create(email='jane@example.com', username='jane',
                        properties={'fullname': 'Jane Doe'})
        events = [e['event'] for e in self.entries()]
        self.assertEqual(events, ['account.created'])
        self.assertEqual(self.entries()[0]['subject'], 'jane')

    def test_profile_change_keeps_field_names_only(self):
        user = api.user.create(email='jane@example.com', username='jane')
        self.new_request()
        user.setMemberProperties({'fullname': 'Jane Secretname', 'location': 'Cape Town'})
        entry = self.entries('profile.changed')[0]
        self.assertEqual(entry['detail'], {'fields': ['fullname', 'location']})
        self.assertNotIn('Cape Town', repr(entry))

    def test_password_change_never_stores_the_password(self):
        api.user.create(email='jane@example.com', username='jane', password='first-Pass-1')
        self.new_request()
        self.portal.acl_users.userSetPassword('jane', 'Very-secret-9')
        entry = self.entries('password.changed')[0]
        self.assertEqual(entry['subject'], 'jane')
        self.assertEqual(entry['detail'], {'how': 'admin'})
        self.assertNotIn('Very-secret-9', repr(list(self.record.entries.values())))

    def test_groups(self):
        api.user.create(email='jane@example.com', username='jane')
        api.group.create(groupname='editors-team', title='Editors team')
        api.group.add_user(groupname='editors-team', username='jane')
        api.group.remove_user(groupname='editors-team', username='jane')
        api.group.delete(groupname='editors-team')
        events = [e['event'] for e in self.entries()]
        self.assertEqual(events, ['account.created', 'group.created', 'group.member_added',
                                  'group.member_removed', 'group.deleted'])
        added = self.entries('group.member_added')[0]
        self.assertEqual(added['detail']['group_title'], 'Editors team')

    def test_shortened_ip(self):
        from juizi.dashboard.recorder import client_address
        api.portal.set_registry_record('juizi.dashboard.ip_addresses', 'shortened')
        self.request._client_addr = '203.0.113.77'
        self.assertEqual(client_address(self.request), '203.0.113.x')
        self.request._client_addr = '2001:db8:85a3:1:2:3:4:5'
        self.assertEqual(client_address(self.request), '2001:db8:85a3::/48')
        api.portal.set_registry_record('juizi.dashboard.ip_addresses', 'off')
        self.assertEqual(client_address(self.request), '')

    def test_settings_changes_are_recorded(self):
        api.portal.set_registry_record('juizi.dashboard.ip_addresses', 'off')
        entry = self.entries('settings.changed')[0]
        self.assertEqual(entry['detail'], {'setting': 'ip_addresses', 'old': 'full', 'new': 'off'})
        self.assertEqual(entry['category'], 'record')


class TestNotInstalled(RecordingBase):

    def test_no_site_no_entry_no_error(self):
        from zope.component.hooks import getSite
        from zope.component.hooks import setSite
        from zope.lifecycleevent import ObjectAddedEvent
        from juizi.dashboard import recorder
        page = api.content.create(container=self.portal, type='Document', id='p', title='P')
        before = len(self.record)
        site = getSite()
        setSite(None)
        try:
            self.new_request()
            recorder.added(page, ObjectAddedEvent(page))
            recorder.modified(page, ObjectModifiedEvent(page))
        finally:
            setSite(site)
        self.assertEqual(len(self.record), before)


class TestFolderContents(RecordingBase):
    """Moves, copies and renames note what a folder took with it (D6)."""

    def test_folder_notes(self):
        from juizi.dashboard.present import note_text
        folder = api.content.create(container=self.portal, type='Folder', id='f', title='F')
        target = api.content.create(container=self.portal, type='Folder', id='t', title='T')
        api.content.create(container=folder, type='Document', id='a', title='A')
        api.content.create(container=folder, type='Document', id='b', title='B')
        self.new_request()
        api.content.rename(obj=folder, new_id='g')
        self.new_request()
        api.content.move(source=self.portal['g'], target=target)
        self.new_request()
        api.content.copy(source=target['g'], target=self.portal)
        for event in ('content.renamed', 'content.moved', 'content.copied'):
            entry = self.entries(event)[0]
            self.assertEqual(entry['detail']['inside'], 2, event)
            self.assertEqual(note_text(entry), 'With 2 items inside')
        self.new_request()
        page = api.content.create(container=self.portal, type='Document', id='p', title='P')
        self.new_request()
        api.content.rename(obj=page, new_id='q')
        self.assertNotIn('inside', self.entries('content.renamed')[-1]['detail'])


class TestFailSafe(RecordingBase):
    """A recording error never blocks the action (D27)."""

    def test_error_is_logged_and_the_action_goes_through(self):
        from unittest import mock
        from juizi.dashboard import recorder
        with mock.patch.object(recorder, 'write', side_effect=RuntimeError('boom')), \
                self.assertLogs('juizi.dashboard', level='ERROR') as logs:
            page = api.content.create(container=self.portal, type='Document', id='p',
                                      title='P')
            api.content.transition(obj=page, transition='publish')
        self.assertEqual(api.content.get_state(page), 'published')
        self.assertIn('could not record added', logs.output[0])

    def test_conflicts_still_propagate(self):
        from unittest import mock
        from ZODB.POSException import ConflictError
        from juizi.dashboard import recorder
        with mock.patch.object(recorder, 'write', side_effect=ConflictError()):
            with self.assertRaises(ConflictError):
                api.content.create(container=self.portal, type='Document', id='p', title='P')


class TestHiddenTypes(RecordingBase):
    """Types hidden from search aren't recorded (D26)."""

    def test_hidden_type_not_recorded(self):
        hidden = tuple(api.portal.get_registry_record('plone.types_not_searched'))
        api.portal.set_registry_record('plone.types_not_searched', hidden + ('News Item',))
        news = api.content.create(container=self.portal, type='News Item', id='n', title='N')
        self.new_request()
        api.content.transition(obj=news, transition='publish')
        api.content.delete(obj=news)
        api.content.create(container=self.portal, type='Document', id='p', title='P')
        titles = [e['title'] for e in self.entries() if e['category'] == 'content']
        self.assertEqual(titles, ['P'])
