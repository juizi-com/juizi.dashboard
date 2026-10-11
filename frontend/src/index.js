import ActivityDashboard from './components/ActivityDashboard';

const applyConfig = (config) => {
  config.settings.controlpanels = [
    ...(config.settings.controlpanels || []),
    { '@id': '/activity', group: 'Add-on Configuration', title: 'Activity' },
  ];

  config.addonRoutes = [
    ...(config.addonRoutes || []),
    { path: '/controlpanel/activity', component: ActivityDashboard },
  ];

  return config;
};

export default applyConfig;
