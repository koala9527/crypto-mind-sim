// ==================== 策略管理 ====================

let availableModels = [];
let availableSymbols = [];
let presetStrategies = [];
let currentEditingPrompt = null;

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

    // 默认选中 BTC/USDT
    symbolSelect.value = 'BTC/USDT';
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

    // 填充表单
    // 如果当前正在编辑已有策略，保留其 id 以便保存时走 PUT 更新
    // 只有在没有编辑已有策略时才清空（新建模式）
    if (!currentEditingPrompt || !currentEditingPrompt.id) {
        currentEditingPrompt = null;
    }
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

    // 如果是用户已保存的策略（有 ai_model 字段），则填充所有字段
    if (strategy.ai_model) {
        document.getElementById('strategyModelSelect').value = strategy.ai_model;
        document.getElementById('strategySymbol').value = strategy.symbol || 'BTC/USDT';
    } else {
        // 如果是预设模板（没有 ai_model 字段），则使用默认值
        document.getElementById('strategyModelSelect').value = '';
        document.getElementById('strategySymbol').value = 'BTC/USDT';
    }

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
    document.getElementById('strategyModelSelect').value = '';
    document.getElementById('strategySymbol').value = 'BTC/USDT';
    document.getElementById('strategyPrompt').value = '';
    currentEditingPrompt = null;

    // 隐藏重置按钮，显示保存按钮
    document.getElementById('resetStrategyBtn').classList.add('hidden');
    document.getElementById('saveStrategyBtn').classList.remove('hidden');
}

// 保存策略
async function saveStrategy() {
    const name = document.getElementById('strategyName').value.trim();
    const description = document.getElementById('strategyDescription').value.trim();
    const ai_model = document.getElementById('strategyModelSelect').value;
    const symbol = document.getElementById('strategySymbol').value;
    const prompt_text = document.getElementById('strategyPrompt').value.trim();

    if (!name) {
        showToast(t('strategyNameRequired'), 'warning');
        return;
    }

    if (!ai_model) {
        showToast(t('modelRequired'), 'warning');
        return;
    }

    if (!prompt_text) {
        showToast(t('promptRequired'), 'warning');
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
        ai_model,
        symbol,
        prompt_text,
        execution_interval: 60
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
function showCreateStrategyModal() {
    // 检查是否已配置 API Key
    if (typeof checkAIConfig === 'function' && !checkAIConfig()) {
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
        loadAvailableModels();
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

            // 直接打开模态框，不调用 showCreateStrategyModal 以避免 clearStrategyForm 清除 currentEditingPrompt
            const modal = document.getElementById('createStrategyModal');
            if (modal) {
                modal.classList.remove('hidden');
            }
            await loadAvailableSymbols();
            await loadAvailableModels();
            await loadPresetStrategies();

            // 设置编辑状态和填充表单
            currentEditingPrompt = strategy;
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
