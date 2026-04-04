/**
 * Utilities for computing store open/closed status from Google Places hours data.
 *
 * Since we don't have per-store timezone data, this module works with the
 * viewer's local time. The trade-off is acceptable: most users search for
 * stores in their own timezone, and we clearly label the status as approximate
 * when timezone data is unavailable.
 */

import type { HoursPeriod } from "./types";

/** Day-of-week constants matching Google Places (0 = Sunday). */
const DAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
] as const;

const MAX_PERIODS = 14;
const MAX_WEEKDAY_LINES = 7;

export interface StoreHoursStatus {
  /** Whether the store is currently open. */
  isOpen: boolean;
  /** Today's hours display string, e.g. "10:00 AM - 9:00 PM" or "Closed". */
  todayHours: string | null;
  /** If closed, the next opening time display string, e.g. "Opens Monday at 10:00 AM". */
  nextOpen: string | null;
}

/**
 * Compute open/closed status from structured periods data.
 *
 * Uses the provided Date (defaults to now) to determine the current day/time,
 * then checks if any period covers the current moment.
 */
export function getStoreHoursStatus(
  periods: HoursPeriod[] | null,
  weekdayText: string[] | null,
  now?: Date
): StoreHoursStatus {
  console.assert(
    periods === null || Array.isArray(periods),
    "getStoreHoursStatus: periods must be an array or null"
  );
  console.assert(
    weekdayText === null || Array.isArray(weekdayText),
    "getStoreHoursStatus: weekdayText must be an array or null"
  );

  const currentTime = now ?? new Date();

  // If we have structured periods, use them for precise open/closed check
  if (periods !== null && periods.length > 0) {
    return computeFromPeriods(periods, currentTime);
  }

  // Fall back to parsing weekday_text for today's hours display only
  if (weekdayText !== null && weekdayText.length > 0) {
    return computeFromWeekdayText(weekdayText, currentTime);
  }

  return { isOpen: false, todayHours: null, nextOpen: null };
}

/**
 * Compute status from structured periods (Google Places format).
 * Each period has open/close with day (0-6, Sunday=0), hour (0-23), minute (0-59).
 */
function computeFromPeriods(
  periods: HoursPeriod[],
  now: Date
): StoreHoursStatus {
  console.assert(periods.length > 0, "computeFromPeriods: periods must not be empty");
  console.assert(now instanceof Date, "computeFromPeriods: now must be a Date");

  const currentDay = now.getDay(); // 0 = Sunday
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

  // Find today's hours for display
  const todayHours = findTodayHoursFromPeriods(periods, currentDay);

  // Check if currently within any period
  let isOpen = false;
  const limit = Math.min(periods.length, MAX_PERIODS);
  for (let i = 0; i < limit; i++) {
    const period = periods[i];
    if (isPeriodActive(period, currentDay, currentMinutes)) {
      isOpen = true;
      break;
    }
  }

  // If closed, find next opening time
  let nextOpen: string | null = null;
  if (!isOpen) {
    nextOpen = findNextOpening(periods, currentDay, currentMinutes);
  }

  return { isOpen, todayHours, nextOpen };
}

/**
 * Check if a single period covers the current day/time.
 * Handles same-day periods (open.day === close.day) and overnight periods.
 */
function isPeriodActive(
  period: HoursPeriod,
  currentDay: number,
  currentMinutes: number
): boolean {
  console.assert(
    currentDay >= 0 && currentDay <= 6,
    "isPeriodActive: currentDay must be 0-6"
  );
  console.assert(
    currentMinutes >= 0 && currentMinutes < 1440,
    "isPeriodActive: currentMinutes must be 0-1439"
  );

  const openMinutes = period.open.hour * 60 + period.open.minute;
  const closeMinutes = period.close.hour * 60 + period.close.minute;

  // Same-day period
  if (period.open.day === period.close.day) {
    if (currentDay !== period.open.day) {
      return false;
    }
    return currentMinutes >= openMinutes && currentMinutes < closeMinutes;
  }

  // Overnight period: check if we're in the opening day after open time,
  // or in the closing day before close time.
  // NOTE: This only handles adjacent-day overnight periods (e.g., Fri->Sat).
  // Multi-day spans (e.g., Fri open through Mon close) are not supported --
  // intermediate days would incorrectly show as closed. Google typically
  // represents 24-hour stores as a single period with matching open/close,
  // so this limitation is low-risk in practice.
  if (currentDay === period.open.day && currentMinutes >= openMinutes) {
    return true;
  }
  if (currentDay === period.close.day && currentMinutes < closeMinutes) {
    return true;
  }

  return false;
}

