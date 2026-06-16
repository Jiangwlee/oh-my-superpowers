#!/usr/bin/env node
// Generate an image through chatgpt.com/images using an authenticated Chrome tab.
// Input: prompt and CLI options from generate-image.sh.
// Output: saved file path, or structured JSON with --json.
// Public entrypoint: omp web-operator generate-image chatgpt <prompt>.

import { spawn } from 'child_process';
import { existsSync, mkdirSync, readFileSync, readdirSync, renameSync, statSync, unlinkSync } from 'fs';
import { homedir } from 'os';
import { basename, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const CHATGPT_DIR = dirname(__filename);
const CDP_SCRIPT = resolve(CHATGPT_DIR, '..', '..', 'cdp.mjs');
const DEFAULT_TIMEOUT_SEC = 180;
const READY_TIMEOUT_MS = 60000;
const POLL_INTERVAL_MS = 2000;

function usage(exitCode = 0) {
  const stream = exitCode === 0 ? process.stdout : process.stderr;
  stream.write(`usage: generate-image.mjs <prompt> [--out PATH] [--target TARGET] [--timeout SEC] [--overwrite] [--json]\n\n`);
  stream.write(`Generate an image on https://chatgpt.com/images/ and save it locally.\n`);
  stream.write(`Requires Chrome remote debugging and a signed-in ChatGPT tab/session.\n`);
  process.exit(exitCode);
}

function parseArgs(argv) {
  const opts = {
    prompt: null,
    out: null,
    target: null,
    timeoutSec: DEFAULT_TIMEOUT_SEC,
    overwrite: false,
    json: false,
  };

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') usage(0);
    if (arg === '--out') {
      opts.out = argv[++i];
    } else if (arg === '--target') {
      opts.target = argv[++i];
    } else if (arg === '--timeout') {
      opts.timeoutSec = Number(argv[++i]);
    } else if (arg === '--overwrite') {
      opts.overwrite = true;
    } else if (arg === '--json') {
      opts.json = true;
    } else if (!opts.prompt) {
      opts.prompt = arg;
    } else {
      throw new Error(`unexpected argument: ${arg}`);
    }
  }

  if (!opts.prompt || !opts.prompt.trim()) throw new Error('prompt is required');
  if (!Number.isInteger(opts.timeoutSec) || opts.timeoutSec <= 0) {
    throw new Error('--timeout must be a positive integer number of seconds');
  }
  if (opts.out === undefined) throw new Error('--out requires a path');
  if (opts.target === undefined) throw new Error('--target requires a target prefix');
  return opts;
}

function expandPath(path) {
  if (!path) {
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    return resolve(homedir(), 'Downloads', `chatgpt-image-${stamp}.png`);
  }
  if (path === '~') return homedir();
  if (path.startsWith('~/')) return resolve(homedir(), path.slice(2));
  return resolve(path);
}

function run(command, args, timeoutMs = 120000) {
  return new Promise((resolvePromise, reject) => {
    const child = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    const stdout = [];
    const stderr = [];
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      reject(new Error(`command timed out: ${command} ${args.join(' ')}`));
    }, timeoutMs);

    child.stdout.on('data', chunk => stdout.push(chunk));
    child.stderr.on('data', chunk => stderr.push(chunk));
    child.on('error', error => {
      clearTimeout(timer);
      reject(error);
    });
    child.on('close', code => {
      clearTimeout(timer);
      const out = Buffer.concat(stdout).toString('utf8').trim();
      const err = Buffer.concat(stderr).toString('utf8').trim();
      if (code === 0) {
        resolvePromise(out);
      } else {
        reject(new Error(err || out || `command failed with exit code ${code}: ${command} ${args.join(' ')}`));
      }
    });
  });
}

async function cdp(args, timeoutMs = 120000) {
  try {
    return await run(process.execPath, [CDP_SCRIPT, ...args], timeoutMs);
  } catch (error) {
    const cmd = args[0] || 'unknown';
    throw new Error(`cdp ${cmd} failed: ${error.message}`);
  }
}

