"""Activity record settings in Site Setup (Volto renders the form:
GET/PATCH @controlpanels/juizi-dashboard-settings)."""
from plone.restapi.controlpanels import RegistryConfigletPanel
from zope.component import adapter
from zope.interface import Interface

from juizi.dashboard import _
from juizi.dashboard.interfaces import IDashboardSettings


@adapter(Interface, Interface)
class DashboardSettingsPanel(RegistryConfigletPanel):
    schema = IDashboardSettings
    schema_prefix = 'juizi.dashboard'
    configlet_id = 'juizi-dashboard-settings'
    configlet_category_id = 'Products'
    title = _('Activity record settings')
    group = 'Products'
