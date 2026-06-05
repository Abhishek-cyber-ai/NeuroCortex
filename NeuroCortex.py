#!/usr/bin/env python3
"""
AutoHack AI - Autonomous Hacking Assistant
Complete solution with GUI, multi-agent system, Kali tools + Ollama MCP Integration
⚠️  Only use on systems you own or have explicit written permission to test.
"""

import subprocess
import json
import re
import threading
import queue
import time
import os
import shutil
import logging
import sys
import signal
import asyncio
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import socket
import random

# ── Web imports ───────────────────────────────────────────────────────────────
try:
    from flask import Flask, render_template_string, request, jsonify
    from flask_socketio import SocketIO, emit
    from flask_cors import CORS
except ImportError:
    print("Installing Flask packages...")
    subprocess.run([sys.executable, "-m", "pip", "install",
                    "flask", "flask-socketio", "flask-cors", "python-socketio"])
    from flask import Flask, render_template_string, request, jsonify
    from flask_socketio import SocketIO, emit
    from flask_cors import CORS

# ── Ollama import ─────────────────────────────────────────────────────────────
try:
    import ollama as ollama_lib
    OLLAMA_AVAILABLE = True
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "ollama"])
    try:
        import ollama as ollama_lib
        OLLAMA_AVAILABLE = True
    except ImportError:
        OLLAMA_AVAILABLE = False

# ── MCP imports ───────────────────────────────────────────────────────────────
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "mcp"])
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        MCP_AVAILABLE = True
    except ImportError:
        MCP_AVAILABLE = False

