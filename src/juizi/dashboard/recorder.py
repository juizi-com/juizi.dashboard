"""Turns the events Plone core fires into activity record entries.

Every write happens in the action's own transaction, so an action that's
rolled back leaves no entry. Nothing here stores a password, a reset token
or a login name as typed, and profile changes keep field names only.
"""
from AccessControl import getSecurityManager
from Acquisition import aq_base
from ipaddress import ip_address
from ipaddress import ip_network
from plone.protect.utils import SAFE_WRITE_KEY
from plone.registry.interfaces import IRegistry
from Products.CMFCore.interfaces import IContentish
from Products.CMFCore.utils import getToolByName
from zope.annotation.interfaces import IAnnotations
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.container.interfaces import IContainerModifiedEvent
from zope.globalrequest import getRequest
from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from juizi.dashboard.record import ACCOUNT
from juizi.dashboard.record import CONTENT
from juizi.dashboard.record import get_record
from juizi.dashboard.record import RECORD

import logging

logger = logging.getLogger('juizi.dashboard')

PREFIX = 'juizi.dashboard.'
REQUEST_KEY = 'juizi.dashboard.seen'
_CURRENT = object()


# Settings

def _registry():
    return queryUtility(IRegistry)


def installed():
    """The add-on is installed on the current site (its settings exist)."""
    registry = _registry()
    return registry is not None and registry.get(PREFIX + 'recording', None) is not None


def setting(name, default=None):
    registry = _registry()
    value = registry.get(PREFIX + name, None) if registry is not None else None
    return default if value is None else value


# Who, where

def _principal_id(principal):
    if principal is None or isinstance(principal, str):
        return principal
    getter = getattr(principal, 'getId', None)
    return getter() if getter else None


def current_user_id():
    user = getSecurityManager().getUser()
    return user.getId() if user is not None else None


def person_name(principal_id, site=None):
    """A user's full name or a group's title, else the id."""
    if not principal_id:
        return ''
    site = site or getSite()
    try:
        member = getToolByName(site, 'portal_membership').getMemberById(principal_id)
        if member is not None:
            return member.getProperty('fullname', '') or principal_id
        group = getToolByName(site, 'portal_groups').getGroupById(principal_id)
        if group is not None:
            return group.getProperty('title', '') or principal_id
    except Exception:
        logger.debug('No name for %s', principal_id, exc_info=True)
    return principal_id


def client_address(request):
    mode = setting('ip_addresses', 'full')
    if mode == 'off' or request is None:
        return ''
    getter = getattr(request, 'getClientAddr', None)
    address = (getter() if getter else '') or ''
    if mode == 'shortened' and address:
        try:
            parsed = ip_address(address)
        except ValueError:
            return ''
        if parsed.version == 4:
            return '.'.join(address.split('.')[:3]) + '.x'
        return str(ip_network(f'{address}/48', strict=False).network_address) + '/48'
    return address


def _item(obj):
    site = getSite()
    path = '/'.join(obj.getPhysicalPath())
    root = '/'.join(site.getPhysicalPath())
    relative = path[len(root):] or '/'
    uid_getter = getattr(aq_base(obj), 'UID', None)
    title_getter = getattr(aq_base(obj), 'Title', None)
    return {
        'uid': uid_getter() if callable(uid_getter) else '',
        'path': relative,
        'title': (obj.Title() if callable(title_getter) else '') or obj.getId(),
        'type': getattr(aq_base(obj), 'portal_type', ''),
    }


# Writing

def _request_seen():
    request = getRequest()
    if request is None:
        return None
    try:
        return IAnnotations(request).setdefault(REQUEST_KEY, set())
    except TypeError:
        return None


def _seen(key):
    """True if this request already recorded `key`; marks it either way."""
    seen = _request_seen()
    if seen is None:
        return False
    if key in seen:
        return True
    seen.add(key)
    return False


def _was_seen(key):
    seen = _request_seen()
    return seen is not None and key in seen


def _add_marked_safe(record, entry):
    """Add the entry, and tell plone.protect its writes are ours (D16).

    Only objects newly registered by this write are marked: whatever else
    the request writes is still checked."""
    jar = record._p_jar
    request = getRequest()
    before = {id(o) for o in jar._registered_objects} if jar is not None else set()
    key = record.add(entry)
    environ = getattr(request, 'environ', None)
    if jar is not None and isinstance(environ, dict):
        safe = environ.setdefault(SAFE_WRITE_KEY, [])
        for obj in jar._registered_objects:
            oid = getattr(obj, '_p_oid', None)
            if id(obj) not in before and oid and oid not in safe:
                safe.append(oid)
    return key


