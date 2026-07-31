#!/usr/bin/env node

import { execFile } from 'child_process';
import { promisify } from 'util';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const execFileAsync = promisify(execFile);
const __filename = fileURLToPath(import.meta.url);
const SCRIPT_DIR = dirname(__filename);
const SKILL_DIR = resolve(SCRIPT_DIR, '..');
const REPO_ROOT = resolve(SKILL_DIR, '..', '..');
const CDP_SCRIPT = resolve(SCRIPT_DIR, 'cdp.mjs');
const SITE_SCRIPTS_DIR = resolve(SCRIPT_DIR, 'sites');
const TESTS_DIR = resolve(SKILL_DIR, 'tests');

const argv = process.argv.slice(2);
const options = {
  json: false,
  failFast: false,
};

const positionals = [];
for (const arg of argv) {
  if (arg === '--json') {
    options.json = true;
  } else if (arg === '--fail-fast') {
    options.failFast = true;
  } else {
    positionals.push(arg);
  }
}

function usage() {
  console.error([
    'usage:',
    '  node skills/web-operator/scripts/test.mjs list',
    '  node skills/web-operator/scripts/test.mjs all [--json] [--fail-fast]',
    '  node skills/web-operator/scripts/test.mjs core [--json] [--fail-fast]',
    '  node skills/web-operator/scripts/test.mjs site <baidu|google|kdocs|reddit|taoguba|weixin-sogou|x|xueqiu> [--json] [--fail-fast]',
  ].join('\n'));
  process.exit(1);
}

function envInt(name, fallback) {
  const raw = process.env[name];
  if (!raw) return fallback;
  const value = Number(raw);
  return Number.isInteger(value) && value > 0 ? value : fallback;
}

function quoteCommand(parts) {
  return parts.map((part) => {
    if (/^[A-Za-z0-9_./:@=-]+$/.test(part)) return part;
    return JSON.stringify(part);
  }).join(' ');
}

function normalizeText(text) {
  return String(text || '').trim();
}

function makeResultBase(test, startedAt) {
  return {
    name: test.name,
    scope: test.scope,
    site: test.site,
    workflow: test.workflow,
    level: test.level,
    status: 'fail',
    duration_ms: Date.now() - startedAt,
  };
}

function isSetupIssue(text) {
  return [
    /no usable .* tab found/i,
    /missing required command:/i,
    /devtoolsactiveport/i,
    /remote debugging/i,
    /econnrefused/i,
    /could not connect/i,
    /failed to fetch/i,
    /websocket/i,
    /credentials_not_autofilled/i,
    /verification_required/i,
  ].some((pattern) => pattern.test(text));
}

function toErrorMessage(error) {
  if (!error) return 'unknown error';
  if (typeof error === 'string') return error;
  return error.message || String(error);
}

async function runCommand(command, args, timeoutMs = 60000) {
  const commandLine = quoteCommand([command, ...args]);
  try {
    const { stdout, stderr } = await execFileAsync(command, args, {
      cwd: REPO_ROOT,
      timeout: timeoutMs,
      maxBuffer: 8 * 1024 * 1024,
    });
    return {
      ok: true,
      command: commandLine,
      stdout: normalizeText(stdout),
      stderr: normalizeText(stderr),
      exit_code: 0,
    };
  } catch (error) {
    return {
      ok: false,
      command: commandLine,
      stdout: normalizeText(error.stdout),
      stderr: normalizeText(error.stderr || error.message),
      exit_code: typeof error.code === 'number' ? error.code : 1,
      error,
    };
  }
}

