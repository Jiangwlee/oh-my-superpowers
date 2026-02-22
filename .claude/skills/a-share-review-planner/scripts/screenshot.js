#!/usr/bin/env node
/**
 * screenshot.js - 通过 Chrome CDP 精确截取全页 PNG
 *
 * 用法：
 *   node screenshot.js <html_file> <output_png> [dpr=3] [width=750] [maxPageHeight=0]
 *
 * 参数：
 *   maxPageHeight: CSS 像素。0=单图模式；>0=分页模式，生成 output_1.png output_2.png ...
 *                  分页模式下每页高度 ≤ maxPageHeight，满足 Telegram sendPhoto 限制
 *                  (宽+高 ≤ 10000px)。
 *
 * 特性：
 *   - 用 Runtime.evaluate scrollHeight 获取真实内容高度
 *   - 用 Emulation.setDeviceMetricsOverride 设置高 DPR（默认 3x）
 *   - mobile: false 避免 Chrome Font Boosting 导致文字变形
 *   - 无 npm 依赖（使用 Node.js 24+ 内置 WebSocket + fetch）
 */

const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const CHROME_CANDIDATES = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium-browser",   // Ubuntu apt
  "/usr/bin/chromium",           // Debian / Alpine
  "/snap/bin/chromium",          // Ubuntu snap
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
      if (msg.method) {
        const listeners = eventListeners.get(msg.method) || [];
        for (const fn of listeners) fn(msg.params);
        return;
      }
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
        close() { ws.close(); },
      });
    });

    ws.addEventListener("error", reject);
  });
}

/**
 * 截取单个矩形区域（CSS 坐标系）并保存为 PNG
 */
async function captureClip(cdp, cssWidth, cssY, cssHeight, dpr, outputFile) {
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: cssWidth,
    height: cssHeight,
    deviceScaleFactor: dpr,
    mobile: false,
  });
  await sleep(100);

  const result = await cdp.send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: true,
    clip: { x: 0, y: cssY, width: cssWidth, height: cssHeight, scale: 1 },
  });

  fs.writeFileSync(outputFile, Buffer.from(result.data, "base64"));
  const physW = Math.round(cssWidth * dpr);
  const physH = Math.round(cssHeight * dpr);
  return { physW, physH };
}

async function screenshot(htmlFile, outputPng, dpr = 3, cssWidth = 750, maxPageHeight = 0) {
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

  proc.on("error", (e) => { throw new Error(`Chrome launch failed: ${e.message}`); });

  try {
    const wsUrl = await connectChrome(port, fileUrl);
    const cdp = await cdpSession(wsUrl);

    await cdp.send("Page.enable");
    await Promise.race([cdp.waitForEvent("Page.loadEventFired"), sleep(8000)]);
    await sleep(300);

    // 获取真实内容尺寸
    const sizeResult = await cdp.send("Runtime.evaluate", {
      expression: "JSON.stringify({w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight})",
    });
    const { w: contentWidth, h: contentHeight } = JSON.parse(sizeResult.result.value);

    const outputFiles = [];

    if (maxPageHeight <= 0 || contentHeight <= maxPageHeight) {
      // ── 单图模式（原有行为）──────────────────────────────────────
      const { physW, physH } = await captureClip(cdp, contentWidth, 0, contentHeight, dpr, outputPng);
      process.stdout.write(`${physW}x${physH}px (${cssWidth}css x${dpr}dpr, content ${contentWidth}x${contentHeight})\n`);
      outputFiles.push(outputPng);
    } else {
      // ── 分页模式 ─────────────────────────────────────────────────
      const numPages = Math.ceil(contentHeight / maxPageHeight);
      const baseName = outputPng.replace(/\.png$/, "");

      for (let i = 0; i < numPages; i++) {
        const cssY = i * maxPageHeight;
        const cssH = Math.min(maxPageHeight, contentHeight - cssY);
        const pageFile = `${baseName}_${i + 1}.png`;

        const { physW, physH } = await captureClip(cdp, contentWidth, cssY, cssH, dpr, pageFile);
        process.stdout.write(`page${i + 1}:${pageFile}:${physW}x${physH}\n`);
        outputFiles.push(pageFile);
      }
    }

    cdp.close();
    return outputFiles;
  } finally {
    proc.kill();
  }
}

