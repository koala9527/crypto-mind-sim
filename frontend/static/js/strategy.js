// ==================== 策略管理 ====================

let availableModels = [];
let availableSymbols = [];
let presetStrategies = [];
let currentEditingPrompt = null;
let strategySymbolAnchor = null;
let strategyPositionConflictState = null;

function getDefaultStrategySymbol() {
    return availableSymbols[0]?.symbol || 'BTC/USDT';
}

function setStrategySymbolAnchor(symbol) {
    strategySymbolAnchor = symbol || getDefaultStrategySymbol();
}

function hideStrategyPositionConflict() {
    strategyPositionConflictState = null;
    const notice = document.getElementById('strategyPositionConflictNotice');
    const text = document.getElementById('strategyPositionConflictText');
    if (notice) notice.classList.add('hidden');
    if (text) text.textContent = '';
}

function dismissStrategyPositionConflict() {
    hideStrategyPositionConflict();
}

function summarizeConflictPositions(positions) {
    const grouped = new Map();
    positions.forEach((position) => {
        grouped.set(position.symbol, (grouped.get(position.symbol) || 0) + 1);
    });

    return Array.from(grouped.entries())
        .map(([symbol, count]) => `${symbol} × ${count}`)
        .join('、');
}

async function onStrategySymbolChange() {
    const symbolSelect = document.getElementById('strategySymbol');
    const userId = localStorage.getItem('userId');
    if (!symbolSelect || !userId) {
        hideStrategyPositionConflict();
        return;
    }

    const nextSymbol = symbolSelect.value;
    if (!nextSymbol) {
        hideStrategyPositionConflict();
        return;
    }

    if (!strategySymbolAnchor) {
        setStrategySymbolAnchor(nextSymbol);
        hideStrategyPositionConflict();
        return;
    }

    if (nextSymbol === strategySymbolAnchor) {
        hideStrategyPositionConflict();
        return;
    }

    try {
        const response = await fetch(`/api/users/${userId}/positions`);
        if (!response.ok) {
            hideStrategyPositionConflict();
            return;
        }

        const positions = await response.json();
        const conflictPositions = (Array.isArray(positions) ? positions : []).filter(
            (position) => position.symbol !== nextSymbol
        );

        if (conflictPositions.length === 0) {
            hideStrategyPositionConflict();
            return;
        }

        strategyPositionConflictState = {
            nextSymbol,
            symbols: [...new Set(conflictPositions.map((position) => position.symbol))],
            count: conflictPositions.length,
        };

        const notice = document.getElementById('strategyPositionConflictNotice');
        const text = document.getElementById('strategyPositionConflictText');
        if (notice && text) {
            text.textContent = `当前准备切换到 ${nextSymbol}，但你还有 ${conflictPositions.length} 笔未平仓持仓：${summarizeConflictPositions(conflictPositions)}。建议先一键平仓，再使用新交易对运行策略。`;
            notice.classList.remove('hidden');
        }

        showToast('检测到当前持仓，可在下方一键平仓', 'warning');
    } catch (error) {
        console.error('检测持仓冲突失败:', error);
        hideStrategyPositionConflict();
    }
}

async function closeConflictingPositionsBeforeSwitch() {
    const userId = localStorage.getItem('userId');
    if (!userId || !strategyPositionConflictState?.symbols?.length) {
        hideStrategyPositionConflict();
        return;
    }

    try {
        const response = await fetch(`/api/users/${userId}/positions/close-all`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbols: strategyPositionConflictState.symbols })
        });

        const result = await response.json();
        if (!response.ok) {
            showToast(result.detail || '一键平仓失败', 'error');
            return;
        }

        hideStrategyPositionConflict();
        showToast(`已一键平仓 ${Number(result.closed_count || 0)} 笔持仓`, 'success');

        if (typeof updateData === 'function') {
            await updateData();
        }

        await onStrategySymbolChange();
    } catch (error) {
        console.error('一键平仓失败:', error);
        showToast('一键平仓失败', 'error');
    }
}

// 加载可用交易对列表
async function loadAvailableSymbols() {
    try {
        const response = await fetch('/api/strategies/symbols');
        if (response.ok) {
            availableSymbols = await response.json();
            populateSymbolSelect();
        }
    } catch (error) {
        console.error('加载交易对列表失败:', error);
    }
}

// 填充交易对下拉框
function populateSymbolSelect() {
    const symbolSelect = document.getElementById('strategySymbol');
    if (!symbolSelect) return;

    symbolSelect.innerHTML = '<option value="">选择交易对</option>';
    availableSymbols.forEach(s => {
        const option = document.createElement('option');
        option.value = s.symbol;
        option.textContent = `${s.symbol} (${s.name})`;
        symbolSelect.appendChild(option);
    });

    symbolSelect.value = getDefaultStrategySymbol();
}

