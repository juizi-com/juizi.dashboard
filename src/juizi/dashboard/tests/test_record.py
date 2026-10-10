"""The record's storage on its own: keys, indexes, ranges, retention."""
from datetime import datetime
from datetime import timezone
from unittest import mock

from juizi.dashboard.record import ActivityRecord
from juizi.dashboard.record import DAY_US
from juizi.dashboard.record import key_for
from juizi.dashboard.record import when

import unittest


def entry(category='content', event='content.edited', actor='jane', subject=None):
    return {'category': category, 'event': event, 'actor': actor, 'subject': subject}


class TestRecord(unittest.TestCase):

    def setUp(self):
        self.record = ActivityRecord()
        self.base = key_for(datetime(2026, 10, 1, tzinfo=timezone.utc))

    def at(self, day, **kw):
        return self.record.add(entry(**kw), key=self.base + day * DAY_US * 1000)

    def test_keys_round_trip_to_time(self):
        self.assertEqual(when(self.base), datetime(2026, 10, 1, tzinfo=timezone.utc))

    def test_taken_key_moves_on(self):
        a = self.at(0)
        b = self.at(0)
        self.assertEqual(b, a + 1)
        self.assertEqual(len(self.record), 2)

    def test_range_is_newest_first_and_end_exclusive(self):
        keys = [self.at(d) for d in range(5)]
        found = self.record.select(keys[1], keys[4])
        self.assertEqual(found, [keys[3], keys[2], keys[1]])

    def test_category_and_person_filters_intersect(self):
        a = self.at(0, category='account', event='login', actor='jane', subject='jane')
        b = self.at(1, actor='bob')
        c = self.at(2, actor='jane')
        d = self.at(3, category='account', event='group.member_added', actor='bob',
                    subject='jane')
        self.assertEqual(self.record.select(person='jane'), [d, c, a])
        self.assertEqual(self.record.select(category='account', person='jane'), [d, a])
        self.assertEqual(self.record.select(category='content', person='bob'), [b])
        self.assertEqual(self.record.select(person='nobody'), [])

    def test_remove_cleans_indexes(self):
        a = self.at(0, actor='solo')
        self.record.remove(a)
        self.assertNotIn('solo', self.record.by_person)
        self.assertEqual(len(self.record), 0)

    def test_retention_prunes_a_few_old_entries_per_write(self):
        with mock.patch.dict('os.environ', {'JUIZI_DASHBOARD_ACCOUNT_RETENTION_DAYS': '10',
                                            'JUIZI_DASHBOARD_CONTENT_RETENTION_DAYS': '0'}):
            for d in range(30):
                self.at(d, category='account', event='login')
            self.at(0)  # content: kept forever
            self.at(0, category='record', event='settings.changed')  # never pruned
            self.at(100, category='account', event='login')
        account = list(self.record.by_category['account'].keys())
        # 20 old ones went with the last write (the batch), the rest earlier.
        self.assertEqual(len(account), 1)
        self.assertEqual(len(self.record.by_category['content']), 1)
        self.assertEqual(len(self.record.by_category['record']), 1)

    def test_prune_batch_is_bounded(self):
        with mock.patch.dict('os.environ', {'JUIZI_DASHBOARD_ACCOUNT_RETENTION_DAYS': '1'}):
            for d in range(50):
                self.record.add(entry(category='account', event='login'),
                                key=self.base + d * 1000)  # same day: nothing expires
            self.at(10, category='account', event='login')
        self.assertEqual(len(self.record.by_category['account']), 51 - 20)
