
const express = require("express");
const path = require("path");
const { createProxyMiddleware } = require("http-proxy-middleware");

const app = express();
const PORT = process.env.PORT || 3000;
const API_TARGET = process.env.API_TARGET || "http://localhost:8000";

app.get("/config.js", (req, res) => {
  res.type("application/javascript");
  res.send(`window.API_BASE = ""; window.API_TARGET_LABEL = ${JSON.stringify(API_TARGET)};`);
});

app.use("/api", createProxyMiddleware({
  target: API_TARGET,
  changeOrigin: true,
  pathRewrite: { "^/api": "" }
}));

app.use(express.static(path.join(__dirname, "public")));

app.listen(PORT, () => {
  console.log(`Bottle Signature UI running at http://localhost:${PORT}`);
  console.log(`Proxying API calls to ${API_TARGET}`);
});
