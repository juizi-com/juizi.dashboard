import ActivityDashboard from './components/ActivityDashboard';
import offerAddon, { availableAddon } from './offerAddon';
import packageJson from '../package.json';

const applyConfig = (config) => {
  config.settings.controlpanels = [
    ...(config.settings.controlpanels || []),
    { '@id': '/activity', group: 'Add-on Configuration', title: 'Activity' },
  ];

  config.addonRoutes = [
    ...(config.addonRoutes || []),
    { path: '/controlpanel/activity', component: ActivityDashboard },
  ];

  // Site Setup → Add-ons offers the backend add-on on this frontend; the
  // backend lists it only once it's installed (offerAddon.js).
  offerAddon(
    config,
    availableAddon({
      id: 'juizi.dashboard',
      title: 'Juizi Dashboard',
      description:
        'Activity record and dashboard for site administrators: content and account activity by date range, with CSV download. Needs the volto-juizi-dashboard frontend add-on.',
      version: packageJson.version,
    }),
  );
  return config;
};

export default applyConfig;
