// Pure logic and HTML rendering for the screen time card. No DOM access, so it's unit-tested with node --test.
// Everything from Qustodio (routine and profile names) goes through escapeHtml before reaching markup.

// Categorical palette (validated light/dark steps). Slot 1 is the screen-time-used colour (also tinted for the
// default rules); routines take slots 2-8.
const PALETTE = {
  light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
  dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
};
const OTHER = { light: "#a3a29b", dark: "#6b6a64" };
const DEFAULT_START_HOUR = 6;
const DEFAULT_END_HOUR = 22;
const TICK_EVERY_HOURS = 4;

/** Colour of screen time used (the blocks on the bar); its tint marks when the default rules apply. */
export const USED_COLOR = (dark) => PALETTE[dark ? "dark" : "light"][0];
/** Shared colour for routines beyond the palette, and for removed routines. */
export const OTHER_COLOR = (dark) => OTHER[dark ? "dark" : "light"];

const round1 = (n) => Math.round(n * 10) / 10;
const round2 = (n) => Math.round(n * 100) / 100;
// Minutes as shown on the card: whole minutes, rounded up (the maths underneath keeps decimals)
export const wholeMinutes = (n) => Math.ceil(round1(n));
const sum = (values) => values.reduce((a, b) => a + b, 0);

/** Escape text for safe insertion into HTML. */
export function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// ---- Day maths -------------------------------------------------------------------------------------------------

/** Per hour: total minutes used, and counted minutes (default rules + routines that count; unknown routines count). */
export function countedByHour(report) {
  const counts = Object.fromEntries((report.routines ?? []).map((r) => [r.uid, r.counts]));
  return (report.hours ?? []).map((hour) => {
    const routines = Object.entries(hour.routines ?? {});
    const defaultRules = hour.default_minutes ?? 0;
    return {
      start: hour.start,
      total: round1(defaultRules + sum(routines.map(([, minutes]) => minutes))),
      counted: round1(
        defaultRules + sum(routines.filter(([uid]) => counts[uid] !== false).map(([, minutes]) => minutes)),
      ),
    };
  });
}

/** Minutes used under the default rules (no routine active) across the day. */
function defaultRulesMinutes(report) {
  return round1(sum((report.hours ?? []).map((hour) => hour.default_minutes ?? 0)));
}

/** The day's limit in minutes (quota plus extra time), or null when there's no limit. */
export function limitMinutes(report) {
  if (report.quota_minutes === null || report.quota_minutes === undefined) return null;
  return report.quota_minutes + (report.extra_time_minutes ?? 0);
}

/** Minutes counted beyond the limit (0 if within it), or null when there's no limit. */
export function minutesOver(report) {
  const limit = limitMinutes(report);
  if (limit === null) return null;
  return round1(Math.max(0, (report.counted_minutes ?? 0) - limit));
}

/** Start of the hour in which cumulative counted time reached the limit, or null. */
export function limitReachedAt(report) {
  const limit = limitMinutes(report);
  if (limit === null) return null;
  let cumulative = 0;
  for (const hour of countedByHour(report)) {
    if (hour.counted <= 0) continue;
    cumulative += hour.counted;
    if (cumulative >= limit) return hour.start;
  }
  return null;
}

/** Whole-minute shares of values that add up to target (largest remainder; exact whole numbers stay as they are). */
function apportion(values, target) {
  const result = values.map((v) => Math.floor(v + 1e-9));
  let remainder = target - sum(result);
  const byFraction = values.map((v, i) => [v - result[i], i]).sort((a, b) => b[0] - a[0] || a[1] - b[1]);
  for (const [fraction, i] of byFraction) {
    if (remainder <= 0 || fraction <= 1e-9) break;
    result[i] += 1;
    remainder -= 1;
  }
  return result;
}

// ---- Colours ---------------------------------------------------------------------------------------------------

/**
 * Colour per routine uid: distinct slots by name, then a shared "other" grey.
 * Slots are assigned over allRoutines (every routine the profile has), so a routine keeps its colour on days
 * when others are missing from the report.
 */
export function routineColors(routines, dark, allRoutines = routines) {
  const palette = PALETTE[dark ? "dark" : "light"];
  const named = (allRoutines ?? [])
    .filter((r) => !r.removed)
    .map((r) => r.name ?? "")
    .filter((name, i, all) => all.indexOf(name) === i)
    .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
  const slotByName = Object.fromEntries(named.map((name, i) => [name, i < palette.length - 1 ? palette[i + 1] : null]));
  return Object.fromEntries(
    (routines ?? []).map((r) => [r.uid, (!r.removed && slotByName[r.name ?? ""]) || OTHER_COLOR(dark)]),
  );
}

/** A routine's colour, or the "other" grey for one the colour map doesn't know. */
export const colorOf = (colors, uid, dark) => colors[uid] ?? OTHER_COLOR(dark);

/** The faint version of a colour used for rules (routine windows, default rules) on the bar and in the legend. */
export const tint = (color) => `color-mix(in srgb, ${color} 18%, transparent)`;

