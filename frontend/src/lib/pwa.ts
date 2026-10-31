/** Installable web app support: the service worker and the browser's install prompt. */

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferred: InstallPromptEvent | null = null;
const CHANGED = "livetrip-install-changed";

export function setUpPwa() {
  // the browser fires this once, early, whenever the app can be installed: keep it for the Install button
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferred = e as InstallPromptEvent;
    window.dispatchEvent(new Event(CHANGED));
  });
  window.addEventListener("appinstalled", () => {
    deferred = null;
    window.dispatchEvent(new Event(CHANGED));
  });
  // production only: a service worker would get in the way of Vite's live reload while developing
  if (import.meta.env.PROD && "serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js").catch(() => { /* the site works fine without it */ });
    });
  }
}

export const isInstalled = () =>
  window.matchMedia?.("(display-mode: standalone)").matches || (navigator as { standalone?: boolean }).standalone === true;

/** iPhones and iPads have no install prompt: people add the app from Safari's Share menu. */
export const isIos = () =>
  /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

export const canPromptInstall = () => deferred !== null;

export function onInstallChange(listener: () => void) {
  window.addEventListener(CHANGED, listener);
  return () => window.removeEventListener(CHANGED, listener);
}

export async function promptInstall() {
  if (!deferred) return;
  const event = deferred;
  deferred = null;  // a prompt can only be used once
  window.dispatchEvent(new Event(CHANGED));
  await event.prompt();
  await event.userChoice;
}