# ==================== HTML TEMPLATE ====================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AutoHack AI - Autonomous Hacking Assistant</title>
    <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap" rel="stylesheet">
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        :root {
            --green:   #00ff41;
            --green2:  #00cc33;
            --red:     #ff003c;
            --yellow:  #ffd600;
            --cyan:    #00e5ff;
            --bg:      #070b1a;
            --bg2:     #0d1224;
            --border:  rgba(0,255,65,0.25);
            --glow:    0 0 12px rgba(0,255,65,0.5);
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            font-family: 'Share Tech Mono', monospace;
            background: var(--bg);
            color: var(--green);
            overflow: hidden;
            height: 100vh;
        }
        #matrix-bg { position:fixed; top:0; left:0; width:100%; height:100%; z-index:-1; opacity:0.07; }

        /* ── Layout ── */
        .dashboard { display:flex; height:100vh; }

        /* ── Sidebar ── */
        .sidebar {
            width: 260px;
            background: var(--bg2);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .logo {
            padding: 18px 16px 14px;
            border-bottom: 1px solid var(--border);
            background: linear-gradient(135deg, rgba(0,255,65,0.06), transparent);
        }
        .logo h1 {
            font-family: 'Orbitron', monospace;
            font-size: 15px;
            font-weight: 900;
            letter-spacing: 2px;
            text-shadow: var(--glow);
        }
        .logo p { font-size: 10px; opacity: 0.5; margin-top: 3px; }
        .logo .version-badge {
            display: inline-block;
            background: var(--green);
            color: var(--bg);
            font-size: 9px;
            padding: 1px 6px;
            margin-top: 6px;
            font-weight: bold;
        }

        .sidebar-section { padding: 12px 14px; border-bottom: 1px solid var(--border); }
        .sidebar-section h3 { font-size: 10px; letter-spacing: 2px; opacity: 0.5; margin-bottom: 8px; }

        .agent-item {
            padding: 8px 10px;
            margin: 4px 0;
            border-left: 2px solid var(--green);
            background: rgba(0,255,65,0.04);
            font-size: 11px;
            transition: background 0.2s;
        }
        .agent-item:hover { background: rgba(0,255,65,0.09); }
        .agent-item b { color: var(--cyan); display: block; margin-bottom: 2px; }
        .agent-item .badge {
            display: inline-block;
            padding: 1px 5px;
            font-size: 9px;
            background: rgba(0,255,65,0.15);
            margin-top: 3px;
        }
        .agent-item.ollama-agent { border-left-color: var(--cyan); }
        .agent-item.ollama-agent b { color: var(--cyan); }

        /* Ollama status pill */
        .ollama-status {
            display: flex; align-items: center; gap: 6px;
            font-size: 11px; padding: 6px 10px;
            background: rgba(0,229,255,0.06);
            border: 1px solid rgba(0,229,255,0.2);
            margin: 8px 0 4px;
        }
        .status-dot { width:7px; height:7px; border-radius:50%; background:#555; flex-shrink:0; }
        .status-dot.online  { background: var(--green); box-shadow: 0 0 6px var(--green); }
        .status-dot.offline { background: var(--red);   box-shadow: 0 0 6px var(--red); }
        .status-dot.loading { background: var(--yellow); animation: pulse 1s infinite; }

        .model-selector {
            width: 100%; padding: 5px 8px;
            background: var(--bg); border: 1px solid var(--border);
            color: var(--cyan); font-family: inherit; font-size: 11px;
            margin-top: 6px; cursor: pointer;
        }

        .quick-actions { padding: 12px 14px; display: flex; flex-direction: column; gap: 5px; }
        .btn {
            background: transparent;
            border: 1px solid var(--green);
            color: var(--green);
            padding: 7px 12px;
            cursor: pointer;
            font-family: 'Share Tech Mono', monospace;
            font-size: 11px;
            letter-spacing: 1px;
            transition: all 0.2s;
            text-align: left;
        }
        .btn:hover { background: var(--green); color: var(--bg); box-shadow: var(--glow); }
        .btn.cyan { border-color: var(--cyan); color: var(--cyan); }
        .btn.cyan:hover { background: var(--cyan); color: var(--bg); box-shadow: 0 0 12px var(--cyan); }
        .btn.red { border-color: var(--red); color: var(--red); }
        .btn.red:hover { background: var(--red); color: #fff; }

        /* ── Main ── */
        .main-content { flex:1; display:flex; flex-direction:column; overflow:hidden; min-width:0; }

        /* Tab bar */
        .tabs {
            display: flex;
            background: var(--bg2);
            border-bottom: 1px solid var(--border);
        }
        .tab {
            padding: 10px 20px;
            font-size: 11px;
            letter-spacing: 1px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            opacity: 0.5;
            transition: all 0.2s;
        }
        .tab.active { opacity: 1; border-bottom-color: var(--green); color: var(--green); }
        .tab.ollama-tab.active { border-bottom-color: var(--cyan); color: var(--cyan); }

        /* Tab panels */
        .tab-panel { display: none; flex: 1; overflow: hidden; }
        .tab-panel.active { display: flex; flex-direction: column; flex: 1; }

        /* ── Classic panel (original layout) ── */
        .toolbar {
            background: var(--bg2);
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
            display: flex;
            gap: 8px;
        }
        .command-input {
            flex: 1;
            background: var(--bg);
            border: 1px solid var(--border);
            color: var(--green);
            padding: 8px 12px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 12px;
            outline: none;
            transition: border-color 0.2s;
        }
        .command-input:focus { border-color: var(--green); box-shadow: var(--glow); }
        .command-input::placeholder { opacity: 0.35; }

        .content-area { flex:1; display:flex; overflow:hidden; }
        .console {
            flex: 2; background: var(--bg2); margin: 8px 4px 8px 8px;
            border: 1px solid var(--border); display: flex; flex-direction: column;
        }
        .panel-header {
            background: rgba(0,255,65,0.06);
            padding: 8px 12px;
            border-bottom: 1px solid var(--border);
            font-size: 11px;
            letter-spacing: 1px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .panel-header .dot { width:6px; height:6px; border-radius:50%; background:var(--green); }
        .console-output {
            flex: 1; padding: 10px 12px;
            overflow-y: auto; font-size: 11px; line-height: 1.7;
            scroll-behavior: smooth;
        }
        .console-output::-webkit-scrollbar { width: 4px; }
        .console-output::-webkit-scrollbar-track { background: transparent; }
        .console-output::-webkit-scrollbar-thumb { background: var(--border); }
        .console-line { margin: 2px 0; white-space: pre-wrap; word-break: break-all; }
        .console-line.cmd     { color: var(--yellow); }
        .console-line.error   { color: var(--red); }
        .console-line.success { color: var(--green); }
        .console-line.info    { color: var(--cyan); opacity: 0.8; }
        .console-line.mcp     { color: #b388ff; }

        .results-panel {
            flex: 1; background: var(--bg2); margin: 8px 8px 8px 4px;
            border: 1px solid var(--border); display: flex; flex-direction: column;
        }
        .results-content { flex:1; padding: 8px; overflow-y: auto; }
        .scan-result {
            background: rgba(0,255,65,0.04);
            padding: 8px 10px; margin: 4px 0;
            border-left: 2px solid var(--green);
            font-size: 11px;
        }
        .vulnerability {
            background: rgba(255,0,60,0.08);
            border-left-color: var(--red);
            color: #ff6680;
        }

        /* ── Ollama Chat panel ── */
        .ollama-panel { flex:1; display:flex; flex-direction:column; overflow:hidden; }
        .chat-messages {
            flex: 1; padding: 14px; overflow-y: auto;
            display: flex; flex-direction: column; gap: 10px;
            scroll-behavior: smooth;
        }
        .chat-messages::-webkit-scrollbar { width: 4px; }
        .chat-messages::-webkit-scrollbar-thumb { background: var(--border); }

        .msg {
            max-width: 88%; padding: 10px 14px;
            font-size: 12px; line-height: 1.6;
            border-radius: 0;
            animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn { from { opacity:0; transform: translateY(4px); } to { opacity:1; transform: none; } }
        .msg.user {
            align-self: flex-end;
            background: rgba(0,255,65,0.08);
            border: 1px solid rgba(0,255,65,0.3);
            color: var(--green);
        }
        .msg.assistant {
            align-self: flex-start;
            background: rgba(0,229,255,0.06);
            border: 1px solid rgba(0,229,255,0.2);
            color: #cce8ff;
        }
        .msg.tool-call {
            align-self: flex-start;
            background: rgba(179,136,255,0.07);
            border: 1px solid rgba(179,136,255,0.3);
            color: #d0b3ff;
            font-size: 11px;
            max-width: 96%;
        }
        .msg.tool-result {
            align-self: flex-start;
            background: rgba(0,255,65,0.04);
            border: 1px solid rgba(0,255,65,0.15);
            color: #99ffbb;
            font-size: 10px;
            max-width: 96%;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 200px;
            overflow-y: auto;
        }
        .msg-label {
            font-size: 9px; opacity: 0.45; letter-spacing: 1px;
            margin-bottom: 4px; display: block;
        }
        .typing-indicator {
            display: none; align-self: flex-start;
            padding: 10px 14px;
            background: rgba(0,229,255,0.06);
            border: 1px solid rgba(0,229,255,0.2);
            font-size: 11px; color: var(--cyan);
        }
        .typing-dots span {
            display: inline-block;
            animation: bounce 1.2s infinite;
            font-size: 16px; line-height: 1;
        }
        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-5px)} }

        .chat-toolbar {
            padding: 10px 14px;
            background: var(--bg2);
            border-top: 1px solid var(--border);
            display: flex; gap: 8px; align-items: flex-end;
        }
        .chat-input {
            flex: 1;
            background: var(--bg);
            border: 1px solid var(--border);
            color: var(--cyan);
            padding: 9px 12px;
            font-family: 'Share Tech Mono', monospace;
            font-size: 12px;
            outline: none;
            resize: none;
            min-height: 38px;
            max-height: 100px;
            transition: border-color 0.2s;
        }
        .chat-input:focus { border-color: var(--cyan); box-shadow: 0 0 10px rgba(0,229,255,0.3); }
        .chat-input::placeholder { opacity: 0.3; }

        /* ── Modals ── */
        .modal {
            display: none; position: fixed; top:0; left:0; width:100%; height:100%;
            background: rgba(0,0,0,0.85); z-index: 1000;
            justify-content: center; align-items: center;
        }
        .modal-content {
            background: var(--bg2);
            border: 1px solid var(--green);
            padding: 28px; width: 90%; max-width: 460px;
            box-shadow: var(--glow);
        }
        .modal-content h2 {
            font-family: 'Orbitron', monospace;
            font-size: 14px; letter-spacing: 2px;
            margin-bottom: 16px;
        }
        .modal input, .modal select {
            width: 100%; padding: 9px 10px; margin: 6px 0;
            background: var(--bg); border: 1px solid var(--border);
            color: var(--green); font-family: 'Share Tech Mono', monospace; font-size: 12px;
        }
        .modal-btns { display: flex; gap: 8px; margin-top: 14px; }

        /* ── Misc ── */
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        .cursor { animation: blink 1s infinite; }
        .glow-text { text-shadow: var(--glow); }

        /* scrollbar global */
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(0,255,65,0.2); }
    </style>
</head>
<body>
<canvas id="matrix-bg"></canvas>

<div class="dashboard">
    <!-- ── Sidebar ── -->
    <div class="sidebar">
        <div class="logo">
            <h1>🔓 AUTOHACK AI</h1>
            <p>Autonomous Hacking Assistant</p>
            <span class="version-badge">v5.0 + OLLAMA MCP</span>
        </div>

        <div class="sidebar-section">
            <h3>ACTIVE AGENTS</h3>
            <div id="agents-list">
                <div class="agent-item"><b>Recon</b><span class="badge">nmap · nikto · gobuster</span></div>
                <div class="agent-item"><b>Exploit</b><span class="badge">sqlmap · hydra</span></div>
                <div class="agent-item"><b>Reporting</b><span class="badge">logs · reports</span></div>
                <div class="agent-item ollama-agent">
                    <b>🤖 Ollama MCP</b>
                    <span class="badge" style="background:rgba(0,229,255,0.15);color:var(--cyan)">AI · all tools</span>
                </div>
            </div>
        </div>

        <div class="sidebar-section">
            <h3>OLLAMA STATUS</h3>
            <div class="ollama-status">
                <div class="status-dot loading" id="ollama-dot"></div>
                <span id="ollama-status-text">Checking...</span>
            </div>
            <select class="model-selector" id="model-select" onchange="setModel(this.value)">
                <option value="llama3.1">llama3.1</option>
                <option value="mistral-nemo">mistral-nemo</option>
                <option value="qwen2.5">qwen2.5</option>
                <option value="command-r">command-r</option>
            </select>
        </div>

        <div class="quick-actions">
            <button class="btn" onclick="showScanModal()">▶ Start Scan</button>
            <button class="btn" onclick="showExploitModal()">⚡ Run Exploit</button>
            <button class="btn" onclick="generateReport()">📋 Generate Report</button>
            <button class="btn cyan" onclick="switchTab('ollama')">🤖 AI Chat (MCP)</button>
            <button class="btn red"  onclick="clearConsole()">✕ Clear Console</button>
        </div>
    </div>

    <!-- ── Main Content ── -->
    <div class="main-content">
        <!-- Tab Bar -->
        <div class="tabs">
            <div class="tab active"       id="tab-classic" onclick="switchTab('classic')">💻 CONSOLE</div>
            <div class="tab ollama-tab"   id="tab-ollama"  onclick="switchTab('ollama')">🤖 AI CHAT (MCP)</div>
        </div>

        <!-- ── CLASSIC TAB ── -->
        <div class="tab-panel active" id="panel-classic">
            <div class="toolbar">
                <input type="text" id="command-input" class="command-input"
                       placeholder="Enter command — e.g. scan 192.168.1.1 | nikto http://target | generate report"
                       onkeypress="handleKeyPress(event)">
                <button class="btn" onclick="executeCommand()">EXECUTE</button>
                <button class="btn" onclick="startAutoMode()">🤖 AUTO</button>
            </div>
            <div class="content-area">
                <div class="console">
                    <div class="panel-header"><div class="dot"></div> CONSOLE OUTPUT</div>
                    <div class="console-output" id="console-output">
                        <div class="console-line info">> AutoHack AI v5.0 + Ollama MCP initialized</div>
                        <div class="console-line info">> All agents ready. Ollama connecting...</div>
                        <div class="console-line cursor">> _</div>
                    </div>
                </div>
                <div class="results-panel">
                    <div class="panel-header"><div class="dot"></div> SCAN RESULTS</div>
                    <div class="results-content" id="results-content">
                        <div class="scan-result">Ready for scans...</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- ── OLLAMA MCP TAB ── -->
        <div class="tab-panel" id="panel-ollama">
            <div class="ollama-panel">
                <div class="panel-header" style="border-bottom:1px solid var(--border);background:rgba(0,229,255,0.05)">
                    <div class="dot" style="background:var(--cyan)"></div>
                    OLLAMA MCP AGENT — AI-POWERED KALI TOOL ORCHESTRATION
                    <span style="margin-left:auto;font-size:10px;opacity:0.4;" id="chat-model-label">model: llama3.1</span>
                </div>
                <div class="chat-messages" id="chat-messages">
                    <div class="msg assistant">
                        <span class="msg-label">AUTOHACK AI / OLLAMA MCP</span>
                        Hello! I'm your AI-powered penetration testing assistant. I can intelligently chain Kali Linux tools via MCP.<br><br>
                        Try: <b>"Run a full assessment on 192.168.1.1"</b> or <b>"Check http://target for web vulnerabilities"</b><br><br>
                        <span style="color:var(--red);font-size:10px;">⚠ Only test systems you own or have explicit written permission to test.</span>
                    </div>
                </div>
                <div class="typing-indicator" id="typing-indicator">
                    <span class="msg-label">AI THINKING</span>
                    <div class="typing-dots"><span>•</span><span>•</span><span>•</span></div>
                </div>
                <div class="chat-toolbar">
                    <textarea id="chat-input" class="chat-input" rows="1"
                              placeholder="Ask the AI to run tools — e.g. 'Scan 10.0.0.1 and check for web vulns'"
                              onkeypress="handleChatKey(event)"
                              oninput="autoResize(this)"></textarea>
                    <button class="btn cyan" onclick="sendChat()" style="height:38px;padding:0 16px;">SEND</button>
                    <button class="btn" onclick="clearChat()" style="height:38px;padding:0 12px;">CLR</button>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Scan Modal -->
<div id="scan-modal" class="modal">
    <div class="modal-content">
        <h2>▶ START SCAN</h2>
        <input type="text" id="scan-target" placeholder="Target IP or Domain">
        <select id="scan-type">
            <option value="quick">Quick Scan</option>
            <option value="full">Full Assessment</option>
            <option value="web">Web Scan</option>
        </select>
        <div class="modal-btns">
            <button class="btn" onclick="startScan()">START</button>
            <button class="btn red" onclick="closeModal('scan-modal')">CANCEL</button>
        </div>
    </div>
</div>

<!-- Exploit Modal -->
<div id="exploit-modal" class="modal">
    <div class="modal-content">
        <h2>⚡ RUN EXPLOIT</h2>
        <input type="text" id="exploit-target" placeholder="Target IP/URL">
        <select id="exploit-type">
            <option value="auto">Auto-detect</option>
            <option value="sqlmap">SQL Injection</option>
            <option value="hydra">Brute Force</option>
        </select>
        <div class="modal-btns">
            <button class="btn" onclick="runExploit()">EXECUTE</button>
            <button class="btn red" onclick="closeModal('exploit-modal')">CANCEL</button>
        </div>
    </div>
</div>

<script>
// ── Socket ────────────────────────────────────────────────────────────────────
let socket = io();
let autoMode = false;
let currentModel = 'llama3.1';

// ── Matrix BG ─────────────────────────────────────────────────────────────────
const canvas = document.getElementById('matrix-bg');
const ctx = canvas.getContext('2d');
canvas.width = window.innerWidth; canvas.height = window.innerHeight;
const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*<>";
const drops = Array(Math.ceil(canvas.width/10)).fill(1);
function drawMatrix() {
    ctx.fillStyle = "rgba(7,11,26,0.05)";
    ctx.fillRect(0,0,canvas.width,canvas.height);
    ctx.fillStyle = "#0F0"; ctx.font = "10px monospace";
    for(let i=0;i<drops.length;i++){
        ctx.fillText(chars[Math.floor(Math.random()*chars.length)],i*10,drops[i]*10);
        if(drops[i]*10>canvas.height&&Math.random()>0.975) drops[i]=0;
        drops[i]++;
    }
}
setInterval(drawMatrix, 40);
window.addEventListener('resize',()=>{canvas.width=window.innerWidth;canvas.height=window.innerHeight;});

// ── Sockets ───────────────────────────────────────────────────────────────────
socket.on('connect',()=>{ addLog('Connected to AutoHack AI','info'); loadAgents(); checkOllama(); });
socket.on('task_completed',(d)=>{ addLog(`Task ${d.task_id} completed`,'success'); displayResults(d.result); });
socket.on('notification',(n)=>{ addLog(`[!] ${n.message}`,'info'); });
socket.on('ollama_status',(d)=>{ updateOllamaStatus(d); });
socket.on('chat_token',(d)=>{ appendChatToken(d.token); });
socket.on('chat_tool_call',(d)=>{ appendToolCall(d); });
socket.on('chat_tool_result',(d)=>{ appendToolResult(d); });
socket.on('chat_done',(d)=>{ finalizeChatMessage(d); });

// ── Tabs ──────────────────────────────────────────────────────────────────────
function switchTab(tab) {
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
    document.getElementById('tab-'+tab).classList.add('active');
    document.getElementById('panel-'+tab).classList.add('active');
}

// ── Ollama status ─────────────────────────────────────────────────────────────
function checkOllama() {
    $.ajax({ url: '/api/ollama/status', method: 'GET', success: updateOllamaStatus });
}
function updateOllamaStatus(r) {
    const dot  = document.getElementById('ollama-dot');
    const text = document.getElementById('ollama-status-text');
    if (r.available) {
        dot.className = 'status-dot online';
        text.textContent = 'Online — ' + (r.models && r.models.length ? r.models.length+' models' : 'ready');
        if (r.models && r.models.length) populateModels(r.models);
    } else {
        dot.className = 'status-dot offline';
        text.textContent = r.error || 'Offline';
    }
}
function populateModels(models) {
    const sel = document.getElementById('model-select');
    sel.innerHTML = models.map(m=>`<option value="${m}">${m}</option>`).join('');
}
function setModel(model) {
    currentModel = model;
    document.getElementById('chat-model-label').textContent = 'model: ' + model;
    $.ajax({ url:'/api/ollama/model', method:'POST', contentType:'application/json', data: JSON.stringify({model}) });
}

// ── Classic console ───────────────────────────────────────────────────────────
function loadAgents() {
    $.ajax({ url:'/api/agents', method:'GET', success:(r)=>{
        if(r.success) {
            const list = Object.entries(r.agents).map(([n,i])=>
                `<div class="agent-item ${n==='ollama_mcp'?'ollama-agent':''}">
                    <b>${n==='ollama_mcp'?'🤖 '+n:n}</b>
                    <span class="badge">${(i.capabilities||[]).slice(0,3).join(' · ')}</span>
                </div>`).join('');
            document.getElementById('agents-list').innerHTML = list;
        }
    }});
}
function addLog(text, type='output') {
    const cls = {cmd:'cmd',error:'error',success:'success',info:'info',mcp:'mcp'}[type]||'output';
    const el = document.createElement('div');
    el.className = 'console-line '+cls;
    el.textContent = text;
    const out = document.getElementById('console-output');
    out.appendChild(el);
    out.scrollTop = out.scrollHeight;
}
function executeCommand() {
    const cmd = $('#command-input').val().trim();
    if(!cmd) return;
    addLog('> '+cmd, 'cmd');
    $('#command-input').val('');
    $.ajax({ url:'/api/execute', method:'POST', contentType:'application/json',
        data: JSON.stringify({command:cmd}),
        success:(r)=>{ if(!r.success) addLog('Error: '+r.error,'error'); }
    });
}
function startScan() {
    const target=$('#scan-target').val(), type=$('#scan-type').val();
    if(!target) return;
    addLog(`Starting ${type} scan on ${target}`,'cmd');
    closeModal('scan-modal');
    $.ajax({ url:'/api/scan', method:'POST', contentType:'application/json',
        data: JSON.stringify({target, scan_type:type}) });
}
function runExploit() {
    const target=$('#exploit-target').val(), type=$('#exploit-type').val();
    if(!target) return;
    addLog(`Running ${type} on ${target}`,'cmd');
    closeModal('exploit-modal');
    $.ajax({ url:'/api/execute', method:'POST', contentType:'application/json',
        data: JSON.stringify({command:`exploit ${target}`, exploit_type:type}) });
}
function startAutoMode() {
    autoMode=!autoMode;
    addLog(autoMode?'[AUTO MODE ENABLED]':'[AUTO MODE DISABLED]','info');
    if(autoMode) autoReconLoop();
}
function autoReconLoop() {
    if(!autoMode) return;
    setTimeout(()=>{
        if(autoMode) {
            addLog('[Auto] Running recon...','info');
            $.ajax({ url:'/api/scan', method:'POST', contentType:'application/json',
                data: JSON.stringify({target:'auto',scan_type:'quick'}),
                complete: autoReconLoop });
        }
    }, 30000);
}
function generateReport() {
    addLog('Generating report...','cmd');
    $.ajax({ url:'/api/execute', method:'POST', contentType:'application/json',
        data: JSON.stringify({command:'generate report'}) });
}
function displayResults(result) {
    if(result && result.vulnerabilities) {
        const html = result.vulnerabilities.map(v=>
            `<div class="scan-result vulnerability">⚠ ${v.type}<br>${v.service} — Risk: ${v.risk}</div>`
        ).join('');
        $('#results-content').prepend(html);
    }
    if(result && result.output) {
        addLog(result.output.slice(0,500),'output');
    }
}
function clearConsole() {
    document.getElementById('console-output').innerHTML =
        '<div class="console-line info">> Console cleared</div><div class="console-line cursor">> _</div>';
}
function handleKeyPress(e) { if(e.key==='Enter') executeCommand(); }
function showScanModal()    { $('#scan-modal').css('display','flex'); }
function showExploitModal() { $('#exploit-modal').css('display','flex'); }
function closeModal(id)     { $('#'+id).css('display','none'); }

// ── Ollama Chat ───────────────────────────────────────────────────────────────
let currentAssistantEl = null;

function sendChat() {
    const input = document.getElementById('chat-input');
    const text  = input.value.trim();
    if (!text) return;
    input.value = ''; input.style.height = '38px';

    appendUserMsg(text);
    showTyping(true);

    $.ajax({ url:'/api/ollama/chat', method:'POST', contentType:'application/json',
        data: JSON.stringify({message: text, model: currentModel}),
        success:(r)=>{
            showTyping(false);
            if(!r.success) appendAssistantMsg('Error: ' + r.error);
        },
        error:()=>{ showTyping(false); appendAssistantMsg('Connection error. Is Ollama running?'); }
    });
}

function appendUserMsg(text) {
    const el = document.createElement('div');
    el.className = 'msg user';
    el.innerHTML = `<span class="msg-label">YOU</span>${escHtml(text)}`;
    document.getElementById('chat-messages').appendChild(el);
    scrollChat();
}
function appendAssistantMsg(text) {
    const el = document.createElement('div');
    el.className = 'msg assistant';
    el.innerHTML = `<span class="msg-label">AUTOHACK AI</span>${escHtml(text)}`;
    document.getElementById('chat-messages').appendChild(el);
    scrollChat();
    return el;
}
function appendChatToken(token) {
    if (!currentAssistantEl) {
        showTyping(false);
        currentAssistantEl = document.createElement('div');
        currentAssistantEl.className = 'msg assistant';
        currentAssistantEl.innerHTML = '<span class="msg-label">AUTOHACK AI</span><span class="msg-body"></span>';
        document.getElementById('chat-messages').appendChild(currentAssistantEl);
    }
    currentAssistantEl.querySelector('.msg-body').textContent += token;
    scrollChat();
}
function appendToolCall(d) {
    const el = document.createElement('div');
    el.className = 'msg tool-call';
    el.innerHTML = `<span class="msg-label">⚙ TOOL CALL — ${escHtml(d.tool)}</span><pre>${escHtml(JSON.stringify(d.args,null,2))}</pre>`;
    document.getElementById('chat-messages').appendChild(el);
    scrollChat();
    addLog(`[MCP] Calling ${d.tool}`, 'mcp');
}
function appendToolResult(d) {
    const preview = d.result.slice(0, 1200) + (d.result.length > 1200 ? '\n…[truncated]' : '');
    const el = document.createElement('div');
    el.className = 'msg tool-result';
    el.innerHTML = `<span class="msg-label">📤 ${escHtml(d.tool)} OUTPUT</span>${escHtml(preview)}`;
    document.getElementById('chat-messages').appendChild(el);
    scrollChat();
    addLog(`[MCP] ${d.tool} completed`, 'mcp');
}
function finalizeChatMessage(d) {
    showTyping(false);
    currentAssistantEl = null;
    if (d && d.final_text && !document.querySelector('.msg.assistant .msg-body')) {
        appendAssistantMsg(d.final_text);
    }
}
function showTyping(show) {
    document.getElementById('typing-indicator').style.display = show ? 'block' : 'none';
}
function scrollChat() {
    const c = document.getElementById('chat-messages');
    c.scrollTop = c.scrollHeight;
}
function clearChat() {
    document.getElementById('chat-messages').innerHTML =
        `<div class="msg assistant"><span class="msg-label">AUTOHACK AI</span>Chat cleared. Ready for new session.</div>`;
    currentAssistantEl = null;
}
function handleChatKey(e) {
    if(e.key==='Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
}
function autoResize(el) {
    el.style.height = '38px';
    el.style.height = Math.min(el.scrollHeight, 100) + 'px';
}
function escHtml(t) { return $('<div/>').text(t).html(); }

// ── Refresh agents every 5s ───────────────────────────────────────────────────
setInterval(loadAgents, 5000);
setInterval(checkOllama, 15000);
</script>
</body>
</html>
'''

# ==================== TOOL MANAGER ====================
class ToolManager:
    def __init__(self):
        self.allowed_tools = [
            'nmap', 'nikto', 'gobuster', 'hydra', 'sqlmap',
            'dirb', 'theharvester', 'wpscan', 'enum4linux',
            'smbclient', 'dnsrecon', 'whois', 'msfconsole'
        ]
        self.installed_tools = {t: shutil.which(t) is not None for t in self.allowed_tools}
        self.blocked_patterns = [r'rm\s+-rf\s+/', r'dd\s+if=', r':\)\{:\|:&\};:', r'mkfs']

    def list_tools(self) -> Dict:
        return {t: {'installed': s} for t, s in self.installed_tools.items()}

    def execute(self, tool: str, args: List[str], timeout: int = 60) -> Dict:
        if tool not in self.allowed_tools:
            return {'success': False, 'error': f'Tool {tool} not allowed'}
        if not self.installed_tools.get(tool):
            return {'success': False, 'error': f'{tool} not installed. Run: sudo apt install {tool}'}
        cmd_str = ' '.join(args)
        for p in self.blocked_patterns:
            if re.search(p, cmd_str):
                return {'success': False, 'error': f'Blocked dangerous pattern'}
        try:
            result = subprocess.run([tool] + args, capture_output=True, text=True, timeout=timeout)
            return {
                'success': result.returncode == 0,
                'output': result.stdout or result.stderr,
                'command': f'{tool} {cmd_str}',
                'return_code': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': f'Timeout after {timeout}s', 'command': f'{tool} {cmd_str}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

# ==================== BASE AGENT ====================
class BaseAgent:
    def __init__(self, name: str, tool_manager: ToolManager):
        self.name = name
        self.tool_manager = tool_manager
        self.capabilities = []
        self.metrics = {}

    def process_command(self, command: str) -> Dict:
        return {'agent': self.name, 'result': 'Not implemented'}

    def get_capabilities(self) -> List[str]: return self.capabilities
    def get_metrics(self) -> Dict: return self.metrics

# ==================== RECON AGENT ====================
class ReconAgent(BaseAgent):
    def __init__(self, tool_manager):
        super().__init__('Recon', tool_manager)
        self.capabilities = ['network_scanning', 'port_scanning', 'web_enumeration', 'dns_recon']
        self.metrics = {'scans': 0}

    def process_command(self, command: str) -> Dict:
        cmd_lower = command.lower()
        target = self._extract_target(command)
        if not target and 'auto' not in cmd_lower:
            return {'error': 'No target specified'}
        if 'nmap' in cmd_lower or 'scan' in cmd_lower:
            return self._run_nmap(target, cmd_lower)
        elif 'gobuster' in cmd_lower or 'directory' in cmd_lower:
            return self._run_gobuster(target)
        elif 'nikto' in cmd_lower:
            return self._run_nikto(target)
        elif 'dnsrecon' in cmd_lower or 'dns' in cmd_lower:
            return self._run_dnsrecon(target)
        else:
            return self._run_smart_scan(target)

    def _extract_target(self, command: str) -> Optional[str]:
        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', command)
        if ips: return ips[0]
        domains = re.findall(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b', command)
        return domains[0] if domains else None

    def _run_nmap(self, target: str, cmd_lower: str) -> Dict:
        flags = ['-sV','-sC','-O','-p-','-T4'] if 'full' in cmd_lower else ['-sV','-sC','-T4','-F']
        result = self.tool_manager.execute('nmap', flags + [target], timeout=120)
        if result['success']:
            self.metrics['scans'] += 1
            result['vulnerabilities'] = self._parse_vulnerabilities(result['output'])
        return result

    def _run_gobuster(self, target: str) -> Dict:
        wl = next((p for p in [
            '/usr/share/wordlists/dirb/common.txt',
            '/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt'
        ] if os.path.exists(p)), None)
        if not wl:
            return {'success': False, 'error': 'No wordlist found. Install: sudo apt install wordlists'}
        return self.tool_manager.execute('gobuster', ['dir','-u',f'http://{target}','-w',wl,'-t','20','--no-error'], 180)

    def _run_nikto(self, target: str) -> Dict:
        return self.tool_manager.execute('nikto', ['-h', target, '-Format', 'txt', '-maxtime', '60'], 120)

    def _run_dnsrecon(self, target: str) -> Dict:
        return self.tool_manager.execute('dnsrecon', ['-d', target, '-t', 'std'], 60)

    def _run_smart_scan(self, target: str) -> Dict:
        results = {'target': target, 'scans': {}}
        results['scans']['nmap'] = self._run_nmap(target, 'quick')
        if target and not re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', target):
            results['scans']['gobuster'] = self._run_gobuster(target)
        return results

    def _parse_vulnerabilities(self, output: str) -> List[Dict]:
        vulns = []
        if 'open' in output.lower() and 'ssh' in output.lower():
            vulns.append({'type':'SSH Service','risk':'Medium','service':'SSH','tool':'hydra'})
        if 'http' in output.lower() or 'https' in output.lower():
            vulns.append({'type':'Web Server','risk':'High','service':'HTTP/HTTPS','tool':'nikto,sqlmap'})
        if 'ftp' in output.lower():
            vulns.append({'type':'FTP Service','risk':'Medium','service':'FTP','tool':'hydra'})
        return vulns

# ==================== EXPLOIT AGENT ====================
class ExploitAgent(BaseAgent):
    def __init__(self, tool_manager):
        super().__init__('Exploit', tool_manager)
        self.capabilities = ['sql_injection', 'brute_force', 'exploitation_suggestions']
        self.metrics = {'exploits': 0, 'successful': 0}

    def process_command(self, command: str) -> Dict:
        cmd_lower = command.lower()
        if 'sqlmap' in cmd_lower or 'sql injection' in cmd_lower:
            return self._run_sqlmap(command)
        elif 'hydra' in cmd_lower or 'brute' in cmd_lower:
            return self._run_hydra(command)
        else:
            return self._suggest_exploits(command)

    def _extract_url(self, cmd): 
        urls = re.findall(r'https?://[^\s]+', cmd)
        return urls[0] if urls else None

    def _extract_target(self, cmd):
        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', cmd)
        return ips[0] if ips else None

    def _run_sqlmap(self, command: str) -> Dict:
        url = self._extract_url(command)
        if not url:
            return {'error': 'No URL provided for SQL injection test'}
        args = ['-u', url, '--batch', '--level=1', '--risk=1']
        if 'dbs' in command.lower(): args.append('--dbs')
        result = self.tool_manager.execute('sqlmap', args, 180)
        if result['success']:
            self.metrics['exploits'] += 1
            if 'vulnerable' in result.get('output','').lower():
                self.metrics['successful'] += 1
        return result

    def _run_hydra(self, command: str) -> Dict:
        target = self._extract_target(command)
        service = next((s for s in ['ssh','ftp','http-post-form','smb'] if s in command.lower()), None)
        if not target or not service:
            return {'error': 'Need target and service (ssh/ftp/http/smb)'}
        wl = next((p for p in ['/usr/share/wordlists/rockyou.txt','/usr/share/wordlists/dirb/small.txt'] if os.path.exists(p)), None)
        if not wl:
            return {'error': 'No wordlist found'}
        args = ['-l','admin','-P',wl,f'{service}://{target}','-t','4','-f']
        result = self.tool_manager.execute('hydra', args, 120)
        if result['success']:
            self.metrics['exploits'] += 1
        return result

    def _suggest_exploits(self, command: str) -> Dict:
        target = self._extract_target(command) or 'TARGET'
        return {'target': target, 'suggested_exploits': [
            {'name': 'SSH Brute Force', 'command': f'hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://{target}'},
            {'name': 'Web Vulnerability Scan', 'command': f'nikto -h {target}'},
            {'name': 'SQL Injection Test', 'command': f'sqlmap -u http://{target}/page?id=1 --batch'},
            {'name': 'Directory Brute Force', 'command': f'gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt'},
        ]}

# ==================== REPORTING AGENT ====================
class ReportingAgent(BaseAgent):
    def __init__(self, tool_manager):
        super().__init__('Reporting', tool_manager)
        self.capabilities = ['report_generation', 'log_analysis', 'finding_summary']
        self.metrics = {'reports': 0}
        self.scan_history = []

    def process_command(self, command: str) -> Dict:
        cmd_lower = command.lower()
        if 'generate' in cmd_lower or 'create' in cmd_lower:
            return self.generate_report()
        elif 'history' in cmd_lower:
            return self.list_history()
        return self.generate_summary()

    def add_scan_result(self, result: Dict):
        self.scan_history.append({'timestamp': datetime.now().isoformat(), 'result': result})
        if len(self.scan_history) > 50:
            self.scan_history = self.scan_history[-50:]

    def generate_report(self) -> Dict:
        self.metrics['reports'] += 1
        if not self.scan_history:
            return {'report': 'No scan data. Run scans first!', 'findings': []}
        findings = []
        for e in self.scan_history:
            if 'vulnerabilities' in e.get('result', {}):
                findings.extend(e['result']['vulnerabilities'])
        unique = list({f['type']:f for f in findings}.values())
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report = (
            f"\n╔═══════════════════════════════════════╗\n"
            f"║       AUTOHACK AI SECURITY REPORT    ║\n"
            f"╠═══════════════════════════════════════╣\n"
            f"║ Generated : {ts}\n"
            f"║ Total Scans: {len(self.scan_history)}\n"
            f"║ Findings   : {len(unique)}\n"
            f"╠═══════════════════════════════════════╣\n"
        )
        for f in unique:
            report += f"║ • {f.get('type','?')} — Risk: {f.get('risk','?')} — Tool: {f.get('tool','?')}\n"
        report += "╚═══════════════════════════════════════╝"
        return {'report': report, 'findings': unique}

    def list_history(self) -> Dict:
        return {'history': self.scan_history, 'count': len(self.scan_history)}

    def generate_summary(self) -> Dict:
        return {
            'total_scans': len(self.scan_history),
            'reports_generated': self.metrics['reports'],
            'latest_scan': self.scan_history[-1] if self.scan_history else None
        }

# ==================== OLLAMA MCP AGENT ====================
class OllamaMCPAgent(BaseAgent):
    """
    AI agent that connects an Ollama LLM to a live MCP server exposing all Kali tools.
    Handles multi-turn tool-calling loops, streaming tokens to the web UI via SocketIO.
    """

    SYSTEM_PROMPT = (
        "You are AutoHack AI, an expert autonomous penetration testing assistant "
        "with access to Kali Linux tools via MCP.\n"
        "Available tools: nmap_scan, nikto_scan, sqlmap_scan, gobuster_scan, "
        "hydra_brute, theharvester_scan, dnsrecon_scan, enum4linux_scan, "
        "wpscan_scan, metasploit_run, whois_lookup, dirb_scan, run_custom_command.\n\n"
        "RULES:\n"
        "1. Always remind the user to only test systems they own or have written permission to test.\n"
        "2. Explain what each tool does before running it.\n"
        "3. Chain tools intelligently based on previous results.\n"
        "4. Summarize findings with actionable next steps.\n"
        "5. Never run destructive commands without explicit confirmation."
    )

    MCP_SERVER_CODE = '''#!/usr/bin/env python3
import asyncio, subprocess, shutil, sys, os, tempfile
from typing import Any
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
except ImportError:
    subprocess.check_call([sys.executable,"-m","pip","install","mcp"])
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types

app = Server("kali-mcp-server")
TIMEOUT = 120

def _run(cmd,timeout=TIMEOUT):
    if not shutil.which(cmd[0]):
        return {"stdout":"","stderr":f"Tool {cmd[0]} not found. Install: sudo apt install {cmd[0]}","returncode":127}
    try:
        r = subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
        return {"stdout":r.stdout,"stderr":r.stderr,"returncode":r.returncode}
    except subprocess.TimeoutExpired:
        return {"stdout":"","stderr":f"Timed out after {timeout}s","returncode":-1}
    except Exception as e:
        return {"stdout":"","stderr":str(e),"returncode":-1}

def _fmt(r,name):
    parts=[f"=== {name.upper()} ==="]
    if r["stdout"]: parts.append(r["stdout"])
    if r["stderr"]: parts.append(f"[STDERR]\\n{r['stderr']}")
    parts.append(f"[exit:{r['returncode']}]")
    return "\\n".join(parts)

@app.list_tools()
async def list_tools():
    return [
        types.Tool(name="nmap_scan",description="Nmap port/service scan",inputSchema={"type":"object","properties":{"target":{"type":"string"},"flags":{"type":"string","default":"-sV -sC"}},"required":["target"]}),
        types.Tool(name="nikto_scan",description="Nikto web vulnerability scan",inputSchema={"type":"object","properties":{"target":{"type":"string"},"extra_flags":{"type":"string","default":""}},"required":["target"]}),
        types.Tool(name="sqlmap_scan",description="SQLMap SQL injection test",inputSchema={"type":"object","properties":{"url":{"type":"string"},"level":{"type":"integer","default":1},"risk":{"type":"integer","default":1},"extra_flags":{"type":"string","default":"--batch"}},"required":["url"]}),
        types.Tool(name="gobuster_scan",description="Gobuster directory brute-force",inputSchema={"type":"object","properties":{"url":{"type":"string"},"wordlist":{"type":"string","default":"/usr/share/wordlists/dirb/common.txt"},"threads":{"type":"integer","default":10},"extensions":{"type":"string","default":""}},"required":["url"]}),
        types.Tool(name="hydra_brute",description="Hydra brute force attack",inputSchema={"type":"object","properties":{"target":{"type":"string"},"service":{"type":"string"},"userlist":{"type":"string","default":"/usr/share/wordlists/metasploit/unix_users.txt"},"passlist":{"type":"string","default":"/usr/share/wordlists/rockyou.txt"},"extra_flags":{"type":"string","default":"-t 4"}},"required":["target","service"]}),
        types.Tool(name="theharvester_scan",description="theHarvester OSINT email/subdomain harvesting",inputSchema={"type":"object","properties":{"domain":{"type":"string"},"sources":{"type":"string","default":"google,bing"},"limit":{"type":"integer","default":100}},"required":["domain"]}),
        types.Tool(name="dnsrecon_scan",description="DNSRecon DNS enumeration",inputSchema={"type":"object","properties":{"domain":{"type":"string"},"type":{"type":"string","default":"std"}},"required":["domain"]}),
        types.Tool(name="enum4linux_scan",description="enum4linux SMB/NetBIOS enumeration",inputSchema={"type":"object","properties":{"target":{"type":"string"},"flags":{"type":"string","default":"-a"}},"required":["target"]}),
        types.Tool(name="wpscan_scan",description="WPScan WordPress scanner",inputSchema={"type":"object","properties":{"url":{"type":"string"},"enumerate":{"type":"string","default":"vp,vt,u"},"extra_flags":{"type":"string","default":""}},"required":["url"]}),
        types.Tool(name="metasploit_run",description="Run Metasploit module via msfconsole",inputSchema={"type":"object","properties":{"commands":{"type":"string"},"timeout":{"type":"integer","default":120}},"required":["commands"]}),
        types.Tool(name="whois_lookup",description="WHOIS domain/IP lookup",inputSchema={"type":"object","properties":{"target":{"type":"string"}},"required":["target"]}),
        types.Tool(name="dirb_scan",description="DIRB web content scanner",inputSchema={"type":"object","properties":{"url":{"type":"string"},"wordlist":{"type":"string","default":"/usr/share/dirb/wordlists/common.txt"}},"required":["url"]}),
        types.Tool(name="run_custom_command",description="Run any custom Kali Linux command",inputSchema={"type":"object","properties":{"command":{"type":"string"},"timeout":{"type":"integer","default":60}},"required":["command"]}),
    ]

@app.call_tool()
async def call_tool(name,arguments):
    if name=="nmap_scan":
        cmd=["nmap"]+arguments.get("flags","-sV -sC").split()+[arguments["target"]]
        return [types.TextContent(type="text",text=_fmt(_run(cmd),"nmap"))]
    elif name=="nikto_scan":
        cmd=["nikto","-h",arguments["target"]]+arguments.get("extra_flags","").split()
        return [types.TextContent(type="text",text=_fmt(_run(cmd),"nikto"))]
    elif name=="sqlmap_scan":
        cmd=["sqlmap","-u",arguments["url"],f"--level={arguments.get(\'level\',1)}",f"--risk={arguments.get(\'risk\',1)}"]+arguments.get("extra_flags","--batch").split()
        return [types.TextContent(type="text",text=_fmt(_run(cmd),"sqlmap"))]
    elif name=="gobuster_scan":
        cmd=["gobuster","dir","-u",arguments["url"],"-w",arguments.get("wordlist","/usr/share/wordlists/dirb/common.txt"),"-t",str(arguments.get("threads",10))]
        if arguments.get("extensions"): cmd+=["-x",arguments["extensions"]]
        return [types.TextContent(type="text",text=_fmt(_run(cmd),"gobuster"))]
    elif name=="hydra_brute":
        cmd=["hydra","-L",arguments.get("userlist","/usr/share/wordlists/metasploit/unix_users.txt"),"-P",arguments.get("passlist","/usr/share/wordlists/rockyou.txt"),arguments["target"],arguments["service"]]+arguments.get("extra_flags","-t 4").split()
        return [types.TextContent(type="text",text=_fmt(_run(cmd,timeout=300),"hydra"))]
    elif name=="theharvester_scan":
        cmd=["theHarvester","-d",arguments["domain"],"-b",arguments.get("sources","google,bing"),"-l",str(arguments.get("limit",100))]
        return [types.TextContent(type="text",text=_fmt(_run(cmd),"theharvester"))]
    elif name=="dnsrecon_scan":
        cmd=["dnsrecon","-d",arguments["domain"],"-t",arguments.get("type","std")]
        return [types.TextContent(type="text",text=_fmt(_run(cmd),"dnsrecon"))]
    elif name=="enum4linux_scan":
        cmd=["enum4linux"]+arguments.get("flags","-a").split()+[arguments["target"]]
        return [types.TextContent(type="text",text=_fmt(_run(cmd),"enum4linux"))]
    elif name=="wpscan_scan":
        cmd=["wpscan","--url",arguments["url"],"--enumerate",arguments.get("enumerate","vp,vt,u")]+arguments.get("extra_flags","").split()
        return [types.TextContent(type="text",text=_fmt(_run(cmd),"wpscan"))]
    elif name=="metasploit_run":
        script=arguments["commands"].replace(";","\\n")+"\\nexit\\n"
        with tempfile.NamedTemporaryFile(mode="w",suffix=".rc",delete=False) as f:
            f.write(script); rc=f.name
        r=_run(["msfconsole","-q","-r",rc],timeout=arguments.get("timeout",120))
        os.unlink(rc)
        return [types.TextContent(type="text",text=_fmt(r,"metasploit"))]
    elif name=="whois_lookup":
        return [types.TextContent(type="text",text=_fmt(_run(["whois",arguments["target"]]),"whois"))]
    elif name=="dirb_scan":
        cmd=["dirb",arguments["url"],arguments.get("wordlist","/usr/share/dirb/wordlists/common.txt")]
        return [types.TextContent(type="text",text=_fmt(_run(cmd),"dirb"))]
    elif name=="run_custom_command":
        return [types.TextContent(type="text",text=_fmt(_run(arguments["command"].split(),timeout=arguments.get("timeout",60)),"custom"))]
    return [types.TextContent(type="text",text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (r,w):
        await app.run(r,w,app.create_initialization_options())

if __name__=="__main__":
    asyncio.run(main())
'''

    def __init__(self, tool_manager: ToolManager, socketio_instance=None):
        super().__init__('ollama_mcp', tool_manager)
        self.capabilities = ['ai_chat', 'tool_orchestration', 'autonomous_assessment', 'all_kali_tools']
        self.metrics = {'chats': 0, 'tool_calls': 0}
        self.socketio = socketio_instance
        self.current_model = 'llama3.1'
        self.chat_history: List[Dict] = []
        self._server_script_path: Optional[str] = None
        self._write_server_script()

    def _write_server_script(self):
        """Write the embedded MCP server to a temp file."""
        tf = tempfile.NamedTemporaryFile(mode='w', suffix='_kali_mcp_server.py', delete=False)
        tf.write(self.MCP_SERVER_CODE)
        tf.close()
        self._server_script_path = tf.name

    def set_model(self, model: str):
        self.current_model = model

    def _mcp_tool_to_ollama(self, tool) -> Dict:
        return {
            'type': 'function',
            'function': {
                'name': tool.name,
                'description': tool.description,
                'parameters': tool.inputSchema,
            }
        }

    def chat(self, user_message: str) -> Dict:
        """Run one user turn through Ollama + MCP tool loop."""
        if not OLLAMA_AVAILABLE:
            return {'success': False, 'error': 'Ollama not installed. Run: pip install ollama'}
        if not MCP_AVAILABLE:
            return {'success': False, 'error': 'MCP not installed. Run: pip install mcp'}

        self.metrics['chats'] += 1
        self.chat_history.append({'role': 'user', 'content': user_message})

        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._async_chat())
                loop.close()
            except Exception as e:
                if self.socketio:
                    self.socketio.emit('chat_done', {'final_text': f'Error: {e}'})

        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
        return {'success': True, 'message': 'Processing...'}

    async def _async_chat(self):
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[self._server_script_path],
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                ollama_tools = [self._mcp_tool_to_ollama(t) for t in tools_result.tools]

                messages = [{'role': 'system', 'content': self.SYSTEM_PROMPT}] + self.chat_history

                # Agentic tool-calling loop
                while True:
                    response = ollama_lib.chat(
                        model=self.current_model,
                        messages=messages,
                        tools=ollama_tools,
                    )
                    msg = response['message']

                    if not msg.get('tool_calls'):
                        # Final text response
                        text = msg.get('content', '')
                        self.chat_history.append({'role': 'assistant', 'content': text})
                        if self.socketio:
                            self.socketio.emit('chat_done', {'final_text': text})
                        break

                    # Model wants to call tools
                    messages.append({
                        'role': 'assistant',
                        'content': msg.get('content', ''),
                        'tool_calls': msg['tool_calls']
                    })

                    for tc in msg['tool_calls']:
                        fn   = tc['function']
                        name = fn['name']
                        args = fn['arguments'] if isinstance(fn['arguments'], dict) else json.loads(fn['arguments'])

                        self.metrics['tool_calls'] += 1
                        if self.socketio:
                            self.socketio.emit('chat_tool_call', {'tool': name, 'args': args})

                        try:
                            tool_result = await session.call_tool(name, args)
                            result_text = '\n'.join(
                                b.text for b in tool_result.content if hasattr(b, 'text')
                            )
                        except Exception as e:
                            result_text = f'Tool error: {e}'

                        if self.socketio:
                            self.socketio.emit('chat_tool_result', {'tool': name, 'result': result_text})

                        messages.append({'role': 'tool', 'content': result_text})

    def process_command(self, command: str) -> Dict:
        return self.chat(command)

    def get_capabilities(self) -> List[str]:
        return self.capabilities

    def get_metrics(self) -> Dict:
        return self.metrics

    def __del__(self):
        if self._server_script_path and os.path.exists(self._server_script_path):
            try: os.unlink(self._server_script_path)
            except: pass

# ==================== ORCHESTRATOR ====================
class AgentOrchestrator:
    def __init__(self, tool_manager: ToolManager, socketio_instance=None):
        self.tool_manager    = tool_manager
        self.recon_agent     = ReconAgent(tool_manager)
        self.exploit_agent   = ExploitAgent(tool_manager)
        self.reporting_agent = ReportingAgent(tool_manager)
        self.ollama_agent    = OllamaMCPAgent(tool_manager, socketio_instance)
        self.agents = {
            'recon':     self.recon_agent,
            'exploit':   self.exploit_agent,
            'reporting': self.reporting_agent,
            'ollama_mcp': self.ollama_agent,
        }
        self.task_history = []

    def process_command(self, command: str) -> Dict:
        cmd_lower = command.lower()
        if any(w in cmd_lower for w in ['scan','nmap','nikto','gobuster','enumerate','dns']):
            result = self.recon_agent.process_command(command)
        elif any(w in cmd_lower for w in ['exploit','sqlmap','hydra','brute','crack']):
            result = self.exploit_agent.process_command(command)
        elif any(w in cmd_lower for w in ['report','history','summary']):
            result = self.reporting_agent.process_command(command)
        elif any(w in cmd_lower for w in ['ask ai','ai:','ollama']):
            result = self.ollama_agent.chat(command)
        else:
            result = self._auto_route(command)

        self.task_history.append({
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'result': result
        })
        if 'vulnerabilities' in result:
            self.reporting_agent.add_scan_result(result)
        return result

    def _auto_route(self, command: str) -> Dict:
        target = self._extract_any_target(command)
        if target:
            return self.recon_agent.process_command(f'scan {target}')
        return {'error': "Try: 'scan 192.168.1.1', 'exploit http://target', or 'generate report'"}

    def _extract_any_target(self, text: str) -> Optional[str]:
        ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)
        if ips: return ips[0]
        domains = re.findall(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b', text)
        return domains[0] if domains else None

    def run_automated_scan(self, target: str, scan_type: str = 'quick') -> Dict:
        result = {
            'target': target, 'scan_type': scan_type,
            'timestamp': datetime.now().isoformat(), 'phases': {}
        }
        recon = self.recon_agent.process_command(f'{scan_type} scan {target}')
        result['phases']['recon'] = recon
        if recon.get('vulnerabilities'):
            result['phases']['vulnerabilities'] = recon['vulnerabilities']
            result['phases']['suggestions'] = self.exploit_agent.process_command(f'suggest exploits for {target}')
        self.reporting_agent.add_scan_result(result)
        result['report'] = self.reporting_agent.generate_report()
        return result

    def get_agent_status(self) -> Dict:
        return {
            name: {
                'status': 'active',
                'capabilities': agent.get_capabilities(),
                'metrics': agent.get_metrics()
            }
            for name, agent in self.agents.items()
        }

# ==================== FLASK APP ====================
flask_app = Flask(__name__)
flask_app.config['SECRET_KEY'] = 'autohack-secret-key'
CORS(flask_app)
socketio = SocketIO(flask_app, cors_allowed_origins='*', async_mode='threading')

tool_manager  = ToolManager()
orchestrator  = AgentOrchestrator(tool_manager, socketio)
task_queue_g  = queue.Queue()


class BackgroundProcessor:
    def __init__(self):
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while self.running:
            try:
                task   = task_queue_g.get(timeout=1)
                result = self._execute(task)
                socketio.emit('task_completed', {'task_id': task.get('id'), 'result': result})
            except queue.Empty:
                continue
            except Exception as e:
                socketio.emit('notification', {'message': f'Error: {e}'})

    def _execute(self, task):
        t = task.get('type', 'command')
        if t == 'command':
            return orchestrator.process_command(task.get('command'))
        elif t == 'scan':
            return orchestrator.run_automated_scan(task.get('target'), task.get('scan_type', 'quick'))
        return {'error': f'Unknown task type: {t}'}


processor = BackgroundProcessor()


# ── Routes ────────────────────────────────────────────────────────────────────
@flask_app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@flask_app.route('/api/tools')
def api_tools():
    return jsonify({'success': True, 'tools': tool_manager.list_tools()})

@flask_app.route('/api/agents')
def api_agents():
    return jsonify({'success': True, 'agents': orchestrator.get_agent_status()})

@flask_app.route('/api/execute', methods=['POST'])
def api_execute():
    data    = request.json
    command = data.get('command')
    if not command:
        return jsonify({'success': False, 'error': 'No command provided'})
    task_id = f'task_{int(time.time())}'
    task_queue_g.put({'id': task_id, 'type': 'command', 'command': command})
    return jsonify({'success': True, 'task_id': task_id})

@flask_app.route('/api/scan', methods=['POST'])
def api_scan():
    data      = request.json
    target    = data.get('target')
    scan_type = data.get('scan_type', 'quick')
    if not target:
        return jsonify({'success': False, 'error': 'No target provided'})
    task_id = f'scan_{int(time.time())}'
    task_queue_g.put({'id': task_id, 'type': 'scan', 'target': target, 'scan_type': scan_type})
    return jsonify({'success': True, 'task_id': task_id})

@flask_app.route('/api/ollama/status')
def api_ollama_status():
    if not OLLAMA_AVAILABLE:
        return jsonify({'available': False, 'error': 'ollama package not installed'})
    try:
        result = ollama_lib.list()
        models = [m['name'] for m in result.get('models', [])]
        return jsonify({'available': True, 'models': models})
    except Exception as e:
        return jsonify({'available': False, 'error': str(e)})

@flask_app.route('/api/ollama/model', methods=['POST'])
def api_ollama_model():
    data  = request.json
    model = data.get('model', 'llama3.1')
    orchestrator.ollama_agent.set_model(model)
    return jsonify({'success': True, 'model': model})

@flask_app.route('/api/ollama/chat', methods=['POST'])
def api_ollama_chat():
    data    = request.json
    message = data.get('message', '')
    model   = data.get('model', 'llama3.1')
    if not message:
        return jsonify({'success': False, 'error': 'No message provided'})
    orchestrator.ollama_agent.set_model(model)
    result = orchestrator.ollama_agent.chat(message)
    return jsonify(result)

@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'Connected to AutoHack AI'})


# ==================== MAIN ====================
def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              AutoHack AI v5.0 + Ollama MCP                    ║
║         Autonomous Hacking Assistant                          ║
║          craete by: Abhishek Rampariya                        ║
╠═══════════════════════════════════════════════════════════════╣
║  Web Interface : http://localhost:5000                        ║
║  Agents        : Recon | Exploit | Reporting | Ollama MCP     ║
║  AI Chat       : Tab → AI CHAT (MCP)                          ║
╚═══════════════════════════════════════════════════════════════╝
    """)

    print('[*] Checking installed tools...')
    for tool, info in tool_manager.list_tools().items():
        status = '✓' if info['installed'] else '✗'
        print(f'    {status} {tool}')

    print()
    if OLLAMA_AVAILABLE:
        try:
            models = [m['name'] for m in ollama_lib.list().get('models', [])]
            print(f'[+] Ollama available — models: {", ".join(models) or "none pulled yet"}')
        except Exception as e:
            print(f'[!] Ollama installed but not running: {e}')
            print('    Start it with: ollama serve')
    else:
        print('[!] Ollama not installed. Run: pip install ollama && ollama serve')

    print()
    print('[!] Use responsibly. Only test systems you own or have permission to test.\n')
    print('[*] Starting web server on http://0.0.0.0:5000 ...\n')

    socketio.run(flask_app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n[!] Shutting down AutoHack AI...')
        sys.exit(0)