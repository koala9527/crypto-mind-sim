// ==================== 交易操作 ====================

// 标签页切换
function switchTab(tab) {
    if (!currentUser) {
        showToast(t('pleaseLogin'), 'warning');
        showLoginModal();
        return;
    }

    // 隐藏所有标签页
    const tabIds = ['strategiesTab', 'positionsTab', 'historyTab'];
    tabIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
    });
    document.querySelectorAll('.tab-button').forEach(el => el.classList.remove('active'));

    // 显示选中的标签页
    const tabs = {
        'strategies': 'strategiesTab',
        'positions': 'positionsTab',
        'history': 'historyTab'
    };

    const targetTab = document.getElementById(tabs[tab]);
    if (targetTab) targetTab.classList.remove('hidden');

    // 使用 event.target 或 fallback 查找按钮
    if (typeof event !== 'undefined' && event && event.target) {
        event.target.classList.add('active');
    }

    // 根据标签页加载对应数据
    if (tab === 'strategies') {
        if (typeof updatePrompts === 'function') updatePrompts();
    } else if (tab === 'history') {
        if (typeof updateTradeHistory === 'function') updateTradeHistory();
    }
}

// AI 分析
async function runAIAnalysis() {
    const marketTrendEl = document.getElementById('marketTrend');
    const volatilityEl = document.getElementById('volatility');
    const aiSuggestionEl = document.getElementById('aiSuggestion');

    if (marketTrendEl) {
        marketTrendEl.textContent = t('analyzing');
        marketTrendEl.className = 'badge badge-info';
    }

    // 模拟 AI 分析（实际应调用后端 API）
    setTimeout(() => {
        const trends = [
            { text: t('uptrend'), class: 'badge-success' },
            { text: t('downtrend'), class: 'badge-danger' },
            { text: t('sideways'), class: 'badge-warning' }
        ];
        const trend = trends[Math.floor(Math.random() * trends.length)];

        if (marketTrendEl) {
            marketTrendEl.textContent = trend.text;
            marketTrendEl.className = 'badge ' + trend.class;
        }

        if (volatilityEl) {
            volatilityEl.textContent = (Math.random() * 5 + 1).toFixed(2) + '%';
        }

        const suggestions = [t('suggestLong'), t('suggestShort'), t('suggestHold')];
        if (aiSuggestionEl) {
            aiSuggestionEl.textContent = suggestions[Math.floor(Math.random() * suggestions.length)];
        }
    }, 1500);
}

// 执行 AI 交易
function executeAITrade() {
    showToast(t('aiTradingComingSoon'), 'info');
}

// 开仓
async function openPosition() {
    if (!currentUser) {
        showToast(t('pleaseLogin'), 'warning');
        showLoginModal();
        return;
    }

    const sideEl = document.getElementById('sideSelect');
    const leverageEl = document.getElementById('leverageInput');
    const quantityEl = document.getElementById('quantityInput');

    if (!sideEl || !leverageEl || !quantityEl) {
        console.warn('交易表单元素不存在');
        return;
    }

    const side = sideEl.value;
    const leverage = parseInt(leverageEl.value);
    const quantity = parseFloat(quantityEl.value);

    if (!quantity || quantity <= 0) {
        showToast(t('invalidQuantity'), 'warning');
        return;
    }

    try {
        const response = await fetch(`/api/users/${currentUser.id}/positions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: 'BTC/USDT',
                side,
                leverage,
                quantity
            })
        });

        if (response.ok) {
            const position = await response.json();
            showToast(`开仓成功！${side} ${quantity} BTC @ ${leverage}x`, 'success');
            updateData();
        } else {
            const error = await response.json();
            showToast(error.detail || t('openFailed'), 'error');
        }
    } catch (error) {
        console.error('开仓失败:', error);
        showToast(t('networkError'), 'error');
    }
}

// 平仓
async function closePosition(positionId) {
    if (!confirm('确认平仓？')) return;

    try {
        const response = await fetch(`/api/positions/${positionId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast(t('closeSuccess'), 'success');
            updateData();
        } else {
            showToast(t('closeFailed'), 'error');
        }
    } catch (error) {
        console.error('平仓失败:', error);
        showToast(t('networkError'), 'error');
    }
}

// 激活策略
async function activatePrompt(promptId) {
    try {
        const response = await fetch(`/api/prompts/${promptId}/activate`, {
            method: 'PUT'
        });

        if (response.ok) {
            showToast(t('strategyActivated'), 'success');
            updatePrompts();
        } else {
            showToast(t('activationFailed'), 'error');
        }
    } catch (error) {
        console.error('激活策略失败:', error);
        showToast(t('networkError'), 'error');
    }
}

// 激活用户策略
async function activateStrategy(strategyId) {
    try {
        const userId = localStorage.getItem('userId');
        if (!userId) {
            showToast(t('pleaseLoginFirst'), 'warning');
            return;
        }

        const response = await fetch(`/api/strategies/${strategyId}/activate?user_id=${userId}`, {
            method: 'POST'
        });

        if (response.ok) {
            showToast(t('strategyStarted'), 'success');
            updatePrompts();
        } else {
            const error = await response.json();
            showToast(error.detail || t('startFailed'), 'error');
        }
    } catch (error) {
        console.error('启动策略失败:', error);
        showToast(t('startFailed'), 'error');
    }
}

// 停用用户策略
async function deactivateStrategy(strategyId) {
    try {
        const userId = localStorage.getItem('userId');
        if (!userId) {
            showToast(t('pleaseLoginFirst'), 'warning');
            return;
        }

        const response = await fetch(`/api/strategies/${strategyId}/deactivate?user_id=${userId}`, {
            method: 'POST'
        });

        if (response.ok) {
            showToast(t('strategyDeactivated'), 'success');
            updatePrompts();
        } else {
            const error = await response.json();
            showToast(error.detail || t('deactivateFailed'), 'error');
        }
    } catch (error) {
        console.error('停用策略失败:', error);
        showToast(t('deactivateFailed'), 'error');
    }
}

// 删除用户策略
async function deleteStrategy(strategyId) {
    if (!confirm('确认删除策略？删除后将无法恢复。')) {
        return;
    }

    try {
        const userId = localStorage.getItem('userId');
        if (!userId) {
            showToast(t('pleaseLoginFirst'), 'warning');
            return;
        }

        const response = await fetch(`/api/strategies/${strategyId}?user_id=${userId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showToast(t('strategyDeleted'), 'success');
            updatePrompts();
        } else {
            const error = await response.json();
            showToast(error.detail || t('deleteFailed'), 'error');
        }
    } catch (error) {
        console.error('删除策略失败:', error);
        showToast(t('deleteFailed'), 'error');
    }
}