/**
 * Find today's formatted hours string from periods.
 */
function findTodayHoursFromPeriods(
  periods: HoursPeriod[],
  currentDay: number
): string | null {
  console.assert(
    currentDay >= 0 && currentDay <= 6,
    "findTodayHoursFromPeriods: currentDay must be 0-6"
  );
  console.assert(
    periods.length > 0,
    "findTodayHoursFromPeriods: periods must not be empty"
  );

  // Collect all periods that open on the current day
  const todayPeriods: HoursPeriod[] = [];
  const limit = Math.min(periods.length, MAX_PERIODS);
  for (let i = 0; i < limit; i++) {
    if (periods[i].open.day === currentDay) {
      todayPeriods.push(periods[i]);
    }
  }

  if (todayPeriods.length === 0) {
    return "Closed";
  }

  // Format first period (most stores have one period per day)
  const first = todayPeriods[0];
  const openStr = formatTime(first.open.hour, first.open.minute);
  const closeStr = formatTime(first.close.hour, first.close.minute);
  return `${openStr} \u2013 ${closeStr}`;
}

/**
 * Find the next opening time from the current moment.
 * Looks forward up to 7 days.
 */
function findNextOpening(
  periods: HoursPeriod[],
  currentDay: number,
  currentMinutes: number
): string | null {
  console.assert(
    periods.length > 0,
    "findNextOpening: periods must not be empty"
  );
  console.assert(
    currentDay >= 0 && currentDay <= 6,
    "findNextOpening: currentDay must be 0-6"
  );

  // Build a sorted list of openings by distance from now
  let bestLabel: string | null = null;
  let bestDistance = 10080; // 7 days in minutes (upper bound)

  const limit = Math.min(periods.length, MAX_PERIODS);
  for (let i = 0; i < limit; i++) {
    const period = periods[i];
    const openMinutes = period.open.hour * 60 + period.open.minute;

    // Distance in days from current day, then add time-of-day offset
    let dayDiff = period.open.day - currentDay;
    if (dayDiff < 0) {
      dayDiff += 7;
    }
    let totalMinutes = dayDiff * 1440 + (openMinutes - currentMinutes);
    if (totalMinutes <= 0) {
      totalMinutes += 7 * 1440;
    }

    if (totalMinutes < bestDistance) {
      bestDistance = totalMinutes;
      const dayName = DAY_NAMES[period.open.day];
      const timeStr = formatTime(period.open.hour, period.open.minute);
      // If it opens later today, just say the time
      if (period.open.day === currentDay && openMinutes > currentMinutes) {
        bestLabel = `Opens at ${timeStr}`;
      } else {
        bestLabel = `Opens ${dayName} at ${timeStr}`;
      }
    }
  }

  return bestLabel;
}

/**
 * Fall back: parse weekday_text strings for today's hours.
 * Format: "Monday: 10:00 AM \u2013 9:00 PM" or "Sunday: Closed"
 */
function computeFromWeekdayText(
  weekdayText: string[],
  now: Date
): StoreHoursStatus {
  console.assert(weekdayText.length > 0, "computeFromWeekdayText: weekdayText must not be empty");
  console.assert(now instanceof Date, "computeFromWeekdayText: now must be a Date");

  const currentDayName = DAY_NAMES[now.getDay()];
  let todayLine: string | null = null;

  const limit = Math.min(weekdayText.length, MAX_WEEKDAY_LINES);
  for (let i = 0; i < limit; i++) {
    if (weekdayText[i].startsWith(currentDayName)) {
      todayLine = weekdayText[i];
      break;
    }
  }

  if (todayLine === null) {
    return { isOpen: false, todayHours: null, nextOpen: null };
  }

  // Extract the hours portion after "DayName: "
  const colonIdx = todayLine.indexOf(":");
  if (colonIdx === -1) {
    return { isOpen: false, todayHours: null, nextOpen: null };
  }

  const hoursStr = todayLine.substring(colonIdx + 1).trim();

  if (hoursStr.toLowerCase() === "closed") {
    // Find next open day from weekday_text
    const nextOpen = findNextOpenFromWeekdayText(weekdayText, now.getDay());
    return { isOpen: false, todayHours: "Closed", nextOpen };
  }

  // We have hours text but can't reliably determine if currently open
  // without parsing the time range. Parse it for a best-effort check.
  const isOpen = checkTimeInRange(hoursStr, now);

  let nextOpen: string | null = null;
  if (!isOpen) {
    nextOpen = findNextOpenFromWeekdayText(weekdayText, now.getDay());
  }

  return { isOpen, todayHours: hoursStr, nextOpen };
}

