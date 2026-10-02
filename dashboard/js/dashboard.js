/**
 * dashboard.html - 仪表盘页面 (Dashboard Page)
 * 职责: Charts 统计图、详细统计
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
                cost_estimate: data.usage.cost_estimate || 0,
                uptime: data.usage.uptime || '0h',
                token_consumers: data.usage.token_consumers || [],
                model_stats: data.usage.model_stats || {},
                connections: data.usage.connections || {},
                subscription: data.usage.subscription || {},
                limits: data.usage.limits || {}
            };
        }

        if (data.skills) {
            state.skills = data.skills;
        }

        if (data.agents) {
            state.agents = data.agents;
            // Update AgentMap with server data (use name_key for consistency)
            data.agents.forEach(agent => {
                const nameKey = agent.name_key || agent.name.split(' ')[0].toLowerCase();
                if (!window.AgentMap[nameKey]) {
                    window.AgentMap[nameKey] = {
                        id: nameKey,
                        icon: agent.config?.icon || '🤖',
                        label: agent.config?.label || agent.name,
                        color: 'agent-main'
                    };
                }
            });
        }

        if (data.collaboration) {
            state.collaboration = data.collaboration;
        }

        if (data.task_monitor) state.task_monitor = data.task_monitor;
        if (data.system) state.system = data.system;
        if (data.tasks) state.tasks = data.tasks;
        if (data.documents) state.documents = data.documents;
        if (data.memories) state.memories = data.memories;
        if (data.risks) state.risks = data.risks;
        if (data.models) state.models = data.models;
        
        console.log('[dashboard updateAll] system:', state.system, 'task_monitor:', state.task_monitor, 'tasks:', state.tasks?.length, 'models:', state.models?.length);

        // Stats
        const agentsEl = document.getElementById('stat-agents');
        if (agentsEl) agentsEl.textContent = Object.keys(window.AgentMap).length || 7;

        const activeAgents = Object.values(window.AgentMap).filter(a => a.id !== 'main' && a.id !== 'perfect_openclaw').length;
        const onlineEl = document.getElementById('stat-online');
        if (onlineEl) onlineEl.textContent = activeAgents || 1;

        const skillsEl = document.getElementById('stat-skills');
        if (skillsEl) skillsEl.textContent = data.skills?.ready || 33;

        const messagesEl = document.getElementById('stat-messages');
        if (messagesEl) messagesEl.textContent = data.usage?.messages_today || 0;

        const conns = data.usage?.connections || {};
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
                usage: usageData,
                system: state.system,
                collaboration: state.collaboration,
                task_monitor: state.task_monitor,
                savedAt: Date.now()
            }));
        } catch (e) {}
    }

    // ============================================================
    // RENDER FUNCTIONS
    // ============================================================
    function renderAll() {
        renderSystem();
        renderCharts();
        renderStats();
        renderStaff();
        renderCollab();
        renderTasks();
        renderRisks();
        renderPending();
        renderDocs();
        renderMemory();
        renderMessages();
        renderUsage();
        renderTokenConsumers();
        renderSubscription();
    }

    function renderStaff() {
        const agentGrid = document.getElementById('agent-status-grid');
        if (!agentGrid) return;
        
        const agents = state.agents || [];
        const taskInfo = state.task_monitor || {};
        
        const staffSummary = document.getElementById('staff-summary');
        if (staffSummary) {
            staffSummary.textContent = `${agents.length} 个 Agent | 运行中: ${taskInfo.running_tasks || 0} | 待处理: ${taskInfo.pending_tasks || 0}`;
        }
        
        if (agents.length === 0) {
            agentGrid.innerHTML = '<p style="color: var(--text-muted); padding: 20px; text-align: center;">暂无员工数据</p>';
            return;
        }
        
        agentGrid.innerHTML = agents.map(agent => {
            const name = agent.name || agent.id || '未知';
            const status = agent.status || 'idle';
            const taskCount = agent.tasks || 0;
            const statusClass = status === 'busy' ? 'working' : status === 'waiting' ? 'waiting' : 'idle';
            const statusText = status === 'busy' ? '工作中' : status === 'waiting' ? '等待中' : '空闲';
            return `
                <div class="agent-status-item ${statusClass}">
                    <span class="agent-icon">🤖</span>
                    <div class="agent-info">
                        <div class="agent-name">${window.escapeHtml(name)}</div>
                        <div class="agent-task">${taskCount} 个任务</div>
                    </div>
                    <span class="agent-badge badge-${statusClass}">${statusText}</span>
                </div>
            `;
        }).join('');
    }

    function renderCollab() {
        const collabGrid = document.getElementById('agent-stats-grid');
        const taskChains = document.getElementById('task-chains-list');
        
        const collabSummary = document.getElementById('collab-summary');
        if (collabSummary) {
            const sessions = state.collaboration?.sessions || [];
            collabSummary.textContent = `${sessions.length} 个活跃会话`;
        }
        
        if (collabGrid) {
            const participation = state.collaboration?.agent_participation || {};
            const agents = Object.keys(window.AgentMap);
            collabGrid.innerHTML = agents.map(id => {
                const info = window.AgentMap[id];
                const stats = participation[id] || {};
                return `
                    <div class="agent-status-item idle">
                        <span class="agent-icon">${info?.icon || '🤖'}</span>
                        <div class="agent-info">
                            <div class="agent-name">${info?.label || id}</div>
                            <div class="agent-task">${stats.tasks || 0} 任务 | ${stats.events || 0} 事件</div>
                        </div>
                        <span class="agent-badge badge-idle">${window.formatNumber(stats.tokens || 0)} tokens</span>
                    </div>
                `;
            }).join('');
        }
        
        if (taskChains) {
            const chains = state.collaboration?.task_chains || [];
            if (chains.length === 0) {
                taskChains.innerHTML = '<p style="color: var(--text-muted); padding: 20px; text-align: center;">暂无任务链</p>';
            } else {
                taskChains.innerHTML = chains.slice(0, 10).map(chain => `
                    <div class="list-item">
                        <span class="list-icon">🔗</span>
                        <div class="list-content">
                            <div class="list-title">${window.escapeHtml(chain.title || '任务链')}</div>
                            <div class="list-meta">${chain.steps?.length || 0} 步骤</div>
                        </div>
                    </div>
                `).join('');
            }
        }
    }

    function renderTasks() {
        const taskList = document.getElementById('task-list');
        const taskSummary = document.getElementById('task-summary');
        
        if (taskSummary) {
            const tm = state.task_monitor || {};
            taskSummary.textContent = `总计: ${tm.total_tasks || 0} | 运行: ${tm.running_tasks || 0} | 完成: ${tm.completed_tasks || 0}`;
        }
        
        if (!taskList) return;
        
        const tasks = state.tasks || [];
        if (tasks.length === 0) {
            taskList.innerHTML = '<p style="color: var(--text-muted); padding: 20px; text-align: center;">暂无任务</p>';
            return;
        }
        
        taskList.innerHTML = tasks.slice(0, 20).map(task => {
            const agentId = task.agent || 'main';
            const info = window.AgentMap[agentId] || { icon: '🤖', label: agentId };
            const status = task.status || 'pending';
            const statusClass = status === 'done' ? 'badge-success' : status === 'failed' ? 'badge-danger' : 'badge-info';
            return `
                <div class="list-item">
                    <span class="list-icon">${info.icon}</span>
                    <div class="list-content">
                        <div class="list-title">${window.escapeHtml(task.title || task.subject || '未知任务')}</div>
                        <div class="list-meta">${info.label} | ${task.time || ''}</div>
                    </div>
                    <span class="list-badge ${statusClass}">${status}</span>
                </div>
            `;
        }).join('');
    }

    function renderRisks() {
        const risksList = document.getElementById('risks-list');
        if (!risksList) return;
        
        const risks = state.risks || [];
        if (risks.length === 0) {
            risksList.innerHTML = '<p style="color: var(--text-muted); padding: 15px; text-align: center;">✅ 系统运行正常，暂无风险</p>';
            return;
        }
        
        risksList.innerHTML = risks.map(risk => {
            const levelColors = { high: 'var(--danger)', medium: 'var(--warning)', low: 'var(--accent)' };
            const color = levelColors[risk.level] || 'var(--text-muted)';
            const levelText = { high: '🔴 高', medium: '🟡 中', low: '🟢 低' };
            return `
                <div style="padding: 8px 12px; margin-bottom: 8px; background: var(--bg-primary); border-radius: 6px; border-left: 3px solid ${color};">
                    <span style="font-weight: 600;">${levelText[risk.level] || '⚪ 未知'}</span>
                    <span style="margin-left: 8px;">${window.escapeHtml(risk.message || '')}</span>
                </div>
            `;
        }).join('');
    }

    function renderPending() {
        const pendingList = document.getElementById('pending-list');
        if (!pendingList) return;
        
        const tm = state.task_monitor || {};
        const pendingCount = tm.pending_tasks || 0;
        
        if (pendingCount === 0) {
            pendingList.innerHTML = '<p style="color: var(--text-muted); padding: 15px; text-align: center;">✅ 暂无待处理事项</p>';
            return;
        }
        
        // Get pending tasks from state.tasks if available
        const tasks = state.tasks || [];
        const pendingTasks = tasks.filter(t => t.status === 'pending');
        
        if (pendingTasks.length === 0) {
            pendingList.innerHTML = `<p style="color: var(--text-muted); padding: 15px; text-align: center;">📋 ${pendingCount} 个待处理任务（详情见任务看板）</p>`;
            return;
        }
        
        pendingList.innerHTML = pendingTasks.slice(0, 10).map(task => {
            const agentId = task.agent || 'main';
            const info = window.AgentMap[agentId] || { icon: '🤖', label: agentId };
            return `
                <div class="list-item">
                    <span class="list-icon">${info.icon}</span>
                    <div class="list-content">
                        <div class="list-title">${window.escapeHtml(task.title || task.subject || '未知任务')}</div>
                        <div class="list-meta">${info.label} | ${task.time || ''}</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function renderDocs() {
        const docsList = document.getElementById('docs-list');
        if (!docsList) return;
        
        let docs = state.documents?.files;
        if (!docs) {
            docs = [];
        } else if (typeof docs === 'object' && !Array.isArray(docs)) {
            docs = Object.values(docs);
        }
        
        if (docs.length === 0) {
            docsList.innerHTML = '<p style="color: var(--text-muted); padding: 20px; text-align: center;">暂无文档</p>';
            return;
        }
        
        docsList.innerHTML = docs.slice(0, 10).map(doc => `
            <div class="list-item">
                <span class="list-icon">📄</span>
                <div class="list-content">
                    <div class="list-title">${window.escapeHtml(doc.name || doc.path || '未知')}</div>
                    <div class="list-meta">${doc.size ? window.formatBytes(doc.size) : ''}</div>
                </div>
            </div>
        `).join('');
    }

    function renderMemory() {
        const memoryList = document.getElementById('memory-list');
        if (!memoryList) return;
        
        let mems = state.memories;
        if (!mems) {
            mems = [];
        } else if (typeof mems === 'object' && !Array.isArray(mems)) {
            // API returns {recent: ["file1.md", ...], total: N, by_agent: {...}}
            // Check if by_agent exists for multi-agent memory display
            if (mems.by_agent) {
                const byAgent = mems.by_agent;
                const agentLabels = {
                    'main': '🦞 主调度',
                    'creative': '🎨 创意助手',
                    'dba': '🗄️ 数据库架构师',
                    'dev': '💻 开发助手',
                    'perfect': '✨ 完美助手',
                    'research': '📚 研究助手',
                    'security': '🔒 安全守护'
                };
                let html = '';
                for (const [agent, files] of Object.entries(byAgent)) {
                    if (files && files.length > 0) {
                        const label = agentLabels[agent] || agent;
                        html += `<div style="margin-bottom: 15px;">
                            <div style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 8px;">${label} (${files.length})</div>`;
                        files.slice(0, 5).forEach(file => {
                            html += `<div class="list-item" style="padding: 6px 10px;">
                                <span class="list-icon">📄</span>
                                <div class="list-content">
                                    <div class="list-title" style="font-size: 0.85rem;">${window.escapeHtml(file)}</div>
                                </div>
                            </div>`;
                        });
                        html += '</div>';
                    }
                }
                memoryList.innerHTML = html || '<p style="color: var(--text-muted); padding: 20px; text-align: center;">暂无记忆数据</p>';
                return;
            }
            // Fallback for simple format
            const recentFiles = mems.recent || [];
            mems = recentFiles.map(name => ({
                name: name,
                agent: 'memory',
                path: name
            }));
        }
        
        if (mems.length === 0) {
            memoryList.innerHTML = '<p style="color: var(--text-muted); padding: 20px; text-align: center;">暂无记忆数据</p>';
            return;
        }
        
        memoryList.innerHTML = mems.slice(0, 10).map(mem => `
            <div class="list-item">
                <span class="list-icon">🧠</span>
                <div class="list-content">
                    <div class="list-title">${window.escapeHtml(mem.name || mem.path || '未知')}</div>
                    <div class="list-meta">${mem.agent || '系统'}</div>
                </div>
            </div>
        `).join('');
    }

    function renderMessages() {
        const messageFlow = document.getElementById('message-flow');
        if (!messageFlow) return;
        
        const messages = state.collaboration?.messages || [];
        if (messages.length === 0) {
            messageFlow.innerHTML = '<p style="color: var(--text-muted); padding: 20px; text-align: center;">暂无通信日志</p>';
            return;
        }
        
        messageFlow.innerHTML = messages.slice(0, 20).map(msg => {
            const agent = msg.agent || 'system';
            const icon = window.AgentMap[agent]?.icon || '💬';
            return `
                <div class="message-item" style="padding: 8px 12px; margin-bottom: 8px; background: var(--bg-primary); border-radius: 8px;">
                    <span style="font-size: 0.85rem;">${icon} <strong>${window.escapeHtml(agent)}</strong>: ${window.escapeHtml(msg.content || msg.text || '').substring(0, 100)}</span>
                    <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">${msg.time || ''}</div>
                </div>
            `;
        }).join('');
    }

    function renderUsage() {
        const requestsEl = document.getElementById('usage-requests');
        const tokensEl = document.getElementById('usage-tokens');
        const cacheEl = document.getElementById('usage-cache');
        const cacheRateEl = document.getElementById('usage-cache-rate');
        const costEl = document.getElementById('usage-cost');
        
        if (requestsEl) requestsEl.textContent = usageData.requests_today || 0;
        if (tokensEl) tokensEl.textContent = window.formatNumber(usageData.tokens_used || 0);
        if (cacheEl) cacheEl.textContent = window.formatNumber(usageData.cache_read_today || 0);
        if (cacheRateEl) cacheRateEl.textContent = (usageData.cache_hit_rate || 0) + '%';
        if (costEl) costEl.textContent = (usageData.cost_estimate || 0).toFixed(2);
        
        const uptimeEl = document.getElementById('usage-uptime');
        if (uptimeEl) uptimeEl.textContent = usageData.uptime || '0h';
    }

    function renderTokenConsumers() {
        const tokenConsumersEl = document.getElementById('token-consumers');
        if (!tokenConsumersEl) return;
        
        const consumers = usageData.token_consumers || [];
        if (consumers.length === 0) {
            tokenConsumersEl.innerHTML = '<p style="color: var(--text-muted); padding: 20px; text-align: center;">暂无消耗数据</p>';
            return;
        }
        
        tokenConsumersEl.innerHTML = consumers.map(c => `
            <div style="padding: 12px; margin-bottom: 10px; background: var(--bg-primary); border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-weight: 600;">${window.escapeHtml(c.model || c.name || 'Unknown')}</span>
                    <span style="color: var(--accent);">${window.formatNumber(c.total_tokens || 0)} tokens</span>
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted);">
                    📥 ${window.formatNumber(c.input_tokens || 0)} in | 📤 ${window.formatNumber(c.output_tokens || 0)} out | ${c.count || 0} 次调用
                </div>
            </div>
        `).join('');
    }

    function renderSubscription() {
        const sub = usageData.subscription || {};
        const limits = usageData.limits || {};
        
        const subPlan = document.getElementById('sub-plan');
        const subQuotaInfo = document.getElementById('sub-quota-info');
        const subReset = document.getElementById('sub-reset');
        
        if (subPlan) subPlan.textContent = sub.plan || '免费版';
        if (subQuotaInfo) subQuotaInfo.textContent = sub.quota_info || '-';
        if (subReset) subReset.textContent = sub.reset_date || 'N/A';
        
        const reqLimitText = document.getElementById('req-limit-text');
        const reqProgress = document.getElementById('req-progress');
        const reqResetInfo = document.getElementById('req-reset-info');
        const reqLimit = limits.requests || {};
        
        if (reqLimitText) {
            const used = reqLimit.used || 0;
            const limit = reqLimit.limit || '∞';
            reqLimitText.textContent = used + ' / ' + limit;
        }
        if (reqProgress) {
            reqProgress.style.width = (reqLimit.percent || 0) + '%';
        }
        if (reqResetInfo) {
            reqResetInfo.textContent = '重置: ' + (reqLimit.reset || 'N/A');
        }
        
        const tokenLimitText = document.getElementById('token-limit-text');
        const tokenProgress = document.getElementById('token-progress');
        const tokenResetInfo = document.getElementById('token-reset-info');
        const tokenLimit = limits.tokens || {};
        
        if (tokenLimitText) {
            const used = tokenLimit.used || 0;
            const limit = tokenLimit.limit || '∞';
            tokenLimitText.textContent = used + ' / ' + limit;
        }
        if (tokenProgress) {
            tokenProgress.style.width = (tokenLimit.percent || 0) + '%';
        }
        if (tokenResetInfo) {
            tokenResetInfo.textContent = '重置: ' + (tokenLimit.reset || 'N/A');
        }
    }

    function renderSystem() {
        console.log('[dashboard renderSystem] state.system:', state.system);
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

    function renderCharts() {
        const tm = state.task_monitor || {};
        const chartRunning = document.getElementById('chart-running');
        const chartCompleted = document.getElementById('chart-completed');
        const chartPending = document.getElementById('chart-pending');

        if (chartRunning) chartRunning.textContent = tm.running_tasks || 0;
        if (chartCompleted) chartCompleted.textContent = tm.completed_tasks || 0;
        if (chartPending) chartPending.textContent = tm.pending_tasks || 0;
        
        // Render model cards
        renderModelCards();
        
        // Render task distribution
        renderTaskDistribution();
    }

    function renderTaskDistribution() {
        const taskDistEl = document.getElementById('task-distribution');
        if (!taskDistEl) return;
        
        const tasks = state.tasks || [];
        const agents = state.agents || [];
        
        if (tasks.length === 0) {
            taskDistEl.innerHTML = '<p style="color: var(--text-muted); padding: 20px; text-align: center;">暂无任务数据</p>';
            return;
        }
        
        // Count tasks by agent
        const agentTaskCounts = {};
        tasks.forEach(t => {
            const agent = t.agent || 'unknown';
            agentTaskCounts[agent] = (agentTaskCounts[agent] || 0) + 1;
        });
        
        // Sort by count descending
        const sorted = Object.entries(agentTaskCounts).sort((a, b) => b[1] - a[1]);
        const total = tasks.length;
        const max = sorted.length > 0 ? sorted[0][1] : 1;
        
        const agentLabels = {
            'main': '🦞 帝钳统帅',
            'research': '📚 研究助手',
            'creative': '🎨 创意助手',
            'dev': '💻 开发助手',
            'perfect': '✨ 完美助手',
            'security': '🔒 安全守护',
            'skill-vetter': '🛡️ 安全审查',
            'dba': '🗄️ 数据库架构师'
        };
        
        const agentIcons = {
            'main': '🦞',
            'research': '📚',
            'creative': '🎨',
            'dev': '💻',
            'perfect': '✨',
            'security': '🔒',
            'skill-vetter': '🛡️',
            'dba': '🗄️'
        };
        
        taskDistEl.innerHTML = sorted.map(([agent, count]) => {
            const pct = Math.round((count / max) * 100);
            const label = agentLabels[agent] || agent;
            const icon = agentIcons[agent] || '🤖';
            return `
                <div style="margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span>${icon} ${label}</span>
                        <span style="color: var(--text-muted);">${count} (${Math.round(count/total*100)}%)</span>
                    </div>
                    <div style="height: 8px; background: var(--bg-secondary); border-radius: 4px; overflow: hidden;">
                        <div style="height: 100%; width: ${pct}%; background: var(--accent); border-radius: 4px; transition: width 0.3s;"></div>
                    </div>
                </div>
            `;
        }).join('');
    }

    function renderModelCards() {
        const modelCards = document.getElementById('model-cards');
        if (!modelCards) return;
        
        const models = state.models || [];
        if (models.length === 0) {
            modelCards.innerHTML = '<div class="loading">暂无模型配置</div>';
            return;
        }
        
        modelCards.innerHTML = models.map(model => {
            const isPrimary = model.type === 'primary';
            const isFree = model.is_free;
            const providerIcon = model.provider === 'bailian' ? '🟠' : model.provider === 'anthropic' ? '🔵' : '⚫';
            const statusClass = isPrimary ? 'primary' : 'backup';
            return `
                <div class="model-card ${statusClass}" style="padding: 15px; background: var(--bg-primary); border-radius: 8px; border: 1px solid var(--border);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: 600;">${window.escapeHtml(model.name || model.model_id)}</span>
                        <span style="font-size: 0.75rem; ${isPrimary ? 'color: var(--success);' : 'color: var(--text-muted);'}">${isPrimary ? '主模型' : '备用'}</span>
                    </div>
                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 5px;">
                        ${providerIcon} ${model.provider || '未知'}
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">
                        ${model.calls ? window.formatNumber(model.calls) + ' 次调用' : '无调用记录'}
                        ${isFree ? ' | 🆓 免费' : ''}
                    </div>
                </div>
            `;
        }).join('');
    }

    function renderStats() {
        const tm = state.task_monitor || {};
        const tasksEl = document.getElementById('stat-running');
        const completedEl = document.getElementById('stat-completed');
        const pendingEl = document.getElementById('stat-pending');
        const skillsEl = document.getElementById('stat-skills');
        const messagesEl = document.getElementById('stat-messages');
        const connectionsEl = document.getElementById('stat-connections');

        if (tasksEl) tasksEl.textContent = tm.running_tasks || 0;
        if (completedEl) completedEl.textContent = tm.completed_tasks || 0;
        if (pendingEl) pendingEl.textContent = tm.pending_tasks || 0;
        if (skillsEl) skillsEl.textContent = state.skills?.ready || 33;
        if (messagesEl) messagesEl.textContent = usageData.requests_today || 0;

        const conns = usageData.connections || {};
        const onlineCount = [conns.feishu, conns.qqbot, conns.weixin, conns.gateway, conns.api]
            .filter(c => c === 'connected' || c === 'online' || c === 'active').length;
        if (connectionsEl) connectionsEl.textContent = onlineCount + '/5';

        // Summary stats
        const totalTokens = usageData.tokens_used || 0;
        const totalRequests = usageData.requests_today || 0;
        const inputTokens = usageData.input_tokens_today || 0;
        const outputTokens = usageData.output_tokens_today || 0;
        const cacheHitRate = usageData.cache_hit_rate || 0;

        const summaryToday = document.getElementById('summary-today');
        const summaryRequests = document.getElementById('summary-requests');
        const summaryInput = document.getElementById('summary-input');
        const summaryOutput = document.getElementById('summary-output');
        const summaryCache = document.getElementById('summary-cache');

        if (summaryToday) summaryToday.textContent = totalRequests;
        if (summaryRequests) summaryRequests.textContent = window.formatNumber(totalTokens);
        if (summaryInput) summaryInput.textContent = window.formatNumber(inputTokens);
        if (summaryOutput) summaryOutput.textContent = window.formatNumber(outputTokens);
        if (summaryCache) summaryCache.textContent = cacheHitRate + '%';
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
                    console.log('[XHR] Received data, task_monitor:', data.task_monitor);
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
