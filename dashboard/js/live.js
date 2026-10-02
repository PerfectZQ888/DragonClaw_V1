/**
 * live.html - 实时监控页面 (Live Monitoring Page)
 * 职责: Agent 实时状态、任务流、消息流、活跃会话
 */
(function() {
    'use strict';

    // ============================================================
    // CONSTANTS (page-specific)
    // ============================================================
    const API_BASE = window.location.protocol + '//' + window.location.hostname + ':8888';

    // ============================================================
    // STATE
    // ============================================================
    let tasks = [];
    let activities = [];
    let agents = [];
    let sessions = [];
    let state = {
        collaboration: { recent_activities: [], sessions: [] },
        usage: {},
        system: {},
        task_monitor: {}
    };
    let usageData = {
        tokens_used: 0, requests_today: 0, input_tokens_today: 0,
        output_tokens_today: 0, cache_read_today: 0, cache_hit_rate: 0,
        token_consumers: [], model_stats: {}
    };

    // API URL (with auth token)
    window.apiUrl = function(path) {
        let token = localStorage.getItem('auth_token');
        if (!token) {
            token = localStorage.getItem('dashboard_token') || '';
        }
        const sep = path.includes('?') ? '&' : '?';
        return API_BASE + path + sep + (token ? 'token=' + encodeURIComponent(token) + '&' : '') + '_=' + Date.now();
    };

    // ============================================================
    // SSE CONNECTION
    // ============================================================
    let eventSource = null;
    let reconnectAttempts = 0;

    function updateConnectionUI(status, color) {
        const statusEl = document.getElementById('update-status');
        const dotEl = document.getElementById('live-dot');
        if (statusEl) statusEl.textContent = status;
        if (dotEl) dotEl.style.background = color;
    }

    async function connectSSE() {
        if (eventSource) { eventSource.close(); eventSource = null; }
        const url = window.apiUrl('/api/events');
        console.log('[SSE] Connecting to:', url.replace(/token=[^&]+/, 'token=***'));
        eventSource = new EventSource(url);

        eventSource.onopen = () => {
            console.log('[SSE] Connected successfully');
            updateConnectionUI('实时监控中', '#22c55e');
            reconnectAttempts = 0;
        };

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                updateAll(data);
                updateConnectionUI('实时监控中', '#22c55e');
                reconnectAttempts = 0;
            } catch (e) { console.error('SSE parse error:', e); }
        };

        eventSource.onerror = (e) => {
            console.error('[SSE] Error, state:', eventSource.readyState);
            updateConnectionUI('重连中...', '#eab308');
            eventSource.close();
            eventSource = null;
            reconnectAttempts++;
            const delay = Math.min(5000 * reconnectAttempts, 30000);
            console.log(`[SSE] Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
            setTimeout(connectSSE, delay);
        };
    }

    async function fetchDataFallback() {
        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 5000);
            const response = await fetch(window.apiUrl('/api/status'), {
                method: 'GET',
                headers: { 'Connection': 'close' },
                signal: controller.signal
            });
            clearTimeout(timeout);
            if (response.ok) {
                const data = await response.json();
                updateAll(data);
                const statusEl = document.getElementById('update-status');
                const dotEl = document.getElementById('live-dot');
                if (statusEl) statusEl.textContent = '实时监控中';
                if (dotEl) dotEl.style.background = '#22c55e';
            }
        } catch (e) {
            const statusEl = document.getElementById('update-status');
            const dotEl = document.getElementById('live-dot');
            if (statusEl) statusEl.textContent = '离线模式';
            if (dotEl) dotEl.style.background = '#ef4444';
        }
    }

    // ============================================================
    // DATA UPDATE
    // ============================================================
    function updateAll(data) {
        if (data.usage) {
            usageData = {
                tokens_used: data.usage.tokens_today || data.usage.today_stats?.total_tokens || 0,
                requests_today: data.usage.requests_today || 0,
                input_tokens_today: data.usage.today_stats?.input_tokens || data.usage.input_tokens_today || 0,
                output_tokens_today: data.usage.today_stats?.output_tokens || data.usage.output_tokens_today || 0,
                cache_read_today: data.usage.today_stats?.cache_read || data.usage.cache_read_today || 0,
                cache_hit_rate: data.usage.cache_hit_rate || 0,
                token_consumers: data.usage.token_consumers || [],
                model_stats: data.usage.model_stats || {},
                connections: data.usage.connections || {}
            };
        }

        if (data.skills) {
            state.skills = data.skills;
        }

        if (data.agents && data.agents.length > 0) {
            state.agents = data.agents;
            agents = data.agents.map(a => {
                const nameKey = a.name_key || a.name.split(' ')[0].toLowerCase();
                const mapped = window.AgentMap[nameKey];
                if (mapped) return { ...mapped };
                return { id: nameKey, icon: a.config?.icon || '🤖', label: a.config?.label || a.name, color: 'agent-main' };
            });
        }

        if (data.tasks) {
            const apiTasks = data.tasks || [];
            const newTasks = apiTasks.map((t, idx) => {
                const agentId = t.agent || 'main';
                const mapped = window.AgentMap[agentId] || { icon: '🤖', label: agentId };
                const status = t.status || 'pending';
                return {
                    id: t.id || `task-${idx}`,
                    agent: agentId,
                    agentIcon: mapped.icon,
                    title: t.title,
                    status,
                    priority: t.priority || 'medium',
                    time: t.time || t.modified || new Date().toLocaleTimeString('zh-CN', {hour:'2-digit', minute:'2-digit'}),
                    duration: t.duration || 0,
                    tokens: t.tokens || 0,
                    isReal: true
                };
            });

            newTasks.forEach(newTask => {
                const exists = tasks.find(t => t.title === newTask.title);
                if (exists) { exists.status = newTask.status; }
                else { tasks.unshift(newTask); }
            });

            // 显示全部任务，不限制数量
        }

        if (data.collaboration) {
            state.collaboration = data.collaboration;
            sessions = data.collaboration.sessions || [];
        }

        if (data.task_monitor) state.task_monitor = data.task_monitor;
        if (data.system) state.system = data.system;
        
        console.log('[updateAll] system data:', state.system);
        console.log('[updateAll] task_monitor:', state.task_monitor);

        // Stats
        const agentsEl = document.getElementById('stat-agents');
        if (agentsEl) agentsEl.textContent = agents.length || 7;

        const activeAgents = agents.filter(a => {
            return tasks.filter(t => t.agent === a.id && (t.status === 'running' || t.status === 'progress')).length > 0;
        }).length;
        const onlineEl = document.getElementById('stat-online');
        if (onlineEl) onlineEl.textContent = activeAgents || 1;

        const skillsEl = document.getElementById('stat-skills');
        if (skillsEl) skillsEl.textContent = state.skills?.ready || 33;

        const messagesEl = document.getElementById('stat-messages');
        if (messagesEl) messagesEl.textContent = usageData.requests_today || 0;

        const conns = usageData.connections || {};
        const onlineCount = [conns.feishu, conns.qqbot, conns.weixin, conns.gateway, conns.api]
            .filter(c => c === 'connected' || c === 'online' || c === 'active').length;
        const connEl = document.getElementById('stat-connections');
        if (connEl) connEl.textContent = onlineCount + '/5';

        renderAll();
        renderSystem();
        saveSharedState();

        const lastUpdateEl = document.getElementById('last-update');
        if (lastUpdateEl) lastUpdateEl.textContent = new Date().toLocaleTimeString();
    }

    function saveSharedState() {
        try {
            localStorage.setItem(window.STORE_KEY, JSON.stringify({
                tasks, agents, activities, savedAt: Date.now()
            }));
        } catch (e) {}
    }

    // ============================================================
    // RENDER FUNCTIONS
    // ============================================================
    function renderAll() {
        renderAgents();
        renderTasks();
        renderActivities();
        renderSummary();
    }

    function getAgentStatus(id) {
        const running = tasks.filter(t => t.agent === id && (t.status === 'running' || t.status === 'progress'));
        const pending = tasks.filter(t => t.agent === id && t.status === 'pending');
        const hasActiveSession = sessions.some(s => s.agent === id);
        if (running.length > 0) {
            return { class: 'status-busy', text: '工作中', task: running[0].title, count: running.length };
        } else if (hasActiveSession) {
            return { class: 'status-online', text: '会话中', task: '', count: pending.length };
        } else if (pending.length > 0) {
            return { class: 'status-online', text: '待命', task: '', count: pending.length };
        }
        return { class: 'status-offline', text: '空闲', task: '', count: 0 };
    }

    function renderAgents() {
        const grid = document.getElementById('agents-grid');
        if (!grid) return;

        if (agents.length === 0) {
            grid.innerHTML = Object.values(window.AgentMap).map(info => {
                const status = getAgentStatus(info.id);
                return renderAgentCard(info, status);
            }).join('');
            return;
        }

        grid.innerHTML = agents.map(agent => {
            const status = getAgentStatus(agent.id);
            return renderAgentCard(agent, status);
        }).join('');
    }

    function renderAgentCard(agent, status) {
        const taskCount = tasks.filter(t => t.agent === agent.id).length;
        const safeLabel = window.escapeHtml(agent.label || '');
        const safeModel = window.escapeHtml(agent.model || 'MiniMax-M2.7-highspeed');
        const safeText = window.escapeHtml(status.text || '');
        const safeTask = status.task ? window.escapeHtml(status.task.substring(0, 25)) : '';
        return `
            <div class="agent-card">
                <div class="agent-header">
                    <div class="agent-avatar">${agent.icon}</div>
                    <div class="agent-info">
                        <h3>${safeLabel}</h3>
                        <div class="role">${safeModel}</div>
                    </div>
                </div>
                <div class="agent-body">
                    <div class="agent-status">
                        <span class="status-dot ${status.class}"></span>
                        <span>${safeText}</span>
                    </div>
                    ${safeTask ? `<div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">📋 ${safeTask}...</div>` : ''}
                    <div class="agent-metrics">
                        <div class="metric"><div class="value">${taskCount}</div><div class="label">总任务</div></div>
                        <div class="metric"><div class="value" style="${status.count > 0 ? 'color: var(--success);' : ''}">${status.count}</div><div class="label">进行中</div></div>
                        <div class="metric"><div class="value">✓</div><div class="label">在线</div></div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderTasks() {
        const sortedTasks = [...tasks].sort((a, b) => (b.time || '00:00').localeCompare(a.time || '00:00'));
        const tm = state.task_monitor || {};
        const pending = sortedTasks.filter(t => t.status === 'pending');
        const running = sortedTasks.filter(t => t.status === 'running' || t.status === 'progress');
        const done = sortedTasks.filter(t => t.status === 'done' || t.status === 'completed');
        const failed = sortedTasks.filter(t => t.status === 'failed');
        const recentDone = done.slice(0, 5);

        const statRunning = document.getElementById('stat-running');
        const statCompleted = document.getElementById('stat-completed');
        const taskPending = document.getElementById('task-pending');
        const taskRunning = document.getElementById('task-running');
        const taskDone = document.getElementById('task-done');

        if (statRunning) statRunning.textContent = tm.running_tasks || running.length;
        if (statCompleted) statCompleted.textContent = tm.completed_tasks || done.length;
        if (taskPending) taskPending.textContent = `待处理: ${tm.pending_tasks || pending.length}`;
        if (taskRunning) taskRunning.textContent = `进行中: ${tm.running_tasks || running.length}`;
        if (taskDone) {
            let text = done.length > 0 ? `已完成: ${done.length}` : '';
            if (failed.length > 0) text += ` ❌ 失败: ${failed.length}`;
            taskDone.textContent = text;
        }

        const taskList = document.getElementById('task-list');
        if (!taskList) return;

        const allDisplayTasks = [...running, ...pending, ...failed.slice(0, 3), ...recentDone];
        if (allDisplayTasks.length === 0 && failed.length === 0) {
            taskList.innerHTML = '<div class="loading">暂无任务数据</div>';
            return;
        }

        taskList.innerHTML = allDisplayTasks.map(task => {
            const info = window.AgentMap[task.agent] || { icon: '🤖', label: task.agent, color: 'agent-main' };
            let statusClass, statusText;
            if (task.status === 'running' || task.status === 'progress') {
                statusClass = 'status-progress'; statusText = '进行中';
            } else if (task.status === 'done' || task.status === 'completed') {
                statusClass = 'status-done'; statusText = '已完成';
            } else if (task.status === 'failed') {
                statusClass = 'status-pending'; statusText = '❌ 失败';
            } else {
                statusClass = 'status-pending'; statusText = '待处理';
            }
            const borderStyle = task.status === 'failed' ? 'border-left: 3px solid var(--danger);' : '';
            const safeTitle = window.escapeHtml(task.title || '');
            const safeTime = window.escapeHtml(task.time || '');
            const safeLabel = window.escapeHtml(info.label || '');
            const safeTokens = task.tokens != null ? window.escapeHtml(String(task.tokens)) : '';
            return `
                <div class="task-item" style="${borderStyle}">
                    <div class="task-priority priority-${window.escapeHtml(task.priority || 'low')}"></div>
                    <span class="activity-agent ${info.color}">${info.icon} ${safeLabel}</span>
                    <div class="task-content">
                        <div class="task-title">${safeTitle}</div>
                        <div class="task-meta">${safeTime}${safeTokens ? ` · ${safeTokens} tokens` : ''}</div>
                    </div>
                    <span class="task-status ${statusClass}">${statusText}</span>
                </div>
            `;
        }).join('');
    }

    function renderActivities() {
        const now = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit', minute:'2-digit'});

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

        const recentActivities = state.collaboration?.recent_activities || [];
        const allActivities = [];

        recentActivities.forEach(act => {
            const agentId = act.agent || 'main';
            const agentInfo = window.AgentMap[agentId] || { icon: '🤖', label: agentId };
            let icon = act.icon || '💬';
            if (act.type === 'task') icon = '📋';
            else if (act.type === 'user') icon = '👤';
            allActivities.push({ time: act.time || now, agent: agentInfo.label, agentIcon: agentInfo.icon, content: `${icon} ${formatContent(act.content)}` });
        });

        sessions.forEach(sess => {
            const agentInfo = window.AgentMap[sess.agent] || { icon: '🤖', label: '未知' };
            allActivities.push({ time: sess.updated || now, agent: agentInfo.label, agentIcon: agentInfo.icon, content: `📱 会话活跃 (${sess.channel})` });
        });

        allActivities.sort((a, b) => (b.time || '').localeCompare(a.time || ''));
        if (allActivities.length > 100) allActivities.length = 100;

        const list = document.getElementById('activity-list');
        const countEl = document.getElementById('activity-count');
        if (countEl) countEl.textContent = `${allActivities.length} 条记录`;
        if (list) {
            list.innerHTML = allActivities.length ?
                allActivities.map(a => `
                    <div class="activity-item">
                        <span class="activity-time">${window.escapeHtml(a.time || '')}</span>
                        <span class="activity-content" style="word-break: break-all; white-space: normal; flex: 1;">
                            <span style="color: var(--accent);">${a.agentIcon} ${window.escapeHtml(a.agent || '')}</span>
                            <span style="margin-left: 8px;">${window.escapeHtml(a.content || '')}</span>
                        </span>
                    </div>
                `).join('') : '<div class="loading">暂无活动记录</div>';
        }
    }

    function renderSummary() {
        const running = tasks.filter(t => t.status === 'running' || t.status === 'progress');
        const done = tasks.filter(t => t.status === 'done');
        const pending = tasks.filter(t => t.status === 'pending');
        const total = tasks.length;
        const activeTotal = running.length + pending.length;
        const rate = total > 0 ? Math.round((done.length / total) * 100) : 100;

        const totalTokens = usageData.tokens_used || 0;
        const avgTokens = total > 0 ? Math.round(totalTokens / total) : 0;

        const summaryToday = document.getElementById('summary-today');
        const summaryProgress = document.getElementById('summary-progress');
        const summaryRate = document.getElementById('summary-rate');
        const summaryTime = document.getElementById('summary-time');

        if (summaryToday) summaryToday.textContent = activeTotal;
        if (summaryProgress) summaryProgress.textContent = running.length;
        if (summaryRate) summaryRate.textContent = rate + '%';
        if (summaryTime) summaryTime.textContent = window.formatNumber(avgTokens) + ' tokens';

        const usageSummary = document.getElementById('usage-summary');
        if (usageSummary) {
            usageSummary.innerHTML = `
                <div style="display: flex; gap: 15px; justify-content: center; font-size: 0.8rem;">
                    <span>🔄 ${usageData.requests_today} 请求</span>
                    <span>📥 ${window.formatNumber(usageData.input_tokens_today)} in</span>
                    <span>📤 ${window.formatNumber(usageData.output_tokens_today)} out</span>
                    <span>⚡ 缓存 ${usageData.cache_hit_rate || 0}%</span>
                </div>
            `;
        }

        // Agent distribution
        const agentParticipation = state.collaboration?.agent_participation || {};
        const counts = {};
        const agentTokens = {};

        tasks.forEach(t => { counts[t.agent] = (counts[t.agent] || 0) + 1; });
        Object.entries(agentParticipation).forEach(([agent, data]) => { agentTokens[agent] = data.tokens || 0; });

        const dist = document.getElementById('agent-distribution');
        if (dist) {
            const max = Math.max(...Object.values(counts), 1);
            dist.innerHTML = Object.entries(counts).map(([id, count]) => {
                const info = window.AgentMap[id] || { icon: '🤖', label: id };
                const barClass = id === 'main' || id === 'perfect_openclaw' ? 'bar-research' :
                                  id === 'security' || id === 'skill-vetter' ? 'bar-security' :
                                  id === 'dev' ? 'bar-dev' : 'bar-creative';
                const tokens = agentTokens[id] || 0;
                return `
                    <div class="chart-bar">
                        <span class="chart-label">${info.icon} ${window.escapeHtml(info.label || '')}</span>
                        <div class="chart-bar-container">
                            <div class="chart-bar-fill ${barClass}" style="width: ${(count/max)*100}%"></div>
                        </div>
                        <span>${count} 任务</span>
                        <span style="color: var(--success); font-size: 0.75rem; margin-left: 10px;">${window.formatNumber(tokens)} tokens</span>
                    </div>
                `;
            }).join('') || '<div class="loading">暂无任务数据</div>';
        }

        // Recent completed
        const allCompleted = tasks
            .filter(t => t.status === 'done' || t.status === 'failed')
            .sort((a, b) => (b.time || '').localeCompare(a.time || ''));

        const renderContent = allCompleted.length === 0
            ? '<div class="loading">暂无已完成任务</div>'
            : allCompleted.slice(0, 5).map(task => {
                const info = window.AgentMap[task.agent] || { icon: '🤖', label: task.agent };
                const statusIcon = task.status === 'done' ? '✅' : '❌';
                const statusText = task.status === 'done' ? '已完成' : '失败';
                const safeTitle = window.escapeHtml(task.title || '');
                const safeLabel = window.escapeHtml(info.label || '');
                const safeTime = window.escapeHtml(task.time || '');
                return `
                    <div class="completed-item">
                        <span class="completed-icon">${info.icon}</span>
                        <div class="completed-info">
                            <div class="completed-task" style="word-break: break-all; white-space: normal;">${statusIcon} ${safeTitle.substring(0, 55)}${safeTitle.length > 55 ? '...' : ''}</div>
                            <div class="completed-time">${safeLabel} · ${safeTime} · ${statusText}</div>
                        </div>
                    </div>
                `;
            }).join('');

        const recentLists = document.getElementsByClassName('recent-completed-list');
        for (const list of recentLists) { list.innerHTML = renderContent; }
    }

    function renderSystem() {
        console.log('[renderSystem] called, state.system:', state.system);
        const sys = state.system || {};
        const cpuPct = typeof sys.cpu_percent === 'number' ? sys.cpu_percent : null;
        const memPct = typeof sys.memory?.percent === 'number' ? sys.memory.percent : null;
        const diskPct = typeof sys.disk?.percent === 'number' ? sys.disk.percent : null;

        const cpuEl = document.getElementById('sys-cpu');
        const memEl = document.getElementById('sys-mem');
        const diskEl = document.getElementById('sys-disk');

        if (cpuEl) {
            if (cpuEl) cpuEl.textContent = cpuPct !== null ? cpuPct.toFixed(1) + '%' : '-';
            if (memEl) memEl.textContent = memPct !== null ? memPct.toFixed(1) + '%' : '-';
            if (diskEl) diskEl.textContent = diskPct !== null ? diskPct.toFixed(1) + '%' : '-';

            const cpuBar = document.getElementById('sys-cpu-bar');
            const memBar = document.getElementById('sys-mem-bar');
            const diskBar = document.getElementById('sys-disk-bar');

            if (cpuBar && cpuPct !== null) {
                cpuBar.style.width = cpuPct + '%';
                cpuBar.style.background = cpuPct > 80 ? 'var(--danger)' : cpuPct > 50 ? 'var(--warning)' : 'var(--success)';
            }
            if (memBar && memPct !== null) {
                memBar.style.width = memPct + '%';
                memBar.style.background = memPct > 80 ? 'var(--danger)' : memPct > 50 ? 'var(--warning)' : 'var(--success)';
            }
            if (diskBar && diskPct !== null) {
                diskBar.style.width = diskPct + '%';
                diskBar.style.background = diskPct > 80 ? 'var(--danger)' : diskPct > 50 ? 'var(--warning)' : 'var(--success)';
            }

            const loadAvg = sys.load;
            if (loadAvg && Array.isArray(loadAvg)) {
                const loadEl = document.getElementById('sys-load');
                if (loadEl) loadEl.textContent = loadAvg.map(v => v.toFixed(2)).join(' / ');
            }
            if (sys.memory) {
                const memFreeEl = document.getElementById('sys-mem-free');
                if (memFreeEl) memFreeEl.textContent = window.formatBytes(sys.memory.available || 0);
            }
            if (sys.disk) {
                const diskFreeEl = document.getElementById('sys-disk-free');
                if (diskFreeEl) diskFreeEl.textContent = window.formatBytes(sys.disk.free || 0);
            }

            const extraLive = document.getElementById('extra-disks-live');
            if (extraLive && sys.extra_disks) {
                extraLive.innerHTML = '';
                for (const [mount, info] of Object.entries(sys.extra_disks)) {
                    const pct = info.percent || 0;
                    const barColor = pct > 80 ? 'var(--danger)' : pct > 50 ? 'var(--warning)' : 'var(--success)';
                    extraLive.innerHTML += `
                        <div style="text-align: center; padding: 12px; background: var(--bg-primary); border-radius: 10px;">
                            <div style="font-size: 1.4rem; font-weight: 700; color: var(--accent);">${pct.toFixed(1)}%</div>
                            <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 5px;">${mount}</div>
                            <div style="height: 6px; background: var(--bg-secondary); border-radius: 3px; overflow: hidden; margin-top: 6px;">
                                <div style="height: 100%; background: ${barColor}; border-radius: 3px; width: ${pct}%; transition: width 0.5s;"></div>
                            </div>
                            <div style="font-size: 0.65rem; color: var(--text-muted); margin-top: 3px;">可用 ${window.formatBytes(info.free)}</div>
                        </div>`;
                }
            }

            const uptimeEl = document.getElementById('sys-uptime');
            if (uptimeEl) uptimeEl.textContent = sys.uptime || (sys.uptime != null ? sys.uptime + 'h' : '-');

            const sysUpdateEl = document.getElementById('sys-update');
            if (sysUpdateEl) sysUpdateEl.textContent = '更新: ' + new Date().toLocaleTimeString();
        }
    }

    // ============================================================
    // XHR FALLBACK
    // ============================================================
    function fetchDataWithXHR() {
        const url = window.apiUrl('/api/status');
        console.log('[XHR] Fetching:', url.replace(/token=[^&]+/, 'token=***'));
        const xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.setRequestHeader('Accept', 'application/json');
        xhr.timeout = 5000;
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4 && xhr.status === 200) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    console.log('[XHR] Received data, tasks:', data.tasks?.length || 0, 'agents:', data.agents?.length || 0);
                    updateAll(data);
                    console.log('Data refreshed:', Date.now());
                } catch(e) { console.error('[XHR] Parse error:', e); }
            } else if (xhr.readyState === 4 && xhr.status === 401) {
                window.location.href = 'index.html';
            } else if (xhr.readyState === 4) {
                console.log('[XHR] Status:', xhr.status);
            }
        };
        xhr.onerror = () => console.error('[XHR] Network error');
        xhr.ontimeout = () => console.error('[XHR] Timeout');
        xhr.send();
    }

    // ============================================================
    // INIT
    // ============================================================
    document.addEventListener('DOMContentLoaded', async () => {
        try { localStorage.removeItem(window.STORE_KEY); } catch(e) {}
        fetchDataWithXHR();
        setTimeout(renderAll, 100);
        connectSSE();
        setInterval(fetchDataFallback, 3000);
    });

    // Expose for HTML onclick
    window.showSection = function(id, btn) {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        if (btn) btn.classList.add('active');
    };

})();