async function cdpJson(args, timeoutMs = 120000) {
  const text = await cdp(args, timeoutMs);
  try {
    return JSON.parse(text || 'null');
  } catch (error) {
    throw new Error(`expected JSON from cdp ${args.join(' ')}: ${text.slice(0, 500)}`);
  }
}

function resolveTargetPrefix(prefix, pages) {
  const upper = prefix.toUpperCase();
  const matches = pages.filter(page => page.targetId.toUpperCase().startsWith(upper));
  if (matches.length === 0) throw new Error(`no Chrome tab matches target prefix: ${prefix}`);
  if (matches.length > 1) throw new Error(`ambiguous target prefix: ${prefix}`);
  return matches[0].targetId.slice(0, 8);
}

async function selectTarget(explicitTarget) {
  let pages = await cdpJson(['list_raw'], 30000);
  if (explicitTarget) {
    return { target: resolveTargetPrefix(explicitTarget, pages), shouldClose: false };
  }

  const chatgptImages = pages.find(page => /^https:\/\/chatgpt\.com\/images\/?/.test(page.url || ''));
  if (chatgptImages) {
    return { target: chatgptImages.targetId.slice(0, 8), shouldClose: true };
  }

  const output = await cdp(['open', 'https://chatgpt.com/images/'], 30000);
  const opened = output.match(/[A-F0-9]{8,}/)?.[0];
  if (!opened) throw new Error(`failed to open ChatGPT Images tab: ${output}`);
  return { target: opened, shouldClose: true };
}

function readyExpression() {
  return `(() => {
    const text = document.body?.innerText || '';
    const composer = document.querySelector('#prompt-textarea')
      || document.querySelector('[contenteditable="true"][aria-label*="Chat"]')
      || document.querySelector('textarea[placeholder*="Describe"]');
    const loginHint = /log in|sign up|sign in/i.test(text);
    return JSON.stringify({
      url: location.href,
      title: document.title,
      hasComposer: !!composer,
      loginHint,
      bodyText: text.slice(0, 1000),
    });
  })()`;
}

async function waitForComposer(target) {
  const deadline = Date.now() + READY_TIMEOUT_MS;
  let last = null;
  while (Date.now() < deadline) {
    last = await cdpJson(['eval', target, readyExpression()], 30000);
    if (last.hasComposer) return last;
    if (last.loginHint) {
      throw new Error('ChatGPT is not signed in. Sign in at https://chatgpt.com/images/ in Chrome, then retry.');
    }
    await new Promise(resolvePromise => setTimeout(resolvePromise, 1000));
  }
  throw new Error(`timed out waiting for ChatGPT image composer. Last page: ${JSON.stringify(last)}`);
}

function imageListExpression() {
  return `(() => {
    const fromUrl = (url) => {
      try { return new URL(url, location.href).searchParams.get('id') || ''; }
      catch { return ''; }
    };
    const images = [...document.images].map((img) => {
      const url = img.currentSrc || img.src || '';
      return {
        id: fromUrl(url),
        url,
        alt: img.alt || '',
        width: img.naturalWidth || 0,
        height: img.naturalHeight || 0,
      };
    }).filter(img => img.id.startsWith('file_') && img.url.includes('/backend-api/estuary/content'));
    return JSON.stringify(images);
  })()`;
}

function prepareComposerExpression() {
  return `(() => {
    const el = document.querySelector('#prompt-textarea')
      || document.querySelector('[contenteditable="true"][aria-label*="Chat"]')
      || document.querySelector('textarea[placeholder*="Describe"]');
    if (!el) return JSON.stringify({ ok: false, error: 'composer not found' });
    el.scrollIntoView({ block: 'center', inline: 'center' });
    el.focus();
    if (el.isContentEditable) {
      document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
    } else {
      el.value = '';
      el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward' }));
    }
    return JSON.stringify({ ok: true });
  })()`;
}

