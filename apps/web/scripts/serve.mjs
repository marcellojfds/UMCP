import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";

const root = process.env.UMCP_WEB_ROOT || "dist";
const types = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8" };
createServer(async (req, res) => {
  const path = normalize(join(root, req.url === "/" ? "index.html" : req.url.split("?")[0]));
  if (!path.startsWith(root)) return res.writeHead(400).end();
  try { res.writeHead(200, { "content-type": types[extname(path)] || "application/octet-stream" }); res.end(await readFile(path)); }
  catch { res.writeHead(404).end(); }
}).listen(Number(process.env.PORT || 4173), "127.0.0.1", () => console.log("UMCP web server ready"));
