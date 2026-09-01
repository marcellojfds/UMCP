import { cp, mkdir, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(__dirname, "..");
const dist = resolve(webRoot, "dist");

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });
await cp(resolve(webRoot, "index.html"), resolve(dist, "index.html"));
await cp(resolve(webRoot, "src"), resolve(dist, "src"), { recursive: true });
console.log("web build complete: " + dist);
