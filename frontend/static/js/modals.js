// ==================== 模态框控制函数 ====================

// 登录模态框
function showLoginModal() {
    document.getElementById('loginModal').classList.remove('hidden');
    isLoginMode = true;
    updateModalUI();
}

function hideLoginModal() {
    document.getElementById('loginModal').classList.add('hidden');
    document.getElementById('modalUsername').value = '';
    document.getElementById('modalPassword').value = '';
    const registerApiKey = document.getElementById('registerApiKey');
    const registerBaseUrl = document.getElementById('registerBaseUrl');
    const registerAiModel = document.getElementById('registerAiModel');
    if (registerApiKey) registerApiKey.value = '';
    if (registerBaseUrl) registerBaseUrl.value = '';
    if (registerAiModel) registerAiModel.value = 'claude-4.5-opus';
}

// 切换登录/注册模式
function switchMode() {
    isLoginMode = !isLoginMode;
    updateModalUI();
}

// 更新模态框 UI
function updateModalUI() {
    const registerAiFields = document.getElementById('registerAiFields');
    if (isLoginMode) {
        document.getElementById('modalTitle').textContent = '登录';
        document.getElementById('loginBtn').textContent = '登录';
        document.getElementById('switchText').textContent = '还没有账号？';
        document.getElementById('switchBtn').textContent = '立即注册';
        if (registerAiFields) registerAiFields.classList.add('hidden');
    } else {
        document.getElementById('modalTitle').textContent = '注册';
        document.getElementById('loginBtn').textContent = '注册';
        document.getElementById('switchText').textContent = '已有账号？';
        document.getElementById('switchBtn').textContent = '立即登录';
        if (registerAiFields) registerAiFields.classList.remove('hidden');
    }
}

// 项目介绍模态框
function showAboutModal() {
    document.getElementById('aboutModal').classList.remove('hidden');
}

function hideAboutModal() {
    document.getElementById('aboutModal').classList.add('hidden');
}

// 使用说明模态框
function showGuideModal() {
    document.getElementById('guideModal').classList.remove('hidden');
}

function hideGuideModal() {
    document.getElementById('guideModal').classList.add('hidden');
}

// 常见问题模态框
function showFaqModal() {
    document.getElementById('faqModal').classList.remove('hidden');
}

function hideFaqModal() {
    document.getElementById('faqModal').classList.add('hidden');
}

// FAQ 折叠功能
function toggleFaq(index) {
    const answer = document.getElementById(`faq-answer-${index}`);
    const icon = document.getElementById(`faq-icon-${index}`);

    answer.classList.toggle('active');
    icon.classList.toggle('active');
}

// 交易详情模态框
async function showTradeDetail(tradeId) {
    const modal = document.getElementById('tradeDetailModal');
    if (!modal) {
        console.error('交易详情模态框不存在');
        return;
    }

    modal.classList.remove('hidden');

    // 显示加载状态
    document.getElementById('tradeDetailContent').innerHTML = `
        <div class="text-center py-8">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            <p class="mt-4" style="color: var(--text-secondary)">加载中...</p>
        </div>
    `;

    try {
        // 获取交易详情
        const tradeResponse = await fetch(`/api/trades/${tradeId}`);
        if (!tradeResponse.ok) throw new Error('获取交易详情失败');
        const trade = await tradeResponse.json();

        // 获取AI决策日志
        const aiResponse = await fetch(`/api/users/${currentUser.id}/ai-decisions?limit=20`);
        const aiDecisions = aiResponse.ok ? await aiResponse.json() : [];

        // 渲染详情
        renderTradeDetail(trade, aiDecisions);
    } catch (error) {
        console.error('加载交易详情失败:', error);
        document.getElementById('tradeDetailContent').innerHTML = `
            <div class="text-center py-8">
                <p style="color: var(--danger)">加载失败: ${error.message}</p>
            </div>
        `;
    }
}