def write(category, event, actor=_CURRENT, subject=None, item=None, detail=None,
          force=False):
    """Record one entry on the current site, if recording is on.

    `force` writes even when recording is switched off: the record's own
    entries (switching it off, settings, install) always go in."""
    site = getSite()
    if site is None or not (force or (installed() and setting('recording', False))):
        return None
    record = get_record(site)
    if record is None:
        return None
    actor = current_user_id() if actor is _CURRENT else actor
    entry = {
        'category': category,
        'event': event,
        'actor': actor or None,
        'actor_name': person_name(actor, site) if actor else '',
        'subject': subject or None,
        'subject_name': person_name(subject, site) if subject else '',
        'detail': detail or {},
        'ip': client_address(getRequest()) if category == ACCOUNT else '',
    }
    if item:
        entry.update(item)
    return _add_marked_safe(record, entry)


# Account events (PAS fires these with the event alone)

def _account(event_name, principal, actor=_CURRENT, detail=None):
    if not installed():
        return
    subject = _principal_id(principal)
    write(ACCOUNT, event_name, actor=actor, subject=subject, detail=detail)


def logged_in(event):
    user_id = _principal_id(event.principal)
    _account('login', user_id, actor=user_id)


def logged_out(event):
    user_id = _principal_id(event.principal)
    _account('logout', user_id, actor=user_id)


def credentials_updated(event):
    # event.password is the new password in clear text: never read it.
    if not installed():
        return
    subject = _principal_id(event.principal)
    actor = current_user_id()
    how = 'reset' if not actor else ('self' if actor == subject else 'admin')
    _account('password.changed', subject, actor=actor, detail={'how': how})


def principal_created(event):
    subject = _principal_id(event.principal)
    if _seen(('created', subject)):
        return
    _account('account.created', subject)


def principal_deleted(event):
    _account('account.deleted', _principal_id(event.principal))


def group_created(event):
    _account('group.created', _principal_id(event.principal))


def group_deleted(event):
    _account('group.deleted', _principal_id(event.principal))


def added_to_group(event):
    if not installed():
        return
    _account('group.member_added', _principal_id(event.principal),
             detail={'group': event.group_id, 'group_title': person_name(event.group_id)})


def removed_from_group(event):
    if not installed():
        return
    _account('group.member_removed', _principal_id(event.principal),
             detail={'group': event.group_id, 'group_title': person_name(event.group_id)})


def properties_updated(event):
    if not installed():
        return
    subject = _principal_id(event.principal)
    if subject is None:
        return
    fields = set(getattr(event, 'properties', None) or {})
    if 'roles' in fields:
        # plone.restapi's @users passes roles through here before setting
        # them; the actual change is compared at commit (D25).
        fields.discard('roles')
        _watch_roles(subject)
    # A new account's first properties belong to "account created".
    if not fields or _was_seen(('created', subject)) or _seen(('properties', subject)):
        return
    _account('profile.changed', subject, detail={'fields': sorted(fields)})


def _direct_roles(site, user_id):
    """Global roles given to the user directly (not through a group)."""
    manager = getattr(site.acl_users, 'portal_role_manager', None)
    user = site.acl_users.getUserById(user_id)
    if manager is None or user is None:
        return set()
    return set(manager.getRolesForPrincipal(user)) - {'Authenticated'}


def _watch_roles(user_id):
    """Record a global role change, if there is one, when the transaction
    commits: what was asked for may still be refused."""
    if _seen(('roles', user_id)):
        return
    import transaction
    from zope.component.hooks import setSite
    site = getSite()
    before = _direct_roles(site, user_id)
    actor = current_user_id()

    def compare():
        previous = getSite()
        setSite(site)
        try:
            after = _direct_roles(site, user_id)
            added, removed = sorted(after - before), sorted(before - after)
            if added or removed:
                write(ACCOUNT, 'roles.changed', actor=actor, subject=user_id,
                      detail={'added': added, 'removed': removed})
        finally:
            setSite(previous)

    transaction.get().addBeforeCommitHook(compare)


# Content actions. Every handler checks installed() before anything else:
# the add-on is loaded for every site in the Zope instance, and events also
# fire with no site at all (while another site is being created).

def _content(obj, event_name, detail=None, once=None):
    if not installed() or not IContentish.providedBy(obj):
        return
    item = _item(obj)
    if once and _seen((once, item['uid'] or item['path'])):
        return
    write(CONTENT, event_name, item=item, detail=detail)


def copied(obj, event):
    # The copy is about to be added; "created" notes where it came from.
    if not installed():
        return
    request = getRequest()
    if request is not None:
        IAnnotations(request).setdefault('juizi.dashboard.copies', {})[id(aq_base(obj))] = (
            _item(event.original)['path'])


def added(obj, event):
    if obj is not event.object or not installed():
        return  # inside a pasted folder: the folder's entry covers it (D6)
    request = getRequest()
    copies = IAnnotations(request).get('juizi.dashboard.copies', {}) if request else {}
    source = copies.get(id(aq_base(obj)))
    key = _item(obj)['uid'] or _item(obj)['path']
    # Creating fires "modified" too, in the same request (D6).
    _seen(('edited', key))
    if source:
        _content(obj, 'content.copied', detail=_with_inside({'from': source}, obj),
                 once='created')
    else:
        _content(obj, 'content.created', once='created')


