from zope import schema
from zope.interface import Interface
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

from juizi.dashboard import _

IP_MODES = SimpleVocabulary([
    SimpleTerm('full', 'full', _('Full address')),
    SimpleTerm('shortened', 'shortened', _('Shortened (203.0.113.x)')),
    SimpleTerm('off', 'off', _('Not recorded')),
])


class IDashboardSettings(Interface):
    """Activity record settings (registry prefix juizi.dashboard). Changing
    one affects only what's recorded from then on, and every change is
    itself recorded. How long entries are kept is set on the server."""

    recording = schema.Bool(
        title=_('Record activity'),
        description=_('Logins, account changes and content actions are added to the '
                      'activity record. Switching this off is itself recorded.'),
        default=True,
        required=False,
    )

    ip_addresses = schema.Choice(
        title=_('IP addresses'),
        description=_('Stored with logins and other account events, never with content '
                      'actions. Shortened keeps the network but not the device.'),
        vocabulary=IP_MODES,
        default='full',
    )

    comment_text = schema.Bool(
        title=_('Workflow comment text'),
        description=_('Off records that a comment was made, without its text.'),
        default=True,
        required=False,
    )