function sendButtonExpression() {
  return `(() => {
    const buttons = [...document.querySelectorAll('button')];
    const btn = buttons.find(button => {
      const label = button.getAttribute('aria-label') || '';
      return /send prompt|send message|send/i.test(label) && !button.disabled;
    });
    if (!btn) return JSON.stringify({ ok: false, error: 'enabled send button not found' });
    btn.scrollIntoView({ block: 'center', inline: 'center' });
    const rect = btn.getBoundingClientRect();
    return JSON.stringify({ ok: true, x: rect.left + rect.width / 2, y: rect.top + rect.height / 2, label: btn.getAttribute('aria-label') || '' });
  })()`;
}

function waitImageExpression(beforeIds) {
  const idsJson = JSON.stringify(beforeIds);
  return `(() => {
    const before = new Set(${idsJson});
    const fromUrl = (url) => {
      try { return new URL(url, location.href).searchParams.get('id') || ''; }
      catch { return ''; }
    };
    const images = [...document.images].map((img) => {
      const url = img.currentSrc || img.src || '';
      return {
        id: fromUrl(url),
        url,
        alt: img.alt || '',
        width: img.naturalWidth || 0,
        height: img.naturalHeight || 0,
      };
    }).filter(img => img.id.startsWith('file_') && img.url.includes('/backend-api/estuary/content'));
    const fresh = images.filter(img => !before.has(img.id) && img.width > 0 && img.height > 0);
    const text = document.body?.innerText || '';
    const stopVisible = [...document.querySelectorAll('button')].some(button => /stop/i.test(button.getAttribute('aria-label') || button.innerText || ''));
    return JSON.stringify({
      found: fresh.at(-1) || null,
      generatedCount: images.length,
      stopVisible,
      creating: /creating image|generating image|creating/i.test(text),
      url: location.href,
      title: document.title,
      bodyTail: text.slice(-1000),
    });
  })()`;
}

async function waitForSendButton(target) {
  const deadline = Date.now() + 10000;
  let last = null;
  while (Date.now() < deadline) {
    last = await cdpJson(['eval', target, sendButtonExpression()], 30000);
    if (last.ok) return last;
    await new Promise(resolvePromise => setTimeout(resolvePromise, 500));
  }
  throw new Error(last?.error || 'failed to find enabled send button');
}

async function submitPrompt(target, prompt) {
  const prepared = await cdpJson(['eval', target, prepareComposerExpression()], 30000);
  if (!prepared.ok) throw new Error(prepared.error || 'failed to prepare composer');

  await cdp(['click', target, '#prompt-textarea'], 30000).catch(async () => {
    await cdp(['eval', target, prepareComposerExpression()], 30000);
  });
  await cdp(['type', target, prompt], 30000);

  const button = await waitForSendButton(target);
  await cdp(['clickxy', target, String(button.x), String(button.y)], 30000);
}

async function waitForNewImage(target, beforeIds, timeoutSec) {
  const deadline = Date.now() + timeoutSec * 1000;
  let last = null;
  while (Date.now() < deadline) {
    last = await cdpJson(['eval', target, waitImageExpression(beforeIds)], 30000);
    if (last.found?.id && last.found?.url) return last;
    await new Promise(resolvePromise => setTimeout(resolvePromise, POLL_INTERVAL_MS));
  }
  throw new Error(`timed out waiting for generated image. Last state: ${JSON.stringify(last)}`);
}