/**
 * 通过 CDP Page.printToPDF 生成 PDF。
 * 等待 document.fonts.ready 确保 web font（Noto Sans SC）已加载并嵌入。
 */
async function printPDF(htmlFile, outputPdf, cssWidth = 750) {
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

  proc.on("error", (e) => { throw new Error(`Chrome launch failed: ${e.message}`); });

  try {
    const wsUrl = await connectChrome(port, fileUrl);
    const cdp = await cdpSession(wsUrl);

    await cdp.send("Page.enable");
    // 等待页面加载
    await Promise.race([cdp.waitForEvent("Page.loadEventFired"), sleep(10000)]);

    // 等待 web font（Noto Sans SC）加载完成，确保 CJK 字符能正确嵌入 PDF
    await cdp.send("Runtime.evaluate", {
      expression: "document.fonts.ready",
      awaitPromise: true,
      timeout: 15000,
    });
    await sleep(500); // 额外等待渲染稳定

    // 使用 A4 纸张尺寸，按内容宽度缩放
    // paperWidth/paperHeight 单位为英寸（A4 = 8.27×11.69）
    const result = await cdp.send("Page.printToPDF", {
      paperWidth: 8.27,
      paperHeight: 11.69,
      marginTop: 0.4,
      marginBottom: 0.4,
      marginLeft: 0.4,
      marginRight: 0.4,
      printBackground: true,
      preferCSSPageSize: false,
      transferMode: "ReturnAsBase64",
    });

    fs.writeFileSync(outputPdf, Buffer.from(result.data, "base64"));
    process.stdout.write(`pdf:${outputPdf}\n`);

    cdp.close();
  } finally {
    proc.kill();
  }
}

// ── main ─────────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
const isPdf = args.includes("--pdf");

if (isPdf) {
  // PDF 模式: node screenshot.js --pdf <html_file> <output_pdf> [width=750]
  const htmlFile = args[args.indexOf("--pdf") + 1];
  const outputPdf = args[args.indexOf("--pdf") + 2];
  const cssWidth = args[args.indexOf("--pdf") + 3] ? parseInt(args[args.indexOf("--pdf") + 3]) : 750;

  if (!htmlFile || !outputPdf) {
    process.stderr.write("Usage: node screenshot.js --pdf <html_file> <output_pdf> [width=750]\n");
    process.exit(1);
  }
  if (!fs.existsSync(htmlFile)) {
    process.stderr.write(`File not found: ${htmlFile}\n`);
    process.exit(1);
  }
  printPDF(htmlFile, outputPdf, cssWidth)
    .then(() => process.exit(0))
    .catch((e) => {
      process.stderr.write(`Error: ${e.message}\n`);
      process.exit(1);
    });
} else {
  // PNG 模式（原有行为）
  const [htmlFile, outputPng, dprArg, widthArg, maxPageHeightArg] = args;

  if (!htmlFile || !outputPng) {
    process.stderr.write(
      "Usage: node screenshot.js <html_file> <output_png> [dpr=3] [width=750] [maxPageHeight=0]\n"
    );
    process.exit(1);
  }
  if (!fs.existsSync(htmlFile)) {
    process.stderr.write(`File not found: ${htmlFile}\n`);
    process.exit(1);
  }

  const dpr = dprArg ? parseInt(dprArg) : 3;
  const width = widthArg ? parseInt(widthArg) : 750;
  const maxPageHeight = maxPageHeightArg ? parseInt(maxPageHeightArg) : 0;

  screenshot(htmlFile, outputPng, dpr, width, maxPageHeight)
    .then(() => process.exit(0))
    .catch((e) => {
      process.stderr.write(`Error: ${e.message}\n`);
      process.exit(1);
    });
}
