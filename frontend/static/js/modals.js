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
}

// 切换登录/注册模式
function switchMode() {
    isLoginMode = !isLoginMode;
    updateModalUI();
}

// 更新模态框 UI
function updateModalUI() {
    if (isLoginMode) {
        document.getElementById('modalTitle').textContent = '登录';
        document.getElementById('loginBtn').textContent = '登录';
        document.getElementById('switchText').textContent = '还没有账号？';
        document.getElementById('switchBtn').textContent = '立即注册';
    } else {
        document.getElementById('modalTitle').textContent = '注册';
        document.getElementById('loginBtn').textContent = '注册';
        document.getElementById('switchText').textContent = '已有账号？';
        document.getElementById('switchBtn').textContent = '立即登录';
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

    // 市场数据快照
    if (marketData) {
        content += `
            <div class="card rounded p-4">
                <h3 class="text-lg font-bold mb-4">📊 市场数据快照</h3>
                <div class="text-sm p-3 rounded" style="background: var(--bg-primary)">
                    <pre style="white-space: pre-wrap; word-wrap: break-word;">${JSON.stringify(marketData, null, 2)}</pre>
                </div>
            </div>
        `;
    }

    content += `</div>`;

    document.getElementById('tradeDetailContent').innerHTML = content;
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
        if (typeof hideCreateStrategyModal === 'function') hideCreateStrategyModal();
        if (typeof hideSettingsModal === 'function') hideSettingsModal();
    }
});
