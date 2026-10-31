/**
 * Keeps muted background videos playing on phones. iPhones refuse autoplay in Low Power Mode, and stop videos when
 * the app is switched away or the connection stalls, leaving a system play button on screen. Videos marked
 * data-autoplay are restarted when that happens, and on the next tap if the phone insists on a gesture.
 */

/** Use as a video's ref. React doesn't write the muted attribute, which iPhones look for before allowing autoplay. */
export function startVideo(video: HTMLVideoElement | null) {
  if (!video) return;
  video.muted = true;
  video.defaultMuted = true;
  video.setAttribute("muted", "");
  video.setAttribute("playsinline", "");
  video.play().catch(() => { /* blocked for now: the first tap retries */ });
}

function shouldPlay(video: HTMLVideoElement) {
  if (!video.hasAttribute("data-autoplay") || document.visibilityState !== "visible") return false;
  const r = video.getBoundingClientRect();
  return r.width > 0 && r.bottom > 0 && r.top < window.innerHeight;
}

function resumeAll() {
  document.querySelectorAll("video").forEach((v) => {
    if (v.paused && shouldPlay(v)) startVideo(v);
  });
}

export function keepVideosPlaying() {
  for (const gesture of ["touchend", "click"]) document.addEventListener(gesture, resumeAll, { passive: true });
  document.addEventListener("visibilitychange", resumeAll);
  window.addEventListener("pageshow", resumeAll);
  // media events don't bubble, so these listen in the capture phase
  document.addEventListener("pause", (e) => {
    const v = e.target as HTMLVideoElement;
    if (shouldPlay(v) && !v.ended) window.setTimeout(() => v.paused && shouldPlay(v) && startVideo(v), 300);
  }, true);
  document.addEventListener("stalled", (e) => {
    const v = e.target as HTMLVideoElement;
    if (shouldPlay(v)) window.setTimeout(() => startVideo(v), 1500);
  }, true);
}
