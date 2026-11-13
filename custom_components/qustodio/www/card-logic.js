// Pure logic and HTML rendering for the screen time card. No DOM access, so it's unit-tested with node --test.
// Everything from Qustodio (routine and profile names) goes through escapeHtml before reaching markup.

// Categorical palette (validated light/dark steps). Slot 1 is default-rules time; routines take slots 2-8.
const PALETTE = {
  light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
  dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
};
const OTHER = { light: "#a3a29b", dark: "#6b6a64" };
const DEFAULT_START_HOUR = 6;
const DEFAULT_END_HOUR = 22;

export const NORMAL_COLOR = (dark) => PALETTE[dark ? "dark" : "light"][0];
export const OTHER_COLOR = (dark) => OTHER[dark ? "dark" : "light"];

const round1 = (n) => Math.round(n * 10) / 10;
const round2 = (n) => Math.round(n * 100) / 100;
// Minutes as shown on the card: whole minutes, rounded up (the maths underneath keeps decimals)
const wholeMinutes = (n) => Math.ceil(round1(n));

/** Escape text for safe insertion into HTML. */
export function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

/** Per hour: total, counted (normal + routines that count; unknown routines count), and the split. */
export function countedByHour(report) {
  const counts = Object.fromEntries((report.routines ?? []).map((r) => [r.uid, r.counts]));
  return (report.hours ?? []).map((hour) => {
    const byRoutine = { ...(hour.routines ?? {}) };
    const routineTotal = Object.values(byRoutine).reduce((a, b) => a + b, 0);
    const countedRoutines = Object.entries(byRoutine)
      .filter(([uid]) => counts[uid] !== false)
      .reduce((a, [, minutes]) => a + minutes, 0);
    const normal = hour.default_minutes ?? 0;
    return {
      start: hour.start,
      normal,
      byRoutine,
      total: round1(normal + routineTotal),
      counted: round1(normal + countedRoutines),
    };
  });
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
    (routines ?? []).map((r) => [
      r.uid,
      { color: (!r.removed && slotByName[r.name ?? ""]) || OTHER_COLOR(dark), hatched: r.counts === false },
    ]),
  );
}

/** Local {hour, minute} of an ISO timestamp in a time zone. */
function localTime(iso, tz) {
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

/** The parts of the strip (0-100%) not covered by any routine window: when the default rules apply. */
function gaps(windows) {
  const covered = windows
    .map((w) => [w.leftPct, w.leftPct + w.widthPct])
    .sort((a, b) => a[0] - b[0]);
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
  const bars = hours.map((hour) => {
    const local = localTime(hour.start, tz).hour;
    const segments = [{ uid: null, minutes: hour.default_minutes ?? 0 }];
    for (const [uid, minutes] of Object.entries(hour.routines ?? {})) segments.push({ uid, minutes });
    const used = segments.reduce((a, s) => a + s.minutes, 0);
    const widthPct = 100 / span;
    return {
      hour: local,
      leftPct: pct(local),
      widthPct,
      // The share of the hour that was used, as a width: 30 minutes fills half the hour
      usedWidthPct: widthPct * Math.min(1, used / 60),
      segments: segments.filter((s) => s.minutes > 0),
    };
  });
  return { startHour, endHour, windows, defaultWindows: gaps(windows), bars };
}

/** Short local hour label, e.g. "4pm". */
function hourLabel(iso, tz) {
  const { hour } = localTime(iso, tz);
  return `${hour % 12 || 12}${hour < 12 ? "am" : "pm"}`;
}

function fill(colors, uid, dark) {
  const entry = uid === null ? { color: NORMAL_COLOR(dark), hatched: false } : colors[uid] ?? { color: OTHER_COLOR(dark) };
  return entry.hatched
    ? `repeating-linear-gradient(45deg, ${entry.color} 0 3px, transparent 3px 6px)`
    : entry.color;
}

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
  const tail = over ? `<div class="over">${wholeMinutes(over)} min over${reached ? ` · limit hit ~${hourLabel(reached, tz)}` : ""}</div>` : "";
  return `<div class="headline">${main}</div>${tail}`;
}

