/**
 * DragonClaw Dashboard - Common Utilities (shared across all pages)
 * Version: 1.1.0
 * Refactored: 2026-04-13
 */

// ============================================================
// AGENT CONFIGURATION (source of truth across all pages)
// ============================================================
const AGENT_CONFIG = {
    main: {
        icon: '🦞', label: '帝钳统帅', role: '调度中枢', color: '#f97316',
        skills: ['任务调度', '跨 Agent 协调', '决策制定'],
        description: 'DragonClaw 团队总调度，负责协调各 Agent 工作'
    },
    research: {
        icon: '📚', label: '研究助手', role: '知识探索', color: '#3b82f6',
        skills: ['深度搜索', '信息整理', '报告撰写'],
        description: '专注知识探索和信息检索，为团队提供研究支持'
    },
    creative: {
        icon: '🎨', label: '创意助手', role: '内容创作', color: '#a855f7',
        skills: ['文案创作', '视觉设计', '品牌策划'],
        description: '负责内容创作和创意策划，激发团队创新思维'
    },
    dev: {
        icon: '💻', label: '开发助手', role: '软件开发', color: '#22c55e',
        skills: ['代码开发', '架构设计', '系统调试'],
        description: '专注软件开发和系统架构，提供技术支持'
    },
    perfect_openclaw: {
        icon: '✨', label: '完美助手', role: '深度分析', color: '#ec4899',
        skills: ['深度分析', '质量把控', '流程优化'],
        description: '专注于深度分析和质量把控，确保交付品质'
    },
    security: {
        icon: '🔒', label: '安全守护', role: '安全监控', color: '#ef4444',
        skills: ['威胁检测', '漏洞扫描', '安全审计'],
        description: '负责系统安全和风险监控，保障团队安全运行'
    },
    'skill-vetter': {
        icon: '🛡️', label: '安全审查', role: '质量把控', color: '#f59e0b',
        skills: ['技能审核', '合规检查', '标准制定'],
        description: '专注技能审核和质量合规，确保规范执行'
    },
    dba: {
        icon: '🗄️', label: '数据库架构师', role: '数据库专家', color: '#06b6d4',
        skills: ['数据库设计', '性能优化', '备份恢复'],
        description: '专注数据库架构和运维，支持数据存储方案'
    }
};

// Alias for backward compatibility
const AGENT_MAP = AGENT_CONFIG;

// ============================================================
// CONSTANTS
// ============================================================
const STORE_KEY = 'dragonclaw_dashboard_v2';

// ============================================================
// API UTILITIES
// ============================================================
const API_BASE = window.location.protocol + '//' + window.location.hostname + (window.location.port ? ':' + window.location.port : '');

function apiUrl(path) {
    // Auth disabled - no token required
    const sep = path.includes('?') ? '&' : '?';
    return API_BASE + path + sep + '_=' + Date.now();
}


// Token management

// ============================================================
// UTILITY FUNCTIONS
// ============================================================
function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatNumber(n) {
    if (!n && n !== 0) return '0';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return String(n);
}

function formatBytes(bytes) {
    if (!bytes) return '0 B';
    if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(1) + ' GB';
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(0) + ' MB';
    return (bytes / 1024).toFixed(0) + ' KB';
}

function getAgentInfo(key) {
    return AGENT_CONFIG[key] || { icon: '🤖', label: key };
}

// ============================================================
// FETCH WITH RETRY (exponential backoff, max 3 attempts)
// ============================================================
async function fetchWithRetry(url, options = {}, retries = 3) {
    const defaultOptions = {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
        timeout: 8000
    };
    const opts = { ...defaultOptions, ...options };

    for (let attempt = 0; attempt <= retries; attempt++) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), opts.timeout);

            const response = await fetch(url, {
                ...opts,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = 'index.html';
                    throw new Error('Unauthorized');
                }
                if (attempt < retries) {
                    const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
                    await sleep(delay);
                    continue;
                }
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();
        } catch (e) {
            if (attempt < retries && (e.name === 'AbortError' || e.message.includes('HTTP'))) {
                const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
                console.log(`[fetch] Attempt ${attempt + 1} failed, retrying in ${delay}ms...`);
                await sleep(delay);
                continue;
            }
            throw e;
        }
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================================
// SSE CONNECTION MANAGER (reusable across pages)
// ============================================================
class SSEConnection {
    constructor(options = {}) {
        this.url = options.url || '/api/events';
        this.onMessage = options.onMessage || (() => {});
        this.onOpen = options.onOpen || (() => {});
        this.onError = options.onError || (() => {});
        this.onReconnecting = options.onReconnecting || (() => {});
        this.reconnectAttempts = 0;
        this.maxReconnectDelay = 30000;
        this.eventSource = null;
        this.reconnectTimer = null;
    }

