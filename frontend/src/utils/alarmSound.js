// Web Audio API harmonic chime synthesizer
// Generates a pleasant, rich acoustic study bell chime without external audio files

let audioCtx = null;
let currentAlarmInterval = null;

function getAudioContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

/**
 * Plays a single multi-frequency harmonic bell chime
 */
export function playChimeNote(freq = 587.33, duration = 1.2, gainLevel = 0.25) {
  const ctx = getAudioContext();
  if (!ctx) return;

  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  // Sine wave for smooth bell chime
  osc.type = "sine";
  osc.frequency.setValueAtTime(freq, now);

  // Attack and decay envelope
  gain.gain.setValueAtTime(0.001, now);
  gain.gain.linearRampToValueAtTime(gainLevel, now + 0.04);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.start(now);
  osc.stop(now + duration);
}

/**
 * Plays a complete multi-tone ascending alert sequence (D5 -> F#5 -> A5 -> D6)
 */
export function playStudyAlertSequence() {
  const notes = [
    { freq: 587.33, delay: 0 },    // D5
    { freq: 739.99, delay: 180 },  // F#5
    { freq: 880.00, delay: 360 },  // A5
    { freq: 1174.66, delay: 560 }, // D6
  ];

  notes.forEach(({ freq, delay }) => {
    setTimeout(() => {
      playChimeNote(freq, 1.4, 0.28);
    }, delay);
  });
}

/**
 * Starts continuous repeating study alarm (rings every 4 seconds until stopped)
 */
export function startContinuousAlarm() {
  stopContinuousAlarm();
  playStudyAlertSequence();
  currentAlarmInterval = setInterval(() => {
    playStudyAlertSequence();
  }, 4000);
}

/**
 * Stops continuous repeating study alarm
 */
export function stopContinuousAlarm() {
  if (currentAlarmInterval) {
    clearInterval(currentAlarmInterval);
    currentAlarmInterval = null;
  }
}