function hideTradeDetail() {
    const modal = document.getElementById('tradeDetailModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function renderTradeDetail(trade, aiDecisions) {
    const pnlClass = trade.pnl >= 0 ? 'profit' : 'loss';
    const typeClass = trade.trade_type === 'OPEN' ? 'badge-info' : 'badge-warning';
    const date = new Date(trade.created_at).toLocaleString('zh-CN');

    // 解析市场数据
    let marketData = null;
    try {
        marketData = trade.market_data ? JSON.parse(trade.market_data) : null;
    } catch (e) {
        console.warn('解析市场数据失败:', e);
    }

    // 查找相关的AI决策
    const relatedDecision = aiDecisions.find(d => {
        const decisionTime = new Date(d.created_at).getTime();
        const tradeTime = new Date(trade.created_at).getTime();
        return Math.abs(decisionTime - tradeTime) < 60000; // 1分钟内
    });

    const buildSnapshotData = (rawData) => {
        if (!rawData || typeof rawData !== 'object' || Array.isArray(rawData)) {
            return null;
        }

        const duplicateKeys = new Set([
            'error',
            'exception',
            'price',
            'decision',
            'reasoning',
            'ai_response'
        ]);

        const snapshot = Object.fromEntries(
            Object.entries(rawData).filter(([key, value]) => {
                if (duplicateKeys.has(key)) return false;
                if (value === null || value === undefined) return false;
                if (typeof value === 'string' && value.trim() === '') return false;
                return true;
            })
        );

        return Object.keys(snapshot).length > 0 ? snapshot : null;
    };

    const snapshotData = buildSnapshotData(marketData);

    let content = `
        <div class="space-y-6">
            <!-- 交易基本信息 -->
            <div class="card rounded p-4">
                <h3 class="text-lg font-bold mb-4">交易信息</h3>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <div class="text-sm" style="color: var(--text-secondary)">交易对</div>
                        <div class="font-semibold text-lg">${trade.symbol}</div>
                    </div>
                    <div>
                        <div class="text-sm" style="color: var(--text-secondary)">类型</div>
                        <div><span class="badge ${typeClass}">${trade.trade_type}</span></div>
                    </div>
                    <div>
                        <div class="text-sm" style="color: var(--text-secondary)">方向</div>
                        <div class="font-semibold">${trade.side}</div>
                    </div>
                    <div>
                        <div class="text-sm" style="color: var(--text-secondary)">杠杆</div>
                        <div class="font-semibold">${trade.leverage}x</div>
                    </div>
                    <div>
                        <div class="text-sm" style="color: var(--text-secondary)">价格</div>
                        <div class="font-semibold">${trade.price.toFixed(2)} USDT</div>
                    </div>
                    <div>
                        <div class="text-sm" style="color: var(--text-secondary)">数量</div>
                        <div class="font-semibold">${trade.quantity}</div>
                    </div>
                    <div>
                        <div class="text-sm" style="color: var(--text-secondary)">盈亏</div>
                        <div class="font-semibold ${pnlClass}">${trade.pnl.toFixed(2)} USDT</div>
                    </div>
                    <div>
                        <div class="text-sm" style="color: var(--text-secondary)">时间</div>
                        <div class="text-sm">${date}</div>
                    </div>
                </div>
            </div>
    `;

    // AI决策信息
    if (relatedDecision) {
        content += `
            <div class="card rounded p-4">
                <h3 class="text-lg font-bold mb-4">🤖 AI 决策分析</h3>
                <div class="space-y-3">
                    <div>
                        <div class="text-sm font-semibold mb-1" style="color: var(--text-secondary)">策略名称</div>
                        <div>${relatedDecision.prompt_name}</div>
                    </div>
                    ${relatedDecision.market_context ? `
                        <div>
                            <div class="text-sm font-semibold mb-1" style="color: var(--text-secondary)">市场上下文</div>
                            <div class="text-sm p-3 rounded" style="background: var(--bg-primary); white-space: pre-wrap;">${relatedDecision.market_context}</div>
                        </div>
                    ` : ''}
                    ${relatedDecision.ai_reasoning ? `
                        <div>
                            <div class="text-sm font-semibold mb-1" style="color: var(--text-secondary)">AI 推理过程</div>
                            <div class="text-sm p-3 rounded" style="background: var(--bg-primary); white-space: pre-wrap;">${relatedDecision.ai_reasoning}</div>
                        </div>
                    ` : ''}
                    <div>
                        <div class="text-sm font-semibold mb-1" style="color: var(--text-secondary)">决策结果</div>
                        <div class="font-semibold">${relatedDecision.decision}</div>
                    </div>
                    <div>
                        <div class="text-sm font-semibold mb-1" style="color: var(--text-secondary)">是否执行</div>
                        <div>${relatedDecision.action_taken ? '✅ 已执行' : '❌ 未执行'}</div>
                    </div>
                </div>
            </div>
        `;
    }

    if (trade.trade_type === 'ERROR' && trade.error_message) {
        content += `
            <div class="card rounded p-4">
                <h3 class="text-lg font-bold mb-4">⚠️ 错误详情</h3>
                <div class="p-3 rounded text-sm" style="background: rgba(246, 70, 93, 0.08); color: var(--danger); white-space: pre-wrap;">
                    ${escapeHtml(trade.error_message)}
                </div>
            </div>
        `;
    }

    // 市场数据快照
    if (snapshotData) {
        content += `
            <div class="card rounded p-4">
                <h3 class="text-lg font-bold mb-4">📊 市场数据快照</h3>
                <div class="text-sm p-3 rounded" style="background: var(--bg-primary)">
                    <pre style="white-space: pre-wrap; word-wrap: break-word;">${escapeHtml(JSON.stringify(snapshotData, null, 2))}</pre>
                </div>
            </div>
        `;
    }

    content += `</div>`;

    document.getElementById('tradeDetailContent').innerHTML = content;
}

async function showPositionDetail(positionId) {
    const modal = document.getElementById('positionDetailModal');
    if (!modal) {
        console.error('持仓详情模态框不存在');
        return;
    }

    modal.classList.remove('hidden');
    document.getElementById('positionDetailContent').innerHTML = `
        <div class="text-center py-8">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            <p class="mt-4" style="color: var(--text-secondary)">加载中...</p>
        </div>
    `;

    try {
        const response = await fetch(`/api/positions/${positionId}`);
        if (!response.ok) throw new Error('获取持仓详情失败');
        const position = await response.json();
        renderPositionDetail(position);
    } catch (error) {
        console.error('加载持仓详情失败:', error);
        document.getElementById('positionDetailContent').innerHTML = `
            <div class="text-center py-8">
                <p style="color: var(--danger)">加载失败: ${escapeHtml(error.message)}</p>
            </div>
        `;
    }
}

function hidePositionDetail() {
    const modal = document.getElementById('positionDetailModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function renderPositionDetail(position) {
    const pnlClass = position.unrealized_pnl >= 0 ? 'profit' : 'loss';
    const roiClass = Number(position.roi_pct || 0) >= 0 ? 'profit' : 'loss';
    const sideText = position.side === 'LONG' ? '做多' : '做空';
    const riskText = position.risk_level === 'HIGH' ? '高风险' : position.risk_level === 'MEDIUM' ? '中风险' : '低风险';
    const riskBadgeClass = position.risk_level === 'HIGH' ? 'badge-danger' : position.risk_level === 'MEDIUM' ? 'badge-warning' : 'badge-success';
    const createdAt = new Date(position.created_at).toLocaleString('zh-CN');

    const formatMoney = (value) => `${Number(value || 0).toFixed(2)} USDT`;
    const formatPrice = (value) => value == null ? '暂无' : `${Number(value).toFixed(2)} USDT`;
    const formatPercent = (value) => value == null ? '暂无' : `${Number(value).toFixed(2)}%`;
    const formatDuration = (seconds) => {
        if (!seconds) return '刚开仓';
        if (seconds < 60) return `${seconds}秒`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时`;
        return `${Math.floor(seconds / 86400)}天`;
    };

    document.getElementById('positionDetailContent').innerHTML = `
        <div class="space-y-4">
            <div class="card rounded p-4">
                <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
                    <div>
                        <div class="text-xl font-bold">${escapeHtml(position.symbol)} · ${sideText}</div>
                        <div class="text-sm" style="color: var(--text-secondary)">开仓于 ${createdAt} · ${Number(position.leverage)}x 杠杆</div>
                    </div>
                    <div class="flex items-center gap-2">
                        <span class="badge ${position.side === 'LONG' ? 'badge-success' : 'badge-danger'}">${escapeHtml(position.side)}</span>
                        <span class="badge ${riskBadgeClass}">${riskText}</span>
                        <span class="badge badge-info">${escapeHtml(position.status_text)}</span>
                    </div>
                </div>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                    <div class="card rounded p-3"><div style="color: var(--text-secondary)">浮动盈亏</div><div class="font-bold ${pnlClass}">${position.unrealized_pnl >= 0 ? '+' : ''}${Number(position.unrealized_pnl).toFixed(2)} USDT</div></div>
                    <div class="card rounded p-3"><div style="color: var(--text-secondary)">当前 ROI</div><div class="font-bold ${roiClass}">${formatPercent(position.roi_pct)}</div></div>
                    <div class="card rounded p-3"><div style="color: var(--text-secondary)">占用保证金</div><div class="font-bold">${formatMoney(position.margin)}</div></div>
                    <div class="card rounded p-3"><div style="color: var(--text-secondary)">预估平仓手续费</div><div class="font-bold">${Number(position.estimated_fee_to_close || 0).toFixed(4)} USDT</div></div>
                </div>
            </div>

            <div class="card rounded p-4">
                <h3 class="text-lg font-bold mb-3">持仓流程</h3>
                <div class="grid grid-cols-1 md:grid-cols-4 gap-3 text-sm">
                    <div class="card rounded p-3"><div class="font-semibold mb-1">1. 建仓</div><div>在 ${formatPrice(position.entry_price)} 建立 ${sideText} 仓位。</div></div>
                    <div class="card rounded p-3"><div class="font-semibold mb-1">2. 持有观察</div><div>当前价格 ${formatPrice(position.current_price)}，持续关注波动和手续费成本。</div></div>
                    <div class="card rounded p-3"><div class="font-semibold mb-1">3. 风险监控</div><div>距离爆仓价约 ${formatPercent(position.distance_to_liquidation_pct)}，风险等级为 ${riskText}。</div></div>
                    <div class="card rounded p-3"><div class="font-semibold mb-1">4. 平仓决策</div><div>${escapeHtml(position.next_action_tip)}</div></div>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="card rounded p-4">
                    <h3 class="text-lg font-bold mb-3">关键价格</h3>
                    <div class="grid grid-cols-2 gap-3 text-sm">
                        <div><div style="color: var(--text-secondary)">开仓价</div><div>${formatPrice(position.entry_price)}</div></div>
                        <div><div style="color: var(--text-secondary)">当前价</div><div>${formatPrice(position.current_price)}</div></div>
                        <div><div style="color: var(--text-secondary)">保本参考价</div><div>${formatPrice(position.break_even_price)}</div></div>
                        <div><div style="color: var(--text-secondary)">爆仓参考价</div><div>${formatPrice(position.liquidation_price)}</div></div>
                    </div>
                </div>
                <div class="card rounded p-4">
                    <h3 class="text-lg font-bold mb-3">仓位快照</h3>
                    <div class="grid grid-cols-2 gap-3 text-sm">
                        <div><div style="color: var(--text-secondary)">数量</div><div>${Number(position.quantity).toFixed(6)}</div></div>
                        <div><div style="color: var(--text-secondary)">仓位价值</div><div>${formatMoney(position.notional_value)}</div></div>
                        <div><div style="color: var(--text-secondary)">价格变动</div><div>${formatPercent(position.price_change_pct)}</div></div>
                        <div><div style="color: var(--text-secondary)">持仓时长</div><div>${formatDuration(position.holding_seconds)}</div></div>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="card rounded p-4">
                    <h3 class="text-lg font-bold mb-3">新手解释</h3>
                    <div class="space-y-2 text-sm">
                        <p>${escapeHtml(position.position_explanation)}</p>
                        <p>仓位价值 = 当前价格 × 数量 = <span class="font-semibold">${formatMoney(position.notional_value)}</span>。</p>
                        <p>收益率 ROI = 浮动盈亏 ÷ 保证金 = <span class="font-semibold ${roiClass}">${formatPercent(position.roi_pct)}</span>。</p>
                        <p>若价格走向不符合判断，杠杆会放大亏损，因此要持续关注风险区间。</p>
                    </div>
                </div>
                <div class="card rounded p-4">
                    <h3 class="text-lg font-bold mb-3">风险提示</h3>
                    <div class="space-y-2 text-sm">
                        <p>当前风险等级：<span class="font-semibold">${riskText}</span>。</p>
                        <p>距离爆仓价：<span class="font-semibold">${formatPercent(position.distance_to_liquidation_pct)}</span>，越小越需要谨慎。</p>
                        <p>杠杆倍数：<span class="font-semibold">${Number(position.leverage)}x</span>，高杠杆更容易放大波动。</p>
                        <p>${escapeHtml(position.next_action_tip)}</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// 帮助菜单切换（备用功能）
function toggleHelpMenu() {
    showToast('点击下方图标查看对应帮助内容', 'info', '帮助中心');
}

// ESC 键关闭所有模态框
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideAboutModal();
        hideGuideModal();
        hideFaqModal();
        hideLoginModal();
        hideTradeDetail();
        hidePositionDetail();
        if (typeof hideCreateStrategyModal === 'function') hideCreateStrategyModal();
        if (typeof hideSettingsModal === 'function') hideSettingsModal();
    }
});
