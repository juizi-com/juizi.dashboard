"""Install, upgrades and uninstall. Uninstalling removes the settings, the
permissions' roles, the Site Activity Viewer role, the Site Setup entry and
the user-menu entry, and keeps the record, dormant (D1, D29)."""
from plone.base.interfaces import INonInstallable
from Products.CMFCore.utils import getToolByName
from Products.GenericSetup.tool import UNKNOWN
from zope.component.hooks import getSite
from zope.interface import implementer

from juizi.dashboard.record import get_record
from juizi.dashboard.record import RECORD
from juizi.dashboard.recorder import write


DEFAULT_PROFILE = 'juizi.dashboard:default'
VIEWER_ROLE = 'Site Activity Viewer'


def is_installed_here():
    """Whether juizi.dashboard is installed on the current site. Read from
    portal_setup directly: asking Plone's installer would ask this utility
    again (it checks the non-installable lists)."""
    setup = getToolByName(getSite(), 'portal_setup', None)
    if setup is None:
        return False
    return setup.getLastVersionForProfile(DEFAULT_PROFILE) != UNKNOWN


@implementer(INonInstallable)
class HiddenProfiles:

    def getNonInstallableProfiles(self):
        return ['juizi.dashboard:uninstall']

    def getNonInstallableProducts(self):
        """juizi.dashboard is left out of the backend's add-ons list until it
        is installed on the site. Several sites can share one backend, and
        only the ones whose frontend includes volto-juizi-dashboard can use
        it: that frontend adds it to Site Setup → Add-ons itself, and Volto's
        usual Install button installs it (a hidden product can still be
        installed by name). Once installed, it is listed as usual, for
        upgrades and uninstalling."""
        return [] if is_installed_here() else ['juizi.dashboard']


def post_install(setup_tool):
    site = getSite()
    existed = get_record(site) is not None
    get_record(site, create=True)
    write(RECORD, 'addon.reinstalled' if existed else 'addon.installed', force=True)


def post_uninstall(setup_tool):
    write(RECORD, 'addon.uninstalled', force=True)
    remove_viewer_role(getSite())


def remove_viewer_role(site):
    """The role grants nothing once uninstalled, so it goes, with everyone's
    assignments of it: a reinstall starts without viewers (D29)."""
    roles = site.acl_users.portal_role_manager
    if VIEWER_ROLE in roles.listRoleIds():
        roles.removeRole(VIEWER_ROLE)
    if VIEWER_ROLE in site.__ac_roles__:
        site._delRoles([VIEWER_ROLE])


def upgrade_1001(setup_tool):
    """The Site Activity Viewer role and the user-menu entry (D29)."""
    setup_tool.runImportStepFromProfile('profile-' + DEFAULT_PROFILE, 'rolemap')
    setup_tool.runImportStepFromProfile('profile-' + DEFAULT_PROFILE, 'actions')