/**
 * Best-effort check: is the current time within a "10:00 AM - 9:00 PM" range?
 */
function checkTimeInRange(hoursStr: string, now: Date): boolean {
  console.assert(typeof hoursStr === "string", "checkTimeInRange: hoursStr must be a string");
  console.assert(now instanceof Date, "checkTimeInRange: now must be a Date");

  // Match patterns like "10:00 AM" at start and end of range
  const timePattern = /(\d{1,2}):(\d{2})\s*(AM|PM)/gi;
  const matches: { hour: number; minute: number }[] = [];

  let match = timePattern.exec(hoursStr);
  const maxIter = 4;
  let iter = 0;
  while (match !== null && iter < maxIter) {
    iter++;
    let hour = parseInt(match[1], 10);
    const minute = parseInt(match[2], 10);
    const ampm = match[3].toUpperCase();

    if (ampm === "PM" && hour !== 12) {
      hour += 12;
    }
    if (ampm === "AM" && hour === 12) {
      hour = 0;
    }

    matches.push({ hour, minute });
    match = timePattern.exec(hoursStr);
  }

  if (matches.length < 2) {
    return false;
  }

  const openMinutes = matches[0].hour * 60 + matches[0].minute;
  const closeMinutes = matches[1].hour * 60 + matches[1].minute;
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

  // Handle overnight ranges
  if (closeMinutes <= openMinutes) {
    return currentMinutes >= openMinutes || currentMinutes < closeMinutes;
  }

  return currentMinutes >= openMinutes && currentMinutes < closeMinutes;
}

/**
 * Find the next non-"Closed" day from weekday_text.
 */
function findNextOpenFromWeekdayText(
  weekdayText: string[],
  currentDayIdx: number
): string | null {
  console.assert(
    weekdayText.length > 0,
    "findNextOpenFromWeekdayText: weekdayText must not be empty"
  );
  console.assert(
    currentDayIdx >= 0 && currentDayIdx <= 6,
    "findNextOpenFromWeekdayText: currentDayIdx must be 0-6"
  );

  // Check the next 7 days (starting from tomorrow)
  for (let offset = 1; offset <= 7; offset++) {
    const checkDay = (currentDayIdx + offset) % 7;
    const dayName = DAY_NAMES[checkDay];
    const limit = Math.min(weekdayText.length, MAX_WEEKDAY_LINES);
    for (let i = 0; i < limit; i++) {
      if (weekdayText[i].startsWith(dayName)) {
        const colonIdx = weekdayText[i].indexOf(":");
        if (colonIdx === -1) {
          break;
        }
        const hours = weekdayText[i].substring(colonIdx + 1).trim();
        if (hours.toLowerCase() !== "closed") {
          // Extract opening time
          const timeMatch = /(\d{1,2}:\d{2}\s*(?:AM|PM))/i.exec(hours);
          if (timeMatch !== null) {
            return `Opens ${dayName} at ${timeMatch[1]}`;
          }
          return `Opens ${dayName}`;
        }
        break;
      }
    }
  }

  return null;
}

/**
 * Format an hour/minute pair as "10:00 AM".
 */
function formatTime(hour: number, minute: number): string {
  console.assert(hour >= 0 && hour <= 23, "formatTime: hour must be 0-23");
  console.assert(minute >= 0 && minute <= 59, "formatTime: minute must be 0-59");

  const ampm = hour >= 12 ? "PM" : "AM";
  const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  const displayMinute = minute.toString().padStart(2, "0");
  return `${displayHour}:${displayMinute} ${ampm}`;
}