function parseJsonOutput(result) {
  try {
    return { ok: true, value: JSON.parse(result.stdout || 'null') };
  } catch (error) {
    return { ok: false, error };
  }
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function runJsonCommand(command, args, timeoutMs = 60000) {
  const result = await runCommand(command, args, timeoutMs);
  if (!result.ok) {
    const combined = [result.stderr, result.stdout].filter(Boolean).join('\n');
    const error = new Error(combined || `command failed: ${result.command}`);
    error.result = result;
    throw error;
  }
  const parsed = parseJsonOutput(result);
  if (!parsed.ok) {
    const error = new Error(`expected JSON output from ${result.command}`);
    error.result = result;
    error.parseError = parsed.error;
    throw error;
  }
  return { result, value: parsed.value };
}

async function runCase(test) {
  const startedAt = Date.now();
  try {
    const details = await test.run();
    return {
      ...makeResultBase(test, startedAt),
      status: details.status || 'pass',
      duration_ms: Date.now() - startedAt,
      hint: details.hint || '',
      command: details.command || '',
      commands: details.commands || [],
      stdout_excerpt: details.stdout_excerpt || '',
      stderr_excerpt: details.stderr_excerpt || '',
      data: details.data || null,
    };
  } catch (error) {
    const result = error.result || null;
    const combined = normalizeText([
      result?.stderr,
      result?.stdout,
      toErrorMessage(error),
    ].filter(Boolean).join('\n'));
    const status = isSetupIssue(combined) ? 'skip' : 'fail';
    return {
      ...makeResultBase(test, startedAt),
      status,
      duration_ms: Date.now() - startedAt,
      hint: status === 'skip'
        ? (test.setupHint || 'Runtime prerequisites are not satisfied for this live browser smoke test.')
        : (test.failHint || 'Inspect the workflow script and reference for this case.'),
      command: result?.command || '',
      commands: result ? [result.command] : [],
      stdout_excerpt: result?.stdout || '',
      stderr_excerpt: result?.stderr || combined,
      data: null,
    };
  }
}

const KDOCS_QUERY = process.env.CDP_TEST_KDOCS_QUERY || '天基遥感';
const KDOCS_AI_QUERY = process.env.CDP_TEST_KDOCS_AI_QUERY || '天基遥感 经费';
const REDDIT_QUERY = process.env.CDP_TEST_REDDIT_QUERY || 'openai';
const X_QUERY = process.env.CDP_TEST_X_QUERY || 'openai';
const XUEQIU_QUERY = process.env.CDP_TEST_XUEQIU_QUERY || '腾讯';
const XUEQIU_STOCK = process.env.CDP_TEST_XUEQIU_STOCK || '00700';
const GOOGLE_QUERY = process.env.CDP_TEST_GOOGLE_QUERY || 'openai';
const BAIDU_QUERY = process.env.CDP_TEST_BAIDU_QUERY || '百度';
const SOGOU_QUERY = process.env.CDP_TEST_SOGOU_QUERY || 'Python';
const TAOGUBA_HOURS = envInt('CDP_TEST_TAOGUBA_HOURS', 168);
const TAOGUBA_LIMIT = envInt('CDP_TEST_TAOGUBA_LIMIT', 5);

const tests = [
  {
    name: 'core.cdp.list.smoke',
    scope: 'core',
    site: 'core',
    workflow: 'cdp.list',
    level: 'smoke',
    setupHint: 'Enable Chrome remote debugging and make sure a Chrome-family browser is running.',
    failHint: 'Inspect scripts/cdp.mjs and references/core/troubleshooting.md.',
    async run() {
      const { result, value } = await runJsonCommand('node', [CDP_SCRIPT, 'list_raw'], 30000);
      assert(Array.isArray(value), 'list_raw should return a JSON array');
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { page_count: value.length },
      };
    },
  },
  {
    name: 'site.google.search.smoke',
    scope: 'site',
    site: 'google',
    workflow: 'search',
    level: 'smoke',
    setupHint: 'Make sure at least one Chrome tab is open before running Google smoke tests.',
    failHint: 'Check scripts/sites/google/search.sh and references/sites/google/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'google', 'search.sh');
      const { result, value } = await runJsonCommand('bash', [script, GOOGLE_QUERY, '5'], 60000);
      assert(Array.isArray(value), 'google search should return a JSON array');
      assert(value.length > 0, 'google search should return at least one result');
      assert(typeof value[0]?.url === 'string' && value[0].url.startsWith('https://'), 'google search result should include a valid URL');
      assert(typeof value[0]?.title === 'string' && value[0].title.length > 0, 'google search result should include a non-empty title');
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { result_count: value.length, first_url: value[0].url },
      };
    },
  },
  {
    name: 'site.baidu.search.smoke',
    scope: 'site',
    site: 'baidu',
    workflow: 'search',
    level: 'smoke',
    setupHint: 'Make sure at least one Chrome tab is open before running Baidu smoke tests.',
    failHint: 'Check scripts/sites/baidu/search.sh and references/sites/baidu/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'baidu', 'search.sh');
      const { result, value } = await runJsonCommand('bash', [script, BAIDU_QUERY, '5'], 60000);
      assert(Array.isArray(value), 'baidu search should return a JSON array');
      assert(value.length > 0, 'baidu search should return at least one result');
      assert(typeof value[0]?.url === 'string' && value[0].url.startsWith('http'), 'baidu search result should include a valid URL');
      assert(typeof value[0]?.title === 'string' && value[0].title.length > 0, 'baidu search result should include a non-empty title');
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { result_count: value.length, first_url: value[0].url },
      };
    },
  },
  {
    name: 'site.weixin-sogou.search.smoke',
    scope: 'site',
    site: 'weixin-sogou',
    workflow: 'search',
    level: 'smoke',
    setupHint: 'Make sure at least one Chrome tab is open before running Weixin-Sogou smoke tests.',
    failHint: 'Check scripts/sites/weixin-sogou/search.sh and references/sites/weixin-sogou/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'weixin-sogou', 'search.sh');
      const { result, value } = await runJsonCommand('bash', [script, SOGOU_QUERY, '5'], 60000);
      assert(Array.isArray(value), 'weixin-sogou search should return a JSON array');
      assert(value.length > 0, 'weixin-sogou search should return at least one result');
      assert(typeof value[0]?.link === 'string' && value[0].link.includes('weixin.sogou.com'), 'weixin-sogou search result should include a sogou link');
      assert(typeof value[0]?.title === 'string' && value[0].title.length > 0, 'weixin-sogou search result should include a non-empty title');
      assert(typeof value[0]?.account === 'string', 'weixin-sogou search result should include an account field');
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { result_count: value.length, first_title: value[0].title, first_account: value[0].account },
      };
    },
  },
  {
    name: 'site.reddit.search.smoke',
    scope: 'site',
    site: 'reddit',
    workflow: 'search',
    level: 'smoke',
    setupHint: 'Open a usable reddit.com tab in Chrome before running Reddit smoke tests.',
    failHint: 'Check scripts/sites/reddit/search.sh and references/sites/reddit/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'reddit', 'search.sh');
      const { result, value } = await runJsonCommand('bash', [script, REDDIT_QUERY, '3'], 60000);
      assert(Array.isArray(value), 'reddit search should return a JSON array');
      assert(value.length > 0, 'reddit search should return at least one result');
      assert(typeof value[0]?.url === 'string' && value[0].url.startsWith('https://www.reddit.com/'), 'reddit search result should include a Reddit URL');
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { result_count: value.length, first_url: value[0].url },
      };
    },
  },
  {
    name: 'site.reddit.open_post.smoke',
    scope: 'site',
    site: 'reddit',
    workflow: 'open_post',
    level: 'smoke',
    setupHint: 'Open a usable reddit.com tab in Chrome before running Reddit smoke tests.',
    failHint: 'Check scripts/sites/reddit/open-post.sh and references/sites/reddit/workflows.md.',
    async run() {
      const searchScript = resolve(SITE_SCRIPTS_DIR, 'reddit', 'search.sh');
      const openScript = resolve(SITE_SCRIPTS_DIR, 'reddit', 'open-post.sh');
      const searchRun = await runJsonCommand('bash', [searchScript, REDDIT_QUERY, '3'], 60000);
      const searchResults = searchRun.value;
      assert(Array.isArray(searchResults) && searchResults.length > 0, 'reddit search must return at least one result before open-post');
      const postUrl = searchResults[0].url;
      const openRun = await runJsonCommand('bash', [openScript, postUrl, '3'], 60000);
      const post = openRun.value;
      assert(post && typeof post === 'object' && !Array.isArray(post), 'reddit open-post should return a JSON object');
      assert(typeof post.title === 'string' && post.title.length > 0, 'reddit open-post should include a title');
      assert(typeof post.url === 'string' && post.url.includes('/comments/'), 'reddit open-post should include the navigated post URL');
      assert(Array.isArray(post.comments), 'reddit open-post should include a comments array');
      return {
        status: 'pass',
        command: openRun.result.command,
        commands: [searchRun.result.command, openRun.result.command],
        stdout_excerpt: openRun.result.stdout.slice(0, 400),
        data: { url: post.url, comment_count: post.comments.length },
      };
    },
  },
  {
    name: 'site.taoguba.search.smoke',
    scope: 'site',
    site: 'taoguba',
    workflow: 'search',
    level: 'smoke',
    setupHint: 'Sign in to Taoguba in the CDP Chrome profile before running this smoke test.',
    failHint: 'Check scripts/sites/taoguba/search.sh and references/sites/taoguba/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'taoguba', 'search.sh');
      const { result, value } = await runJsonCommand(
        'bash',
        [script, '1112 复盘', '5', '--year', '2024', '--sort', 'hot'],
        60000,
      );
      assert(value && typeof value === 'object' && !Array.isArray(value), 'taoguba search should return a JSON object');
      assert(value.ok === true, 'taoguba search should report success');
      assert(value.applied_filters?.year === '2024', 'taoguba search should verify the requested year');
      assert(value.applied_filters?.sort === 'hot', 'taoguba search should verify hot sorting');
      assert(Array.isArray(value.results) && value.results.length > 0, 'taoguba search should return result cards');
      assert(
        value.results.every((item) => item.displayed_time?.startsWith('2024-')),
        'taoguba search results should stay inside the requested year',
      );
      assert(
        value.results.every((item) => item.url?.startsWith('https://www.tgb.cn/a/')),
        'taoguba search results should contain Taoguba post URLs',
      );
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: {
          result_count: value.result_count,
          year: value.applied_filters.year,
          sort: value.applied_filters.sort,
        },
      };
    },
  },
  {
    name: 'site.taoguba.login.smoke',
    scope: 'site',
    site: 'taoguba',
    workflow: 'login',
    level: 'smoke',
    setupHint: 'Save Taoguba account credentials in the CDP Chrome profile before running this smoke test.',
    failHint: 'Check scripts/sites/taoguba/login.sh and references/sites/taoguba/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'taoguba', 'login.sh');
      const { result, value } = await runJsonCommand('bash', [script, '15'], 30000);
      assert(value && typeof value === 'object' && !Array.isArray(value), 'taoguba login should return a JSON object');
      assert(value.ok === true, 'taoguba login should report success');
      assert(
        value.status === 'logged_in' || value.status === 'already_logged_in',
        'taoguba login should return a stable success status',
      );
      assert(!Object.hasOwn(value, 'username'), 'taoguba login must not return a username');
      assert(!Object.hasOwn(value, 'password'), 'taoguba login must not return a password');
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { status: value.status },
      };
    },
  },
  {
    name: 'site.taoguba.jinghua.smoke',
    scope: 'site',
    site: 'taoguba',
    workflow: 'jinghua',
    level: 'smoke',
    setupHint: 'Open a usable Taoguba tab in Chrome before running Taoguba smoke tests.',
    failHint: 'Check scripts/sites/taoguba/jinghua.sh and references/sites/taoguba/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'taoguba', 'jinghua.sh');
      const { result, value } = await runJsonCommand('bash', [script, String(TAOGUBA_HOURS), String(TAOGUBA_LIMIT)], 60000);
      assert(Array.isArray(value), 'taoguba jinghua should return a JSON array');
      assert(value.length > 0, 'taoguba jinghua should return at least one result');
      assert(typeof value[0]?.url === 'string' && value[0].url.startsWith('https://www.tgb.cn/a/'), 'taoguba jinghua result should include a post URL');
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { result_count: value.length, first_url: value[0].url },
      };
    },
  },
  {
    name: 'site.taoguba.open_post.smoke',
    scope: 'site',
    site: 'taoguba',
    workflow: 'open_post',
    level: 'smoke',
    setupHint: 'Open a usable Taoguba tab in Chrome before running Taoguba smoke tests.',
    failHint: 'Check scripts/sites/taoguba/open-post.sh and references/sites/taoguba/workflows.md.',
    async run() {
      const listScript = resolve(SITE_SCRIPTS_DIR, 'taoguba', 'jinghua.sh');
      const openScript = resolve(SITE_SCRIPTS_DIR, 'taoguba', 'open-post.sh');
      const listRun = await runJsonCommand('bash', [listScript, String(TAOGUBA_HOURS), String(TAOGUBA_LIMIT)], 60000);
      const results = listRun.value;
      assert(Array.isArray(results) && results.length > 0, 'taoguba jinghua must return at least one result before open-post');
      const postUrl = results[0].url;
      const openRun = await runJsonCommand('bash', [openScript, postUrl], 60000);
      const post = openRun.value;
      assert(post && typeof post === 'object' && !Array.isArray(post), 'taoguba open-post should return a JSON object');
      assert(typeof post.title === 'string' && post.title.length > 0, 'taoguba open-post should include a title');
      assert(typeof post.url === 'string' && post.url.startsWith('https://www.tgb.cn/a/'), 'taoguba open-post should include the navigated post URL');
      return {
        status: 'pass',
        command: openRun.result.command,
        commands: [listRun.result.command, openRun.result.command],
        stdout_excerpt: openRun.result.stdout.slice(0, 400),
        data: { url: post.url },
      };
    },
  },
  {
    name: 'site.taoguba.following.smoke',
    scope: 'site',
    site: 'taoguba',
    workflow: 'following',
    level: 'smoke',
    setupHint: 'Open a usable Taoguba tab in Chrome before running Taoguba smoke tests.',
    failHint: 'Check scripts/sites/taoguba/following.sh and references/sites/taoguba/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'taoguba', 'following.sh');
      const { result, value } = await runJsonCommand('bash', [script, String(TAOGUBA_HOURS), String(TAOGUBA_LIMIT)], 60000);
      assert(Array.isArray(value), 'taoguba following should return a JSON array');
      if (value.length > 0) {
        assert(typeof value[0]?.actor === 'string', 'taoguba following result should include an actor field');
        assert(typeof value[0]?.update_time === 'string', 'taoguba following result should include an update_time field');
      }
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { result_count: value.length },
      };
    },
  },
  {
    name: 'site.kdocs.search.smoke',
    scope: 'site',
    site: 'kdocs',
    workflow: 'search',
    level: 'smoke',
    setupHint: 'Open a 365.kdocs.cn/latest tab in Chrome before running kdocs smoke tests.',
    failHint: 'Check scripts/sites/kdocs/search.sh and references/sites/kdocs/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'kdocs', 'search.sh');
      const { result, value } = await runJsonCommand('bash', [script, KDOCS_QUERY, '3'], 60000);
      assert(Array.isArray(value), 'kdocs search should return a JSON array');
      assert(value.length > 0, 'kdocs search should return at least one result');
      assert(
        typeof value[0]?.file_key === 'string' && value[0].file_key.startsWith('file_'),
        'kdocs search result should include a file_key starting with "file_"'
      );
      assert(
        typeof value[0]?.title === 'string' && value[0].title.length > 0,
        'kdocs search result should include a non-empty title'
      );
      assert(
        typeof value[0]?.is_latest === 'boolean',
        'kdocs search result should include an is_latest boolean'
      );
      return {
        status: 'pass',
        command: result.command,
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { result_count: value.length },
      };
    },
  },
  {
    name: 'site.kdocs.ask_ai.smoke',
    scope: 'site',
    site: 'kdocs',
    workflow: 'ask_ai',
    level: 'smoke',
    setupHint: 'Open a 365.kdocs.cn/latest tab with Docs Chat enabled before running kdocs AI QA smoke tests.',
    failHint: 'Check scripts/sites/kdocs/ask-ai.sh and references/sites/kdocs/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'kdocs', 'ask-ai.sh');
      const { result, value } = await runJsonCommand('bash', [script, KDOCS_AI_QUERY], 90000);
      assert(value && typeof value === 'object' && !Array.isArray(value), 'kdocs ask-ai should return a JSON object');
      assert(
        typeof value.question === 'string' && value.question.length > 0,
        'kdocs ask-ai result should include the original question'
      );
      assert(
        typeof value.answer === 'string' && value.answer.length > 0,
        'kdocs ask-ai result should include a non-empty answer'
      );
      assert(
        value.scope === 'all_parsed_files',
        'kdocs ask-ai result should report the current Docs Chat scope'
      );
      assert(
        Array.isArray(value.references),
        'kdocs ask-ai result should include a references array'
      );
      assert(
        typeof value.main_target === 'string' && value.main_target.length > 0,
        'kdocs ask-ai result should include a non-empty main_target'
      );
      return {
        status: 'pass',
        command: result.command,
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { reference_count: value.references.length },
      };
    },
  },
  {
    name: 'site.kdocs.close_doc_guard.smoke',
    scope: 'site',
    site: 'kdocs',
    workflow: 'close_doc_guard',
    level: 'smoke',
    setupHint: 'Open a 365.kdocs.cn/latest tab in Chrome before running kdocs close-doc guard tests.',
    failHint: 'Check scripts/sites/kdocs/close-doc.sh and references/sites/kdocs/workflows.md.',
    async run() {
      const script = resolve(TESTS_DIR, 'sites', 'kdocs', 'close-doc-guard-smoke.sh');
      const result = await runCommand('bash', [script], 60000);
      assert(result.exitCode === 0, 'kdocs close-doc guard smoke should exit successfully');
      assert(
        /refusing to close non-document tab/i.test(result.stdout),
        'kdocs close-doc guard smoke should confirm the main tab was rejected'
      );
      return {
        status: 'pass',
        command: result.command,
        stdout_excerpt: result.stdout.slice(0, 400),
      };
    },
  },
  {
    name: 'site.x.search.smoke',
    scope: 'site',
    site: 'x',
    workflow: 'search',
    level: 'smoke',
    setupHint: 'Open a usable x.com tab in Chrome before running X smoke tests.',
    failHint: 'Check scripts/sites/x/search.sh and references/sites/x/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'x', 'search.sh');
      const { result, value } = await runJsonCommand('bash', [script, X_QUERY, '3'], 60000);
      assert(Array.isArray(value), 'x search should return a JSON array');
      assert(value.length > 0, 'x search should return at least one result');
      assert(typeof value[0]?.url === 'string' && value[0].url.startsWith('https://x.com/'), 'x search result should include an X status URL');
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { result_count: value.length, first_url: value[0].url },
      };
    },
  },
  {
    name: 'site.x.open_post.smoke',
    scope: 'site',
    site: 'x',
    workflow: 'open_post',
    level: 'smoke',
    setupHint: 'Open a usable x.com tab in Chrome before running X smoke tests.',
    failHint: 'Check scripts/sites/x/open-post.sh and references/sites/x/workflows.md.',
    async run() {
      const searchScript = resolve(SITE_SCRIPTS_DIR, 'x', 'search.sh');
      const openScript = resolve(SITE_SCRIPTS_DIR, 'x', 'open-post.sh');
      const searchRun = await runJsonCommand('bash', [searchScript, X_QUERY, '3'], 60000);
      const results = searchRun.value;
      assert(Array.isArray(results) && results.length > 0, 'x search must return at least one result before open-post');
      const postUrl = results[0].url;
      const openRun = await runJsonCommand('bash', [openScript, postUrl], 60000);
      const post = openRun.value;
      assert(post && typeof post === 'object' && !Array.isArray(post), 'x open-post should return a JSON object');
      assert(typeof post.url === 'string' && post.url.startsWith('https://x.com/'), 'x open-post should include the navigated post URL');
      assert(typeof post.text === 'string' && post.text.length > 0, 'x open-post should include extracted post text');
      return {
        status: 'pass',
        command: openRun.result.command,
        commands: [searchRun.result.command, openRun.result.command],
        stdout_excerpt: openRun.result.stdout.slice(0, 400),
        data: { url: post.url },
      };
    },
  },
  {
    name: 'site.xueqiu.search.smoke',
    scope: 'site',
    site: 'xueqiu',
    workflow: 'search',
    level: 'smoke',
    setupHint: 'Open a usable xueqiu.com tab in Chrome before running Xueqiu smoke tests.',
    failHint: 'Check scripts/sites/xueqiu/search.sh and references/sites/xueqiu/workflows.md.',
    async run() {
      const script = resolve(SITE_SCRIPTS_DIR, 'xueqiu', 'search.sh');
      const { result, value } = await runJsonCommand('bash', [script, XUEQIU_QUERY, '3'], 60000);
      assert(Array.isArray(value), 'xueqiu search should return a JSON array');
      assert(value.length > 0, 'xueqiu search should return at least one result');
      assert(typeof value[0]?.url === 'string' && value[0].url.startsWith('https://xueqiu.com/'), 'xueqiu search result should include a Xueqiu post URL');
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { result_count: value.length, first_url: value[0].url },
      };
    },
  },
  {
    name: 'site.xueqiu.open_post.smoke',
    scope: 'site',
    site: 'xueqiu',
    workflow: 'open_post',
    level: 'smoke',
    setupHint: 'Open a usable xueqiu.com tab in Chrome before running Xueqiu smoke tests.',
    failHint: 'Check scripts/sites/xueqiu/open-post.sh and references/sites/xueqiu/workflows.md.',
    async run() {
      const searchScript = resolve(SITE_SCRIPTS_DIR, 'xueqiu', 'search.sh');
      const openScript = resolve(SITE_SCRIPTS_DIR, 'xueqiu', 'open-post.sh');
      const searchRun = await runJsonCommand('bash', [searchScript, XUEQIU_QUERY, '3'], 60000);
      const results = searchRun.value;
      assert(Array.isArray(results) && results.length > 0, 'xueqiu search must return at least one result before open-post');
      const postUrl = results[0].url;
      const openRun = await runJsonCommand('bash', [openScript, postUrl, '3'], 60000);
      const post = openRun.value;
      assert(post && typeof post === 'object' && !Array.isArray(post), 'xueqiu open-post should return a JSON object');
      assert(typeof post.url === 'string' && post.url.startsWith('https://xueqiu.com/'), 'xueqiu open-post should include the navigated post URL');
      assert(typeof post.text === 'string' && post.text.length > 0, 'xueqiu open-post should include extracted post text');
      assert(Array.isArray(post.comments), 'xueqiu open-post should include a comments array');
      return {
        status: 'pass',
        command: openRun.result.command,
        commands: [searchRun.result.command, openRun.result.command],
        stdout_excerpt: openRun.result.stdout.slice(0, 400),
        data: { url: post.url, comment_count: post.comments.length },
      };
    },
  },
  {
    name: 'site.xueqiu.hot.smoke',
    scope: 'site',
    site: 'xueqiu',
    workflow: 'hot',
    level: 'smoke',
    setupHint: 'Open a usable xueqiu.com tab in Chrome before running Xueqiu smoke tests.',
    failHint: 'Check scripts/sites/xueqiu/hot.sh, tests/sites/xueqiu/smoke.sh, and references/sites/xueqiu/workflows.md.',
    async run() {
      const script = resolve(TESTS_DIR, 'sites', 'xueqiu', 'smoke.sh');
      const result = await runCommand('bash', [script], 60000);
      assert(result.ok, 'xueqiu hot smoke should exit successfully');
      const parsed = parseJsonOutput(result);
      assert(parsed.ok, 'xueqiu hot smoke should emit JSON');
      assert(Array.isArray(parsed.value) && parsed.value.length > 0, 'xueqiu hot smoke should return at least one result');
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: { result_count: parsed.value.length },
      };
    },
  },
  {
    name: 'site.xueqiu.stock_info.smoke',
    scope: 'site',
    site: 'xueqiu',
    workflow: 'stock_info',
    level: 'smoke',
    setupHint: 'Open a usable xueqiu.com tab in Chrome before running Xueqiu stock-info smoke tests.',
    failHint: 'Check scripts/sites/xueqiu/stock-info.sh, tests/sites/xueqiu/stock-info-smoke.sh, and references/sites/xueqiu/workflows.md.',
    async run() {
      const script = resolve(TESTS_DIR, 'sites', 'xueqiu', 'stock-info-smoke.sh');
      const result = await runCommand('bash', [script, XUEQIU_STOCK], 90000);
      assert(result.ok, 'xueqiu stock-info smoke should exit successfully');
      const parsed = parseJsonOutput(result);
      assert(parsed.ok, 'xueqiu stock-info smoke should emit JSON');
      assert(Array.isArray(parsed.value?.announcements), 'xueqiu stock-info should include announcements');
      assert(Array.isArray(parsed.value?.discussions), 'xueqiu stock-info should include discussions');
      assert(parsed.value.announcements.length > 0, 'xueqiu stock-info should return at least one announcement');
      assert(parsed.value.discussions.length > 0, 'xueqiu stock-info should return at least one discussion');
      return {
        status: 'pass',
        command: result.command,
        commands: [result.command],
        stdout_excerpt: result.stdout.slice(0, 400),
        data: {
          stock_url: parsed.value.stock_url,
          announcement_count: parsed.value.announcements.length,
          discussion_count: parsed.value.discussions.length,
        },
      };
    },
  },
];

