import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { dirname, extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const defaultRoot = resolve(__dirname, "..", "dist");
const root = resolve(process.env.UMCP_WEB_ROOT || defaultRoot);
const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

const port = Number(process.env.PORT || 4174);
createServer(async (req, res) => {
  const pathname = (req.url || "/").split("?")[0];
  const reqUrl = (pathname === "/" || pathname === "/index.html" || !pathname) ? "index.html" : pathname.replace(/^\//, "");
  const filePath = normalize(join(root, reqUrl));
  if (!filePath.startsWith(root)) {
    res.writeHead(400).end();
    return;
  }
  try {
    const data = await readFile(filePath);
    res.writeHead(200, { "content-type": types[extname(filePath)] || "application/octet-stream" });
    res.end(data);
  } catch {
    res.writeHead(404).end("Not found");
  }
}).listen(port, "127.0.0.1", () => console.log(`UMCP web server ready on http://127.0.0.1:${port}`));
