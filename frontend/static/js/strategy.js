// ==================== 策略管理 ====================

let availableModels = [];
let availableSymbols = [];
let presetStrategies = [];
let currentEditingPrompt = null;
let currentStrategyBasePrompt = '';
let strategySymbolAnchor = null;
let strategyPositionConflictState = null;

function getEditingStrategyId() {
    const editingStrategyIdInput = document.getElementById('editingStrategyId');
    const rawValue = editingStrategyIdInput?.value;
    const strategyId = Number(rawValue);
    return Number.isFinite(strategyId) && strategyId > 0 ? strategyId : null;
}

function resolveStrategyBasePrompt(strategy) {
    return String(strategy?.base_prompt_text || strategy?.prompt_text || '').trim();
}

function findMatchingPresetIndex(strategy) {
    if (!strategy || !Array.isArray(presetStrategies) || presetStrategies.length === 0) {
        return -1;
    }

    const basePrompt = resolveStrategyBasePrompt(strategy);
    if (basePrompt) {
        const indexByBasePrompt = presetStrategies.findIndex(p => (p.prompt_text || '').trim() === basePrompt);
        if (indexByBasePrompt >= 0) {
            return indexByBasePrompt;
        }
    }

    return presetStrategies.findIndex(p => p.name === strategy.name);
}

function applyPresetStrategy(presetStrategy) {
    if (!presetStrategy) return;

    const editingStrategyId = getEditingStrategyId();
    const isEditingExistingStrategy = Boolean(editingStrategyId || currentEditingPrompt?.id);

    const draftStrategy = {
        ...presetStrategy,
        id: isEditingExistingStrategy ? (currentEditingPrompt?.id || editingStrategyId) : undefined,
        prompt_text: presetStrategy.prompt_text || '',
        base_prompt_text: presetStrategy.prompt_text || '',
        symbol: document.getElementById('strategySymbol')?.value || getDefaultStrategySymbol(),
        execution_interval: 1,
        auto_optimize_prompt: false,
        prompt_optimization_interval: 1,
        prompt_optimization_include_hold: true,
    };

    if (isEditingExistingStrategy) {
        currentEditingPrompt = {
            ...(currentEditingPrompt || {}),
            id: currentEditingPrompt?.id || editingStrategyId,
            name: draftStrategy.name,
            description: draftStrategy.description,
            prompt_text: draftStrategy.prompt_text,
            base_prompt_text: draftStrategy.base_prompt_text,
            symbol: draftStrategy.symbol,
            execution_interval: draftStrategy.execution_interval,
            auto_optimize_prompt: draftStrategy.auto_optimize_prompt,
            prompt_optimization_interval: draftStrategy.prompt_optimization_interval,
            prompt_optimization_include_hold: draftStrategy.prompt_optimization_include_hold,
        };
    } else {
        currentEditingPrompt = null;
    }

    fillStrategyForm(draftStrategy);

    const editingStrategyIdInput = document.getElementById('editingStrategyId');
    if (editingStrategyIdInput) {
        editingStrategyIdInput.value = isEditingExistingStrategy ? String(currentEditingPrompt?.id || editingStrategyId) : '';
    }
}

function escapePromptHistoryHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function getPromptRevisionSourceLabel(source) {
    const labels = {
        CREATE: '创建初始版',
        MANUAL_UPDATE: '手动修改',
        RESET_DEFAULT: '恢复预设',
        AUTO_OPTIMIZE: '自动修正'
    };
    return labels[source] || source || '未知';
}

function getPromptRevisionSourceClass(source) {
    const map = {
        CREATE: 'badge-info',
        MANUAL_UPDATE: 'badge-info',
        RESET_DEFAULT: 'badge-warning',
        AUTO_OPTIMIZE: 'badge-success'
    };
    return map[source] || 'badge-info';
}

function formatPromptRevisionTime(time) {
    if (!time) return '-';
    return new Date(time).toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function togglePromptOptimizationSettings() {
    const enabled = document.getElementById('strategyAutoOptimizePrompt')?.checked;
    const settings = document.getElementById('strategyPromptOptimizationSettings');
    if (!settings) return;
    settings.classList.toggle('hidden', !enabled);
}

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

// 加载可用交易对列表（返回 Promise 以便 await）
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
        if (getEditingStrategyId()) {
            return;
        }
        clearStrategyForm();
        return;
    }

    // 获取选中的预设策略
    const strategy = presetStrategies[parseInt(selectedIndex)];
    if (!strategy) return;

    // 基于默认模板复制一份可编辑提示词，保留模板作为风格基准
    applyPresetStrategy(strategy);

    // 编辑已有策略时仍然保留更新态；新建时隐藏重置按钮
    document.getElementById('saveStrategyBtn').classList.remove('hidden');
    if (!getEditingStrategyId()) {
        document.getElementById('resetStrategyBtn').classList.add('hidden');
    }
}