// 加载可用模型列表
async function loadAvailableModels() {
    try {
        const response = await fetch('/api/models');
        if (response.ok) {
            const data = await response.json();
            availableModels = data.models || [];
            populateModelSelect();
        }
    } catch (error) {
        console.error('加载模型列表失败:', error);
    }
}

// 填充模型下拉框
function populateModelSelect() {
    const modelSelect = document.getElementById('strategyModelSelect');
    if (!modelSelect) return;

    modelSelect.innerHTML = '<option value="">选择AI模型</option>';
    availableModels.forEach(model => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = `${model.icon} ${model.name} - ${model.description}`;
        modelSelect.appendChild(option);
    });
}

// 加载预设策略列表
async function loadPresetStrategies() {
    try {
        const response = await fetch('/api/strategies/presets');
        if (response.ok) {
            presetStrategies = await response.json();
            populateStrategyPresets();
        }
    } catch (error) {
        console.error('加载预设策略失败:', error);
    }
}

// 填充预设策略下拉框
function populateStrategyPresets() {
    const presetSelect = document.getElementById('strategyPresetSelect');
    if (!presetSelect) return;

    presetSelect.innerHTML = '<option value="">选择预设策略（或创建新策略）</option>';
    presetStrategies.forEach((strategy, index) => {
        const option = document.createElement('option');
        option.value = index; // 使用索引作为值
        option.textContent = `${strategy.name} - ${strategy.description || ''}`;
        presetSelect.appendChild(option);
    });
}

// 当选择预设策略时
async function onPresetStrategyChange() {
    const presetSelect = document.getElementById('strategyPresetSelect');
    const selectedIndex = presetSelect.value;

    if (selectedIndex === '') {
        clearStrategyForm();
        return;
    }

    // 获取选中的预设策略
    const strategy = presetStrategies[parseInt(selectedIndex)];
    if (!strategy) return;

    // 填充表单（这是预设模板，不是用户的策略）
    currentEditingPrompt = null; // 清空当前编辑的策略，因为这是新建
    fillStrategyForm(strategy);

    // 显示保存按钮，隐藏重置按钮（因为这是新建，还没保存）
    document.getElementById('saveStrategyBtn').classList.remove('hidden');
    document.getElementById('resetStrategyBtn').classList.add('hidden');
}

// 填充策略表单
function fillStrategyForm(strategy) {
    document.getElementById('strategyName').value = strategy.name || '';
    document.getElementById('strategyDescription').value = strategy.description || '';
    document.getElementById('strategyPrompt').value = strategy.prompt_text || '';
    document.getElementById('strategySymbol').value = strategy.symbol || getDefaultStrategySymbol();
    document.getElementById('strategyInterval').value = strategy.execution_interval || 1;
    setStrategySymbolAnchor(strategy.symbol || getDefaultStrategySymbol());
    hideStrategyPositionConflict();

    // 显示保存按钮
    document.getElementById('saveStrategyBtn').classList.remove('hidden');

    // 只有已保存的策略才显示重置按钮
    if (strategy.id) {
        document.getElementById('resetStrategyBtn').classList.remove('hidden');
    } else {
        document.getElementById('resetStrategyBtn').classList.add('hidden');
    }
}

// 清空策略表单
function clearStrategyForm() {
    document.getElementById('strategyName').value = '';
    document.getElementById('strategyDescription').value = '';
    document.getElementById('strategySymbol').value = getDefaultStrategySymbol();
    document.getElementById('strategyPrompt').value = '';
    document.getElementById('strategyInterval').value = '1';
    currentEditingPrompt = null;
    setStrategySymbolAnchor(getDefaultStrategySymbol());
    hideStrategyPositionConflict();

    document.getElementById('resetStrategyBtn').classList.add('hidden');
    document.getElementById('saveStrategyBtn').classList.remove('hidden');
}

