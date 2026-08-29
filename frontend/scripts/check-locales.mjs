// Every catalogue must carry the same keys as English, with the same
// placeholders. A missing key falls back silently, a lost placeholder
// swallows a value — neither shows up until someone reports it.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

// Not URL.pathname: that keeps the percent encoding and breaks on a path
// with a space in it.
const dir = fileURLToPath(new URL("../src/locales/", import.meta.url));

function parse(file) {
  const source = readFileSync(join(dir, file), "utf8");
  const entries = [...source.matchAll(/^ {2}"([^"]+)":\s*("(?:[^"\\]|\\.)*"),$/gm)];
  return new Map(entries.map(([, key, value]) => [key, JSON.parse(value)]));
}

const placeholders = (text) =>
  [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(",");

const en = parse("en.ts");
let failed = false;

for (const file of readdirSync(dir).filter((f) => f.endsWith(".ts") && f !== "en.ts")) {
  const other = parse(file);
  for (const key of en.keys()) {
    if (!other.has(key)) {
      console.error(`${file}: missing ${key}`);
      failed = true;
    } else if (placeholders(other.get(key)) !== placeholders(en.get(key))) {
      console.error(`${file}: placeholders differ in ${key}`);
      failed = true;
    }
  }
  for (const key of other.keys()) {
    if (!en.has(key)) {
      console.error(`${file}: unknown key ${key}`);
      failed = true;
    }
  }
  for (const [key, value] of other) {
    if (!value.trim()) {
      console.error(`${file}: empty value for ${key}`);
      failed = true;
    }
  }
}

if (failed) process.exit(1);
console.log(`${en.size} keys, every catalogue matches.`);
