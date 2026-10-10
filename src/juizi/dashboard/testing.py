from plone.app.testing import applyProfile
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import PloneSandboxLayer

import juizi.dashboard
import plone.app.contenttypes
import plone.restapi


class DashboardLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        self.loadZCML(package=plone.app.contenttypes)
        self.loadZCML(package=plone.restapi)
        self.loadZCML(package=juizi.dashboard)

    def setUpPloneSite(self, portal):
        applyProfile(portal, 'plone.app.contenttypes:default')
        applyProfile(portal, 'plone.restapi:default')
        portal.portal_workflow.setDefaultChain('simple_publication_workflow')
        applyProfile(portal, 'juizi.dashboard:default')


DASHBOARD_FIXTURE = DashboardLayer()
DASHBOARD_INTEGRATION_TESTING = IntegrationTesting(
    bases=(DASHBOARD_FIXTURE,), name='DashboardLayer:IntegrationTesting')
DASHBOARD_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(DASHBOARD_FIXTURE,), name='DashboardLayer:FunctionalTesting')
