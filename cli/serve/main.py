#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["typer", "rich"]
# ///
"""omp serve — Local project workbench for skill development."""

from __future__ import annotations

import html
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

APP_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>omp-serve</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.20.1/cdn/themes/dark.css">
  <style>
    :root {
      --bg: #10100e;
      --panel: #191814;
      --ink: #f3ecdd;
      --muted: #b3aa9b;
      --faint: #7c7467;
      --line: rgba(243, 236, 221, .10);
      --green: #a4d86f;
      --amber: #e9b85f;
      --red: #ed806c;
      --cyan: #7bcbd1;
      --shadow: 0 18px 44px rgba(0, 0, 0, .28);
      --mono: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;
      --sans: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    body[data-theme="light"] {
      --bg: #f4efe4;
      --panel: #fbf7ed;
      --ink: #25231d;
      --muted: #5f5a4d;
      --faint: #8c8474;
      --line: rgba(42, 37, 27, .12);
      --green: #517d46;
      --amber: #9b6a1d;
      --red: #aa4f3c;
      --cyan: #3c7b82;
      --shadow: 0 16px 34px rgba(61, 51, 31, .12);
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; height: 100%; overflow: hidden; }
    body {
      background:
        radial-gradient(circle at 15% 12%, rgba(164,216,111,.10), transparent 30%),
        radial-gradient(circle at 86% 78%, rgba(123,203,209,.08), transparent 28%),
        linear-gradient(rgba(243,236,221,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(243,236,221,.018) 1px, transparent 1px),
        var(--bg);
      background-size: auto, auto, 20px 20px, 20px 20px;
      color: var(--ink);
      font-family: var(--sans);
      letter-spacing: 0;
    }
    body[data-theme="light"] {
      background:
        radial-gradient(circle at 18% 12%, rgba(81,125,70,.12), transparent 30%),
        radial-gradient(circle at 88% 78%, rgba(60,123,130,.10), transparent 28%),
        linear-gradient(rgba(42,37,27,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(42,37,27,.025) 1px, transparent 1px),
        var(--bg);
      background-size: auto, auto, 20px 20px, 20px 20px;
    }
    button, textarea, input { font: inherit; }
    button { cursor: pointer; }
    .app { height: 100vh; padding: 12px; display: grid; grid-template-rows: 44px 1fr 30px; gap: 10px; }
    .top, .bottom {
      display: flex;
      align-items: center;
      gap: 12px;
      background: rgba(25,24,20,.78);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 0 12px;
      box-shadow: 0 10px 28px rgba(0,0,0,.18);
      backdrop-filter: blur(16px);
    }
    .bottom { color: var(--faint); font: 11px/1 var(--mono); box-shadow: none; min-width: 0; }
    .brand { display: flex; align-items: center; gap: 9px; min-width: 150px; font-weight: 750; }
    .pulse { width: 9px; height: 9px; border-radius: 50%; background: var(--green); box-shadow: 0 0 18px rgba(164,216,111,.7); }
    .cmd {
      flex: 1;
      height: 28px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(10,10,8,.58);
      color: var(--muted);
      padding: 0 12px;
      font: 12px/26px var(--mono);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .state {
      height: 28px;
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      background: rgba(164,216,111,.11);
      color: var(--green);
      padding: 0 10px;
      font: 11px/1 var(--mono);
      white-space: nowrap;
    }
    .theme-toggle {
      height: 28px;
      border: 0;
      border-radius: 999px;
      background: rgba(164,216,111,.11);
      color: var(--green);
      padding: 0 10px;
      font: 700 11px/1 var(--mono);
      text-transform: uppercase;
      letter-spacing: .06em;
      white-space: nowrap;
    }
    .theme-toggle:hover { background: rgba(164,216,111,.17); }
    .shell { min-height: 0; display: grid; grid-template-columns: 252px minmax(440px, 1fr) minmax(390px, .86fr); gap: 10px; }
    .files, .editor, .agent {
      min-width: 0;
      min-height: 0;
      background: rgba(16,16,14,.74);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: 0 14px 34px rgba(0, 0, 0, .24);
      overflow: hidden;
      display: grid;
      grid-template-rows: 44px 1fr;
    }
    .agent { grid-template-rows: 44px minmax(0, 1fr) 150px; }
    .head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 14px;
      color: var(--muted);
      font: 700 11px/1 var(--mono);
      text-transform: uppercase;
      letter-spacing: .08em;
      min-width: 0;
    }
    .head span:last-child { color: var(--faint); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .file-list { overflow: auto; padding: 10px; background: transparent; }
    .file-list::-webkit-scrollbar, .preview::-webkit-scrollbar, .diff-view::-webkit-scrollbar { width: 10px; height: 10px; }
    .file-list::-webkit-scrollbar-thumb, .preview::-webkit-scrollbar-thumb, .diff-view::-webkit-scrollbar-thumb {
      background: rgba(243,236,221,.16);
      border-radius: 999px;
      border: 3px solid transparent;
      background-clip: content-box;
    }
    sl-tree {
      --indent-guide-width: 0;
      --indent-size: 8px;
      color: var(--muted);
      font: 12px/1 var(--mono);
    }
    sl-tree-item::part(item) {
      min-height: 30px;
      border-radius: 11px;
      margin: 2px 0;
      border: 0;
      box-shadow: none;
      outline: 0;
      color: var(--muted);
    }
    sl-tree-item::part(item):hover { background: rgba(34,32,25,.72); }
    sl-tree-item::part(item--selected) {
      background: rgba(34,32,25,.72);
      color: var(--ink);
      border: 0;
      box-shadow: none;
      outline: 0;
    }
    sl-tree-item::part(label) { border: 0; box-shadow: none; outline: 0; font: 12px/1 var(--mono); }
    sl-tree-item.folder::part(label) { color: var(--amber); }
    sl-tree-item.empty::part(label) { color: var(--faint); font-style: italic; }
    .badge { margin-left: auto; color: var(--green); background: rgba(164,216,111,.11); border-radius: 999px; padding: 3px 7px; font-size: 10px; }
    .editor-body { min-height: 0; display: grid; grid-template-rows: 34px 1fr; gap: 10px; padding: 0 10px 10px; }
    .editor-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      min-width: 0;
      padding: 0 2px;
    }
    .tabs, .mode-tabs { display: flex; align-items: center; gap: 4px; min-width: 0; }
    .tabs { overflow: hidden; }
    .tab {
      border: 0;
      border-radius: 8px;
      background: transparent;
      color: var(--faint);
      padding: 0 6px;
      font: 700 10px/24px var(--mono);
      text-transform: uppercase;
      letter-spacing: .08em;
      white-space: nowrap;
    }
    .tab:hover { color: var(--muted); background: transparent; }
    .tab.file.active {
      color: var(--faint);
      background: transparent;
      max-width: 280px;
      overflow: hidden;
      text-overflow: ellipsis;
      padding-left: 0;
      text-transform: none;
      letter-spacing: 0;
      font-weight: 600;
    }
    .tab.mode { color: var(--faint); background: transparent; }
    .tab.mode.active { color: var(--amber); background: transparent; }
    .tab.save { color: var(--faint); background: transparent; }
    .tab.save.dirty { color: var(--green); background: rgba(164,216,111,.10); }
    .editor-surface {
      min-height: 0;
      border-radius: 18px;
      background: rgba(8,8,7,.64);
      overflow: hidden;
    }
    textarea.editor-text {
      width: 100%;
      height: 100%;
      resize: none;
      border: 0;
      background: transparent;
      color: var(--ink);
      padding: 16px;
      outline: none;
      font: 13px/1.72 var(--mono);
      tab-size: 2;
    }
    .preview, .diff-view {
      height: 100%;
      overflow: auto;
      padding: 22px;
      font-size: 14px;
      line-height: 1.7;
      color: var(--muted);
    }
    .preview h1, .preview h2, .preview h3 { color: var(--ink); line-height: 1.22; }
    .preview h1 { font-size: 28px; }
    .preview h2 { font-size: 20px; margin-top: 28px; }
    .preview code, .diff-view code { font-family: var(--mono); color: var(--amber); }
    .preview pre, .diff-view pre { background: rgba(0,0,0,.25); border-radius: 14px; padding: 14px; overflow: auto; }
    .preview blockquote { margin-left: 0; padding-left: 14px; border-left: 3px solid rgba(164,216,111,.28); color: var(--faint); }
    .preview table { border-collapse: collapse; width: 100%; }
    .preview th, .preview td { border-bottom: 1px solid var(--line); padding: 6px 8px; text-align: left; }
    .html-frame { width: 100%; height: 100%; border: 0; background: #fff; border-radius: 16px; }
    .empty { height: 100%; display: grid; place-items: center; color: var(--faint); font: 13px/1.5 var(--mono); text-align: center; padding: 24px; }
    .agent-stream { min-height: 0; overflow-y: auto; overflow-x: hidden; padding: 10px; display: flex; flex-direction: column; gap: 10px; }
    .agent-stream::-webkit-scrollbar { width: 10px; }
    .agent-stream::-webkit-scrollbar-thumb { background: rgba(243,236,221,.16); border-radius: 999px; border: 3px solid transparent; background-clip: content-box; }
    .turn { flex: 0 0 auto; background: rgba(34,32,25,.72); border: 1px solid var(--line); border-radius: 18px; overflow: hidden; }
    .turn.user { background: rgba(123,203,209,.07); }
    .turn-head { display: flex; align-items: center; justify-content: space-between; min-height: 34px; padding: 0 12px; color: var(--faint); font: 700 10px/1 var(--mono); text-transform: uppercase; }
    .turn.user .turn-head { color: var(--cyan); }
    .turn.assistant .turn-head { color: var(--green); }
    .turn-body { padding: 0 12px 13px; }
    .turn-body p { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.6; white-space: pre-wrap; }
    .assistant-md { color: var(--muted); font-size: 13px; line-height: 1.65; }
    .assistant-md > :first-child { margin-top: 0; }
    .assistant-md > :last-child { margin-bottom: 0; }
    .assistant-md h1, .assistant-md h2, .assistant-md h3 { color: var(--ink); line-height: 1.25; }
    .assistant-md h1 { font-size: 18px; }
    .assistant-md h2 { font-size: 15px; margin-top: 16px; }
    .assistant-md h3 { font-size: 13px; margin-top: 14px; }
    .assistant-md p, .assistant-md ul, .assistant-md ol, .assistant-md blockquote, .assistant-md pre, .assistant-md table { margin: 0 0 10px; }
    .assistant-md code { font-family: var(--mono); color: var(--amber); }
    .assistant-md pre { background: rgba(8,8,7,.56); border-radius: 12px; padding: 10px; overflow: auto; }
    .assistant-md blockquote { margin-left: 0; padding-left: 12px; border-left: 2px solid rgba(164,216,111,.24); color: var(--faint); }
    .assistant-md table { border-collapse: collapse; width: 100%; }
    .assistant-md th, .assistant-md td { border-bottom: 1px solid var(--line); padding: 5px 6px; text-align: left; }
    .timeline { margin: 0 0 12px; display: grid; gap: 7px; }
    .step { display: flex; align-items: center; gap: 9px; min-height: 28px; border-radius: 999px; background: rgba(16,16,14,.52); padding: 0 10px; color: var(--muted); font: 12px/1.35 var(--mono); }
    .step::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--faint); flex: 0 0 auto; }
    .step.done::before { background: var(--green); box-shadow: 0 0 10px rgba(164,216,111,.44); }
    .step.patch::before { background: var(--amber); box-shadow: 0 0 10px rgba(233,184,95,.38); }
    .composer { height: 150px; min-height: 150px; padding: 0 10px 10px; background: transparent; }
    .input-box {
      width: 100%;
      height: 100%;
      display: grid;
      grid-template-rows: minmax(0, 1fr) 38px;
      background: rgba(8,8,7,.64);
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
    }
    textarea.chat {
      width: 100%;
      height: 100%;
      resize: none;
      background: transparent;
      border: 0;
      color: var(--ink);
      padding: 12px;
      outline: none;
      font-size: 13px;
    }
    .input-box:focus-within { border-color: rgba(164,216,111,.42); box-shadow: 0 0 0 3px rgba(164,216,111,.08); }
    .compose-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0 8px 8px 12px;
      color: var(--faint);
      font: 700 10px/1 var(--mono);
      text-transform: uppercase;
      letter-spacing: .08em;
    }
    .send { height: 30px; border: 0; border-radius: 999px; background: var(--green); color: #10100e; padding: 0 14px; font-size: 12px; font-weight: 750; }
    .send:disabled { opacity: .45; cursor: default; }
    body[data-theme="light"] .top,
    body[data-theme="light"] .bottom {
      background: rgba(251,247,237,.76);
      box-shadow: 0 10px 26px rgba(61,51,31,.10);
    }
    body[data-theme="light"] .cmd,
    body[data-theme="light"] .editor-surface,
    body[data-theme="light"] .input-box {
      background: rgba(255,252,246,.74);
    }
    body[data-theme="light"] .files,
    body[data-theme="light"] .editor,
    body[data-theme="light"] .agent {
      background: rgba(251,247,237,.72);
      box-shadow: var(--shadow);
    }
    body[data-theme="light"] sl-tree-item::part(item):hover,
    body[data-theme="light"] sl-tree-item::part(item--selected),
    body[data-theme="light"] .turn,
    body[data-theme="light"] .step {
      background: rgba(255,252,246,.78);
    }
    body[data-theme="light"] .turn.user { background: rgba(60,123,130,.08); }
    body[data-theme="light"] .preview pre,
    body[data-theme="light"] .diff-view pre,
    body[data-theme="light"] .assistant-md pre {
      background: rgba(42,37,27,.06);
    }
    body[data-theme="light"] .file-list::-webkit-scrollbar-thumb,
    body[data-theme="light"] .preview::-webkit-scrollbar-thumb,
    body[data-theme="light"] .diff-view::-webkit-scrollbar-thumb,
    body[data-theme="light"] .agent-stream::-webkit-scrollbar-thumb {
      background: rgba(42,37,27,.20);
      border: 3px solid transparent;
      background-clip: content-box;
    }
    body[data-theme="light"] .send {
      color: #fbf7ed;
    }
    @media (max-width: 1100px) {
      .shell { grid-template-columns: 220px 1fr; }
      .agent { position: fixed; right: 12px; top: 66px; bottom: 52px; width: 390px; box-shadow: -20px 0 48px rgba(0,0,0,.36); }
    }
    @media (max-width: 780px) {
      .files { display: none; }
      .shell { grid-template-columns: 1fr; }
      .agent { display: none; }
      .brand { min-width: auto; }
      .cmd { display: none; }
    }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
  <script type="module" src="https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.20.1/cdn/components/tree/tree.js"></script>
  <script type="module" src="https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.20.1/cdn/components/tree-item/tree-item.js"></script>
</head>
<body data-theme="dark">
  <div class="app">
    <header class="top">
      <div class="brand"><span class="pulse"></span><span>omp-serve</span></div>
      <div class="cmd" id="workspace-label">Loading workspace...</div>
      <button class="theme-toggle" id="theme-toggle">Light</button>
      <div class="state">approved</div>
    </header>
    <main class="shell">
      <aside class="files">
        <div class="head"><span>Files</span><span id="tree-count">0</span></div>
        <div class="file-list"><sl-tree id="file-tree" selection="single"></sl-tree></div>
      </aside>
      <section class="editor">
        <div class="head"><span>Editor</span><span id="file-status">no file</span></div>
        <div class="editor-body">
          <div class="editor-toolbar">
            <div class="tabs"><button class="tab file active" id="active-file">Select a file</button></div>
            <div class="mode-tabs">
              <button class="tab mode active" data-mode="preview">Preview</button>
              <button class="tab mode" data-mode="edit">Edit</button>
              <button class="tab mode" data-mode="diff">Diff</button>
              <button class="tab save" id="save-btn">Save</button>
            </div>
          </div>
          <div class="editor-surface" id="editor-surface"></div>
        </div>
      </section>
      <aside class="agent">
        <div class="head"><span>Assistant</span><span id="chat-status">idle</span></div>
        <div class="agent-stream" id="chat-log"></div>
        <div class="composer">
          <div class="input-box">
            <textarea class="chat" id="chat-input" placeholder="Ask the assistant to inspect or edit this skill..."></textarea>
            <div class="compose-footer"><span>Message</span><button class="send" id="send-btn">Send</button></div>
          </div>
        </div>
      </aside>
    </main>
    <footer class="bottom">
      <span>Pi JSON mode</span><span id="session-label">session: project-local</span><span id="mode-label">mode: edit</span><span id="dirty-label">clean</span>
    </footer>
  </div>
  <script>
    const state = {
      workspace: '',
      sessionId: '',
      selectedPath: '',
      original: '',
      content: '',
      mode: 'preview',
      dirty: false,
      sending: false,
      assistantEl: null,
      assistantTextEl: null,
      assistantRaw: '',
      toolListEl: null,
      toolSteps: new Map(),
    };

    const $ = (id) => document.getElementById(id);
    const esc = (value) => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

    function setTheme(theme) {
      const next = theme === 'light' ? 'light' : 'dark';
      document.body.dataset.theme = next;
      localStorage.setItem('ompServeTheme', next);
      $('theme-toggle').textContent = next === 'light' ? 'Dark' : 'Light';
    }

    function toggleTheme() {
      setTheme(document.body.dataset.theme === 'light' ? 'dark' : 'light');
    }

    function newSessionId() {
      if (crypto?.randomUUID) return crypto.randomUUID();
      return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
    }

    function ext(path) {
      const idx = path.lastIndexOf('.');
      return idx === -1 ? '' : path.slice(idx + 1).toLowerCase();
    }

    function isMarkdown(path) { return ['md', 'mdx', 'markdown'].includes(ext(path)); }
    function isHtml(path) { return ['html', 'htm'].includes(ext(path)); }

    async function api(path, options) {
      const res = await fetch(path, options);
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `${res.status} ${res.statusText}`);
      }
      return res;
    }

    async function loadMeta() {
      const data = await (await api('/api/meta')).json();
      state.workspace = data.workspace;
      $('workspace-label').textContent = `pi -p --mode json --approve · ${data.workspace} · ${data.model}`;
    }

    async function loadTree() {
      const tree = $('file-tree');
      const data = await loadDirectory('');
      tree.innerHTML = '';
      $('tree-count').textContent = String(data.count);
      for (const node of data.nodes) tree.appendChild(createTreeItem(node));
    }

    async function loadDirectory(path) {
      const data = await (await api(`/api/tree?path=${encodeURIComponent(path || '')}`)).json();
      return data;
    }

    function createTreeItem(node) {
      const item = document.createElement('sl-tree-item');
      item.textContent = node.name;
      item.title = node.path;
      item.dataset.path = node.path;
      item.dataset.type = node.type;
      item.classList.add(node.type === 'directory' ? 'folder' : 'file');
      if (node.type === 'directory' && node.hasChildren) item.setAttribute('lazy', '');
      if (node.path === state.selectedPath) item.selected = true;
      return item;
    }

    async function populateDirectory(item) {
      const path = item.dataset.path || '';
      const data = await loadDirectory(path);
      item.innerHTML = '';
      item.textContent = item.title.split('/').pop() || item.title;
      for (const node of data.nodes) item.appendChild(createTreeItem(node));
      if (!data.nodes.length) {
        const empty = document.createElement('sl-tree-item');
        empty.textContent = '(empty)';
        empty.disabled = true;
        empty.classList.add('empty');
        item.appendChild(empty);
      }
      item.removeAttribute('lazy');
    }

    async function selectFile(path) {
      if (state.dirty && !confirm('Discard unsaved changes?')) return;
      const data = await (await api(`/api/file?path=${encodeURIComponent(path)}`)).json();
      state.selectedPath = data.path;
      state.original = data.content ?? '';
      state.content = data.content ?? '';
      state.dirty = false;
      state.mode = 'preview';
      updateChrome();
      syncTreeSelection();
      renderEditor();
    }

    function syncTreeSelection() {
      document.querySelectorAll('sl-tree-item').forEach(item => {
        item.selected = item.dataset.path === state.selectedPath;
      });
    }

    function updateChrome() {
      $('active-file').textContent = state.selectedPath || 'Select a file';
      $('file-status').textContent = state.selectedPath ? `${state.content.length} chars` : 'no file';
      $('dirty-label').textContent = state.dirty ? 'dirty' : 'clean';
      $('save-btn').classList.toggle('dirty', state.dirty);
      document.querySelectorAll('[data-mode]').forEach(btn => btn.classList.toggle('active', btn.dataset.mode === state.mode));
      $('mode-label').textContent = `mode: ${state.mode}`;
    }

    function setMode(mode) {
      state.mode = mode;
      updateChrome();
      renderEditor();
    }

    function renderEditor() {
      const root = $('editor-surface');
      if (!state.selectedPath) {
        root.innerHTML = '<div class="empty">Select a file from the project tree.</div>';
        return;
      }
      if (state.mode === 'edit') {
        root.innerHTML = `<textarea class="editor-text" spellcheck="false">${esc(state.content)}</textarea>`;
        const ta = root.querySelector('textarea');
        ta.addEventListener('input', () => {
          state.content = ta.value;
          state.dirty = state.content !== state.original;
          updateChrome();
        });
        ta.focus();
        return;
      }
      if (state.mode === 'preview') {
        if (isMarkdown(state.selectedPath)) {
          root.innerHTML = `<div class="preview">${renderMarkdown(state.content)}</div>`;
        } else if (isHtml(state.selectedPath)) {
          root.innerHTML = `<iframe class="html-frame" sandbox="allow-scripts allow-forms allow-popups allow-modals" srcdoc="${esc(state.content)}"></iframe>`;
        } else {
          root.innerHTML = `<pre class="preview">${esc(state.content)}</pre>`;
        }
        return;
      }
      root.innerHTML = `<pre class="diff-view">${renderDiff(state.original, state.content)}</pre>`;
    }

    function renderMarkdown(markdown) {
      if (window.marked) {
        marked.setOptions({ gfm: true, breaks: false });
        return marked.parse(markdown);
      }
      return renderMarkdownFallback(markdown);
    }

    function renderMarkdownFallback(markdown) {
      const lines = markdown.split(/\r?\n/);
      let out = [];
      let inCode = false;
      let listOpen = false;
      for (const raw of lines) {
        const line = raw.replace(/\s+$/, '');
        if (line.startsWith('```')) {
          if (inCode) out.push('</code></pre>');
          else out.push('<pre><code>');
          inCode = !inCode;
          continue;
        }
        if (inCode) {
          out.push(esc(raw) + '\n');
          continue;
        }
        if (/^\s*[-*]\s+/.test(line)) {
          if (!listOpen) { out.push('<ul>'); listOpen = true; }
          out.push(`<li>${inlineMd(line.replace(/^\s*[-*]\s+/, ''))}</li>`);
          continue;
        }
        if (listOpen) { out.push('</ul>'); listOpen = false; }
        if (line.startsWith('# ')) out.push(`<h1>${inlineMd(line.slice(2))}</h1>`);
        else if (line.startsWith('## ')) out.push(`<h2>${inlineMd(line.slice(3))}</h2>`);
        else if (line.startsWith('### ')) out.push(`<h3>${inlineMd(line.slice(4))}</h3>`);
        else if (line.startsWith('> ')) out.push(`<blockquote>${inlineMd(line.slice(2))}</blockquote>`);
        else if (!line.trim()) out.push('');
        else out.push(`<p>${inlineMd(line)}</p>`);
      }
      if (listOpen) out.push('</ul>');
      if (inCode) out.push('</code></pre>');
      return out.join('\n') || '<div class="empty">No preview content.</div>';
    }

    function inlineMd(text) {
      return esc(text)
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
    }

    function renderDiff(a, b) {
      if (a === b) return 'No changes.';
      const before = a.split(/\r?\n/);
      const after = b.split(/\r?\n/);
      let out = [];
      const max = Math.max(before.length, after.length);
      for (let i = 0; i < max; i++) {
        if (before[i] === after[i]) {
          if (before[i] !== undefined) out.push(`  ${esc(before[i])}`);
        } else {
          if (before[i] !== undefined) out.push(`<span style="color:var(--red)">- ${esc(before[i])}</span>`);
          if (after[i] !== undefined) out.push(`<span style="color:var(--green)">+ ${esc(after[i])}</span>`);
        }
      }
      return out.join('\n');
    }

    async function saveFile() {
      if (!state.selectedPath) return;
      await api('/api/file', {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path: state.selectedPath, content: state.content})
      });
      state.original = state.content;
      state.dirty = false;
      updateChrome();
    }

    function addTurn(role, text) {
      const article = document.createElement('article');
      article.className = `turn ${role === 'User' ? 'user' : 'assistant'}`;
      const body = role === 'Assistant'
        ? `<div class="assistant-md">${renderMarkdown(text || '')}</div>`
        : `<p>${esc(text)}</p>`;
      article.innerHTML = `<div class="turn-head"><span>${role}</span><span>${role === 'User' ? 'prompt' : 'working'}</span></div><div class="turn-body">${body}</div>`;
      $('chat-log').appendChild(article);
      $('chat-log').scrollTop = $('chat-log').scrollHeight;
      return article;
    }

    function startAssistantTurn() {
      const article = addTurn('Assistant', '');
      state.assistantEl = article;
      state.assistantTextEl = article.querySelector('.assistant-md');
      state.assistantRaw = '';
      const timeline = document.createElement('div');
      timeline.className = 'timeline';
      article.querySelector('.turn-body').insertBefore(timeline, state.assistantTextEl);
      state.toolListEl = timeline;
    }

    function appendAssistant(delta) {
      if (!state.assistantTextEl) startAssistantTurn();
      state.assistantRaw += delta;
      state.assistantTextEl.innerHTML = renderMarkdown(state.assistantRaw);
      $('chat-log').scrollTop = $('chat-log').scrollHeight;
    }

    function addStep(text, done = false) {
      if (!state.toolListEl) startAssistantTurn();
      const step = document.createElement('div');
      step.className = `step ${done ? 'done' : 'patch'}`;
      step.textContent = text;
      state.toolListEl.appendChild(step);
      $('chat-log').scrollTop = $('chat-log').scrollHeight;
      return step;
    }

    async function sendMessage() {
      const input = $('chat-input');
      const message = input.value.trim();
      if (!message || state.sending) return;
      state.sending = true;
      $('send-btn').disabled = true;
      $('chat-status').textContent = 'running';
      addTurn('User', message);
      startAssistantTurn();
      input.value = '';
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({message, sessionId: state.sessionId})
        });
        if (!res.ok) {
          throw new Error(await res.text() || `HTTP ${res.status}`);
        }
        if (!res.body) {
          throw new Error('Streaming response body is unavailable.');
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        while (true) {
          const {value, done} = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, {stream: true});
          const chunks = buffer.split('\n\n');
          buffer = chunks.pop() || '';
          for (const chunk of chunks) {
            const line = chunk.split('\n').find(l => l.startsWith('data: '));
            if (!line) continue;
            const event = JSON.parse(line.slice(6));
            if (event.type === 'assistant_delta') appendAssistant(event.delta || '');
            if (event.type === 'tool_start') {
              const label = [event.name || 'tool', event.detail].filter(Boolean).join(': ');
              state.toolSteps.set(event.id || label, addStep(label));
            }
            if (event.type === 'tool_end') {
              const id = event.id || event.name || 'tool';
              const step = state.toolSteps.get(id);
              if (step) {
                step.classList.remove('patch');
                step.classList.add('done');
              } else {
                const label = [event.name || 'tool done', event.detail].filter(Boolean).join(': ');
                addStep(label, true);
              }
            }
            if (event.type === 'error') appendAssistant(`\n\n${event.message}`);
            if (event.type === 'done') {
              state.sending = false;
              $('send-btn').disabled = false;
              $('chat-status').textContent = 'idle';
              input.focus();
            }
          }
        }
      } catch (err) {
        appendAssistant(`\n\n${err.message || err}`);
      } finally {
        state.sending = false;
        $('send-btn').disabled = false;
        $('chat-status').textContent = 'idle';
        input.focus();
      }
    }

    document.querySelectorAll('[data-mode]').forEach(btn => btn.addEventListener('click', () => setMode(btn.dataset.mode)));
    $('save-btn').addEventListener('click', saveFile);
    $('send-btn').addEventListener('click', sendMessage);
    $('theme-toggle').addEventListener('click', toggleTheme);
    $('chat-input').addEventListener('keydown', (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') sendMessage();
    });
    $('file-tree').addEventListener('sl-selection-change', (event) => {
      const selected = event.detail.selection?.[0];
      if (selected?.dataset?.type === 'file') selectFile(selected.dataset.path);
    });
    $('file-tree').addEventListener('sl-lazy-load', async (event) => {
      await populateDirectory(event.target);
    });

    (async function boot() {
      try {
        setTheme(localStorage.getItem('ompServeTheme') || 'dark');
        state.sessionId = newSessionId();
        $('session-label').textContent = `session: ${state.sessionId.slice(0, 8)}`;
        await loadMeta();
        await loadTree();
        renderEditor();
      } catch (err) {
        $('file-list').innerHTML = `<div class="empty">${esc(err.message)}</div>`;
      }
    })();
  </script>
