// Pure logic and HTML rendering for the screen time report (the popup opened from the card). No DOM access, so it's
// unit-tested with node --test. Everything from Qustodio (app names, websites) goes through escapeHtml.

// Load the card's logic with this file's own ?v= version, so the two always come from the same release
const {
  USED_COLOR,
  colorOf,
  escapeHtml,
  hourName,
  localTime,
  renderCard,
  routineColors,
  stripLayout,
  ticks,
  tint,
  wholeMinutes,
} = await import(new URL("./card-logic.js" + new URL(import.meta.url).search, import.meta.url));

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

// ---- Hourly chart and ranked usage -----------------------------------------------------------------------------

/** One column per hour with usage (height = share of the hour used), on the same time axis and bands as the card. */
export function hourlyChart(report, tz) {
  const layout = stripLayout(report, tz);
  const columns = (report.hours ?? []).map((hour, i) => {
    const minutes = round1((hour.default_minutes ?? 0) + sum(Object.values(hour.routines ?? {})));
    const { leftPct, widthPct } = layout.bars[i];
    const local = localTime(hour.start, tz).hour;
    return {
      hour: local,
      minutes,
      leftPct,
      widthPct,
      heightPct: Math.min(100, (minutes / 60) * 100),
      label: `${hourName(local)} · ${wholeMinutes(minutes)} min`,
    };
  });
  return {
    startHour: layout.startHour,
    endHour: layout.endHour,
    bands: { windows: layout.windows, defaultWindows: layout.defaultWindows },
    columns,
  };
}

/** Apps and websites in one list, largest first (then by name), without zero-minute items. */
export function rankedUsage(report) {
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
    .sort(
      (a, b) =>
        b.minutes - a.minutes || String(a.name ?? "").localeCompare(String(b.name ?? ""), undefined, { sensitivity: "base" }),
    );
  const largest = items.length ? items[0].minutes : 0;
  return items.map((item) => ({ ...item, sharePct: (item.minutes / largest) * 100 }));
}

// ---- Rendering -------------------------------------------------------------------------------------------------

function hourlyHtml(report, tz, dark) {
  const chart = hourlyChart(report, tz);
  const colors = routineColors(report.routines ?? [], dark, report.all_routines ?? report.routines ?? []);
  const band = (w, color) =>
    `<div class="band" style="left:${w.leftPct}%;width:${w.widthPct}%;background:${tint(color)}"></div>`;
  const bands = [
    ...chart.bands.defaultWindows.map((w) => band(w, USED_COLOR(dark))),
    ...chart.bands.windows.map((w) => band(w, colorOf(colors, w.uid, dark))),
  ].join("");
  const gridlines = [50, 100].map((pct) => `<div class="gridline" style="bottom:${pct}%"></div>`).join("");
  const columns = chart.columns
    .map(
      (c) =>
        `<div class="column" style="left:${c.leftPct}%;width:${c.widthPct}%" title="${escapeHtml(c.label)}">` +
        `<div class="fill" style="height:${round2(c.heightPct)}%;background:${USED_COLOR(dark)}"></div></div>`,
    )
    .join("");
  return `<div class="hourly"><div class="plot">${bands}${gridlines}${columns}</div>${ticks(chart)}</div>`;
}

function rankedHtml(report, showAll) {
  const items = rankedUsage(report);
  const shown = showAll ? items : items.slice(0, TOP_ITEMS);
  const rows = shown
    .map(
      (item) =>
        `<div class="item"><span class="name">${escapeHtml(item.name)}</span>` +
        `<span class="detail">${escapeHtml(item.detail)}</span>` +
        `<span class="minutes">${wholeMinutes(item.minutes)} min</span>` +
        `<span class="share" style="width:${round2(item.sharePct)}%"></span></div>`,
    )
    .join("");
  const toggle =
    items.length > TOP_ITEMS
      ? `<button class="show-all" data-action="toggle-all">${showAll ? "Show fewer" : `Show all ${items.length}`}</button>`
      : "";
  const empty = items.length ? "" : `<p class="note">No apps or websites recorded.</p>`;
  return `<div class="ranked"><h3>Apps and websites</h3>${rows}${empty}${toggle}</div>`;
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
  const rows = hourlyChart(report, tz)
    .columns.map((c) => `<tr><td>${hourName(c.hour)}</td><td>${wholeMinutes(c.minutes)}</td></tr>`)
    .join("");
  return (
    `<details class="table"><summary>Hourly numbers</summary>` +
    `<table><tr><th>Hour</th><th>Minutes used</th></tr>${rows}</table></details>`
  );
}

/** Inner HTML of the report popup for one day: the card's summary, the hourly chart, apps and websites, notes, table. */
export function renderReport(report, { name, tz, dark, today, showAll }) {
  const summary = renderCard(report, { name, tz, dark });
  if (!(report.hours ?? []).length) return `${summary}${notesHtml(report, today)}`;
  return `${summary}${hourlyHtml(report, tz, dark)}${rankedHtml(report, showAll)}${notesHtml(report, today)}${tableHtml(report, tz)}`;
}
