// Copies the pipeline's site data (../data/site, committed) into public/data before every dev run and build,
// so the site is built from exactly the committed results. public/data is git-ignored.
import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(web, "..", "data", "site");
const dst = join(web, "public", "data");
if (!existsSync(join(src, "story.json"))) {
  console.error("data/site/story.json is missing: run `python -m reimagine.run --stage site` first.");
  process.exit(1);
}
rmSync(dst, { recursive: true, force: true });
mkdirSync(dst, { recursive: true });
cpSync(src, dst, { recursive: true });
console.log("copied data/site into web/public/data");
