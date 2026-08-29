import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";

const root = process.env.UMCP_WEB_ROOT || "dist";
const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
};

createServer(async (req, res) => {
  const reqUrl = req.url === "/" ? "index.html" : req.url.split("?")[0].replace(/^\//, "");
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
}).listen(Number(process.env.PORT || 4174), "127.0.0.1", () => console.log("UMCP web server ready on http://127.0.0.1:4174"));
