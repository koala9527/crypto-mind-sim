// ==================== 数据更新 ====================

// updateStrategies 是 updatePrompts 的别名
const updateStrategies = (...args) => updatePrompts(...args);

// 更新所有数据
async function updateData() {
    if (currentUser) {
        // 登录后：获取 BTC 价格（用于保证金计算）+ 显示总资产图表 + 用户数据
        await Promise.all([
            fetchBtcPrice(),
            updateAssetsChart(),
            updateUserInfo(),
            updatePositions(),
            updateLeaderboard(),
            updateStats(),
            updatePrompts()
        ]);
        updateEstimatedMargin();
    } else {
        // 未登录：显示 BTC 行情
        await updatePriceChart();
        await Promise.all([
            updateLeaderboard(),
            updateStats()
        ]);
    }
}

// 获取最新 BTC 价格（登录后用于保证金计算）
async function fetchBtcPrice() {
    try {
        const response = await fetch('/api/price/current');
        const data = await response.json();
        latestBtcPrice = data.price;
    } catch (error) {
        console.error('获取BTC价格失败:', error);
    }
}

// 更新用户信息
async function updateUserInfo() {
    if (!currentUser) return;

    try {
        const response = await fetch(`/api/users/${currentUser.id}`);
        if (!response.ok) {
            throw new Error('用户不存在');
        }
        const user = await response.json();

        const positionsResponse = await fetch(`/api/users/${currentUser.id}/positions`);
        if (!positionsResponse.ok) {
            throw new Error('获取持仓失败');
        }
        const positions = await positionsResponse.json();

        // 确保 positions 是数组
        const positionsArray = Array.isArray(positions) ? positions : [];
        const positionValue = positionsArray.reduce((sum, p) => sum + p.margin + p.unrealized_pnl, 0);
        const totalAssets = user.balance + positionValue;
        const roi = ((totalAssets - user.initial_balance) / user.initial_balance * 100).toFixed(2);

        document.getElementById('balance').textContent = user.balance.toFixed(2) + ' USDT';
        document.getElementById('positionValue').textContent = positionValue.toFixed(2) + ' USDT';
        document.getElementById('totalAssets').textContent = totalAssets.toFixed(2) + ' USDT';

        const roiElement = document.getElementById('roi');
        roiElement.textContent = roi + '%';
        roiElement.className = `text-2xl font-bold mt-1 ${parseFloat(roi) >= 0 ? 'profit' : 'loss'}`;
    } catch (error) {
        console.error('更新用户信息失败:', error);
    }
}

// 更新预估保证金
function updateEstimatedMargin() {
    try {
        const quantityInput = document.getElementById('quantityInput');
        const leverageInput = document.getElementById('leverageInput');
        const estimatedMarginElement = document.getElementById('estimatedMargin');

        // 检查所有必需的元素是否存在
        if (!quantityInput || !leverageInput || !estimatedMarginElement) {
            return;
        }

        // 使用全局 BTC 价格变量
        const currentPrice = latestBtcPrice || 0;
        const quantity = parseFloat(quantityInput.value) || 0;
        const leverage = parseFloat(leverageInput.value) || 1;

        const margin = (currentPrice * quantity) / leverage;
        estimatedMarginElement.textContent = margin.toFixed(2) + ' USDT';
    } catch (error) {
        console.error('计算保证金失败:', error);
    }
}