</body>
</html>
"""

console = Console(stderr=True)
app = typer.Typer(
    name="serve",
    help="Local project workbench for skill development.",
    no_args_is_help=False,
    add_completion=False,
    invoke_without_command=True,
)

DEFAULT_IGNORES = {
    ".agents",
    ".claude",
    ".git",
    ".hg",
    ".omp",
    ".pi",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
}

TEXT_EXTENSIONS = {
    ".css",
    ".csv",
    ".html",
    ".htm",
    ".js",
    ".json",
    ".jsonl",
    ".jsx",
    ".md",
    ".mdx",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


def _pids_on_port(port: int) -> list[int]:
    if shutil.which("fuser"):
        proc = subprocess.run(
            ["fuser", "-n", "tcp", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        return sorted({int(pid) for pid in re.findall(r"\d+", proc.stdout) if int(pid) != port})
    if shutil.which("lsof"):
        proc = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        return sorted({int(pid) for pid in re.findall(r"\d+", proc.stdout) if int(pid) != port})
    return []


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _stop_port(port: int, quiet: bool = False) -> bool:
    pids = _pids_on_port(port)
    if not pids:
        if not quiet:
            console.print(f"[omp serve] no process listening on port [cyan]{port}[/cyan]")
        return False

    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.time() + 3
    while time.time() < deadline:
        alive = [pid for pid in pids if _pid_exists(pid)]
        if not alive:
            if not quiet:
                console.print(f"[omp serve] stopped port [cyan]{port}[/cyan] ({', '.join(map(str, pids))})")
            return True
        time.sleep(0.1)

    for pid in pids:
        if not _pid_exists(pid):
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if not quiet:
        console.print(f"[omp serve] force stopped port [cyan]{port}[/cyan] ({', '.join(map(str, pids))})")
    return True


def _serve(
    workspace: Path,
    host: str,
    port: int,
    model: str,
    open_browser: bool,
) -> None:
    root = workspace.resolve()
    if not root.is_dir():
        console.print(f"[red]workspace not found:[/red] {root}")
        raise typer.Exit(1)
    state = ServeState(root, model)
    handler = _make_handler(state)
    try:
        server = ThreadingHTTPServer((host, port), handler)
    except OSError as exc:
        console.print(f"[red][omp serve] failed to bind {host}:{port}:[/red] {exc}")
        raise typer.Exit(1) from exc
    url = f"http://{host}:{port}/"
    console.print(f"[omp serve] workspace: [cyan]{root}[/cyan]")
    console.print(f"[omp serve] url: [bold]{url}[/bold]")
    console.print(f"[omp serve] pi: [cyan]pi -p --mode json --approve --session .omp/serve/sessions/<page>.jsonl[/cyan]")
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[omp serve] stopped")
    finally:
        server.server_close()


@app.callback()
def _main(
    ctx: typer.Context,
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Project workspace root."),
    host: str = typer.Option("0.0.0.0", "--host", help="HTTP host."),
    port: int = typer.Option(8765, "--port", "-p", help="HTTP port."),
    model: str = typer.Option(
        os.environ.get("OMP_DEFAULT_MODEL_PI", "openai-codex/gpt-5.4-mini"),
        "--model",
        "-m",
        help="Pi model.",
    ),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser after start."),
) -> None:
    """Start the local skill development workbench."""
    if ctx.invoked_subcommand is None:
        _serve(workspace, host, port, model, open_browser)


@app.command()
def start(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Project workspace root."),
    host: str = typer.Option("0.0.0.0", "--host", help="HTTP host."),
    port: int = typer.Option(8765, "--port", "-p", help="HTTP port."),
    model: str = typer.Option(
        os.environ.get("OMP_DEFAULT_MODEL_PI", "openai-codex/gpt-5.4-mini"),
        "--model",
        "-m",
        help="Pi model.",
    ),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser after start."),
) -> None:
    """Start the local skill development workbench."""
    _serve(workspace, host, port, model, open_browser)


@app.command()
def stop(
    port: int = typer.Option(8765, "--port", "-p", help="HTTP port."),
) -> None:
    """Stop the workbench process listening on the port."""
    _stop_port(port)


@app.command()
def restart(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Project workspace root."),
    host: str = typer.Option("0.0.0.0", "--host", help="HTTP host."),
    port: int = typer.Option(8765, "--port", "-p", help="HTTP port."),
    model: str = typer.Option(
        os.environ.get("OMP_DEFAULT_MODEL_PI", "openai-codex/gpt-5.4-mini"),
        "--model",
        "-m",
        help="Pi model.",
    ),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser after start."),
) -> None:
    """Restart the local skill development workbench."""
    _stop_port(port, quiet=True)
    _serve(workspace, host, port, model, open_browser)


class ServeState:
    def __init__(self, workspace: Path, model: str) -> None:
        self.workspace = workspace.resolve()
        self.model = model
        self.session_dir = self.workspace / ".omp" / "serve"
        self.sessions_dir = self.session_dir / "sessions"


def _is_safe(root: Path, target: Path) -> bool:
    resolved_root = root.resolve()
    resolved_target = target.resolve()
    return resolved_target == resolved_root or resolved_root in resolved_target.parents


def _resolve_rel(state: ServeState, rel_path: str) -> Path:
    target = (state.workspace / rel_path).resolve()
    if not _is_safe(state.workspace, target):
        raise ValueError("path escapes workspace")
    return target


def _session_path(state: ServeState, session_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._-]{8,80}", session_id):
        raise ValueError("invalid session id")
    return state.sessions_dir / f"{session_id}.jsonl"


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _read_body(handler: BaseHTTPRequestHandler) -> bytes:
    length = int(handler.headers.get("Content-Length") or "0")
    return handler.rfile.read(length) if length else b""


def _is_visible_entry(path: Path) -> bool:
    return path.name not in DEFAULT_IGNORES and not path.name.startswith(".")


def _has_visible_child(directory: Path) -> bool:
    try:
        return any(_is_visible_entry(entry) for entry in directory.iterdir())
    except OSError:
        return False


def _list_directory(root: Path, rel_path: str) -> list[dict[str, Any]]:
    directory = (root / rel_path).resolve()
    if not _is_safe(root, directory):
        raise ValueError("path escapes workspace")
    if not directory.is_dir():
        raise ValueError("directory not found")
    try:
        entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except OSError:
        return []

    nodes: list[dict[str, Any]] = []
    for entry in entries:
        if not _is_visible_entry(entry):
            continue
        rel = f"{rel_path}/{entry.name}" if rel_path else entry.name
        if entry.is_dir():
            nodes.append(
                {
                    "type": "directory",
                    "name": entry.name,
                    "path": rel,
                    "hasChildren": _has_visible_child(entry),
                }
            )
        elif entry.is_file():
            nodes.append({"type": "file", "name": entry.name, "path": rel, "hasChildren": False})
    return nodes


def _looks_binary(data: bytes) -> bool:
    return b"\0" in data[:8192]


def _read_text_file(path: Path) -> str:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        data = path.read_bytes()
        if _looks_binary(data):
            raise ValueError("binary preview is not supported")
        return data.decode("utf-8")
    return path.read_text(encoding="utf-8")


def _truncate(value: str, limit: int = 160) -> str:
    compact = " ".join(value.strip().split())
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit - 3]}..."


def _tool_detail(tool_name: str, args: Any) -> str:
    if not isinstance(args, dict):
        return ""
    lowered = tool_name.lower()
    if lowered in {"read", "file_read"}:
        for key in ("file_path", "path", "absolute_path", "filename"):
            value = args.get(key)
            if isinstance(value, str) and value:
                return _truncate(value)
    if lowered in {"bash", "shell", "exec", "exec_command"}:
        for key in ("command", "cmd", "script"):
            value = args.get(key)
            if isinstance(value, str) and value:
                return _truncate(value)
    if lowered in {"edit", "write", "replace"}:
        for key in ("file_path", "path", "absolute_path", "filename"):
            value = args.get(key)
            if isinstance(value, str) and value:
                return _truncate(value)
    parts: list[str] = []
    for key, value in args.items():
        if isinstance(value, str):
            rendered = value
        else:
            rendered = json.dumps(value, ensure_ascii=False)
        parts.append(f"{key}={_truncate(rendered, 80)}")
        if len(parts) >= 3:
            break
    return _truncate(" ".join(parts))


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


def _extract_text_delta(event: dict[str, Any]) -> str:
    update = event.get("assistantMessageEvent") or {}
    if update.get("type") == "text_delta":
        return str(update.get("delta") or "")
    return ""


def _make_handler(state: ServeState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "omp-serve/0.1"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            console.print(f"[dim]{self.address_string()}[/dim] {format % args}")

        def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            if content_type.startswith("text/html"):
                self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            self._send(status, _json_bytes(payload), "application/json; charset=utf-8")

        def _send_error_json(self, status: HTTPStatus, message: str) -> None:
            self._send_json({"error": message}, status)

        def do_HEAD(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path in {"/", "/api/meta", "/api/tree"}:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8" if parsed.path == "/" else "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            try:
                if parsed.path == "/":
                    self._send(HTTPStatus.OK, APP_HTML.encode("utf-8"), "text/html; charset=utf-8")
                elif parsed.path == "/api/meta":
                    self._send_json(
                        {
                            "workspace": str(state.workspace),
                            "model": state.model,
                            "sessionMode": "page-local",
                        }
                    )
                elif parsed.path == "/api/tree":
                    rel = query.get("path", [""])[0]
                    nodes = _list_directory(state.workspace, rel)
                    self._send_json({"path": rel, "nodes": nodes, "count": len(nodes)})
                elif parsed.path == "/api/file":
                    rel = query.get("path", [""])[0]
                    path = _resolve_rel(state, rel)
                    if not path.is_file():
                        self._send_error_json(HTTPStatus.NOT_FOUND, "file not found")
                        return
                    content = _read_text_file(path)
                    self._send_json({"path": rel, "content": content})
                else:
                    self._send_error_json(HTTPStatus.NOT_FOUND, "not found")
            except Exception as exc:
                self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/api/file":
                self._send_error_json(HTTPStatus.NOT_FOUND, "not found")
                return
            try:
                payload = json.loads(_read_body(self).decode("utf-8"))
                rel = str(payload.get("path") or "")
                content = str(payload.get("content") or "")
                path = _resolve_rel(state, rel)
                if not path.is_file():
                    self._send_error_json(HTTPStatus.NOT_FOUND, "file not found")
                    return
                path.write_text(content, encoding="utf-8")
                self._send_json({"ok": True, "path": rel})
            except Exception as exc:
                self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

        def do_POST(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/api/chat":
                self._send_error_json(HTTPStatus.NOT_FOUND, "not found")
                return
            try:
                payload = json.loads(_read_body(self).decode("utf-8"))
                message = str(payload.get("message") or "").strip()
                session_id = str(payload.get("sessionId") or "").strip()
                if not message:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "message is required")
                    return
                if not session_id:
                    self._send_error_json(HTTPStatus.BAD_REQUEST, "sessionId is required")
                    return
                self._stream_pi(message, session_id)
            except Exception as exc:
                self._send_error_json(HTTPStatus.BAD_REQUEST, str(exc))

        def _stream_pi(self, message: str, session_id: str) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            if not shutil.which("pi"):
                self.wfile.write(_sse({"type": "error", "message": "pi binary not found in PATH"}))
                self.wfile.flush()
                return

            session_path = _session_path(state, session_id)
            state.sessions_dir.mkdir(parents=True, exist_ok=True)
            cmd = [
                "pi",
                "-p",
                "--mode",
                "json",
                "--approve",
                "--session",
                str(session_path),
                "--model",
                state.model,
                message,
            ]
            proc = subprocess.Popen(
                cmd,
                cwd=state.workspace,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            stderr_lines: list[str] = []

            def drain_stderr() -> None:
                if not proc.stderr:
                    return
                for line in proc.stderr:
                    stderr_lines.append(line.rstrip())

            thread = threading.Thread(target=drain_stderr, daemon=True)
            thread.start()
            if not proc.stdout:
                return
            sent_done = False
            for raw in proc.stdout:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("type")
                if event_type == "message_update":
                    delta = _extract_text_delta(event)
                    if delta:
                        self.wfile.write(_sse({"type": "assistant_delta", "delta": delta}))
                        self.wfile.flush()
                elif event_type == "tool_execution_start":
                    name = str(event.get("toolName") or "tool")
                    self.wfile.write(
                        _sse(
                            {
                                "type": "tool_start",
                                "id": str(event.get("toolCallId") or name),
                                "name": name,
                                "detail": _tool_detail(name, event.get("args")),
                            }
                        )
                    )
                    self.wfile.flush()
                elif event_type == "tool_execution_end":
                    name = str(event.get("toolName") or "tool")
                    self.wfile.write(
                        _sse(
                            {
                                "type": "tool_end",
                                "id": str(event.get("toolCallId") or name),
                                "name": name,
                                "detail": _tool_detail(name, event.get("args")),
                            }
                        )
                    )
                    self.wfile.flush()
                elif event_type == "error":
                    self.wfile.write(_sse({"type": "error", "message": str(event.get("message", "pi error"))}))
                    self.wfile.flush()
                elif event_type == "agent_end":
                    self.wfile.write(_sse({"type": "done", "returncode": 0}))
                    self.wfile.flush()
                    sent_done = True
                    break
            if sent_done and proc.poll() is None:
                try:
                    proc.terminate()
                    rc = proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    rc = proc.wait()
            else:
                rc = proc.wait()
            if rc != 0 and not sent_done:
                detail = "\n".join(stderr_lines[-8:]) or f"pi exited with {rc}"
                self.wfile.write(_sse({"type": "error", "message": detail}))
            if not sent_done:
                self.wfile.write(_sse({"type": "done", "returncode": rc}))
            self.wfile.flush()

    return Handler


@app.command()
def dev(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="Project workspace root."),
    host: str = typer.Option("0.0.0.0", "--host", help="HTTP host."),
    port: int = typer.Option(8765, "--port", "-p", help="HTTP port."),
    model: str = typer.Option(
        os.environ.get("OMP_DEFAULT_MODEL_PI", "openai-codex/gpt-5.4-mini"),
        "--model",
        "-m",
        help="Pi model.",
    ),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser after start."),
) -> None:
    """Compatibility alias for `omp serve`."""
    console.print("[yellow][omp serve] dev is deprecated; use `omp serve`.[/yellow]")
    _serve(workspace, host, port, model, open_browser)


if __name__ == "__main__":
    app()
