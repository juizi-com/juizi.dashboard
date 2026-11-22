/**
 * The parts every Juizi dashboard shares, as in juizi-blocks' Dashboard:
 * the credit and version footer, and the toolbar's back button to Site
 * Setup. Copied rather than imported: this add-on works on plain Volto.
 */
import React from 'react';
import { createPortal } from 'react-dom';
import { useSelector } from 'react-redux';
import { useHistory, useLocation } from 'react-router-dom';
import { Button } from 'semantic-ui-react';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import Toolbar from '@plone/volto/components/manage/Toolbar/Toolbar';
import { useClient } from '@plone/volto/hooks/client/useClient';
import { getParentUrl } from '@plone/volto/helpers/Url/Url';
import backSVG from '@plone/volto/icons/back.svg';

// Not a <p>: Volto Light Theme restyles every `.content-area p > a`.
export const DashboardFooter = ({ name, version }) => (
  <div className="juizi-dashboard__version-footer">
    <span className="juizi-dashboard__credit">
      <span aria-hidden>❤️🤖</span> Vibe Coded with Care by{' '}
      <a
        href="https://github.com/aboycalledhero"
        target="_blank"
        rel="noopener noreferrer"
      >
        aboycalledhero
      </a>
    </span>
    <span className="juizi-dashboard__version">
      {name} v{version}
    </span>
  </div>
);

// Back to Site Setup, in Volto's toolbar (as Volto's own control panels do).
// Someone who can't open Site Setup, such as a Site Activity Viewer, goes
// back to the home page instead (D29). The backend lists the plone_setup
// user action only for people who may open Site Setup.
export const BackToSiteSetup = () => {
  const isClient = useClient();
  const history = useHistory();
  const location = useLocation();
  const canSetup = useSelector((state) =>
    (state.actions?.actions?.user || []).some((a) => a.id === 'plone_setup'),
  );
  if (!isClient) return null;
  const target = document.getElementById('toolbar');
  if (!target) return null;
  return createPortal(
    <Toolbar
      pathname={location.pathname}
      hideDefaultViewButtons
      inner={
        <Button
          className="item"
          aria-label={canSetup ? 'Back to Site Setup' : 'Back to the site'}
          title={canSetup ? 'Back to Site Setup' : 'Back to the site'}
          onClick={() =>
            history.push(canSetup ? getParentUrl(location.pathname) : '/')
          }
        >
          <Icon name={backSVG} className="contents circled" size="30px" />
        </Button>
      }
    />,
    target,
  );
};