// 更新持仓列表
async function updatePositions() {
    if (!currentUser) return;

    try {
        const response = await fetch(`/api/users/${currentUser.id}/positions`);
        if (!response.ok) {
            throw new Error('获取持仓失败');
        }
        const positions = await response.json();

        const container = document.getElementById('positionsList');
        if (!container) return;

        // 确保 positions 是数组
        const positionsArray = Array.isArray(positions) ? positions : [];

        if (positionsArray.length === 0) {
            container.innerHTML = '<div class="text-center py-8" style="color: var(--text-secondary)">暂无持仓</div>';
            return;
        }

        container.innerHTML = positionsArray.map(p => {
            const pnlClass = p.unrealized_pnl >= 0 ? 'profit' : 'loss';
            const sideClass = p.side === 'LONG' ? 'badge-success' : 'badge-danger';
            return `
                <div class="card rounded p-4">
                    <div class="flex justify-between items-start mb-3">
                        <div>
                            <span class="font-bold text-lg">${p.symbol}</span>
                            <span class="badge ${sideClass} ml-2">${p.side} ${p.leverage}x</span>
                        </div>
                        <button onclick="closePosition(${p.id})"
                            class="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded text-sm transition">
                            平仓
                        </button>
                    </div>
                    <div class="grid grid-cols-3 gap-2 text-sm">
                        <div>
                            <div style="color: var(--text-secondary)">开仓价</div>
                            <div class="font-semibold">${p.entry_price.toFixed(2)}</div>
                        </div>
                        <div>
                            <div style="color: var(--text-secondary)">数量</div>
                            <div class="font-semibold">${p.quantity}</div>
                        </div>
                        <div>
                            <div style="color: var(--text-secondary)">盈亏</div>
                            <div class="font-semibold ${pnlClass}">${p.unrealized_pnl.toFixed(2)}</div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('更新持仓失败:', error);
    }
}

// 更新交易历史
async function updateTradeHistory() {
    if (!currentUser) return;

    try {
        const response = await fetch(`/api/users/${currentUser.id}/trades?page=${tradeHistoryPage}&page_size=10`);
        const result = await response.json();

        const container = document.getElementById('tradeHistory');
        const pagination = document.getElementById('tradePagination');

        if (result.total === 0) {
            container.innerHTML = '<div class="text-center py-8" style="color: var(--text-secondary)">暂无交易记录</div>';
            pagination.classList.add('hidden');
            return;
        }

        const trades = result.trades;
        container.innerHTML = trades.map(t => {
            const typeClass = t.trade_type === 'OPEN' ? 'badge-info' : 'badge-warning';
            const pnlClass = t.pnl >= 0 ? 'profit' : 'loss';
            const date = new Date(t.created_at).toLocaleString('zh-CN');
            return `
                <div class="card rounded p-3 text-sm hover:shadow-lg transition cursor-pointer" onclick="showTradeDetail(${t.id})">
                    <div class="flex justify-between items-center">
                        <div class="flex items-center gap-2">
                            <span class="badge ${typeClass}">${t.trade_type}</span>
                            <span class="font-semibold">${t.symbol}</span>
                            <span style="color: var(--text-secondary)">${t.side} ${t.leverage}x</span>
                        </div>
                        <div class="text-right">
                            <div class="font-semibold">${t.price.toFixed(2)}</div>
                            ${t.pnl !== 0 ? `<div class="${pnlClass}">${t.pnl.toFixed(2)} USDT</div>` : ''}
                        </div>
                    </div>
                    <div class="mt-2 text-xs" style="color: var(--text-secondary)">
                        ${date}
                    </div>
                </div>
            `;
        }).join('');

        // 更新分页控件
        pagination.classList.remove('hidden');
        document.getElementById('tradeTotalCount').textContent = result.total;
        document.getElementById('tradeCurrentPage').textContent = result.page;
        document.getElementById('tradeTotalPages').textContent = result.total_pages;
        document.getElementById('tradePrevBtn').disabled = result.page <= 1;
        document.getElementById('tradeNextBtn').disabled = result.page >= result.total_pages;
    } catch (error) {
        console.error('更新交易历史失败:', error);
    }
}

// 交易历史翻页
function changeTradeHistoryPage(delta) {
    tradeHistoryPage += delta;
    if (tradeHistoryPage < 1) tradeHistoryPage = 1;
    updateTradeHistory();
}

// 更新排行榜
async function updateLeaderboard() {
    try {
        const response = await fetch('/api/leaderboard');
        const leaderboard = await response.json();

        const container = document.getElementById('leaderboard');
        container.innerHTML = leaderboard.map((entry, index) => {
            const medal = ['🥇', '🥈', '🥉'][index] || `${index + 1}.`;
            const roiClass = entry.roi >= 0 ? 'profit' : 'loss';
            return `
                <div class="card rounded p-3 flex justify-between items-center">
                    <div>
                        <span class="text-lg mr-2">${medal}</span>
                        <span class="font-semibold">${entry.username}</span>
                    </div>
                    <div class="text-right">
                        <div class="font-bold">${entry.total_assets.toFixed(2)}</div>
                        <div class="text-sm ${roiClass}">${entry.roi.toFixed(2)}%</div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('更新排行榜失败:', error);
    }
}

// 更新统计信息
async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        document.getElementById('totalUsers').textContent = stats.total_users;
        document.getElementById('totalPositions').textContent = stats.total_positions;
        document.getElementById('totalTrades').textContent = stats.total_trades;
    } catch (error) {
        console.error('更新统计失败:', error);
    }
}