// ---- Time of day -----------------------------------------------------------------------------------------------

/** Local {hour, minute} of an ISO timestamp in a time zone. */
export function localTime(iso, tz) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: tz,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(iso));
  const get = (type) => Number(parts.find((p) => p.type === type).value);
  return { hour: get("hour"), minute: get("minute") };
}

/** Local fractional hour; an end at local midnight counts as 24. */
function localHour(iso, tz, isEnd = false) {
  const { hour, minute } = localTime(iso, tz);
  const value = hour + minute / 60;
  return isEnd && value === 0 ? 24 : value;
}

/** Short label for an hour of the day (0-24), e.g. "4pm"; 0 and 24 are "12am". */
export function hourName(hour) {
  const h = hour % 24;
  return `${h % 12 || 12}${h < 12 ? "am" : "pm"}`;
}

// ---- Bar layout ------------------------------------------------------------------------------------------------

/** The parts of the strip (0-100%) not covered by any routine window: when the default rules apply. */
function gaps(windows) {
  const covered = windows.map((w) => [w.leftPct, w.leftPct + w.widthPct]).sort((a, b) => a[0] - b[0]);
  const result = [];
  let cursor = 0;
  for (const [from, to] of covered) {
    if (from - cursor > 1e-9) result.push({ leftPct: cursor, widthPct: from - cursor });
    cursor = Math.max(cursor, to);
  }
  if (100 - cursor > 1e-9) result.push({ leftPct: cursor, widthPct: 100 - cursor });
  return result;
}

/** Positions (as % of the strip) of routine windows, default-rules time and hourly usage between startHour and endHour. */
export function stripLayout(report, tz) {
  const hours = report.hours ?? [];
  const usageHours = hours.map((h) => localTime(h.start, tz).hour);
  const startHour = Math.min(DEFAULT_START_HOUR, ...usageHours);
  const endHour = Math.max(DEFAULT_END_HOUR, ...usageHours.map((h) => h + 1));
  const span = endHour - startHour;
  const pct = (hour) => ((hour - startHour) / span) * 100;

  const windows = [];
  for (const routine of report.routines ?? []) {
    for (const window of routine.windows ?? []) {
      const from = Math.max(localHour(window.start, tz), startHour);
      const to = Math.min(localHour(window.end, tz, true), endHour);
      if (to > from) windows.push({ uid: routine.uid, leftPct: pct(from), widthPct: pct(to) - pct(from) });
    }
  }
  const bars = hours.map((hour, i) => {
    const used = (hour.default_minutes ?? 0) + sum(Object.values(hour.routines ?? {}));
    const widthPct = 100 / span;
    return {
      hour: usageHours[i],
      leftPct: pct(usageHours[i]),
      widthPct,
      // The share of the hour that was used, as a width: 30 minutes fills half the hour
      usedWidthPct: widthPct * Math.min(1, used / 60),
    };
  });
  return { startHour, endHour, windows, defaultWindows: gaps(windows), bars };
}

/** Today's date (YYYY-MM-DD) in a time zone. */
export function localDate(tz) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(
    new Date(Date.now()),
  );
}

/** Styles for the card face (renderCard output), shared by the card and the report popup. */
export const CARD_STYLE = `
  .title { font-weight: 500; font-size: 16px; margin-bottom: 4px; }
  .headline .big { font-size: 28px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .headline .unit { color: var(--secondary-text-color); }
  .counted { font-size: 12px; color: var(--secondary-text-color); margin-top: -2px; }
  .over { color: var(--primary-text-color); font-size: 13px; margin-top: 2px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px 12px; margin: 10px 0; font-size: 13px; }
  .chip { display: inline-flex; align-items: center; gap: 6px; color: var(--primary-text-color); }
  .swatch { width: 10px; height: 10px; border-radius: 2px; display: inline-block; outline: 1px solid var(--divider-color); }
  .note { color: var(--secondary-text-color); font-size: 12px; }
  .strip { position: relative; height: 28px; border-radius: 4px; background: var(--secondary-background-color); overflow: hidden; }
  .window { position: absolute; top: 0; bottom: 0; opacity: 0.18; }
  .use { position: absolute; inset: 0; }
  .block { position: absolute; top: 0; bottom: 0; display: flex; }
  .chips.rules { margin: 14px 0 0; color: var(--secondary-text-color); }
  .ticks { position: relative; height: 16px; font-size: 11px; color: var(--secondary-text-color); }
  .ticks span { position: absolute; transform: translateX(-50%); }
  .ticks span:first-child { transform: none; }
  .ticks span:last-child { transform: translateX(-100%); }
  .empty, .message { color: var(--secondary-text-color); margin-top: 8px; }
`;

// ---- Rendering -------------------------------------------------------------------------------------------------

const swatch = (background) => `<span class="swatch" style="background:${background}"></span>`;

