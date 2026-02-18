#!/usr/bin/env node
/**
 * screenshot.js - 通过 Chrome CDP 精确截取全页 PNG
 *
 * 用法：
 *   node screenshot.js <html_file> <output_png> [dpr=3] [width=390]
 *
 * 特性：
 *   - 用 Page.getLayoutMetrics 获取真实内容高度（无多余空白）
 *   - 用 Emulation.setDeviceMetricsOverride 设置高 DPR（默认 3x）
 *   - 用 Page.captureScreenshot + captureBeyondViewport 截全页
 *   - 无 npm 依赖（使用 Node.js 24+ 内置 WebSocket + fetch）
 */

const fs = require("fs");
const { spawn } = require("child_process");

const CHROME_CANDIDATES = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium-browser",
];

function findChrome() {
  for (const p of CHROME_CANDIDATES) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function connectChrome(port, targetUrl, retries = 40) {
  for (let i = 0; i < retries; i++) {
    try {
      const pages = await fetch(`http://localhost:${port}/json`).then((r) =>
        r.json()
      );
      // 优先找我们的 file:// 页面（避免拿到 Chrome 扩展背景页）
      const target =
        pages.find((p) => p.url === targetUrl && p.type === "page") ||
        pages.find((p) => p.url.startsWith("file://") && p.type === "page") ||
        pages.find((p) => p.type === "page") ||
        pages[0];
      if (target) return target.webSocketDebuggerUrl;
    } catch {
      // not ready yet
    }
    await sleep(200);
  }
  throw new Error(`Chrome remote debugging port ${port} not ready after ${retries} retries`);
}

function cdpSession(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let msgId = 0;
    const pending = new Map();

    const eventListeners = new Map();

    ws.addEventListener("message", (e) => {
      const msg = JSON.parse(e.data);
      // CDP event (no id)
      if (msg.method) {
        const listeners = eventListeners.get(msg.method) || [];
        for (const fn of listeners) fn(msg.params);
        return;
      }
      // CDP response (has id)
      if (msg.id !== undefined && pending.has(msg.id)) {
        const { res, rej } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) rej(new Error(msg.error.message));
        else res(msg.result);
      }
    });

    ws.addEventListener("open", () => {
      resolve({
        send(method, params = {}) {
          const id = ++msgId;
          return new Promise((res, rej) => {
            pending.set(id, { res, rej });
            ws.send(JSON.stringify({ id, method, params }));
          });
        },
        waitForEvent(eventName, timeout = 8000) {
          return Promise.race([
            new Promise((res) => {
              const list = eventListeners.get(eventName) || [];
              const handler = (params) => {
                const idx = (eventListeners.get(eventName) || []).indexOf(handler);
                if (idx >= 0) eventListeners.get(eventName).splice(idx, 1);
                res(params);
              };
              list.push(handler);
              eventListeners.set(eventName, list);
            }),
            sleep(timeout),
          ]);
        },
        close() {
          ws.close();
        },
      });
    });

    ws.addEventListener("error", reject);
  });
}

async function screenshot(htmlFile, outputPng, dpr = 3, cssWidth = 390) {
  const chrome = findChrome();
  if (!chrome) throw new Error("Chrome not found");

  const port = 10000 + Math.floor(Math.random() * 10000);

  const fileUrl = `file://${htmlFile}`;

  const proc = spawn(
    chrome,
    [
      "--headless=new",
      "--disable-gpu",
      "--no-sandbox",
      "--disable-extensions",
      `--remote-debugging-port=${port}`,
      `--window-size=${cssWidth},1200`,
      fileUrl,
    ],
    { stdio: "ignore" }
  );

  proc.on("error", (e) => {
    throw new Error(`Chrome launch failed: ${e.message}`);
  });

  try {
    const wsUrl = await connectChrome(port, fileUrl);
    const cdp = await cdpSession(wsUrl);

    // 等待页面加载（loadEventFired 或超时）
    await cdp.send("Page.enable");
    await Promise.race([
      cdp.waitForEvent("Page.loadEventFired"),
      sleep(8000),
    ]);
    await sleep(300); // 渲染稳定

    // 用 JS 获取真实 scrollHeight（比 getLayoutMetrics 更可靠）
    const sizeResult = await cdp.send("Runtime.evaluate", {
      expression:
        "JSON.stringify({w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight})",
    });
    const { w: contentWidth, h: contentHeight } = JSON.parse(
      sizeResult.result.value
    );

    // 设置视口：CSS 宽度 + 真实高度 + 高 DPR
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: cssWidth,
      height: contentHeight,
      deviceScaleFactor: dpr,
      mobile: true,
    });

    await sleep(200);

    // 全页截图
    const result = await cdp.send("Page.captureScreenshot", {
      format: "png",
      captureBeyondViewport: true,
      clip: {
        x: 0,
        y: 0,
        width: contentWidth,
        height: contentHeight,
        scale: 1,
      },
    });

    fs.writeFileSync(outputPng, Buffer.from(result.data, "base64"));

    const actualW = Math.round(contentWidth * dpr);
    const actualH = Math.round(contentHeight * dpr);
    process.stdout.write(
      `${actualW}x${actualH}px (${cssWidth}css x${dpr}dpr, content ${contentWidth}x${contentHeight})\n`
    );

    cdp.close();
  } finally {
    proc.kill();
  }
}

// ── main ─────────────────────────────────────────────────────────────────────
const [, , htmlFile, outputPng, dprArg, widthArg] = process.argv;

if (!htmlFile || !outputPng) {
  process.stderr.write(
    "Usage: node screenshot.js <html_file> <output_png> [dpr=3] [width=390]\n"
  );
  process.exit(1);
}

if (!fs.existsSync(htmlFile)) {
  process.stderr.write(`File not found: ${htmlFile}\n`);
  process.exit(1);
}

const dpr = dprArg ? parseInt(dprArg) : 3;
const width = widthArg ? parseInt(widthArg) : 390;

screenshot(htmlFile, outputPng, dpr, width)
  .then(() => process.exit(0))
  .catch((e) => {
    process.stderr.write(`Error: ${e.message}\n`);
    process.exit(1);
  });
