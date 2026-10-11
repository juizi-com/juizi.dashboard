/**
 * Site Setup → Activity: one list of what happened on the site, newest
 * first, filtered by date range, with a CSV download of the same filters.
 * Site administrators only (the backend answers 401 to anyone else).
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
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

// Times show in the site's time zone, as the date filter and CSV do (D11).
const dateTime = (iso, timeZone) => {
  const options = { dateStyle: 'medium', timeStyle: 'short' };
  try {
    return new Date(iso).toLocaleString(undefined, { ...options, timeZone });
  } catch (e) {
    return new Date(iso).toLocaleString(undefined, options);
  }
};

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

// Every link opens in a new tab, so the dashboard stays where it was.
const NewTab = ({ to, children }) => (
  <a href={to} target="_blank" rel="noopener noreferrer">
    {children}
    <span className="juizi-activity__sr"> (opens in a new tab)</span>
  </a>
);

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
    const label = item.title || item.path;
    return (
      <>
        {item.event === 'content.deleted' ? (
          <span>{label}</span>
        ) : (
          <NewTab to={item.path}>{label}</NewTab>
        )}
        <div className="juizi-dashboard__muted">
          {item.type_title && `${item.type_title} · `}
          {item.path}
        </div>
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

// Page numbers: the first, the last, and two either side of the current
// page, with a gap marker between runs.
const pageNumbers = (page, pages) => {
  const wanted = new Set([1, pages]);
  for (let n = page - 2; n <= page + 2; n += 1) {
    if (n >= 1 && n <= pages) wanted.add(n);
  }
  const sorted = [...wanted].sort((a, b) => a - b);
  return sorted.flatMap((n, i) =>
    i > 0 && n - sorted[i - 1] > 1 ? ['gap', n] : [n],
  );
};

const Pager = ({ page, size, total, onChange, disabled }) => {
  const pages = Math.ceil(total / size);
  if (pages <= 1) return null;
  const first = (page - 1) * size + 1;
  const last = Math.min(page * size, total);
  return (
    <nav className="juizi-activity__pager" aria-label="Pages">
      <button
        type="button"
        className="juizi-dashboard__btn juizi-dashboard__btn--secondary"
        disabled={page <= 1 || disabled}
        onClick={() => onChange(page - 1)}
      >
        ← Previous
      </button>
      <ul className="juizi-activity__pages">
        {pageNumbers(page, pages).map((n, i) =>
          n === 'gap' ? (
            // eslint-disable-next-line react/no-array-index-key
            <li key={`gap-${i}`} aria-hidden="true">
              …
            </li>
          ) : (
            <li key={n}>
              <button
                type="button"
                className={
                  n === page
                    ? 'juizi-activity__page juizi-activity__page--current'
                    : 'juizi-activity__page'
                }
                aria-label={`Page ${n}`}
                aria-current={n === page ? 'page' : undefined}
                disabled={disabled}
                onClick={() => n !== page && onChange(n)}
              >
                {n}
              </button>
            </li>
          ),
        )}
      </ul>
      <button
        type="button"
        className="juizi-dashboard__btn juizi-dashboard__btn--secondary"
        disabled={page >= pages || disabled}
        onClick={() => onChange(page + 1)}
      >
        Next →
      </button>
      <span className="juizi-activity__range">
        {first}–{last} of {total}
      </span>
    </nav>
  );
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
  // After a page change, focus moves to the summary above the list, so
  // keyboard and screen reader users start at the top of the new page.
  const summaryRef = useRef(null);
  const pageChanged = useRef(false);

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

  useEffect(() => {
    if (pageChanged.current && data && summaryRef.current) {
      pageChanged.current = false;
      summaryRef.current.focus();
      summaryRef.current.scrollIntoView({ block: 'start' });
    }
  }, [data]);

  if (!token || forbidden) return <Unauthorized />;

  const change = (next) => {
    setPage(1);
    setFilters((current) => ({ ...current, ...next }));
  };
  const goTo = (n) => {
    pageChanged.current = true;
    setPage(n);
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
    <div id="page-juizi-activity" className="juizi-dashboard juizi-activity">
      <h1>Activity</h1>
      <p className="juizi-dashboard__description">
        What happened on this site, newest first: content that was created,
        edited, published, moved or deleted, and people's logins and account
        changes.
      </p>

      {data && !data.recording && (
        <div className="juizi-dashboard__error" role="status">
          Recording is switched off, so nothing new is being added.{' '}
          <NewTab to="/controlpanel/juizi-dashboard-settings">
            Switch it on in the settings
          </NewTab>
          .
        </div>
      )}

      <div className="juizi-activity__filters">
        <div
          className="juizi-dashboard__tabs juizi-activity__presets"
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
        <p
          ref={summaryRef}
          tabIndex={-1}
          className="juizi-dashboard__muted juizi-activity__summary"
          aria-live="polite"
        >
          {total === 1 ? '1 entry' : `${total} entries`} from {day(data.from)}{' '}
          to {day(data.to)}
          {filters.person && ` for ${personName || filters.person}`}
          {pages > 1 && `, page ${data.page} of ${pages}`}. Dates and times
          follow the site's time zone ({data.timezone}).
        </p>
      )}

      {data && total === 0 && !loading && (
        <div className="juizi-dashboard__section">
          Nothing was recorded in this range.
          {data.started &&
            ` The record started on ${dateTime(data.started, data.timezone)}; nothing before that was recorded.`}
        </div>
      )}

      {data && total > 0 && (
        <table
          className="juizi-dashboard__table juizi-activity__table"
          aria-busy={loading}
        >
          <caption className="juizi-activity__sr">
            Activity, newest first
          </caption>
          <thead>
            <tr>
              <th scope="col">Type</th>
              <th scope="col">When</th>
              <th scope="col">Who</th>
              <th scope="col">What</th>
              <th scope="col">Details</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item) => (
              // Explicit roles keep the table's meaning for screen readers
              // when narrow screens show each row as a card.
              <tr key={item.id} role="row">
                <td role="cell" data-label="Type">
                  <span
                    className={`juizi-activity__badge juizi-activity__badge--${item.category}`}
                  >
                    {CATEGORY_LABELS[item.category]}
                  </span>
                </td>
                <td role="cell" data-label="When">
                  {dateTime(item.when, data.timezone)}
                </td>
                <td role="cell" data-label="Who">
                  <Person
                    id={item.actor}
                    name={item.actor_name}
                    onPick={pickPerson}
                  />
                  {item.ip && (
                    <div className="juizi-dashboard__muted">IP {item.ip}</div>
                  )}
                </td>
                <td role="cell" data-label="What">
                  {item.label}
                </td>
                <td role="cell" data-label="Details">
                  <Concerning item={item} onPick={pickPerson} />
                  {item.detail && (
                    <div className="juizi-activity__detail">{item.detail}</div>
                  )}
                  {item.note && (
                    <div className="juizi-activity__note">{item.note}</div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {data && (
        <Pager
          page={data.page}
          size={SIZE}
          total={total}
          onChange={goTo}
          disabled={loading}
        />
      )}

      {data && (
        <p className="juizi-dashboard__hint juizi-activity__retention">
          Account activity is kept {keep(data.retention.account_days)} and
          content actions {keep(data.retention.content_days)}.{' '}
          <NewTab to="/controlpanel/juizi-dashboard-settings">Settings</NewTab>
        </p>
      )}

      <DashboardFooter name={packageJson.name} version={packageJson.version} />
      <BackToSiteSetup />
    </div>
  );
};

export default ActivityDashboard;
