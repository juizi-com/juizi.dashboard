/**
 * Offers a backend add-on in Site Setup → Add-ons on this frontend.
 *
 * The backend leaves the add-on out of its add-ons list until it is installed
 * on the site (its setuphandlers.HiddenProfiles): one backend can serve
 * several sites, and only the ones whose frontend includes this Volto add-on
 * can use it. On this frontend the list gets it back as an available add-on,
 * so Volto's usual Install button installs it. Once installed, the backend
 * lists it itself and nothing is added.
 *
 * Other add-ons do the same (juizi-blocks, the collective payments and form
 * add-ons), so this wraps whichever add-ons reducer is already configured
 * instead of replacing it: replacing it would drop the add-ons offered by
 * the ones loaded earlier. Keep this file the same in every add-on that has
 * a copy.
 */
import addons from '@plone/volto/reducers/addons/addons';
import { LIST_ADDONS } from '@plone/volto/constants/ActionTypes';

/** The action, with the add-on added to the backend's list if it's missing. */
export function withAddon(action, addon) {
  const items = action?.result?.items;
  if (
    action?.type !== `${LIST_ADDONS}_SUCCESS` ||
    !Array.isArray(items) ||
    items.some((item) => item?.id === addon.id)
  ) {
    return action;
  }
  return { ...action, result: { ...action.result, items: [...items, addon] } };
}

/** An entry shaped as the backend lists an add-on that isn't installed. */
export function availableAddon({ id, title, description, version }) {
  return {
    '@id': `/@addons/${id}`,
    id,
    title,
    description,
    install_profile_id: `${id}:default`,
    is_installed: false,
    profile_type: 'default',
    uninstall_profile_id: '',
    upgrade_info: {},
    version,
  };
}

export default function offerAddon(config, addon) {
  const previous = config.addonReducers?.addons || addons;
  config.addonReducers = {
    ...config.addonReducers,
    addons: (state, action = {}) => previous(state, withAddon(action, addon)),
  };
  return config;
}
