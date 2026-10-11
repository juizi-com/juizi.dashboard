"""Install and uninstall. Uninstalling removes the settings, the permission's
roles and the Site Setup entry, and keeps the record, dormant (D1)."""
from plone.base.interfaces import INonInstallable
from zope.component.hooks import getSite
from zope.interface import implementer

from juizi.dashboard.record import get_record
from juizi.dashboard.record import RECORD
from juizi.dashboard.recorder import write


@implementer(INonInstallable)
class HiddenProfiles:

    def getNonInstallableProfiles(self):
        return ['juizi.dashboard:uninstall']


def post_install(setup_tool):
    site = getSite()
    existed = get_record(site) is not None
    get_record(site, create=True)
    write(RECORD, 'addon.reinstalled' if existed else 'addon.installed', force=True)


def post_uninstall(setup_tool):
    write(RECORD, 'addon.uninstalled', force=True)
