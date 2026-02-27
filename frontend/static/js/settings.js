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
function saveAIConfigLocal(apiKey, baseUrl, aiModel) {
    const config = {
        apiKey: apiKey,
        baseUrl: baseUrl || '',
        aiModel: aiModel || 'claude-4.5-opus'
    };
    localStorage.setItem(AI_CONFIG_KEY, JSON.stringify(config));
}

// 同步 AI 配置到服务器
async function syncAIConfigToServer(apiKey, baseUrl, aiModel) {
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
                base_url: baseUrl || '',
                ai_model: aiModel || 'claude-4.5-opus'
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
async function saveAIConfig(apiKey, baseUrl, aiModel) {
    saveAIConfigLocal(apiKey, baseUrl, aiModel);

    const userId = localStorage.getItem('userId');
    if (userId) {
        try {
            await syncAIConfigToServer(apiKey, baseUrl, aiModel);
            showToast(t('configSyncedToServer'), 'success');
        } catch (error) {
            showToast(t('configSyncFailed') + ': ' + error.message, 'warning');
        }
    } else {
        showToast(t('configSavedLocally'), 'success');
    }
}

// 从服务器获取 AI 配置
async function loadAIConfigFromServer() {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        return null;
    }

    try {
        const response = await fetch(`/api/users/${userId}/ai-config`);
        if (!response.ok) {
            throw new Error('获取配置失败');
        }

        const data = await response.json();
        if (data.configured) {
            // 同步到本地存储
            saveAIConfigLocal(data.api_key, data.base_url, data.ai_model);
            return {
                apiKey: data.api_key,
                baseUrl: data.base_url || '',
                aiModel: data.ai_model || 'claude-4.5-opus'
            };
        }
        return null;
    } catch (error) {
        console.error('从服务器加载配置失败:', error);
        return null;
    }
}

// 显示设置模态框
async function showSettingsModal() {
    // 检查是否已登录
    const userId = localStorage.getItem('userId');
    if (!userId) {
        showToast('请先登录', 'warning');
        return;
    }

    const modal = document.getElementById('settingsModal');
    if (!modal) return;

    // 先尝试从服务器加载配置
    const serverConfig = await loadAIConfigFromServer();
    const config = serverConfig || getAIConfig();

    if (config) {
        document.getElementById('apiKeyInput').value = config.apiKey || '';
        document.getElementById('baseUrlInput').value = config.baseUrl || '';
        document.getElementById('aiModelInput').value = config.aiModel || 'claude-4.5-opus';
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
    const baseUrl = document.getElementById('baseUrlInput').value.trim() || '';
    const aiModel = document.getElementById('aiModelInput').value.trim() || 'claude-4.5-opus';

    if (!apiKey) {
        showToast(t('apiKeyRequired'), 'warning');
        return;
    }

    try {
        await saveAIConfig(apiKey, baseUrl, aiModel);
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

// 登录后从服务器加载配置
async function syncConfigOnLogin() {
    const userId = localStorage.getItem('userId');
    if (!userId) {
        return;
    }

    try {
        // 从服务器加载配置
        const serverConfig = await loadAIConfigFromServer();
        if (serverConfig) {
            console.log('已从服务器加载 AI 配置');
        } else {
            // 如果服务器没有配置，尝试同步本地配置到服务器
            const localConfig = getAIConfig();
            if (localConfig && localConfig.apiKey) {
                await syncAIConfigToServer(localConfig.apiKey, localConfig.baseUrl, localConfig.aiModel);
                console.log('本地配置已同步到服务器');
            }
        }
    } catch (error) {
        console.error('配置同步失败:', error);
    }
}

// 测试 AI 配置连通性
async function testAIConfig() {
    const apiKey = document.getElementById('apiKeyInput').value.trim();
    const baseUrl = document.getElementById('baseUrlInput').value.trim();
    const aiModel = document.getElementById('aiModelInput').value.trim() || 'claude-4.5-opus';

    if (!apiKey) {
        showToast('请先填写 API Key', 'warning');
        return;
    }
    if (!baseUrl) {
        showToast('请先填写 Base URL', 'warning');
        return;
    }

    const btn = document.getElementById('testAIBtn');
    btn.textContent = '测试中...';
    btn.disabled = true;

    try {
        const response = await fetch(`${baseUrl}/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`
            },
            body: JSON.stringify({
                model: aiModel,
                messages: [{ role: 'user', content: 'hi' }],
                max_tokens: 10
            })
        });

        if (response.ok) {
            const data = await response.json();
            const reply = data?.choices?.[0]?.message?.content;
            if (reply) {
                showToast('连接正常，AI 响应成功', 'success');
            } else {
                showToast('连接成功但响应格式异常', 'warning');
            }
        } else {
            const err = await response.json().catch(() => ({}));
            showToast(`连接失败 (${response.status})：${err?.error?.message || response.statusText}`, 'error');
        }
    } catch (e) {
        showToast(`连接异常：${e.message}`, 'error');
    } finally {
        btn.textContent = '测试连接';
        btn.disabled = false;
    }
}


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