function resolveDownloadExpression(image) {
  const imageJson = JSON.stringify(image);
  return `(async () => {
    try {
      const image = ${imageJson};
      const pathParts = location.pathname.split('/');
      const conversationId = pathParts.includes('c') ? pathParts[pathParts.indexOf('c') + 1] || null : null;
      let downloadInfo = null;
      let contentUrl = image.url;
      if (image.id && conversationId) {
        const metaUrl = '/backend-api/files/download/' + encodeURIComponent(image.id)
          + '?conversation_id=' + encodeURIComponent(conversationId)
          + '&inline=false&download_intent=false';
        const metaRes = await fetch(metaUrl, { credentials: 'include' });
        if (metaRes.ok) {
          downloadInfo = await metaRes.json();
          if (downloadInfo.download_url) contentUrl = downloadInfo.download_url;
        }
      }
      return JSON.stringify({
        ok: true,
        download_url: contentUrl,
        mime_type: downloadInfo?.mime_type || null,
        file_name: downloadInfo?.file_name || null,
        file_size_bytes: downloadInfo?.file_size_bytes || null,
        conversation_id: conversationId,
        conversation_url: location.href,
        file_id: image.id,
        alt: image.alt || '',
        rendered_width: image.width || 0,
        rendered_height: image.height || 0,
      });
    } catch (error) {
      return JSON.stringify({ ok: false, error: error?.message || String(error), stack: error?.stack || null });
    }
  })()`;
}

function triggerDownloadExpression(url, filename) {
  const urlJson = JSON.stringify(url);
  const filenameJson = JSON.stringify(filename);
  return `(() => {
    const a = document.createElement('a');
    a.href = ${urlJson};
    a.download = ${filenameJson};
    a.rel = 'noopener';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => a.remove(), 1000);
    return JSON.stringify({ ok: true });
  })()`;
}

function findDownloadedCandidate(dir, existingNames, startTimeMs) {
  const names = readdirSync(dir).filter(name => !name.endsWith('.crdownload'));
  const candidates = names
    .filter(name => !existingNames.has(name))
    .map(name => {
      const path = resolve(dir, name);
      const stat = statSync(path);
      return { name, path, size: stat.size, mtimeMs: stat.mtimeMs };
    })
    .filter(file => file.size > 0 && file.mtimeMs >= startTimeMs - 2000)
    .sort((a, b) => b.mtimeMs - a.mtimeMs);
  return candidates[0] || null;
}

async function waitForBrowserDownload(dir, existingNames, startTimeMs, timeoutSec) {
  const deadline = Date.now() + timeoutSec * 1000;
  let lastPath = null;
  let lastSize = -1;
  let stableCount = 0;

  while (Date.now() < deadline) {
    const candidate = findDownloadedCandidate(dir, existingNames, startTimeMs);
    if (candidate) {
      if (candidate.path === lastPath && candidate.size === lastSize) stableCount += 1;
      else stableCount = 0;
      lastPath = candidate.path;
      lastSize = candidate.size;
      if (stableCount >= 1) return candidate.path;
    }
    await new Promise(resolvePromise => setTimeout(resolvePromise, 1000));
  }
  throw new Error(`timed out waiting for browser download in ${dir}`);
}

function sniffImage(buffer) {
  if (buffer.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) {
    return {
      format: 'png',
      mimeType: 'image/png',
      width: buffer.readUInt32BE(16),
      height: buffer.readUInt32BE(20),
    };
  }
  if (buffer.subarray(0, 3).equals(Buffer.from([0xff, 0xd8, 0xff]))) {
    for (let offset = 2; offset + 9 < buffer.length;) {
      if (buffer[offset] !== 0xff) break;
      const marker = buffer[offset + 1];
      const length = buffer.readUInt16BE(offset + 2);
      if (marker >= 0xc0 && marker <= 0xc3) {
        return {
          format: 'jpeg',
          mimeType: 'image/jpeg',
          height: buffer.readUInt16BE(offset + 5),
          width: buffer.readUInt16BE(offset + 7),
        };
      }
      offset += 2 + length;
    }
    return { format: 'jpeg', mimeType: 'image/jpeg', width: null, height: null };
  }
  if (buffer.toString('ascii', 0, 4) === 'RIFF' && buffer.toString('ascii', 8, 12) === 'WEBP') {
    return { format: 'webp', mimeType: 'image/webp', width: null, height: null };
  }
  throw new Error('downloaded file is not a recognized PNG/JPEG/WebP image');
}