// 更新 AI 策略列表
async function updatePrompts() {
    try {
        const userId = localStorage.getItem('userId');
        if (!userId) {
            const container = document.getElementById('strategiesList');
            if (container) {
                container.innerHTML = '<div class="text-sm" style="color: var(--text-secondary)">请先登录</div>';
            }
            return;
        }

        const response = await fetch(`/api/strategies?user_id=${userId}`);
        if (!response.ok) {
            throw new Error('获取策略失败');
        }
        const prompts = await response.json();

        const container = document.getElementById('strategiesList');
        if (!container) {
            console.warn('策略列表容器不存在');
            return;
        }

        // 确保 prompts 是数组
        const promptsArray = Array.isArray(prompts) ? prompts : [];

        // 用户只能有一个策略
        if (promptsArray.length === 0) {
            container.innerHTML = `
                <div class="text-center" style="color: var(--text-secondary)">
                    <p class="mb-3">您还没有创建策略</p>
                    <button onclick="showCreateStrategyModal()" class="btn-primary px-4 py-2 rounded">
                        创建我的策略
                    </button>
                </div>
            `;
            return;
        }

        // 显示唯一的策略
        const p = promptsArray[0];
        container.innerHTML = `
            <div class="card rounded p-4">
                <div class="flex justify-between items-start mb-3">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-2">
                            <div class="font-semibold text-lg">${p.name}</div>
                            ${p.is_active ? '<span class="badge badge-success text-xs">✓ 运行中</span>' : '<span class="badge badge-warning text-xs">已停用</span>'}
                        </div>
                        ${p.description ? `<div class="text-sm mb-2" style="color: var(--text-secondary)">${p.description}</div>` : ''}
                        <div class="flex gap-3 text-xs" style="color: var(--text-secondary)">
                            <span>📊 ${p.symbol || 'BTC/USDT'}</span>
                            <span>🤖 ${p.ai_model || 'claude-4.5-opus'}</span>
                            <span>⏱️ ${p.execution_interval || 60}秒</span>
                        </div>
                    </div>
                </div>
                <div class="flex gap-2 flex-wrap">
                    ${!p.is_active ? `
                        <button onclick="activateStrategy(${p.id})"
                            class="btn-primary px-4 py-2 rounded text-sm">
                            启动策略
                        </button>
                    ` : `
                        <button onclick="deactivateStrategy(${p.id})"
                            class="bg-yellow-600 hover:bg-yellow-700 text-white px-4 py-2 rounded text-sm transition">
                            停用策略
                        </button>
                    `}
                    <button onclick="editStrategy(${p.id})"
                        class="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded text-sm transition">
                        编辑策略
                    </button>
                    <button onclick="deleteStrategy(${p.id})"
                        class="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded text-sm transition">
                        删除策略
                    </button>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('更新策略失败:', error);
    }
}