// 填充策略表单
function fillStrategyForm(strategy) {
    currentStrategyBasePrompt = resolveStrategyBasePrompt(strategy);

    document.getElementById('strategyName').value = strategy.name || '';
    document.getElementById('strategyDescription').value = strategy.description || '';
    document.getElementById('strategyPrompt').value = strategy.prompt_text || '';
    document.getElementById('strategySymbol').value = strategy.symbol || getDefaultStrategySymbol();
    document.getElementById('strategyInterval').value = strategy.execution_interval || 1;
    document.getElementById('strategyAutoOptimizePrompt').checked = Boolean(strategy.auto_optimize_prompt);
    document.getElementById('strategyPromptOptimizationInterval').value = strategy.prompt_optimization_interval || 1;
    document.getElementById('strategyPromptOptimizationIncludeHold').checked = strategy.prompt_optimization_include_hold !== false;
    togglePromptOptimizationSettings();
    setStrategySymbolAnchor(strategy.symbol || getDefaultStrategySymbol());
    hideStrategyPositionConflict();

    const editingStrategyIdInput = document.getElementById('editingStrategyId');
    if (editingStrategyIdInput) {
        editingStrategyIdInput.value = strategy.id || '';
    }

    const modalTitle = document.getElementById('strategyModalTitle');
    if (modalTitle) {
        modalTitle.textContent = strategy.id ? '编辑策略' : '创建策略';
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
    document.getElementById('strategySymbol').value = getDefaultStrategySymbol();
    document.getElementById('strategyPrompt').value = '';
    document.getElementById('strategyInterval').value = '1';
    document.getElementById('strategyAutoOptimizePrompt').checked = false;
    document.getElementById('strategyPromptOptimizationInterval').value = '1';
    document.getElementById('strategyPromptOptimizationIncludeHold').checked = true;
    togglePromptOptimizationSettings();
    currentEditingPrompt = null;
    currentStrategyBasePrompt = '';
    setStrategySymbolAnchor(getDefaultStrategySymbol());
    hideStrategyPositionConflict();

    const editingStrategyIdInput = document.getElementById('editingStrategyId');
    if (editingStrategyIdInput) {
        editingStrategyIdInput.value = '';
    }

    const presetSelect = document.getElementById('strategyPresetSelect');
    if (presetSelect) {
        presetSelect.value = '';
    }

    const modalTitle = document.getElementById('strategyModalTitle');
    if (modalTitle) {
        modalTitle.textContent = '创建策略';
    }

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
    const auto_optimize_prompt = document.getElementById('strategyAutoOptimizePrompt').checked;
    const prompt_optimization_interval = parseInt(document.getElementById('strategyPromptOptimizationInterval').value) || 1;
    const prompt_optimization_include_hold = document.getElementById('strategyPromptOptimizationIncludeHold').checked;

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

    if (auto_optimize_prompt && prompt_optimization_interval < 1) {
        showToast('提示词修正间隔最小为1次决策', 'warning');
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
        base_prompt_text: currentStrategyBasePrompt || currentEditingPrompt?.base_prompt_text || prompt_text,
        execution_interval,
        auto_optimize_prompt,
        prompt_optimization_interval,
        prompt_optimization_include_hold
    };

    try {
        let response;
        const editingStrategyId = getEditingStrategyId() || currentEditingPrompt?.id || null;
        if (editingStrategyId) {
            // 更新现有策略
            response = await fetch(`/api/strategies/${editingStrategyId}?user_id=${userId}`, {
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
        const presetIndex = findMatchingPresetIndex(currentEditingPrompt);
        const presetStrategy = presetIndex >= 0 ? presetStrategies[presetIndex] : null;
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
                prompt_text: presetStrategy.prompt_text,
                base_prompt_text: presetStrategy.prompt_text,
                revision_source: 'RESET_DEFAULT'
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

function hidePromptRevisionHistory() {
    const modal = document.getElementById('promptRevisionHistoryModal');
    if (modal) modal.classList.add('hidden');
}

function renderPromptRevisionHistoryItems(revisions) {
    if (!Array.isArray(revisions) || revisions.length === 0) {
        return `
            <div class="text-center py-10" style="color: var(--text-secondary)">
                暂无提示词修正历史
            </div>
        `;
    }

    return revisions.map((item) => {
        const badgeClass = getPromptRevisionSourceClass(item.source);
        const previousBlock = item.previous_prompt_text
            ? `
                <details class="mt-3">
                    <summary class="cursor-pointer text-sm" style="color: var(--text-secondary)">查看修正前提示词</summary>
                    <pre class="mt-2 p-3 rounded text-xs whitespace-pre-wrap" style="background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-secondary);">${escapePromptHistoryHtml(item.previous_prompt_text)}</pre>
                </details>
            `
            : '';

        return `
            <div class="card rounded-lg p-4">
                <div class="flex flex-wrap items-center gap-2 mb-3">
                    <span class="badge ${badgeClass} text-xs">${escapePromptHistoryHtml(getPromptRevisionSourceLabel(item.source))}</span>
                    <span class="text-xs" style="color: var(--text-secondary)">版本 #${item.revision_no}</span>
                    <span class="text-xs" style="color: var(--text-secondary)">${escapePromptHistoryHtml(formatPromptRevisionTime(item.created_at))}</span>
                </div>
                ${item.summary ? `<div class="text-sm mb-3" style="color: var(--text-secondary)">${escapePromptHistoryHtml(item.summary)}</div>` : ''}
                <div class="grid gap-3 lg:grid-cols-2">
                    <div>
                        <div class="text-xs mb-2 font-semibold" style="color: var(--text-secondary)">当前版本提示词</div>
                        <pre class="p-3 rounded text-xs whitespace-pre-wrap" style="background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary);">${escapePromptHistoryHtml(item.prompt_text)}</pre>
                    </div>
                    <div>
                        <div class="text-xs mb-2 font-semibold" style="color: var(--text-secondary)">风格基准提示词</div>
                        <pre class="p-3 rounded text-xs whitespace-pre-wrap" style="background: var(--bg-primary); border: 1px solid var(--border-color); color: var(--text-primary);">${escapePromptHistoryHtml(item.base_prompt_text || item.prompt_text)}</pre>
                    </div>
                </div>
                ${previousBlock}
            </div>
        `;
    }).join('');
}

async function showPromptRevisionHistory(strategyId, strategyName = '') {
    const modal = document.getElementById('promptRevisionHistoryModal');
    const content = document.getElementById('promptRevisionHistoryContent');
    const subtitle = document.getElementById('promptRevisionHistorySubtitle');
    const userId = localStorage.getItem('userId');

    if (!modal || !content || !userId) return;

    subtitle.textContent = strategyName
        ? `策略「${strategyName}」整个生命周期内的提示词版本记录`
        : '跟随当前策略整个生命周期的版本记录';
    content.innerHTML = '<div class="text-center py-8" style="color: var(--text-secondary)">加载中...</div>';
    modal.classList.remove('hidden');

    try {
        const response = await fetch(`/api/strategies/${strategyId}/prompt-revisions?user_id=${userId}&limit=200`);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || '加载提示词修正历史失败');
        }

        const revisions = await response.json();
        content.innerHTML = renderPromptRevisionHistoryItems(revisions);
    } catch (error) {
        console.error('加载提示词修正历史失败:', error);
        content.innerHTML = `<div class="text-center py-8" style="color: var(--danger)">${escapePromptHistoryHtml(error.message || '加载失败')}</div>`;
    }
}

// 显示策略创建模态框
async function showCreateStrategyModal(options = {}) {
    const { strategy = null } = options;

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
        // 等待下拉框数据加载完成，确保后续 fillStrategyForm 能正确回显
        await Promise.all([loadAvailableSymbols(), loadPresetStrategies()]);

        if (strategy && strategy.id) {
            currentEditingPrompt = strategy;
            fillStrategyForm(strategy);

            const presetIndex = findMatchingPresetIndex(strategy);
            document.getElementById('strategyPresetSelect').value = presetIndex >= 0 ? String(presetIndex) : '';
        } else if (presetStrategies.length > 0) {
            document.getElementById('strategyPresetSelect').value = '0';
            applyPresetStrategy(presetStrategies[0]);
        }
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
            await showCreateStrategyModal({ strategy });

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