function selectTests(args) {
  const [mode, site] = args;
  if (!mode) usage();
  if (mode === 'list') return { mode, tests: [] };
  if (mode === 'all') return { mode, tests };
  if (mode === 'core') return { mode, tests: tests.filter((test) => test.scope === 'core') };
  if (mode === 'site') {
    if (!site) usage();
    const selected = tests.filter((test) => test.site === site);
    if (!selected.length) {
      console.error(`unknown site: ${site}`);
      process.exit(1);
    }
    return { mode: `${mode}:${site}`, tests: selected };
  }
  usage();
}

function printHumanSummary(summary) {
  for (const result of summary.results) {
    const status = result.status.toUpperCase().padEnd(4, ' ');
    const duration = `${result.duration_ms}ms`.padStart(6, ' ');
    console.log(`${status} ${duration} ${result.name}`);
    if (result.hint && result.status !== 'pass') {
      console.log(`      hint: ${result.hint}`);
    }
    if (result.stderr_excerpt && result.status !== 'pass') {
      console.log(`      stderr: ${result.stderr_excerpt.split('\n')[0]}`);
    }
  }
  console.log('');
  const allSkipped = summary.pass_count === 0 && summary.fail_count === 0 && summary.skip_count > 0;
  console.log(`Summary: ${summary.pass_count} passed, ${summary.fail_count} failed, ${summary.skip_count} skipped${allSkipped ? ' (all skipped — check browser/setup prerequisites)' : ''}`);
}

