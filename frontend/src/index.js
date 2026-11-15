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
  // backend lists it only once it's installed (offerAddon.js). It has an
  // uninstall profile: without it, Volto says before installing that the
  // add-on can't be uninstalled. Set here, not in offerAddon.js, which stays
  // the same in every add-on that has a copy.
  offerAddon(config, {
    ...availableAddon({
      id: 'juizi.dashboard',
      title: 'Juizi Dashboard',
      description:
        'Activity record and dashboard for site administrators: content and account activity by date range, with CSV download. Needs the volto-juizi-dashboard frontend add-on.',
      version: packageJson.version,
    }),
    uninstall_profile_id: 'juizi.dashboard:uninstall',
  });
  return config;
};

export default applyConfig;
