// ==================== 设置管理 ====================

// AI 配置
const AI_CONFIG_KEY = 'ai_config';

// 获取 AI 配置
function getAIConfig() {
    const config = localStorage.getItem(AI_CONFIG_KEY);
    if (config) {
        try {
            return JSON.parse(config);
        } catch (e) {
            console.error('解析 AI 配置失败:', e);
            return null;
        }
    }
    return null;
}

// 保存 AI 配置到 localStorage
function saveAIConfigLocal(apiKey, baseUrl) {
    const config = {
        apiKey: apiKey,
        baseUrl: baseUrl || 'https://api.hodlai.fun/v1'
    };
    localStorage.setItem(AI_CONFIG_KEY, JSON.stringify(config));
}

// 同步 AI 配置到服务器
async function syncAIConfigToServer(apiKey, baseUrl) {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        throw new Error('请先登录');
    }

    try {
        const response = await fetch(`/api/users/${userId}/ai-config`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_key: apiKey,
                base_url: baseUrl || 'https://api.hodlai.fun/v1'
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '同步配置失败');
        }

        return await response.json();
    } catch (error) {
        console.error('同步配置到服务器失败:', error);
        throw error;
    }
}

// 保存 AI 配置（同时保存到本地和服务器）
async function saveAIConfig(apiKey, baseUrl) {
    // 保存到本地
    saveAIConfigLocal(apiKey, baseUrl);

    // 如果已登录，同步到服务器
    const userId = localStorage.getItem('userId');
    if (userId) {
        try {
            await syncAIConfigToServer(apiKey, baseUrl);
            showToast(t('configSyncedToServer'), 'success');
        } catch (error) {
            showToast(t('configSyncFailed') + ': ' + error.message, 'warning');
        }
    } else {
        showToast(t('configSavedLocally'), 'success');
    }
}

// 显示设置模态框
function showSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (!modal) return;

    // 加载当前配置
    const config = getAIConfig();
    if (config) {
        document.getElementById('apiKeyInput').value = config.apiKey || '';
        document.getElementById('baseUrlInput').value = config.baseUrl || 'https://api.hodlai.fun/v1';
    }

    modal.classList.remove('hidden');
}

// 隐藏设置模态框
function hideSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

// 保存设置
async function saveSettings() {
    const apiKey = document.getElementById('apiKeyInput').value.trim();
    const baseUrl = document.getElementById('baseUrlInput').value.trim() || 'https://api.hodlai.fun/v1';

    if (!apiKey) {
        showToast(t('apiKeyRequired'), 'warning');
        return;
    }

    try {
        await saveAIConfig(apiKey, baseUrl);
        hideSettingsModal();
    } catch (error) {
        console.error('保存配置失败:', error);
        showToast(t('saveConfigFailed') + ': ' + error.message, 'error');
    }
}

// 检查是否已配置 AI
function checkAIConfig() {
    const config = getAIConfig();
    return config && config.apiKey;
}

// 显示配置提示
function showConfigPrompt() {
    if (!checkAIConfig()) {
        showToast(t('configureApiKey'), 'warning');
        setTimeout(() => {
            showSettingsModal();
        }, 1000);
        return false;
    }
    return true;
}

// 登录后同步配置到服务器
async function syncConfigOnLogin() {
    const config = getAIConfig();
    if (config && config.apiKey) {
        try {
            await syncAIConfigToServer(config.apiKey, config.baseUrl);
            console.log('配置已自动同步到服务器');
        } catch (error) {
            console.error('自动同步配置失败:', error);
        }
    }
}

// 一键重置所有数据
async function resetAllData() {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        showToast(t('pleaseLoginFirst'), 'warning');
        return;
    }

    if (!confirm(t('resetConfirm'))) {
        return;
    }

    try {
        const response = await fetch(`/api/users/${userId}/reset`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || t('resetFailed'));
        }

        showToast(t('resetSuccess'), 'success');
        hideSettingsModal();

        // 刷新页面数据
        await updateData();
    } catch (error) {
        console.error('重置数据失败:', error);
        showToast(t('resetFailed') + ': ' + error.message, 'error');
    }
}