function computeOk(results) {
  if (results.some((result) => result.status === 'fail')) return false;
  if (results.every((result) => result.status === 'skip')) return false;
  return results.some((result) => result.status === 'pass');
}

async function main() {
  const selection = selectTests(positionals);
  if (selection.mode === 'list') {
    const payload = tests.map((test) => ({
      name: test.name,
      scope: test.scope,
      site: test.site,
      workflow: test.workflow,
      level: test.level,
    }));
    if (options.json) {
      console.log(JSON.stringify(payload, null, 2));
    } else {
      for (const test of payload) {
        console.log(`${test.name}`);
      }
    }
    return;
  }

  const results = [];
  for (const test of selection.tests) {
    const result = await runCase(test);
    results.push(result);
    if (options.failFast && result.status === 'fail') break;
  }

  const summary = {
    ok: computeOk(results),
    suite: selection.mode,
    generated_at: new Date().toISOString(),
    env: {
      reddit_query: REDDIT_QUERY,
      x_query: X_QUERY,
      xueqiu_query: XUEQIU_QUERY,
      xueqiu_stock: XUEQIU_STOCK,
      taoguba_hours: TAOGUBA_HOURS,
      taoguba_limit: TAOGUBA_LIMIT,
    },
    pass_count: results.filter((result) => result.status === 'pass').length,
    fail_count: results.filter((result) => result.status === 'fail').length,
    skip_count: results.filter((result) => result.status === 'skip').length,
    results,
  };

  if (options.json) {
    console.log(JSON.stringify(summary, null, 2));
  } else {
    printHumanSummary(summary);
  }

  process.exit(summary.ok ? 0 : 1);
}

main().catch((error) => {
  console.error(toErrorMessage(error));
  process.exit(1);
});