def modified(obj, event):
    if IContainerModifiedEvent.providedBy(event) or _is_sharing(event) or not installed():
        return
    fields = []
    for description in getattr(event, 'descriptions', ()) or ():
        # plone.restapi names them with their schema: IDublinCore.title.
        fields.extend(name.rsplit('.', 1)[-1]
                      for name in getattr(description, 'attributes', ()) or ())
    _content(obj, 'content.edited', detail={'fields': sorted(set(fields))} if fields else None,
             once='edited')


def transitioned(obj, event):
    if event.transition is None:
        return  # the initial state, set when an item is created
    status = getattr(event, 'status', None) or {}
    comment = status.get('comments') or ''
    detail = {
        'transition': event.transition.getId(),
        # The menu's name ("Publish"), not the long title ("Reviewer
        # publishes content").
        'transition_title': (getattr(event.transition, 'actbox_name', '')
                             or event.transition.title or event.transition.getId()),
        'from': event.old_state.title or event.old_state.getId(),
        'to': event.new_state.title or event.new_state.getId(),
    }
    if comment:
        detail['comment'] = comment if setting('comment_text', True) else None
    _content(obj, 'content.transition', detail=detail)


def moved(obj, event):
    if IObjectAddedEvent.providedBy(event) or IObjectRemovedEvent.providedBy(event):
        return
    if not installed():
        return
    if obj is not event.object or event.oldParent is None or event.newParent is None:
        return
    if aq_base(event.oldParent) is aq_base(event.newParent):
        _content(obj, 'content.renamed',
                 detail=_with_inside({'from': event.oldName, 'to': event.newName}, obj))
        return
    site_path = '/'.join(getSite().getPhysicalPath())
    old = '/'.join(event.oldParent.getPhysicalPath() + (event.oldName,))[len(site_path):]
    _content(obj, 'content.moved', detail=_with_inside({'from': old}, obj))


def _with_inside(detail, obj):
    """Adds how many items a folder carried with it (D6)."""
    inside = _descendants(obj)
    if inside:
        detail['inside'] = inside
    return detail


def _descendants(obj):
    count = 0
    values = getattr(aq_base(obj), 'objectValues', None)
    if values is None:
        return 0
    for child in obj.objectValues():
        if IContentish.providedBy(child):
            count += 1 + _descendants(child)
    return count


def will_be_removed(obj, event):
    if obj is not event.object or not installed():
        return  # inside a deleted folder: the folder's entry counts it (D6)
    inside = _descendants(obj)
    _content(obj, 'content.deleted', detail={'inside': inside} if inside else None)
    record = get_record(getSite())
    uid = getattr(aq_base(obj), 'UID', None)
    if record is not None and callable(uid):
        record.sharing_memory().pop(uid(), None)


# Sharing

def _is_sharing(event):
    from plone.app.workflow.interfaces import ILocalrolesModifiedEvent
    return ILocalrolesModifiedEvent.providedBy(event)


def _role_changes(before, after, names):
    """[{id, title, roles}] for roles in `after` that `before` didn't have."""
    changes = []
    for principal in sorted(after):
        added = sorted(set(after[principal]) - set(before.get(principal, ())))
        if added:
            changes.append({'id': principal, 'title': names[principal], 'roles': added})
    return changes


def sharing_changed(obj, event):
    """The roles now, and, once the record has seen this item's roles
    before, what was given and taken away (D7)."""
    if not installed():
        return
    record = get_record(getSite())
    if record is None:
        return
    current = {}
    for principal, assigned in obj.get_local_roles():
        assigned = sorted(r for r in assigned if r != 'Owner')
        if assigned:
            current[principal] = assigned
    names = {p: person_name(p) for p in current}
    inherit = not getattr(aq_base(obj), '__ac_local_roles_block__', False)
    item = _item(obj)
    detail = {'roles': [{'id': p, 'title': names[p], 'roles': current[p]}
                        for p in sorted(current)],
              'inherit': inherit}
    memory = record.sharing_memory()
    key = item['uid'] or item['path']
    previous = memory.get(key)
    if previous is not None:
        before = previous['roles']
        names.update({p: person_name(p) for p in before if p not in names})
        detail['given'] = _role_changes(before, current, names)
        detail['taken'] = _role_changes(current, before, names)
        if previous['inherit'] != inherit:
            detail['inherit_changed'] = True
    memory[key] = {'roles': current, 'inherit': inherit}
    write(ACCOUNT, 'sharing.changed', item=item, detail=detail)


# The record's own settings (D10)

def settings_changed(settings, event):
    name = event.record.fieldName
    if name == 'recording':
        write(RECORD, 'recording.on' if event.newValue else 'recording.off', force=True)
    else:
        write(RECORD, 'settings.changed', force=True,
              detail={'setting': name, 'old': event.oldValue, 'new': event.newValue})
