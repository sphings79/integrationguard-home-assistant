/**
 * Panel translations.
 *
 * English is bundled because it is the fallback for every missing key. The
 * other languages are loaded on demand, so a German installation never ships
 * the Polish catalogue — that matters most for the Lovelace card, which is
 * loaded on every dashboard.
 */

import { en } from "./locales/en";

export type Strings = Record<string, string>;

/** Languages with their own catalogue, beyond the bundled English. */
const LOADERS: Record<string, () => Promise<Strings>> = {
  cs: () => import("./locales/cs").then((m) => m.cs),
  da: () => import("./locales/da").then((m) => m.da),
  de: () => import("./locales/de").then((m) => m.de),
  es: () => import("./locales/es").then((m) => m.es),
  fr: () => import("./locales/fr").then((m) => m.fr),
  it: () => import("./locales/it").then((m) => m.it),
  nl: () => import("./locales/nl").then((m) => m.nl),
  pl: () => import("./locales/pl").then((m) => m.pl),
  pt: () => import("./locales/pt").then((m) => m.pt),
  sv: () => import("./locales/sv").then((m) => m.sv),
};

export const AVAILABLE_LANGUAGES = ["en", ...Object.keys(LOADERS)].sort();

const loaded: Record<string, Strings> = { en };

/** Reduce "de-CH" to "de"; Home Assistant hands out regional codes. */
function base(language: string): string {
  return (language || "en").split("-")[0].toLowerCase();
}

/**
 * Fetch a catalogue, falling back to English when the language is unknown or
 * its chunk cannot be loaded.
 */
export async function loadCatalogue(language: string): Promise<Strings> {
  const code = base(language);
  if (loaded[code]) return loaded[code];

  const loader = LOADERS[code];
  if (!loader) return en;

  try {
    loaded[code] = await loader();
    return loaded[code];
  } catch {
    return en;
  }
}

/** Build a translator over an already loaded catalogue. */
export function localize(
  catalogue: Strings,
): (key: string, vars?: Record<string, string | number>) => string {
  return (key, vars) => {
    let text = catalogue[key] ?? en[key] ?? key;
    if (vars) {
      for (const [name, value] of Object.entries(vars)) {
        text = text.replace(new RegExp(`\\{${name}\\}`, "g"), String(value));
      }
    }
    return text;
  };
}

export type Localizer = ReturnType<typeof localize>;

/** The English translator, usable before a catalogue has been loaded. */
export const fallbackLocalizer: Localizer = localize(en);
