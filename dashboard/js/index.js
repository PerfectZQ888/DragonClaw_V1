/**
 * index.html - 综合监控首页 (Overview Page)
 * 职责：系统总览、Agent 网格、任务看板、Skills、活動
 */
(function() {
    'use strict';

    // ============================================================
    // STATE
    // ============================================================
    let state = new DashboardState();
    let lastUpdateTime = null;

    // ============================================================
    // AUTH
    // ============================================================
    function getAuthToken() {
        const urlParams = new URLSearchParams(window.location.search);
        let token = urlParams.get('token');
        if (token) localStorage.setItem('dashboard_token', token);
        else token = localStorage.getItem('dashboard_token');
        return token;
    }

    function isLoggedIn() {
        return !!getAuthToken();
    }

    function logout() {
        localStorage.removeItem('dashboard_token');
        window.location.href = 'login.html';
    }

    function updateAuthUI() {
        const authContainer = document.getElementById('auth-container');
        if (!authContainer) return;
        if (isLoggedIn()) {
            authContainer.innerHTML = `
                <span style="color: var(--success); margin-right: 10px;">✓ 已登录</span>
                <button class="tab" onclick="logout()" style="padding: 6px 12px; font-size: 0.8rem;">退出</button>
            `;
        } else {
            authContainer.innerHTML = `
                <button class="tab" onclick="window.location.href='login.html'" style="background: var(--accent); color: white;">🔐 登录</button>
            `;
        }
    }

    // Override apiUrl for this page
    const _originalApiUrl = window.apiUrl;
    const _serverBase = window.location.protocol + '//' + window.location.hostname + (window.location.port ? ':' + window.location.port : '');
    window.apiUrl = function(path) {
        const token = getAuthToken() || '';
        const sep = path.includes('?') ? '&' : '?';
        return _serverBase + path + sep + 'token=' + encodeURIComponent(token) + '&_=' + Date.now();
    };

    // ============================================================
    // SSE CONNECTION
    // ============================================================
    let eventSource = null;
    let reconnectAttempts = 0;

    function connectSSE() {
        if (eventSource) eventSource.close();

        eventSource = new EventSource(window.apiUrl('/api/events'));

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleDataUpdate(data);
                reconnectAttempts = 0;
                hideReconnectBanner();
            } catch (e) {
                console.error('SSE parse error:', e);
            }
        };

        eventSource.onerror = () => {
            updateConnectionStatus(false);
            eventSource.close();
            eventSource = null;
            reconnectAttempts++;
            const banner = document.getElementById('reconnect-banner');
            if (banner) {
                banner.textContent = `⚠️ 连接中断，正在重连... (第 ${reconnectAttempts} 次)`;
                banner.className = 'reconnect-banner show';
            }
            setTimeout(connectSSE, Math.min(5000 * reconnectAttempts, 30000));
        };
    }

    function updateConnectionStatus(connected) {
        const dot = document.getElementById('status-dot');
        const text = document.getElementById('status-text');
        if (!dot || !text) return;
        if (connected) {
            dot.className = 'status-dot online';
            text.textContent = '实时监控中';
        } else {
            dot.className = 'status-dot offline';
            text.textContent = '离线 (重连中...)';
        }
    }

    // ============================================================
    // DATA UPDATE
    // ============================================================
    function handleDataUpdate(data) {
        state.update(data);
        lastUpdateTime = new Date();
        updateConnectionStatus(true);
        updateUI();
    }

    // ============================================================
    // UI FUNCTIONS
    // ============================================================
    function showSection(id, btn) {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        if (btn) btn.classList.add('active');
    }

    function toggleAllTasks() {
        const body = document.getElementById('all-tasks-body');
        const icon = document.getElementById('toggle-all-icon');
        if (!body || !icon) return;
        body.classList.toggle('show');
        icon.style.transform = body.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
    }

    function updateUI() {
        // Header stats
        const agentsEl = document.getElementById('stat-agents');
        const tasksEl = document.getElementById('stat-tasks');
        const skillsEl = document.getElementById('stat-skills');
        if (agentsEl) agentsEl.textContent = state.agents.length || 7;
        if (tasksEl) tasksEl.textContent = state.tasks.length || 0;
        if (skillsEl) skillsEl.textContent = state.skills?.ready || 0;

        // Overview
        const counts = getTaskCounts(state.tasks, state.task_monitor);
        const overviewAgents = document.getElementById('overview-agents');
        const overviewTasks = document.getElementById('overview-tasks');
        const overviewCompleted = document.getElementById('overview-completed');
        const overviewSkills = document.getElementById('overview-skills');
        if (overviewAgents) overviewAgents.textContent = state.agents.length || 0;
        if (overviewTasks) overviewTasks.textContent = counts.running;
        if (overviewCompleted) {
            overviewCompleted.textContent = counts.completed;
            if (counts.failed > 0) {
                overviewCompleted.innerHTML = `${counts.completed} <span style="color: var(--danger); font-size: 0.8rem;">(${counts.failed} 失败)</span>`;
            }
        }
        if (overviewSkills) overviewSkills.textContent = state.skills?.ready || 0;

        // Last update
        if (lastUpdateTime) {
            const lastUpdateEl = document.getElementById('last-update');
            const footerUpdateEl = document.getElementById('footer-update');
            const timeStr = lastUpdateTime.toLocaleTimeString('zh-CN');
            if (lastUpdateEl) lastUpdateEl.textContent = '最后更新: ' + timeStr;
            if (footerUpdateEl) footerUpdateEl.textContent = timeStr;
        }

        updateSystemSummary();
        renderAgents();
        renderTasks();
        renderSkills();
        renderActivity();
    }

    function updateSystemSummary() {
        const summary = state.summary || {};
        const usage = state.usage || {};
        const connections = usage.connections || {};
        const container = document.getElementById('system-summary');
        if (!container) return;

        container.innerHTML = `
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                <div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">系统状态</div>
                    <div style="margin-top: 5px;">
                        <span class="badge ${summary.system_status === 'healthy' ? 'badge-success' : 'badge-warning'}">
                            ${summary.system_status === 'healthy' ? '✓ 健康' : '⚡ 繁忙'}
                        </span>
                    </div>
                </div>
                <div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">今日请求 / 缓存命中</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent); margin-top: 5px;">
                        ${usage.requests_today || 0}
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-muted);">缓存 ${usage.cache_hit_rate || 0}%</div>
                </div>
                <div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">Token 消耗</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent); margin-top: 5px;">
                        ${formatNumber(usage.tokens_today || 0)}
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-muted);">📥${formatNumber(usage.input_tokens_today||0)} 📤${formatNumber(usage.output_tokens_today||0)}</div>
                </div>
                <div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">连接状态</div>
                    <div style="margin-top: 5px; display: flex; gap: 5px; flex-wrap: wrap;">
                        <span class="badge ${connections.feishu === 'connected' ? 'badge-success' : 'badge-warning'}">飞书</span>
                        <span class="badge ${connections.qqbot === 'connected' ? 'badge-success' : 'badge-warning'}">QQ Bot</span>
                        <span class="badge ${connections.gateway === 'online' ? 'badge-success' : 'badge-warning'}">Gateway</span>
                    </div>
                </div>
            </div>
        `;
    }

    function renderAgents() {
        // Overview grid (compact)
        const overviewGrid = document.getElementById('agents-overview');
        if (overviewGrid) {
            const agentsToShow = state.agents.length > 0 ? state.agents : Object.values(AGENT_CONFIG);
            overviewGrid.innerHTML = agentsToShow.map(item => {
                const agentKey = item.name_key || item.name?.split(' ')[0]?.toLowerCase() || 'main';
                const config = item.config || AGENT_CONFIG[agentKey] || { icon: '🤖', label: item.name || agentKey, role: 'Agent', color: '#666' };
                const rawStatus = item.status || 'idle';
                let status, statusClass;
                if (rawStatus === 'busy') { status = '忙碌中'; statusClass = 'status-busy'; }
                else if (rawStatus === 'active') { status = '活跃'; statusClass = 'status-ready'; }
                else { status = '空闲'; statusClass = 'status-idle'; }
                return `
                    <div class="agent-card">
                        <div class="agent-header">
                            <div class="agent-avatar" style="background: ${config.color}20; color: ${config.color};">${config.icon}</div>
                            <div class="agent-info">
                                <h3>${escapeHtml(config.label)}</h3>
                                <div class="role">${escapeHtml(config.role)}</div>
                            </div>
                        </div>
                        <div style="text-align: center;">
                            <span class="agent-status ${statusClass}">${escapeHtml(status)}</span>
                        </div>
                        <div class="agent-stats">
                            <div class="agent-stat">
                                <div class="value">${item.tasks || 0}</div>
                                <div class="label">任务</div>
                            </div>
                            <div class="agent-stat">
                                <div class="value">${item.sessions || 0}</div>
                                <div class="label">会话</div>
                            </div>
                            <div class="agent-stat">
                                <div class="value" style="font-size: 0.7rem;">${escapeHtml(item.model || 'MiniMax-M2.7')}</div>
                                <div class="label">模型</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Detail grid
        const detailGrid = document.getElementById('agents-detail');
        if (detailGrid) {
            detailGrid.innerHTML = Object.entries(AGENT_CONFIG).map(([key, config]) => {
                const agentData = state.agents.find(a => (a.name_key === key) || (a.name?.toLowerCase().includes(key)));
                const rawStatus = agentData?.status || 'idle';
                let status, statusClass;
                if (rawStatus === 'busy') { status = '忙碌中'; statusClass = 'status-busy'; }
                else if (rawStatus === 'active') { status = '活跃'; statusClass = 'status-ready'; }
                else { status = '空闲'; statusClass = 'status-idle'; }
                const taskCount = agentData?.tasks || 0;
                const skills = config.skills || [];
                const description = config.description || '暂无描述';
                return `
                    <div class="agent-card" style="padding: 20px;">
                        <div class="agent-header">
                            <div class="agent-avatar" style="background: ${config.color}20; color: ${config.color};">${config.icon}</div>
                            <div class="agent-info">
                                <h3>${escapeHtml(config.label)}</h3>
                                <div class="role">${escapeHtml(config.role)}</div>
                            </div>
                            <span class="agent-status ${statusClass}" style="margin-left: auto;">${escapeHtml(status)}</span>
                        </div>
                        <div style="margin: 15px 0; padding: 12px; background: var(--bg-secondary); border-radius: 8px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px;">📝 简介</div>
                            <div style="font-size: 0.85rem; color: var(--text);">${escapeHtml(description)}</div>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 10px;">🛠️ 擅长技能</div>
                            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                                ${skills.map(s => `<span style="padding: 4px 10px; background: var(--bg-secondary); border-radius: 12px; font-size: 0.75rem; border: 1px solid var(--border);">${escapeHtml(s)}</span>`).join('')}
                            </div>
                        </div>
                        <div class="agent-stats">
                            <div class="agent-stat"><div class="value">${taskCount}</div><div class="label">任务</div></div>
                            <div class="agent-stat"><div class="value">${agentData?.sessions || 0}</div><div class="label">会话</div></div>
                            <div class="agent-stat"><div class="value">${escapeHtml(agentData?.model || 'MiniMax-M2.7-highspeed')}</div><div class="label">模型</div></div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    }

    function renderTasks() {
        const tasks = state.tasks || [];
        const tm = state.task_monitor || {};

        const pendingCount = tm.pending_tasks || tasks.filter(t => t.status === 'pending').length;
        const progressCount = tm.running_tasks || tasks.filter(t => t.status === 'running' || t.status === 'progress').length;
        const doneCount = tm.completed_tasks || tasks.filter(t => t.status === 'done' || t.status === 'completed').length;
        const failedCount = tm.failed_tasks || tasks.filter(t => t.status === 'failed').length;
        const totalCount = tm.total_tasks || tasks.length;

        const countEls = {
            'count-pending': pendingCount,
            'count-progress': progressCount,
            'count-done': doneCount,
            'count-failed': failedCount,
            'count-all': totalCount
        };
        Object.entries(countEls).forEach(([id, val]) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        });

        const pendingTasks = tasks.filter(t => t.status === 'pending');
        const progressTasks = tasks.filter(t => t.status === 'running' || t.status === 'progress');
        const doneTasks = tasks.filter(t => t.status === 'done' || t.status === 'completed');
        const failedTasks = tasks.filter(t => t.status === 'failed');

        const emptyMsg = '<p style="color: var(--text-muted); text-align: center; padding: 20px;">暂无</p>';
        const setContent = (id, items) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.innerHTML = items.length ? items.map(t => {
                const agentConfig = AGENT_CONFIG[t.agent] || { icon: '🤖', label: t.agent };
                const statusBadge = t.status === 'failed' ? '<span class="badge badge-danger" style="margin-left: 8px;">失败</span>' : '';
                return `
                    <div class="task-card ${t.status === 'failed' ? 'failed' : t.status === 'done' || t.status === 'completed' ? 'completed' : t.status === 'running' || t.status === 'progress' ? 'running' : ''}">
                        <div class="task-title">${escapeHtml(t.title || t.subject || '未知任务')}${statusBadge}</div>
                        <div class="task-meta">
                            <span>${agentConfig.icon} ${escapeHtml(agentConfig.label)}</span>
                            <span>${escapeHtml(t.time || '')}</span>
                        </div>
                    </div>
                `;
            }).join('') : emptyMsg;
        };

        setContent('tasks-pending', pendingTasks);
        setContent('tasks-progress', progressTasks);
        setContent('tasks-done', doneTasks);
        setContent('tasks-failed', failedTasks);
        setContent('tasks-all', tasks);
    }

    function renderSkills() {
        const skills = state.skills || {};
        const ready = skills.ready || 0;
        const missing = skills.missing || 0;
        const total = ready + missing;
        const percent = total ? Math.round((ready / total) * 100) : 0;

        const summaryEl = document.getElementById('skills-summary');
        if (summaryEl) {
            summaryEl.innerHTML = `
                <span class="badge badge-success">✓ 就绪 ${ready}</span>
                <span class="badge badge-warning" style="margin-left: 10px;">✗ 缺失 ${missing}</span>
            `;
        }

        const statusEl = document.getElementById('skills-status');
        if (!statusEl) return;

        let html = `
            <div style="margin-bottom: 25px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <span>Skills 就绪率</span>
                    <span>${percent}% (${ready}/${total})</span>
                </div>
                <div style="height: 10px; background: var(--bg-primary); border-radius: 5px; overflow: hidden;">
                    <div style="height: 100%; width: ${percent}%; background: linear-gradient(90deg, var(--success), var(--accent)); border-radius: 5px; transition: width 0.5s;"></div>
                </div>
            </div>
        `;

        html += `<h4 style="margin: 20px 0 15px; color: var(--accent);">🛠️ 各 Agent 擅长技能</h4>`;
        html += `<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; margin-bottom: 25px;">`;
        Object.entries(AGENT_CONFIG).forEach(([key, config]) => {
            const agentSkills = config.skills || [];
            html += `
                <div style="background: var(--bg-secondary); border-radius: 10px; padding: 15px; border: 1px solid var(--border);">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                        <span style="font-size: 1.5rem;">${config.icon}</span>
                        <div>
                            <div style="font-weight: 600;">${escapeHtml(config.label)}</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(config.role)}</div>
                        </div>
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                        ${agentSkills.map(s => `<span style="padding: 4px 10px; background: var(--bg-primary); border-radius: 12px; font-size: 0.75rem; border: 1px solid ${config.color}40; color: ${config.color};">${escapeHtml(s)}</span>`).join('')}
                    </div>
                </div>
            `;
        });
        html += `</div>`;

        const skillsList = skills.skills || [];
        if (skillsList.length > 0) {
            html += `<h4 style="margin: 20px 0 15px; color: var(--accent);">📦 系统 Skills 清单</h4>`;
            html += `<div class="skills-grid">`;
            skillsList.forEach(s => {
                html += `
                    <div class="skill-item">
                        <span class="skill-icon">${s.status === 'ready' ? '✓' : '✗'}</span>
                        <span class="skill-name">${escapeHtml(s.name)}</span>
                        <span class="skill-status" style="color: ${s.status === 'ready' ? 'var(--success)' : 'var(--warning)'};">${s.status === 'ready' ? '就绪' : '缺失'}</span>
                    </div>
                `;
            });
            html += `</div>`;
        }

        statusEl.innerHTML = html;
    }

    function renderActivity() {
        const recentActivities = state.collaboration?.recent_activities || [];
        const sessions = state.collaboration?.sessions || [];

        const activities = [];
        const agentLabels = {
            'main': { icon: '🦞', label: '帝钳统帅' },
            'research': { icon: '📚', label: '研究助手' },
            'creative': { icon: '🎨', label: '创意助手' },
            'dev': { icon: '💻', label: '开发助手' },
            'perfect_openclaw': { icon: '✨', label: '完美助手' },
            'security': { icon: '🔒', label: '安全守护' },
            'skill-vetter': { icon: '🛡️', label: '安全审查' },
            'dba': { icon: '🗄️', label: '数据库架构师' }
        };

        function formatContent(content) {
            if (!content) return '';
            if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
                try {
                    const parsed = JSON.parse(content);
                    if (parsed.title) return `📋 ${parsed.title}`;
                    if (parsed.content) return `💬 ${parsed.content.substring(0, 50)}...`;
                    return '📄 JSON 数据';
                } catch { return content.substring(0, 100) + (content.length > 100 ? '...' : ''); }
            }
            if (content.length > 500) return content.substring(0, 500) + '...';
            return content.replace(/\n+/g, ' ').trim();
        }

        recentActivities.forEach(act => {
            const agentId = act.agent || 'main';
            const agentInfo = agentLabels[agentId] || { icon: '🤖', label: agentId };
            let icon = '💬';
            if (act.type === 'task') icon = '📋';
            else if (act.type === 'user') icon = '👤';
            else if (act.type === 'status') icon = '⚡';
            activities.push({ time: act.time || '', agent: agentInfo.label, agentIcon: agentInfo.icon, content: `${icon} ${escapeHtml(formatContent(act.content))}` });
        });

        sessions.forEach(sess => {
            const agentInfo = agentLabels[sess.agent] || { icon: '🤖', label: '未知' };
            activities.push({ time: sess.updated || '', agent: agentInfo.label, agentIcon: agentInfo.icon, content: `📱 会话活跃 (${escapeHtml(sess.channel)})` });
        });

        activities.sort((a, b) => (b.time || '').localeCompare(a.time || ''));

        const countEl = document.getElementById('activity-count');
        const listEl = document.getElementById('activity-list');
        if (countEl) countEl.textContent = activities.length + ' 条';
        if (listEl) {
            listEl.innerHTML = activities.length ?
                activities.slice(0, 100).map(a => `
                    <div class="activity-item">
                        <div class="activity-time">${escapeHtml(a.time)}</div>
                        <div class="activity-content" style="word-break: break-all; white-space: normal; flex: 1;">
                            <span style="color: var(--accent);">${a.agentIcon} ${escapeHtml(a.agent)}</span>
                            <span style="margin-left: 8px;">${escapeHtml(a.content || '')}</span>
                        </div>
                    </div>
                `).join('') : '<p style="color: var(--text-muted); text-align: center; padding: 20px;">暂无活动记录</p>';
        }
    }

    // ============================================================
    // XHR FALLBACK
    // ============================================================
    function fetchDataWithXHR() {
        const xhr = new XMLHttpRequest();
        xhr.open('GET', window.apiUrl('/api/status'), true);
        xhr.setRequestHeader('Accept', 'application/json');
        xhr.timeout = 5000;
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4 && xhr.status === 200) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    handleDataUpdate(data);
                } catch(e) { console.error('XHR parse error:', e); }
            } else if (xhr.readyState === 4 && xhr.status === 401) {
                window.location.href = 'login.html';
            }
        };
        xhr.send();
    }

    // ============================================================
    // INIT
    // ============================================================
    document.addEventListener('DOMContentLoaded', async () => {
        if (!isLoggedIn()) {
            const main = document.querySelector('.main-content');
            const navTabs = document.querySelector('.nav-tabs');
            const headerStats = document.querySelector('.header-stats');
            if (main) main.innerHTML = `
                <div style="text-align: center; padding: 60px 20px;">
                    <div style="font-size: 4rem; margin-bottom: 20px;">🔐</div>
                    <h2 style="color: var(--text); margin-bottom: 15px;">请先登录</h2>
                    <p style="color: var(--text-muted); margin-bottom: 30px;">登录后可查看 DragonClaw 监控数据</p>
                    <button onclick="window.location.href='login.html'" style="padding: 12px 30px; background: var(--accent); color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer;">立即登录</button>
                </div>
            `;
            if (navTabs) navTabs.style.display = 'none';
            if (headerStats) headerStats.style.display = 'none';
            return;
        }

        try { localStorage.removeItem('dragonclaw_state'); } catch(e) {}
        fetchDataWithXHR();
        connectSSE();
        setInterval(fetchDataWithXHR, 10000);
        updateUI();
    });

    // Expose globals for HTML onclick handlers
    window.showSection = showSection;
    window.toggleAllTasks = toggleAllTasks;
    window.logout = logout;

})();