// 保存策略
async function saveStrategy() {
    const name = document.getElementById('strategyName').value.trim();
    const description = document.getElementById('strategyDescription').value.trim();
    const symbol = document.getElementById('strategySymbol').value;
    const prompt_text = document.getElementById('strategyPrompt').value.trim();
    const execution_interval = parseInt(document.getElementById('strategyInterval').value) || 1;

    if (!name) {
        showToast(t('strategyNameRequired'), 'warning');
        return;
    }

    if (!prompt_text) {
        showToast(t('promptRequired'), 'warning');
        return;
    }

    if (execution_interval < 1) {
        showToast('执行频率最小为1分钟', 'warning');
        return;
    }

    const userId = localStorage.getItem('userId');
    if (!userId) {
        showToast(t('pleaseLoginFirst'), 'warning');
        return;
    }

    const strategyData = {
        name,
        description,
        symbol,
        prompt_text,
        execution_interval
    };

    try {
        let response;
        if (currentEditingPrompt && currentEditingPrompt.id) {
            // 更新现有策略
            response = await fetch(`/api/strategies/${currentEditingPrompt.id}?user_id=${userId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(strategyData)
            });
        } else {
            // 创建新策略
            response = await fetch(`/api/strategies?user_id=${userId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(strategyData)
            });
        }

        if (response.ok) {
            const savedStrategy = await response.json();
            currentEditingPrompt = savedStrategy; // 保存返回的策略对象
            setStrategySymbolAnchor(savedStrategy.symbol);
            hideStrategyPositionConflict();
            showToast(t('strategySaved'), 'success');
            hideCreateStrategyModal();
            if (typeof updatePrompts === 'function') {
                updatePrompts(); // 刷新策略列表
            }
            // 显示重置按钮（现在已经保存了，可以重置）
            document.getElementById('resetStrategyBtn').classList.remove('hidden');
        } else {
            const error = await response.json();
            showToast(error.detail || t('saveFailed'), 'error');
        }
    } catch (error) {
        console.error('保存策略失败:', error);
        showToast(t('networkError'), 'error');
    }
}

// 重置为默认预设
async function resetToDefault() {
    if (!currentEditingPrompt || !currentEditingPrompt.id) {
        showToast(t('resetAfterSave'), 'warning');
        return;
    }

    if (!confirm('确认重置为默认预设提示词？当前的修改将丢失。\n注意：只会重置策略描述和提示词，不会改变交易对、AI模型等设置。')) {
        return;
    }

    try {
        // 查找对应的预设策略
        const presetStrategy = presetStrategies.find(p => p.name === currentEditingPrompt.name);
        if (!presetStrategy) {
            showToast(t('noPresetTemplate'), 'warning');
            return;
        }

        // 只重置描述和提示词，保留用户选择的其他参数
        const userId = localStorage.getItem('userId');
        const response = await fetch(`/api/strategies/${currentEditingPrompt.id}?user_id=${userId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description: presetStrategy.description,
                prompt_text: presetStrategy.prompt_text
            })
        });

        if (response.ok) {
            const updatedStrategy = await response.json();
            currentEditingPrompt = updatedStrategy;
            showToast(t('resetToDefaultSuccess'), 'success');
            fillStrategyForm(updatedStrategy);
            if (typeof updatePrompts === 'function') {
                updatePrompts(); // 刷新策略列表
            }
        } else {
            const error = await response.json();
            showToast(error.detail || t('saveFailed'), 'error');
        }
    } catch (error) {
        console.error('重置策略失败:', error);
        showToast(t('networkError'), 'error');
    }
}

// 显示策略创建模态框
async function showCreateStrategyModal() {
    // 检查是否已配置 API Key（检查本地和服务器）
    const localConfig = typeof getAIConfig === 'function' ? getAIConfig() : null;
    const serverConfig = typeof loadAIConfigFromServer === 'function' ? await loadAIConfigFromServer() : null;

    if (!localConfig && !serverConfig) {
        showToast(t('configureApiKey'), 'warning');
        setTimeout(() => {
            if (typeof showSettingsModal === 'function') showSettingsModal();
        }, 500);
        return;
    }

    const modal = document.getElementById('createStrategyModal');
    if (modal) {
        modal.classList.remove('hidden');
        clearStrategyForm();
        loadAvailableSymbols();
        loadPresetStrategies();
    }
}

// 隐藏策略创建模态框
function hideCreateStrategyModal() {
    const modal = document.getElementById('createStrategyModal');
    if (modal) {
        modal.classList.add('hidden');
        clearStrategyForm();
    }
}

// 编辑策略
async function editStrategy(strategyId) {
    try {
        const userId = localStorage.getItem('userId');
        const response = await fetch(`/api/strategies/${strategyId}?user_id=${userId}`);
        if (response.ok) {
            const strategy = await response.json();
            showCreateStrategyModal();
            currentEditingPrompt = strategy; // 在 showCreateStrategyModal 清空表单后再赋值
            fillStrategyForm(strategy);

            // 尝试匹配预设策略下拉框
            const presetIndex = presetStrategies.findIndex(p => p.name === strategy.name);
            if (presetIndex >= 0) {
                document.getElementById('strategyPresetSelect').value = presetIndex;
            } else {
                document.getElementById('strategyPresetSelect').value = '';
            }

            // 显示保存和重置按钮
            document.getElementById('saveStrategyBtn').classList.remove('hidden');
            document.getElementById('resetStrategyBtn').classList.remove('hidden');
        }
    } catch (error) {
        console.error('加载策略失败:', error);
        showToast(t('loadStrategyFailed'), 'error');
    }
}

// 初始化策略管理
function initStrategyManagement() {
    loadAvailableSymbols();
    loadAvailableModels();
    loadPresetStrategies();
}