function headline(report, tz) {
  const counted = report.counted_minutes ?? 0;
  const limit = limitMinutes(report);
  let main;
  if (limit === null) {
    main = `<span class="big">${wholeMinutes(counted)} min</span> <span class="unit">no limit</span>`;
  } else {
    // Share of the limit used, from the unrounded minutes; none for a limit of 0
    const percent = limit > 0 ? ` <span class="unit">${Math.round((counted / limit) * 100)}%</span>` : "";
    main = `<span class="big">${wholeMinutes(counted)} / ${wholeMinutes(limit)} min</span>${percent}`;
  }
  const over = minutesOver(report);
  const reached = limitReachedAt(report);
  const hit = reached ? ` · limit hit ~${hourName(localTime(reached, tz).hour)}` : "";
  const tail = over ? `<div class="over">${wholeMinutes(over)} min over${hit}</div>` : "";
  const note = limit === null ? "" : `<div class="counted">counted toward limit</div>`;
  return `<div class="headline">${main}</div>${note}${tail}`;
}

/**
 * Legend in two parts, mirroring the bar. Above the bar: the total screen time used (solid, the colour of the blocks).
 * Below the bar: the rules (tinted, the colour of the bands): the default rules and every routine with time or a scheduled
 * window today, each with the minutes used under it, apportioned so the rows add up to the total shown.
 */
function legend(report, layout, colors, dark) {
  const total = wholeMinutes(report.total_minutes ?? 0);
  const used = `<span class="chip">${swatch(USED_COLOR(dark))}Screen time used · ${total} min</span>`;

  const defaultRules = defaultRulesMinutes(report);
  const withTime = (report.routines ?? []).filter((r) => r.minutes);
  const [defaultShare, ...routineShares] = apportion([defaultRules, ...withTime.map((r) => r.minutes)], total);
  const shareOf = new Map(withTime.map((r, i) => [r.uid, routineShares[i]]));

  const rules = [];
  if (defaultRules > 0 || layout.defaultWindows.length) {
    const minutes = defaultRules > 0 ? ` · ${defaultShare} min` : "";
    rules.push(`<span class="chip">${swatch(tint(USED_COLOR(dark)))}Default rules${minutes}</span>`);
  }
  for (const routine of report.routines ?? []) {
    if (!routine.minutes && !(routine.windows ?? []).length) continue;
    const minutes = routine.minutes ? ` · ${shareOf.get(routine.uid)} min` : "";
    const note = routine.minutes && routine.counts === false ? ` <span class="note">not counted</span>` : "";
    const color = tint(colorOf(colors, routine.uid, dark));
    rules.push(`<span class="chip">${swatch(color)}${escapeHtml(routine.name)}${minutes}${note}</span>`);
  }
  return { used: `<div class="chips used">${used}</div>`, rules: `<div class="chips rules">${rules.join("")}</div>` };
}

function strip(layout, colors, dark) {
  const band = (w, color, cls = "window") =>
    `<div class="${cls}" style="left:${w.leftPct}%;width:${w.widthPct}%;background:${color}"></div>`;
  const defaults = layout.defaultWindows.map((w) => band(w, USED_COLOR(dark), "window default")).join("");
  const windows = layout.windows.map((w) => band(w, colorOf(colors, w.uid, dark))).join("");
  // Usage overlaid on the rule bands, always one colour: each hour fills the share of it that was used
  const blocks = layout.bars
    .map(
      (bar) =>
        `<div class="block" style="left:${bar.leftPct}%;width:${round2(bar.usedWidthPct)}%;background:${USED_COLOR(dark)}"></div>`,
    )
    .join("");
  return `<div class="strip">${defaults}${windows}<div class="use">${blocks}</div></div>${ticks(layout)}`;
}

/** Hour labels under a bar or chart laid out with stripLayout, every TICK_EVERY_HOURS hours. */
export function ticks(layout) {
  const span = layout.endHour - layout.startHour;
  const marks = [];
  for (let h = layout.startHour; h <= layout.endHour; h += TICK_EVERY_HOURS) {
    marks.push(`<span style="left:${((h - layout.startHour) / span) * 100}%">${hourName(h)}</span>`);
  }
  return `<div class="ticks">${marks.join("")}</div>`;
}

/** Inner HTML of the card face for one day's report. */
export function renderCard(report, { name, tz, dark }) {
  const title = `<div class="title">${escapeHtml(name)}</div>`;
  if (!(report.hours ?? []).length) {
    return `${title}<div class="empty">No screen time yet today</div>`;
  }
  const colors = routineColors(report.routines ?? [], dark, report.all_routines ?? report.routines ?? []);
  const layout = stripLayout(report, tz);
  const { used, rules } = legend(report, layout, colors, dark);
  // Screen time used above the bar, the rules (each routine's swatch) below it
  return `${title}${headline(report, tz)}${used}${strip(layout, colors, dark)}${rules}`;
}

/** Message for a day_report error code. */
export function errorText(code) {
  if (code === "unauthorized") return "Only admins can view this report";
  if (code === "not_found") return "This sensor isn't a child's screen time sensor";
  return "Couldn't load today's screen time";
}
