/**
 * Whole-app translation into the traveller's chosen language, using Google's website translator in the browser
 * (free, no key, ~130 languages, and it also translates live trip data). The page is written in English;
 * place names carry translate="no" so "Paradise" stays a restaurant name.
 *
 * shortcut: machine translation of the rendered page, not hand-written translations; add i18n string files if a
 * language needs reviewed wording.
 */
export const LANGUAGES = [
  { code: "en", name: "English", native: "English", flag: "🇺🇸" },
  { code: "hi", name: "Hindi", native: "हिन्दी", flag: "🇮🇳" },
  { code: "bn", name: "Bengali", native: "বাংলা", flag: "🇮🇳" },
  { code: "te", name: "Telugu", native: "తెలుగు", flag: "🇮🇳" },
  { code: "ta", name: "Tamil", native: "தமிழ்", flag: "🇮🇳" },
  { code: "mr", name: "Marathi", native: "मराठी", flag: "🇮🇳" },
  { code: "gu", name: "Gujarati", native: "ગુજરાતી", flag: "🇮🇳" },
  { code: "kn", name: "Kannada", native: "ಕನ್ನಡ", flag: "🇮🇳" },
  { code: "ml", name: "Malayalam", native: "മലയാളം", flag: "🇮🇳" },
  { code: "pa", name: "Punjabi", native: "ਪੰਜਾਬੀ", flag: "🇮🇳" },
  { code: "ur", name: "Urdu", native: "اردو", flag: "🇵🇰" },
  { code: "es", name: "Spanish", native: "Español", flag: "🇪🇸" },
  { code: "fr", name: "French", native: "Français", flag: "🇫🇷" },
  { code: "de", name: "German", native: "Deutsch", flag: "🇩🇪" },
  { code: "it", name: "Italian", native: "Italiano", flag: "🇮🇹" },
  { code: "pt", name: "Portuguese", native: "Português", flag: "🇵🇹" },
  { code: "ru", name: "Russian", native: "Русский", flag: "🇷🇺" },
  { code: "ja", name: "Japanese", native: "日本語", flag: "🇯🇵" },
  { code: "ko", name: "Korean", native: "한국어", flag: "🇰🇷" },
  { code: "zh-CN", name: "Chinese", native: "中文", flag: "🇨🇳" },
  { code: "ar", name: "Arabic", native: "العربية", flag: "🇸🇦" },
  { code: "th", name: "Thai", native: "ไทย", flag: "🇹🇭" },
  { code: "vi", name: "Vietnamese", native: "Tiếng Việt", flag: "🇻🇳" },
  { code: "id", name: "Indonesian", native: "Bahasa Indonesia", flag: "🇮🇩" },
  { code: "tr", name: "Turkish", native: "Türkçe", flag: "🇹🇷" },
  { code: "nl", name: "Dutch", native: "Nederlands", flag: "🇳🇱" },
  { code: "pl", name: "Polish", native: "Polski", flag: "🇵🇱" },
  { code: "sv", name: "Swedish", native: "Svenska", flag: "🇸🇪" },
  { code: "el", name: "Greek", native: "Ελληνικά", flag: "🇬🇷" },
  { code: "iw", name: "Hebrew", native: "עברית", flag: "🇮🇱" },
];

export const languageName = (code: string) => {
  const l = LANGUAGES.find((x) => x.code === code);
  return l ? `${l.flag} ${l.name}` : code;
};

const KEY = "liveTrip-language";

export function currentLanguage(): string {
  try {
    return localStorage.getItem(KEY) || "en";
  } catch {
    return "en";
  }
}

declare global {
  interface Window {
    google?: { translate?: { TranslateElement: new (opts: object, id: string) => unknown } };
    liveTripTranslateInit?: () => void;
  }
}

let loading: Promise<void> | null = null;

/** Google's translator wraps text in <font> tags; React then fails to remove nodes it no longer owns. */
function guardReactDom() {
  const remove = Node.prototype.removeChild;
  Node.prototype.removeChild = function <T extends Node>(this: Node, child: T): T {
    return child.parentNode === this ? (remove.call(this, child) as T) : child;
  };
  const insert = Node.prototype.insertBefore;
  Node.prototype.insertBefore = function <T extends Node>(this: Node, node: T, ref: Node | null): T {
    return ref && ref.parentNode !== this ? node : (insert.call(this, node, ref) as T);
  };
}

function loadTranslator(): Promise<void> {
  loading ??= new Promise((resolve, reject) => {
    guardReactDom();
    const holder = document.createElement("div");
    holder.id = "google_translate_element";
    holder.hidden = true;
    document.body.appendChild(holder);
    window.liveTripTranslateInit = () => {
      new window.google!.translate!.TranslateElement({ pageLanguage: "en", autoDisplay: false }, holder.id);
      resolve();
    };
    const s = document.createElement("script");
    s.src = "https://translate.google.com/translate_a/element.js?cb=liveTripTranslateInit";
    s.onerror = () => { loading = null; reject(new Error("translator unavailable")); };
    document.body.appendChild(s);
  });
  return loading;
}

function setCookie(code: string) {
  const value = code === "en" ? "" : `/en/${code}`;
  document.cookie = `googtrans=${value}; path=/${value ? "" : "; expires=Thu, 01 Jan 1970 00:00:00 GMT"}`;
}

/** Switch the whole app to `code` (an entry of LANGUAGES) right away and remember it. */
export async function setLanguage(code: string): Promise<void> {
  try { localStorage.setItem(KEY, code); } catch { /* private mode: still switch for this visit */ }
  setCookie(code);
  window.dispatchEvent(new Event("livetrip-language"));
  if (code === "en" && !loading) return;
  await loadTranslator();
  // the widget's hidden <select> appears a moment after init
  for (let i = 0; i < 50; i++) {
    const combo = document.querySelector<HTMLSelectElement>("select.goog-te-combo");
    if (combo && combo.options.length > 1) {
      combo.value = code === "en" ? "en" : code;
      combo.dispatchEvent(new Event("change"));
      return;
    }
    await new Promise((r) => setTimeout(r, 100));
  }
}

/** On start-up: re-apply the remembered language (the cookie makes the widget translate on load). */
export function startTranslation() {
  const code = currentLanguage();
  if (code === "en") return;
  setCookie(code);
  loadTranslator().catch(() => { /* offline: the app stays in English */ });
}

/** The language to show after ticking/unticking in a language list: the newest pick, else what remains. */
export function languageAfterToggle(selection: string[], toggled: string): string {
  return selection.includes(toggled) ? toggled : selection.includes(currentLanguage()) ? currentLanguage() : selection[0] || "en";
}
