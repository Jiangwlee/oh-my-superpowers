#!/usr/bin/env node
/* eslint-disable no-console */
/**
 * Unified Chrome CDP backend for markdown-to-anything.
 * Commands:
 *   --png <html_or_svg_file> <output_png> [dpr=3] [width=1080] [maxPageHeight=0]
 *   --pdf <html_file> <output_pdf> [width=750]
 *   --svg-validate <svg_file>
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');

const CHROME_CANDIDATES = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium',
  '/usr/bin/google-chrome',
  '/usr/bin/google-chrome-stable',
  '/usr/bin/chromium-browser',
  '/usr/bin/chromium',
  '/snap/bin/chromium',
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

async function connectChrome(port, targetUrl, retries = 50) {
  for (let i = 0; i < retries; i += 1) {
    try {
      const pages = await fetch(`http://127.0.0.1:${port}/json`).then((r) => r.json());
      const target =
        pages.find((p) => p.url === targetUrl && p.type === 'page') ||
        pages.find((p) => p.url.startsWith('file://') && p.type === 'page') ||
        pages.find((p) => p.type === 'page') ||
        pages[0];
      if (target && target.webSocketDebuggerUrl) return target.webSocketDebuggerUrl;
    } catch (_e) {
      // retry until ready
    }
    await sleep(200);
  }
  throw new Error(`Chrome not ready on port ${port}`);
}

function cdpSession(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let msgId = 0;
    const pending = new Map();
    const listeners = new Map();

    ws.addEventListener('message', (event) => {
      const msg = JSON.parse(event.data);
      if (msg.method) {
        const list = listeners.get(msg.method) || [];
        list.forEach((fn) => fn(msg.params));
        return;
      }
      if (pending.has(msg.id)) {
        const { ok, fail } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) fail(new Error(msg.error.message || 'CDP error'));
        else ok(msg.result);
      }
    });

    ws.addEventListener('open', () => {
      resolve({
        send(method, params = {}) {
          const id = ++msgId;
          return new Promise((ok, fail) => {
            pending.set(id, { ok, fail });
            ws.send(JSON.stringify({ id, method, params }));
          });
        },
        waitForEvent(name, timeoutMs = 8000) {
          return Promise.race([
            new Promise((ok) => {
              const list = listeners.get(name) || [];
              const handler = (params) => {
                const cur = listeners.get(name) || [];
                const idx = cur.indexOf(handler);
                if (idx >= 0) cur.splice(idx, 1);
                listeners.set(name, cur);
                ok(params);
              };
              list.push(handler);
              listeners.set(name, list);
            }),
            sleep(timeoutMs),
          ]);
        },
        close() {
          ws.close();
        },
      });
    });
    ws.addEventListener('error', reject);
  });
}

function startChrome(fileUrl, width) {
  const chrome = findChrome();
  if (!chrome) throw new Error('Chrome not found');
  const port = 10000 + Math.floor(Math.random() * 10000);
  const userDataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'mta-chrome-'));
  const proc = spawn(
    chrome,
    [
      '--headless=new',
      '--disable-gpu',
      '--no-sandbox',
      '--disable-extensions',
      `--user-data-dir=${userDataDir}`,
      `--remote-debugging-port=${port}`,
      '--remote-debugging-address=127.0.0.1',
      `--window-size=${width},1200`,
      fileUrl,
    ],
    { stdio: ['ignore', 'ignore', 'pipe'] },
  );
  let stderrBuf = '';
  if (proc.stderr) {
    proc.stderr.on('data', (chunk) => {
      stderrBuf += String(chunk);
      if (stderrBuf.length > 8000) stderrBuf = stderrBuf.slice(-8000);
    });
  }
  return { port, proc, userDataDir, getStderr: () => stderrBuf };
}

async function openPage(filePath, width) {
  const fileUrl = `file://${filePath}`;
  const { port, proc, userDataDir, getStderr } = startChrome(fileUrl, width);
  const cleanup = () => {
    proc.kill();
    try { fs.rmSync(userDataDir, { recursive: true, force: true }); } catch (_e) {}
  };
  try {
    const wsUrl = await connectChrome(port, fileUrl);
    const cdp = await cdpSession(wsUrl);
    await cdp.send('Page.enable');
    await cdp.send('Runtime.enable');
    await Promise.race([cdp.waitForEvent('Page.loadEventFired', 10000), sleep(10000)]);
    await sleep(350);
    return { cdp, proc, fileUrl, cleanup, getStderr };
  } catch (e) {
    const stderr = getStderr().trim();
    cleanup();
    if (stderr) {
      throw new Error(`${e.message}; chrome stderr: ${stderr.split('\n').slice(-4).join(' | ')}`);
    }
    throw e;
  }
}

async function capturePng(inputFile, outputPng, dpr = 3, cssWidth = 1080, maxPageHeight = 0) {
  const ctx = await openPage(inputFile, cssWidth);
  const { cdp, proc } = ctx;
  try {
    const sizeRes = await cdp.send('Runtime.evaluate', {
      expression: "JSON.stringify({w:Math.max(document.documentElement.scrollWidth,document.body?document.body.scrollWidth:0),h:Math.max(document.documentElement.scrollHeight,document.body?document.body.scrollHeight:0)})",
    });
    const content = JSON.parse(sizeRes.result.value);
    const contentWidth = Math.max(cssWidth, Number(content.w || cssWidth));
    const contentHeight = Math.max(1, Number(content.h || 1));

    async function captureClip(y, h, fileOut) {
      await cdp.send('Emulation.setDeviceMetricsOverride', {
        width: contentWidth,
        height: Math.max(1, h),
        deviceScaleFactor: dpr,
        mobile: false,
      });
      await sleep(80);
      const shot = await cdp.send('Page.captureScreenshot', {
        format: 'png',
        captureBeyondViewport: true,
        clip: { x: 0, y, width: contentWidth, height: h, scale: 1 },
      });
      fs.writeFileSync(fileOut, Buffer.from(shot.data, 'base64'));
    }

    if (!maxPageHeight || contentHeight <= maxPageHeight) {
      await captureClip(0, contentHeight, outputPng);
      console.log(`${Math.round(contentWidth * dpr)}x${Math.round(contentHeight * dpr)}px`);
      return [outputPng];
    }

    const base = outputPng.endsWith('.png') ? outputPng.slice(0, -4) : outputPng;
    const outputs = [];
    const pages = Math.ceil(contentHeight / maxPageHeight);
    for (let i = 0; i < pages; i += 1) {
      const y = i * maxPageHeight;
      const h = Math.min(maxPageHeight, contentHeight - y);
      const fileOut = `${base}_${i + 1}.png`;
      await captureClip(y, h, fileOut);
      outputs.push(fileOut);
      console.log(`page${i + 1}:${fileOut}:${Math.round(contentWidth * dpr)}x${Math.round(h * dpr)}`);
    }
    return outputs;
  } finally {
    cdp.close();
    ctx.cleanup();
  }
}

async function printPdf(htmlFile, outputPdf, cssWidth = 750) {
  const ctx = await openPage(htmlFile, cssWidth);
  const { cdp, proc } = ctx;
  try {
    // Wait for base64 embedded fonts to load (local Noto Sans SC for CJK text)
    await cdp.send('Runtime.evaluate', {
      expression: 'document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve(true)',
      awaitPromise: true,
      timeout: 5000,
    }).catch(() => {});
    await sleep(300); // Brief wait for font rendering stabilization
    const result = await cdp.send('Page.printToPDF', {
      paperWidth: 8.27,
      paperHeight: 11.69,
      marginTop: 0.4,
      marginBottom: 0.4,
      marginLeft: 0.4,
      marginRight: 0.4,
      printBackground: true,
      preferCSSPageSize: false,
      transferMode: 'ReturnAsBase64',
    });
    fs.writeFileSync(outputPdf, Buffer.from(result.data, 'base64'));
    console.log(JSON.stringify({ ok: true, file: outputPdf }));
  } finally {
    cdp.close();
    ctx.cleanup();
  }
}

async function validateSvgBBoxes(svgFile) {
  const ctx = await openPage(svgFile, 1080);
  const { cdp, proc } = ctx;
  try {
    const evalRes = await cdp.send('Runtime.evaluate', {
      expression: `(() => {
        const root = document.querySelector('svg');
        const width = root ? (root.viewBox && root.viewBox.baseVal ? root.viewBox.baseVal.width : parseFloat(root.getAttribute('width') || '1080')) : 1080;
        const height = root ? (root.viewBox && root.viewBox.baseVal ? root.viewBox.baseVal.height : parseFloat(root.getAttribute('height') || '1920')) : 1920;
        const els = Array.from(document.querySelectorAll('svg text, svg rect, svg circle, svg line'));
        const entries = els.map((el) => {
          if (getComputedStyle(el).display === 'none' || getComputedStyle(el).visibility === 'hidden') return null;
          let b;
          try { b = el.getBBox(); } catch (e) { return null; }
          return { id: el.id || null, tag: el.tagName.toLowerCase(), x: b.x, y: b.y, width: b.width, height: b.height };
        }).filter(Boolean);
        const errors = [];
        const warnings = [];
        for (const e of entries) {
          if (e.x < -0.5 || e.y < -0.5 || e.x + e.width > width + 0.5 || e.y + e.height > height + 0.5) {
            errors.push({ code: 'out_of_bounds', message: 'Element exceeds canvas bounds', element_id: e.id });
          }
        }
        for (let i = 0; i < entries.length; i++) {
          const a = entries[i];
          if (a.tag !== 'text') continue;
          for (let j = i + 1; j < entries.length; j++) {
            const b = entries[j];
            if (b.tag !== 'text') continue;
            const x1 = Math.max(a.x, b.x), y1 = Math.max(a.y, b.y), x2 = Math.min(a.x + a.width, b.x + b.width), y2 = Math.min(a.y + a.height, b.y + b.height);
            if (x2 <= x1 || y2 <= y1) continue;
            const inter = (x2 - x1) * (y2 - y1);
            const minArea = Math.max(1, Math.min(a.width * a.height, b.width * b.height));
            if (inter / minArea > 0.10) {
              errors.push({ code: 'overlap', message: 'Elements overlap >10%', element_id: a.id || b.id || null });
            }
          }
        }
        return { ok: errors.length === 0, errors, warnings };
      })()`,
      returnByValue: true,
    });
    console.log(JSON.stringify(evalRes.result.value || { ok: false, errors: [{ code: 'empty', message: 'No result', element_id: null }], warnings: [] }));
  } finally {
    cdp.close();
    ctx.cleanup();
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args[0] === '--pdf') {
    const [, htmlFile, outputPdf, widthArg] = args;
    if (!htmlFile || !outputPdf) throw new Error('Usage: --pdf <html_file> <output_pdf> [width=750]');
    await printPdf(htmlFile, outputPdf, widthArg ? parseInt(widthArg, 10) : 750);
    return;
  }
  if (args[0] === '--png') {
    const [, inputFile, outputPng, dprArg, widthArg, maxPageHeightArg] = args;
    if (!inputFile || !outputPng) throw new Error('Usage: --png <html_or_svg_file> <output_png> [dpr=3] [width=1080] [maxPageHeight=0]');
    await capturePng(
      inputFile,
      outputPng,
      dprArg ? parseInt(dprArg, 10) : 3,
      widthArg ? parseInt(widthArg, 10) : 1080,
      maxPageHeightArg ? parseInt(maxPageHeightArg, 10) : 0,
    );
    return;
  }
  if (args[0] === '--svg-validate') {
    const [, svgFile] = args;
    if (!svgFile) throw new Error('Usage: --svg-validate <svg_file>');
    await validateSvgBBoxes(svgFile);
    return;
  }

  // Backward-compatible PNG mode if command omitted.
  if (args.length >= 2) {
    const [inputFile, outputPng, dprArg, widthArg, maxPageHeightArg] = args;
    await capturePng(
      inputFile,
      outputPng,
      dprArg ? parseInt(dprArg, 10) : 3,
      widthArg ? parseInt(widthArg, 10) : 1080,
      maxPageHeightArg ? parseInt(maxPageHeightArg, 10) : 0,
    );
    return;
  }
  throw new Error('Usage: --png/--pdf/--svg-validate ...');
}

main().catch((e) => {
  console.error(`Error: ${e.message}`);
  process.exit(1);
});
