"""The activity record: entries in a BTree keyed by time, with indexes.

One persistent object per site, in the site root's annotations (D4), so
uninstalling the add-on leaves it in place, dormant. Nothing on the
website can remove entries: clearing, erasing and purging are in
scripts.py, for whoever runs the server.
"""
from BTrees.LLBTree import intersection
from BTrees.LLBTree import LLTreeSet
from BTrees.LOBTree import LOBTree
from BTrees.Length import Length
from BTrees.OOBTree import OOBTree
from datetime import datetime
from datetime import timezone
from persistent import Persistent
from zope.annotation.interfaces import IAnnotations
from zope.component.hooks import getSite

import os
import random
import time

ANNOTATION_KEY = 'juizi.dashboard.record'

CONTENT = 'content'
ACCOUNT = 'account'
# The record itself: install, settings, clears. Never pruned (D17).
RECORD = 'record'
CATEGORIES = (CONTENT, ACCOUNT, RECORD)

# Retention, from the server's environment only (D9). 0 keeps forever.
RETENTION_ENV = {
    ACCOUNT: ('JUIZI_DASHBOARD_ACCOUNT_RETENTION_DAYS', 365),
    CONTENT: ('JUIZI_DASHBOARD_CONTENT_RETENTION_DAYS', 1825),
}
# Expired entries removed per write: small, so no request does a big delete.
PRUNE_BATCH = 20

DAY_US = 86400 * 1000000


def retention_days(category):
    name, default = RETENTION_ENV[category]
    try:
        days = int(os.environ.get(name, default))
    except ValueError:
        days = default
    return max(days, 0)


def key_for(dt):
    """The lowest key at a moment: UTC microseconds × 1000 (D5)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000000) * 1000


def when(key):
    """The UTC datetime of an entry's key."""
    return datetime.fromtimestamp(key // 1000 / 1000000, tz=timezone.utc)


def now_key():
    return (time.time_ns() // 1000) * 1000 + random.randrange(1000)


class ActivityRecord(Persistent):

    def __init__(self):
        self.entries = LOBTree()
        self.by_category = OOBTree()
        # Who did it or whom it concerns: one index for both, so a person's
        # filter shows what they did and what was done to their account.
        self.by_person = OOBTree()
        self.count = Length()
        self.last_sharing = OOBTree()
        self.names = OOBTree()

    def person_names(self):
        """Each person's latest name in the record, by id: for the Person
        box (D21). Records made before this existed build it on first use."""
        names = getattr(self, 'names', None)
        if names is None:
            names = self.names = OOBTree()
            for person, keys in self.by_person.items():
                names[person] = _name_in(self.entries[keys.maxKey()], person)
        return names

    def sharing_memory(self):
        """Each item's local roles at its last Sharing change (D7), by UID.
        Records made before this existed get it on first use."""
        memory = getattr(self, 'last_sharing', None)
        if memory is None:
            memory = self.last_sharing = OOBTree()
        return memory

    # Writing

    def add(self, entry, key=None):
        key = now_key() if key is None else key
        while key in self.entries:
            key += 1
        entry = dict(entry)
        self.entries[key] = entry
        self._index(key, entry)
        names = self.person_names()
        for person in {entry.get('actor'), entry.get('subject')} - {None, ''}:
            name = _name_in(entry, person)
            if names.get(person) != name:
                names[person] = name
        self.count.change(1)
        self.prune(key)
        return key

    def _sets(self, entry):
        yield self.by_category, entry['category']
        for person in {entry.get('actor'), entry.get('subject')} - {None, ''}:
            yield self.by_person, person

    def _index(self, key, entry):
        for index, value in self._sets(entry):
            keys = index.get(value)
            if keys is None:
                keys = index[value] = LLTreeSet()
            keys.insert(key)

    def _unindex(self, key, entry):
        for index, value in self._sets(entry):
            keys = index.get(value)
            if keys is not None and key in keys:
                keys.remove(key)
                if not keys:
                    del index[value]

    def remove(self, key):
        entry = self.entries.get(key)
        if entry is None:
            return None
        self._unindex(key, entry)
        del self.entries[key]
        names = self.person_names()
        for person in {entry.get('actor'), entry.get('subject')} - {None, ''}:
            if person not in self.by_person and person in names:
                del names[person]  # no entries left: no longer suggested
        self.count.change(-1)
        return entry

    def replace(self, key, entry):
        """Rewrite one entry (erasure only: scripts.py)."""
        self._unindex(key, self.entries[key])
        self.entries[key] = dict(entry)
        self._index(key, self.entries[key])

    def prune(self, now):
        """Remove a few entries past their category's retention."""
        removed = 0
        for category in (ACCOUNT, CONTENT):
            days = retention_days(category)
            if not days:
                continue
            cutoff = now - days * DAY_US * 1000
            while removed < PRUNE_BATCH:
                keys = self.by_category.get(category)
                if not keys or keys.minKey() >= cutoff:
                    break
                self.remove(keys.minKey())
                removed += 1
        return removed

    # Reading

    def select(self, start=None, end=None, category=None, person=None):
        """Keys between start (inclusive) and end (exclusive), newest first."""
        lo = start
        hi = end - 1 if end is not None else None
        sets = []
        if category:
            sets.append(self.by_category.get(category) or LLTreeSet())
        if person:
            sets.append(self.by_person.get(person) or LLTreeSet())
        if sets:
            found = sets[0]
            for other in sets[1:]:
                found = intersection(found, other)
            keys = list(found.keys(lo, hi))
        else:
            keys = list(self.entries.keys(lo, hi))
        keys.reverse()
        return keys

    def __len__(self):
        return self.count()


def _name_in(entry, person):
    if entry.get('actor') == person and entry.get('actor_name'):
        return entry['actor_name']
    if entry.get('subject') == person and entry.get('subject_name'):
        return entry['subject_name']
    return person


def get_record(site=None, create=False):
    site = site if site is not None else getSite()
    if site is None:
        return None
    annotations = IAnnotations(site)
    record = annotations.get(ANNOTATION_KEY)
    if record is None and create:
        record = annotations[ANNOTATION_KEY] = ActivityRecord()
    return record
