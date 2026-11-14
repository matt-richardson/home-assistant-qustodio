// Pure logic and HTML rendering for the screen time report (the popup opened from the card). No DOM access, so it's
// unit-tested with node --test. Everything from Qustodio (app names, websites) goes through escapeHtml.

// Load the card's logic with this file's own ?v= version, so the two always come from the same release
const { escapeHtml, hourName, localTime, renderCard, wholeMinutes } = await import(new URL("./card-logic.js" + new URL(import.meta.url).search, import.meta.url));

const MAX_LOOKBACK_DAYS = 30;
const TOP_ITEMS = 10;
const DAY_MS = 86_400_000;
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const round1 = (n) => Math.round(n * 10) / 10;
const round2 = (n) => Math.round(n * 100) / 100;
const sum = (values) => values.reduce((a, b) => a + b, 0);

// ---- Days ------------------------------------------------------------------------------------------------------

/** A YYYY-MM-DD date as a UTC midnight timestamp, so day arithmetic isn't affected by daylight saving. */
const dayStamp = (date) => Date.parse(`${date}T00:00:00Z`);
const dayString = (stamp) => new Date(stamp).toISOString().slice(0, 10);

/** The date delta days from date, or null if that's after today or more than maxBack days before it. */
export function stepDay(date, delta, today, maxBack = MAX_LOOKBACK_DAYS) {
  const next = dayStamp(date) + delta * DAY_MS;
  if (next > dayStamp(today) || next < dayStamp(today) - maxBack * DAY_MS) return null;
  return dayString(next);
}

/** "Today", "Yesterday", or e.g. "Thu 12 Nov". */
export function dayLabel(date, today) {
  if (date === today) return "Today";
  if (date === stepDay(today, -1, today, Infinity)) return "Yesterday";
  const d = new Date(dayStamp(date));
  return `${WEEKDAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

// ---- Hourly usage and ranked usage -----------------------------------------------------------------------------

/** Minutes used in each hour that has usage, by local hour. */
export function hourlyMinutes(report, tz) {
  return (report.hours ?? []).map((hour) => ({
    hour: localTime(hour.start, tz).hour,
    minutes: round1((hour.default_minutes ?? 0) + sum(Object.values(hour.routines ?? {}))),
  }));
}

const DEFAULT_SORT = { key: "minutes", dir: "desc" };
const byName = (a, b) => String(a.name ?? "").localeCompare(String(b.name ?? ""), undefined, { sensitivity: "base" });
const COMPARE = {
  name: byName,
  detail: (a, b) => a.detail.localeCompare(b.detail, undefined, { sensitivity: "base" }),
  minutes: (a, b) => a.minutes - b.minutes,
};

/**
 * Apps and websites in one list, without zero-minute items, sorted by sort.key ("name", "detail" or "minutes") in
 * sort.dir ("asc" or "desc"); ties go to the most minutes, then the name. sharePct is relative to the largest item.
 */
export function rankedUsage(report, sort = DEFAULT_SORT) {
  const sign = sort.dir === "desc" ? -1 : 1;
  const items = [
    ...(report.apps ?? []).map((a) => ({
      kind: "app",
      name: a.name,
      detail: `App · ${a.platform}`,
      minutes: a.minutes,
    })),
    ...(report.websites ?? []).map((w) => ({ kind: "website", name: w.host, detail: "Website", minutes: w.minutes })),
  ]
    .filter((item) => item.minutes > 0)
    .sort((a, b) => sign * COMPARE[sort.key](a, b) || b.minutes - a.minutes || byName(a, b));
  const largest = Math.max(0, ...items.map((item) => item.minutes));
  return items.map((item) => ({ ...item, sharePct: (item.minutes / largest) * 100 }));
}

/** The sort after clicking a column's header: the same column reverses; a new one starts A to Z, or most minutes. */
export function nextSort(sort, key) {
  if (sort.key === key) return { key, dir: sort.dir === "asc" ? "desc" : "asc" };
  return { key, dir: key === "minutes" ? "desc" : "asc" };
}

// ---- Rendering -------------------------------------------------------------------------------------------------

const COLUMNS = [
  ["name", "Name"],
  ["detail", "Type"],
  ["minutes", "Minutes"],
];

function sortHeader([key, label], sort) {
  const active = sort.key === key;
  const ariaSort = active ? (sort.dir === "asc" ? "ascending" : "descending") : "none";
  const arrow = active ? (sort.dir === "asc" ? " ▲" : " ▼") : "";
  return `<th aria-sort="${ariaSort}"><button class="sort" data-action="sort-${key}">${label}${arrow}</button></th>`;
}

function rankedHtml(report, showAll, sort) {
  const items = rankedUsage(report, sort);
  if (!items.length) return `<div class="ranked"><h3>Apps and websites</h3><p class="note">No apps or websites recorded.</p></div>`;
  const shown = showAll ? items : items.slice(0, TOP_ITEMS);
  const head = `<tr>${COLUMNS.map((column) => sortHeader(column, sort)).join("")}</tr>`;
  const rows = shown
    .map(
      (item) =>
        `<tr class="item"><td class="name">${escapeHtml(item.name)}</td>` +
        `<td class="detail">${escapeHtml(item.detail)}</td>` +
        `<td class="minutes">${wholeMinutes(item.minutes)} min</td></tr>` +
        `<tr class="share-row"><td colspan="3"><span class="share" style="width:${round2(item.sharePct)}%"></span></td></tr>`,
    )
    .join("");
  const toggle =
    items.length > TOP_ITEMS
      ? `<button class="show-all" data-action="toggle-all">${showAll ? "Show fewer" : `Show all ${items.length}`}</button>`
      : "";
  return `<div class="ranked"><h3>Apps and websites</h3><table>${head}${rows}</table>${toggle}</div>`;
}

function notesHtml(report, today) {
  const notes = [];
  if ((report.partial ?? []).length) notes.push("Apps and websites couldn't be loaded for this day.");
  if (report.date && report.date !== today) {
    notes.push("Routines and limits shown are today's settings; extra time isn't included.");
  }
  return notes.map((note) => `<p class="note">${escapeHtml(note)}</p>`).join("");
}

function tableHtml(report, tz) {
  const rows = hourlyMinutes(report, tz)
    .map((c) => `<tr><td>${hourName(c.hour)}</td><td>${wholeMinutes(c.minutes)}</td></tr>`)
    .join("");
  return (
    `<details class="table"><summary>Hourly numbers</summary>` +
    `<table><tr><th>Hour</th><th>Minutes used</th></tr>${rows}</table></details>`
  );
}

/** Inner HTML of the report popup for one day: the card's summary, apps and websites, notes, and an hourly table. */
export function renderReport(report, { name, tz, dark, today, showAll, sort = DEFAULT_SORT }) {
  const summary = renderCard(report, { name, tz, dark });
  if (!(report.hours ?? []).length) return `${summary}${notesHtml(report, today)}`;
  return `${summary}${rankedHtml(report, showAll, sort)}${notesHtml(report, today)}${tableHtml(report, tz)}`;
}