async function main() {
  let phase = 'parse arguments';
  try {
    const opts = parseArgs(process.argv.slice(2));
    const outPath = expandPath(opts.out);
    if (existsSync(outPath) && !opts.overwrite) {
      throw new Error(`output file already exists: ${outPath}. Use --overwrite to replace it.`);
    }

    phase = 'select target';
    const { target, shouldClose } = await selectTarget(opts.target);
    phase = 'navigate to ChatGPT Images';
    await cdp(['nav', target, 'https://chatgpt.com/images/', 'load'], 45000).catch(() => {});
    phase = 'wait for composer';
    await waitForComposer(target);

    phase = 'snapshot existing images';
    const beforeImages = await cdpJson(['eval', target, imageListExpression()], 30000);
    const beforeIds = beforeImages.map(image => image.id).filter(Boolean);

    phase = 'submit prompt';
    await submitPrompt(target, opts.prompt);
    phase = 'wait for generated image';
    const imageState = await waitForNewImage(target, beforeIds, opts.timeoutSec);
    phase = 'resolve generated image download URL';
    const downloaded = await cdpJson(['eval', target, resolveDownloadExpression(imageState.found)], 30000);
    if (!downloaded.ok) throw new Error(`image download URL resolution failed: ${downloaded.error || 'unknown error'}`);

    phase = 'trigger browser download';
    const outDir = dirname(outPath);
    mkdirSync(outDir, { recursive: true });
    if (existsSync(outPath)) {
      if (!opts.overwrite) throw new Error(`output file already exists: ${outPath}. Use --overwrite to replace it.`);
      unlinkSync(outPath);
    }
    const existingNames = new Set(readdirSync(outDir));
    const downloadStart = Date.now();
    await cdp(['evalraw', target, 'Page.setDownloadBehavior', JSON.stringify({ behavior: 'allow', downloadPath: outDir })], 30000);
    const triggered = await cdpJson(['eval', target, triggerDownloadExpression(downloaded.download_url, basename(outPath))], 30000);
    if (!triggered.ok) throw new Error('failed to trigger browser download');

    phase = 'wait for browser download';
    const downloadedPath = await waitForBrowserDownload(outDir, existingNames, downloadStart, Math.min(opts.timeoutSec, 60));
    if (downloadedPath !== outPath) {
      if (existsSync(outPath)) {
        if (!opts.overwrite) throw new Error(`output file already exists after download: ${outPath}`);
        unlinkSync(outPath);
      }
      renameSync(downloadedPath, outPath);
    }

    phase = 'validate output file';
    const buffer = readFileSync(outPath);
    const sniffed = sniffImage(buffer);

    const payload = {
      site: 'chatgpt',
      prompt: opts.prompt,
      path: outPath,
      mime_type: downloaded.mime_type || sniffed.mimeType,
      bytes: buffer.length,
      width: sniffed.width || imageState.found.width || downloaded.rendered_width || null,
      height: sniffed.height || imageState.found.height || downloaded.rendered_height || null,
      conversation_id: downloaded.conversation_id,
      file_id: downloaded.file_id,
      file_name: downloaded.file_name,
      alt: downloaded.alt,
      conversation_url: downloaded.conversation_url,
      target,
    };

    phase = 'close ChatGPT tab';
    if (shouldClose) await cdp(['close', target], 30000).catch(() => {});

    if (opts.json) console.log(JSON.stringify(payload, null, 2));
    else console.log(outPath);
  } catch (error) {
    throw new Error(`[${phase}] ${error.message}`);
  }
}

main().catch(error => {
  console.error(`chatgpt generate-image: ${error.message}`);
  process.exit(1);
});
