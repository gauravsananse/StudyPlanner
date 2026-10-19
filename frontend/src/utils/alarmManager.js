import { startContinuousAlarm, stopContinuousAlarm, playStudyAlertSequence } from "./alarmSound";

/**
 * Parses time strings like "09:00 - 10:30 AM", "06:30 - 08:00 PM", "14:00 - 15:30"
 * Returns { startHours, startMinutes, endHours, endMinutes } or null
 */
export function parseSlotTimes(timeSlotStr) {
  if (!timeSlotStr) return null;

  // Extract the time range portion, e.g. "09:00 - 10:30 AM" from "Morning (09:00 - 10:30 AM)"
  const cleanStr = timeSlotStr.replace(/^[^(]*\(/, "").replace(/\)[^)]*$/, "").trim();
  const parts = cleanStr.split("-").map((p) => p.trim());
  if (parts.length < 1) return null;

  const startPart = parts[0];
  const endPart = parts[1] || parts[0];

  // Determine overall AM/PM if present at the end
  const hasPM = /pm/i.test(cleanStr);
  const hasAM = /am/i.test(cleanStr);

  function parseSingleTime(str, defaultIsPM) {
    const match = str.match(/(\d{1,2}):(\d{2})\s*(am|pm)?/i);
    if (!match) return null;

    let h = parseInt(match[1], 10);
    const m = parseInt(match[2], 10);
    const period = match[3] ? match[3].toLowerCase() : defaultIsPM ? "pm" : null;

    if (period === "pm" && h < 12) h += 12;
    if (period === "am" && h === 12) h = 0;

    return { hours: h, minutes: m };
  }

  const startParsed = parseSingleTime(startPart, /pm/i.test(startPart) || (hasPM && !hasAM && !/am/i.test(startPart)));
  const endParsed = parseSingleTime(endPart, /pm/i.test(endPart) || hasPM);

  if (!startParsed) return null;

  return {
    startHours: startParsed.hours,
    startMinutes: startParsed.minutes,
    endHours: endParsed ? endParsed.hours : startParsed.hours + 1,
    endMinutes: endParsed ? endParsed.minutes : startParsed.minutes,
  };
}

/**
 * Requests browser desktop notification permissions
 */
export async function requestNotificationPermission() {
  if (!("Notification" in window)) {
    return false;
  }
  if (Notification.permission === "granted") {
    return true;
  }
  if (Notification.permission !== "denied") {
    const perm = await Notification.requestPermission();
    return perm === "granted";
  }
  return false;
}

/**
 * Shows desktop system notification
 */
export function showSystemNotification(title, body) {
  if ("Notification" in window && Notification.permission === "granted") {
    try {
      new Notification(title, {
        body,
        icon: "🎓",
        requireInteraction: true,
      });
    } catch (e) {
      console.warn("Notification error:", e);
    }
  }
}

// Session state storage keys
const DISMISSED_SESSIONS_KEY = "study_planner_dismissed_sessions";
const SNOOZED_SESSIONS_KEY = "study_planner_snoozed_sessions";

export function getDismissedSessions() {
  try {
    return JSON.parse(localStorage.getItem(DISMISSED_SESSIONS_KEY) || "{}");
  } catch {
    return {};
  }
}

export function dismissSessionAlarm(sessionId) {
  const dismissed = getDismissedSessions();
  dismissed[sessionId] = Date.now();
  localStorage.setItem(DISMISSED_SESSIONS_KEY, JSON.stringify(dismissed));
}

export function getSnoozedSessions() {
  try {
    return JSON.parse(localStorage.getItem(SNOOZED_SESSIONS_KEY) || "{}");
  } catch {
    return {};
  }
}

export function snoozeSessionAlarm(sessionId, snoozeMinutes = 5) {
  const snoozed = getSnoozedSessions();
  snoozed[sessionId] = Date.now() + snoozeMinutes * 60 * 1000;
  localStorage.setItem(SNOOZED_SESSIONS_KEY, JSON.stringify(snoozed));
}

/**
 * Checks today's sessions and returns the session that should trigger an alarm right now
 */
export function checkForActiveAlarm(todaySessions) {
  if (!todaySessions || todaySessions.length === 0) return null;

  const now = new Date();
  const currentHours = now.getHours();
  const currentMinutes = now.getMinutes();
  const currentTotalMins = currentHours * 60 + currentMinutes;

  const dismissed = getDismissedSessions();
  const snoozed = getSnoozedSessions();

  for (const session of todaySessions) {
    if (session.status === "Completed") continue;

    // Check if snoozed
    if (snoozed[session.id] && Date.now() < snoozed[session.id]) {
      continue;
    }

    // Check if dismissed within the last 4 hours
    if (dismissed[session.id] && Date.now() - dismissed[session.id] < 4 * 3600 * 1000) {
      continue;
    }

    const times = parseSlotTimes(session.time_slot);
    if (!times) continue;

    const slotStartMins = times.startHours * 60 + times.startMinutes;
    const slotEndMins = times.endHours * 60 + times.endMinutes;

    // Trigger if current time is at or within the slot window (e.g. from slot start up to slot end)
    if (currentTotalMins >= slotStartMins && currentTotalMins <= slotEndMins) {
      return session;
    }
  }

  return null;
}