    connect() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        const fullUrl = apiUrl(this.url);
        console.log('[SSE] Connecting to:', fullUrl.replace(/token=[^&]+/, 'token=***'));

        this.eventSource = new EventSource(fullUrl);

        this.eventSource.onopen = () => {
            console.log('[SSE] Connected');
            this.reconnectAttempts = 0;
            this.onOpen();
        };

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.onMessage(data);
            } catch (e) {
                console.error('[SSE] Parse error:', e);
            }
        };

        this.eventSource.onerror = () => {
            console.warn('[SSE] Error, state:', this.eventSource.readyState);
            this.eventSource.close();
            this.eventSource = null;
            this.scheduleReconnect();
        };
    }

    scheduleReconnect() {
        if (this.reconnectTimer) return;
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), this.maxReconnectDelay);
        console.log(`[SSE] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        this.onReconnecting(this.reconnectAttempts);
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, delay);
    }

    disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }
}

// ============================================================
// XHR FALLBACK (for environments where SSE doesn't work)
// ============================================================
function fetchDataWithXHR(url, onSuccess, onError) {
    url = apiUrl(url || '/api/status');
    const xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.timeout = 8000;

    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    onSuccess(data);
                } catch (e) {
                    onError(e);
                }
            } else if (xhr.status === 401) {
                window.location.href = 'index.html';
            } else {
                onError(new Error(`HTTP ${xhr.status}`));
            }
        }
    };

    xhr.onerror = () => onError(new Error('Network error'));
    xhr.ontimeout = () => onError(new Error('Timeout'));

    xhr.send();
    return xhr;
}

// ============================================================
// STATE MANAGEMENT (shared state utilities)
// ============================================================
class DashboardState {
    constructor() {
        this.reset();
    }

    reset() {
        this.agents = [];
        this.tasks = [];
        this.skills = {};
        this.usage = {};
        this.summary = {};
        this.collaboration = {};
        this.documents = {};
        this.memories = {};
        this.risks = [];
        this.system = {};
        this.task_monitor = {};
        this.models = [];
        this.lastUpdate = null;
    }

    update(data) {
        if (data.agents) this.agents = data.agents;
        if (data.tasks) this.tasks = data.tasks;
        if (data.skills) this.skills = data.skills;
        if (data.models) this.models = data.models;
        if (data.usage) this.usage = data.usage;
        if (data.collaboration) this.collaboration = data.collaboration;
        if (data.summary) this.summary = data.summary;
        if (data.documents) this.documents = data.documents;
        if (data.memories) this.memories = data.memories;
        if (data.risks) this.risks = data.risks;
        if (data.system) this.system = data.system;
        if (data.task_monitor) this.task_monitor = data.task_monitor;
        this.lastUpdate = new Date();
    }

    save() {
        try {
            localStorage.setItem(STORE_KEY, JSON.stringify({
                agents: this.agents,
                tasks: this.tasks,
                savedAt: Date.now()
            }));
        } catch (e) { /* ignore */ }
    }

    load() {
        try {
            const stored = localStorage.getItem(STORE_KEY);
            if (!stored) return false;
            const data = JSON.parse(stored);
            if (Date.now() - (data.savedAt || 0) > 60 * 60 * 1000) {
                localStorage.removeItem(STORE_KEY);
                return false;
            }
            if (data.agents) this.agents = data.agents;
            if (data.tasks) this.tasks = data.tasks;
            return true;
        } catch (e) {
            return false;
        }
    }
}

// ============================================================
// CONNECTION STATUS UI HELPER
// ============================================================
function updateConnectionBadge(dotId, textId, isOnline, textOnline, textOffline) {
    const dot = document.getElementById(dotId);
    const text = document.getElementById(textId);
    if (dot) {
        dot.className = 'status-dot ' + (isOnline ? 'online' : 'offline');
    }
    if (text) {
        text.textContent = isOnline ? textOnline : textOffline;
    }
}

// ============================================================
// LOADING / ERROR STATES
// ============================================================
function showLoading(containerId) {
    const el = document.getElementById(containerId);
    if (el) {
        el.innerHTML = '<div class="loading"><div class="loading-skeleton" style="height: 60px; margin: 10px 0;"></div><div class="loading-skeleton" style="height: 120px; margin: 10px 0;"></div></div>';
    }
}

function showError(containerId, message) {
    const el = document.getElementById(containerId);
    if (el) {
        el.innerHTML = `<div style="text-align: center; padding: 30px; color: var(--danger);">
            <div style="font-size: 2rem; margin-bottom: 10px;">⚠️</div>
            <div>${escapeHtml(message)}</div>
        </div>`;
    }
}

// ============================================================
// TASK HELPERS
// ============================================================
function getTaskCounts(tasks, taskMonitor) {
    const running = tasks.filter(t => t.status === 'running' || t.status === 'progress');
    const pending = tasks.filter(t => t.status === 'pending');
    const done = tasks.filter(t => t.status === 'done' || t.status === 'completed');
    const failed = tasks.filter(t => t.status === 'failed');

    return {
        total: taskMonitor?.total_tasks ?? tasks.length,
        running: taskMonitor?.running_tasks ?? running.length,
        pending: taskMonitor?.pending_tasks ?? pending.length,
        completed: taskMonitor?.completed_tasks ?? done.length,
        failed: taskMonitor?.failed_tasks ?? failed.length
    };
}

function createTaskCardHTML(task, extraClass = '') {
    const agentConfig = AGENT_CONFIG[task.agent] || { icon: '🤖', label: task.agent };
    const statusBadge = task.status === 'failed' ? '<span class="badge badge-danger" style="margin-left: 8px;">失败</span>' : '';
    const title = escapeHtml(task.title || task.subject || '未知任务');
    return `
        <div class="task-card ${extraClass}">
            <div class="task-title">${title}${statusBadge}</div>
            <div class="task-meta">
                <span>${agentConfig.icon} ${escapeHtml(agentConfig.label)}</span>
                <span>${escapeHtml(task.time || '')}</span>
            </div>
        </div>
    `;
}

// ============================================================
// RECONNECT BANNER
// ============================================================
function showReconnectBanner(message, isError = false) {
    const banner = document.getElementById('reconnect-banner');
    if (banner) {
        banner.textContent = message;
        banner.className = 'reconnect-banner show' + (isError ? ' error' : '');
    }
}

function hideReconnectBanner() {
    const banner = document.getElementById('reconnect-banner');
    if (banner) {
        banner.className = 'reconnect-banner';
    }
}

// Export for use in HTML files
window.AgentConfig = AGENT_CONFIG;
window.AgentMap = AGENT_MAP;
window.apiUrl = apiUrl;
window.escapeHtml = escapeHtml;
window.formatNumber = formatNumber;
window.formatBytes = formatBytes;
window.getAgentInfo = getAgentInfo;
window.fetchWithRetry = fetchWithRetry;
window.fetchDataWithXHR = fetchDataWithXHR;
window.SSEConnection = SSEConnection;
window.DashboardState = DashboardState;
window.updateConnectionBadge = updateConnectionBadge;
window.showLoading = showLoading;
window.showError = showError;
window.getTaskCounts = getTaskCounts;
window.createTaskCardHTML = createTaskCardHTML;
window.showReconnectBanner = showReconnectBanner;
window.hideReconnectBanner = hideReconnectBanner;
window.STORE_KEY = STORE_KEY;
