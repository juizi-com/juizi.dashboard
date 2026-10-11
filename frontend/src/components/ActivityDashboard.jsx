/**
 * Site Setup → Activity: one list of what happened on the site, newest
 * first, filtered by date range, with a CSV download of the same filters.
 * Site administrators only (the backend answers 401 to anyone else).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { Unauthorized } from '@plone/volto/components';
import { download, getJson } from '../api';
import { BackToSiteSetup, DashboardFooter } from './DashboardChrome';
import packageJson from '../../package.json';
import './juizi-dashboard.scss';
import './activity.scss';

const PRESETS = [
  [7, 'Last 7 days'],
  [28, 'Last 28 days'],
  [90, 'Last 90 days'],
];

const CATEGORIES = [
  ['', 'Everything'],
  ['content', 'Content'],
  ['account', 'People'],
  ['record', 'The record'],
];

const CATEGORY_LABELS = {
  content: 'Content',
  account: 'People',
  record: 'Record',
};

const SIZE = 50;

const keep = (days) => (days ? `for ${days} days` : 'forever');

const dateTime = (iso) =>
  new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

const day = (isoDate) =>
  new Date(`${isoDate}T12:00:00`).toLocaleDateString(undefined, {
    dateStyle: 'medium',
  });

const query = (filters, extra = {}) => {
  const params = new URLSearchParams();
  if (filters.days) params.set('days', filters.days);
  else {
    params.set('from', filters.from);
    params.set('to', filters.to);
  }
  if (filters.category) params.set('category', filters.category);
  if (filters.person) params.set('person', filters.person);
  Object.entries(extra).forEach(([k, v]) => params.set(k, v));
  return params.toString();
};

const Person = ({ id, name, onPick }) => {
  if (!id) return <span className="juizi-dashboard__muted">Anonymous</span>;
  return (
    <button
      type="button"
      className="juizi-dashboard__link-button"
      title="Show only this person's activity"
      onClick={() => onPick(id, name || id)}
    >
      {name || id}
    </button>
  );
};

const Concerning = ({ item, onPick }) => {
  if (item.path) {
    const gone = item.event === 'content.deleted';
    const label = item.title || item.path;
    return (
      <>
        {gone ? <span>{label}</span> : <Link to={item.path}>{label}</Link>}
        <div className="juizi-dashboard__muted">{item.path}</div>
      </>
    );
  }
  if (item.subject && item.subject !== item.actor) {
    return (
      <Person id={item.subject} name={item.subject_name} onPick={onPick} />
    );
  }
  return null;
};

const ActivityDashboard = () => {
  const token = useSelector((state) => state.userSession?.token);
  const [filters, setFilters] = useState({
    days: 28,
    from: '',
    to: '',
    category: '',
    person: '',
  });
  const [personName, setPersonName] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const load = useCallback(() => {
    if (!filters.days && (!filters.from || !filters.to)) return;
    setLoading(true);
    getJson(token, `@activity?${query(filters, { page, size: SIZE })}`)
      .then((result) => {
        setData(result);
        setError('');
      })
      .catch((e) => {
        if ([401, 403].includes(e.status)) setForbidden(true);
        else if (e.status === 404)
          setError(
            'The activity record is not installed on this site. Install juizi.dashboard in Site Setup → Add-ons to see it.',
          );
        else setError(e.message);
      })
      .finally(() => setLoading(false));
  }, [token, filters, page]);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  if (!token || forbidden) return <Unauthorized />;

  const change = (next) => {
    setPage(1);
    setFilters((current) => ({ ...current, ...next }));
  };
  const pickPerson = (id, name) => {
    setPersonName(name);
    change({ person: id });
  };
  const custom = !filters.days;
  const total = data?.total || 0;
  const pages = Math.max(1, Math.ceil(total / SIZE));

  const downloadCsv = () => {
    if (
      total > data.csv_limit &&
      // eslint-disable-next-line no-alert
      !window.confirm(
        `This range holds ${total} entries. The file will have the newest ${data.csv_limit}. Narrow the range to get the rest.`,
      )
    )
      return;
    setDownloading(true);
    download(
      token,
      `@activity?${query(filters, { format: 'csv' })}`,
      `activity-${data.from}-to-${data.to}.csv`,
    )
      .catch((e) => setError(e.message))
      .finally(() => setDownloading(false));
  };

  return (
    <div
      id="page-juizi-activity"
      className="juizi-dashboard juizi-dashboard--wide juizi-activity"
    >
      <h1>Activity</h1>
      <p className="juizi-dashboard__description">
        What happened on this site, newest first: content that was created,
        edited, published, moved or deleted, and people's logins and account
        changes.
      </p>

      {data && !data.recording && (
        <div className="juizi-dashboard__error" role="status">
          Recording is switched off, so nothing new is being added.{' '}
          <Link to="/controlpanel/juizi-dashboard-settings">
            Switch it on in the settings
          </Link>
          .
        </div>
      )}

      <div className="juizi-activity__filters">
        <div
          className="juizi-dashboard__tabs"
          role="group"
          aria-label="Date range"
        >
          {PRESETS.map(([days, label]) => (
            <button
              key={days}
              type="button"
              aria-pressed={filters.days === days}
              className={
                filters.days === days
                  ? 'juizi-dashboard__tab juizi-dashboard__tab--active'
                  : 'juizi-dashboard__tab'
              }
              onClick={() => change({ days })}
            >
              {label}
            </button>
          ))}
          <button
            type="button"
            aria-pressed={custom}
            className={
              custom
                ? 'juizi-dashboard__tab juizi-dashboard__tab--active'
                : 'juizi-dashboard__tab'
            }
            onClick={() =>
              change({ days: 0, from: data?.from || '', to: data?.to || '' })
            }
          >
            Choose dates
          </button>
        </div>

        <div className="juizi-activity__row">
          {custom && (
            <>
              <label className="juizi-activity__field">
                <span>From</span>
                <input
                  type="date"
                  className="juizi-dashboard__input"
                  value={filters.from}
                  max={filters.to || undefined}
                  onChange={(e) => change({ from: e.target.value })}
                />
              </label>
              <label className="juizi-activity__field">
                <span>To</span>
                <input
                  type="date"
                  className="juizi-dashboard__input"
                  value={filters.to}
                  min={filters.from || undefined}
                  onChange={(e) => change({ to: e.target.value })}
                />
              </label>
            </>
          )}
          <label className="juizi-activity__field">
            <span>Show</span>
            <select
              className="juizi-dashboard__select"
              value={filters.category}
              onChange={(e) => change({ category: e.target.value })}
            >
              {CATEGORIES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          {filters.person && (
            <span className="juizi-activity__person">
              Only {personName || filters.person}
              <button
                type="button"
                className="juizi-dashboard__link-button"
                aria-label="Show everyone"
                onClick={() => change({ person: '' })}
              >
                ×
              </button>
            </span>
          )}
          <span className="juizi-activity__spacer" />
          <button
            type="button"
            className="juizi-dashboard__btn juizi-dashboard__btn--secondary"
            disabled={!total || downloading}
            onClick={downloadCsv}
          >
            {downloading ? 'Preparing…' : 'Download CSV'}
          </button>
        </div>
      </div>

      {error && (
        <div className="juizi-dashboard__error" role="alert">
          {error}
        </div>
      )}

      {data && (
        <p className="juizi-dashboard__muted juizi-activity__summary">
          {total === 1 ? '1 entry' : `${total} entries`} from {day(data.from)}{' '}
          to {day(data.to)}
          {filters.person && ` for ${personName || filters.person}`}. Dates
          follow the site's time zone ({data.timezone}).
        </p>
      )}

      {data && total === 0 && !loading && (
        <div className="juizi-dashboard__section">
          Nothing was recorded in this range.
          {data.started &&
            ` The record started on ${dateTime(data.started)}; nothing before that was recorded.`}
        </div>
      )}

      {data && total > 0 && (
        <div className="juizi-activity__scroll">
          <table
            className="juizi-dashboard__table juizi-activity__table"
            aria-busy={loading}
          >
            <thead>
              <tr>
                <th>Type</th>
                <th>When</th>
                <th>Who</th>
                <th>What</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id}>
                  <td className="juizi-dashboard__cell--fit">
                    <span
                      className={`juizi-activity__badge juizi-activity__badge--${item.category}`}
                    >
                      {CATEGORY_LABELS[item.category]}
                    </span>
                  </td>
                  <td className="juizi-dashboard__cell--fit">
                    {dateTime(item.when)}
                  </td>
                  <td>
                    <Person
                      id={item.actor}
                      name={item.actor_name}
                      onPick={pickPerson}
                    />
                    {item.ip && (
                      <div className="juizi-dashboard__muted">IP {item.ip}</div>
                    )}
                  </td>
                  <td>{item.label}</td>
                  <td>
                    <Concerning item={item} onPick={pickPerson} />
                    {item.detail && (
                      <div className="juizi-activity__detail">
                        {item.detail}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && pages > 1 && (
        <div className="juizi-dashboard__actions juizi-activity__pager">
          <button
            type="button"
            className="juizi-dashboard__btn juizi-dashboard__btn--secondary"
            disabled={page <= 1 || loading}
            onClick={() => setPage(page - 1)}
          >
            Newer
          </button>
          <span>
            Page {page} of {pages}
          </span>
          <button
            type="button"
            className="juizi-dashboard__btn juizi-dashboard__btn--secondary"
            disabled={page >= pages || loading}
            onClick={() => setPage(page + 1)}
          >
            Older
          </button>
        </div>
      )}

      {data && (
        <p className="juizi-dashboard__hint juizi-activity__retention">
          Account activity is kept {keep(data.retention.account_days)} and
          content actions {keep(data.retention.content_days)}. That's set on the
          server, and entries can only be cleared there. Failed logins aren't
          recorded, because Plone doesn't report them yet. Role changes are
          recorded when made in Users (Volto), not in the classic Users and
          Groups screen.{' '}
          <Link to="/controlpanel/juizi-dashboard-settings">Settings</Link>
        </p>
      )}

      <DashboardFooter name={packageJson.name} version={packageJson.version} />
      <BackToSiteSetup />
    </div>
  );
};

export default ActivityDashboard;