/** The faint version of a colour used for rules (routine windows, default rules) on the bar and in the legend. */
const tint = (color) => `color-mix(in srgb, ${color} 18%, transparent)`;
const swatch = (background) => `<span class="swatch" style="background:${background}"></span>`;

/**
 * Legend in two rows, mirroring the bar. Row 1: the screen time used, with solid swatches ("Screen time used"
 * for default-rules time, then each routine with time). Row 2: the rules, with tinted swatches (the default rules and every routine with
 * time or a scheduled window today), so each shaded band on the bar has a label.
 */
function chips(report, colors, dark, layout) {
  const normal = round1(countedByHour(report).reduce((a, h) => a + h.normal, 0));
  const scheduled = (report.routines ?? []).filter((r) => r.minutes || (r.windows ?? []).length);
  const colorOf = (routine) => (colors[routine.uid] ?? {}).color ?? OTHER_COLOR(dark);

  const used = [];
  if (normal > 0) {
    used.push(`<span class="chip">${swatch(NORMAL_COLOR(dark))}Screen time used · ${wholeMinutes(normal)} min</span>`);
  }
  for (const routine of scheduled.filter((r) => r.minutes)) {
    const note = routine.counts === false ? ` <span class="note">not counted</span>` : "";
    used.push(
      `<span class="chip">${swatch(fill(colors, routine.uid, dark))}${escapeHtml(routine.name)} · ${wholeMinutes(routine.minutes)} min${note}</span>`,
    );
  }

  const rules = [];
  if (normal > 0 || layout.defaultWindows.length) {
    rules.push(`<span class="chip">${swatch(tint(NORMAL_COLOR(dark)))}Default rules</span>`);
  }
  for (const routine of scheduled) {
    rules.push(`<span class="chip">${swatch(tint(colorOf(routine)))}${escapeHtml(routine.name)}</span>`);
  }
  return `<div class="chips used">${used.join("")}</div><div class="chips rules">${rules.join("")}</div>`;
}

function strip(report, colors, tz, dark) {
  const layout = stripLayout(report, tz);
  const defaults = layout.defaultWindows
    .map((w) => `<div class="window default" style="left:${w.leftPct}%;width:${w.widthPct}%;background:${NORMAL_COLOR(dark)}"></div>`)
    .join("");
  const windows = layout.windows
    .map(
      (w) =>
        `<div class="window" style="left:${w.leftPct}%;width:${w.widthPct}%;background:${(colors[w.uid] ?? {}).color ?? OTHER_COLOR(dark)}"></div>`,
    )
    .join("");
  // Usage overlaid on the routine windows: each hour fills the share of it that was used, split by routine
  const blocks = layout.bars
    .map((bar) => {
      const segments = bar.segments
        .map((s) => `<div class="seg" style="flex:${s.minutes} 1 0;background:${fill(colors, s.uid, dark)}"></div>`)
        .join("");
      return `<div class="block" style="left:${bar.leftPct}%;width:${round2(bar.usedWidthPct)}%">${segments}</div>`;
    })
    .join("");
  const ticks = [];
  for (let h = layout.startHour; h <= layout.endHour; h += 4) {
    const label = `${h % 12 || 12}${h < 12 || h === 24 ? "am" : "pm"}`;
    ticks.push(`<span style="left:${((h - layout.startHour) / (layout.endHour - layout.startHour)) * 100}%">${label}</span>`);
  }
  return `<div class="strip">${defaults}${windows}<div class="use">${blocks}</div></div><div class="ticks">${ticks.join("")}</div>`;
}

/** Inner HTML of the card face for one day's report. */
export function renderCard(report, { name, tz, dark }) {
  const title = `<div class="title">${escapeHtml(name)}</div>`;
  if (!(report.hours ?? []).length) {
    return `${title}<div class="empty">No screen time yet today</div>`;
  }
  const colors = routineColors(report.routines ?? [], dark, report.all_routines ?? report.routines ?? []);
  return `${title}${headline(report, tz)}${chips(report, colors, dark, stripLayout(report, tz))}${strip(report, colors, tz, dark)}`;
}

/** Message for a day_report error code. */
export function errorText(code) {
  if (code === "unauthorized") return "Only admins can view this report";
  if (code === "not_found") return "This sensor isn't a child's screen time sensor";
  return "Couldn't load today's screen time";
}
