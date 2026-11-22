/**
 * An Activity entry in the toolbar's user menu, for everyone the backend
 * offers it to: its `juizi-activity` user action needs the permission to
 * view the dashboard. It's how a Site Activity Viewer, who can't open
 * Site Setup, finds the dashboard (D29). Rendered from appExtras into
 * Volto's `toolbar-user-menu` pluggable (Volto 18 and 19).
 */
import React from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { Plug } from '@plone/volto/components/manage/Pluggable';
import Icon from '@plone/volto/components/theme/Icon/Icon';
import rightArrowSVG from '@plone/volto/icons/right-key.svg';

const ActivityMenuItem = () => {
  const action = useSelector((state) =>
    (state.actions?.actions?.user || []).find((a) => a.id === 'juizi-activity'),
  );
  if (!action) return null;
  return (
    <Plug pluggable="toolbar-user-menu" id="juizi-activity">
      <li>
        <Link to="/controlpanel/activity">
          {action.title || 'Activity'}
          <Icon name={rightArrowSVG} size="24px" />
        </Link>
      </li>
    </Plug>
  );
};

export default ActivityMenuItem;
