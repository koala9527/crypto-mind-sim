// ==================== 用户认证 ====================

// 处理登录/注册
async function handleLogin() {
    const username = document.getElementById('modalUsername').value.trim();
    const password = document.getElementById('modalPassword').value.trim();

    if (!username || !password) {
        showToast(t('enterCredentials'), 'warning');
        return;
    }

    if (!isLoginMode && password.length < 4) {
        showToast(t('passwordTooShort'), 'warning');
        return;
    }

    try {
        const endpoint = isLoginMode ? '/api/login' : '/api/register';
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (response.ok) {
            currentUser = await response.json();
            // 保存用户信息到 localStorage
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            localStorage.setItem('userId', currentUser.id);
            hideLoginModal();
            updateUserArea();
            initApp();

            // 登录后同步 AI 配置到服务器
            if (typeof syncConfigOnLogin === 'function') {
                await syncConfigOnLogin();
            }

            showToast(
                isLoginMode ? `欢迎回来，${currentUser.username}！` : '注册成功，欢迎加入！',
                'success'
            );
        } else {
            const error = await response.json();
            showToast(error.detail || t('openFailed'), 'error');
        }
    } catch (error) {
        console.error('操作失败:', error);
        showToast(t('networkError'), 'error');
    }
}

// 更新用户区域显示
function updateUserArea() {
    const userArea = document.getElementById('userArea');
    const publicContent = document.getElementById('publicContent');
    const mainContent = document.getElementById('mainContent');

    if (currentUser) {
        userArea.innerHTML = `
            <div class="flex items-center gap-3">
                <span class="text-sm font-semibold">${currentUser.username}</span>
                <button onclick="logout()" class="text-sm px-3 py-1 rounded" style="background-color: var(--bg-secondary); color: var(--text-secondary);">
                    退出
                </button>
                <button onclick="deleteAccount()" class="text-sm px-3 py-1 rounded bg-red-500 hover:bg-red-600 text-white transition">
                    注销账号
                </button>
            </div>
        `;
        // 隐藏公共内容，显示个人主内容
        publicContent.classList.add('hidden');
        mainContent.classList.remove('hidden');
    } else {
        userArea.innerHTML = `
            <button onclick="showLoginModal()" class="btn-primary px-4 py-2 rounded font-semibold">
                登录
            </button>
        `;
        // 显示公共内容，隐藏个人主内容
        publicContent.classList.remove('hidden');
        mainContent.classList.add('hidden');
    }
}

// 退出登录
function logout() {
    if (confirm('确认退出登录？')) {
        currentUser = null;
        // 清除 localStorage
        localStorage.removeItem('currentUser');
        localStorage.removeItem('userId');
        if (updateInterval) {
            clearInterval(updateInterval);
        }
        // 销毁总资产图表，重置为 BTC 模式
        destroyAssetsChart();
        // 隐藏主内容区域
        document.getElementById('mainContent').classList.add('hidden');
        updateUserArea();
        // 重新初始化 BTC 图表
        initPriceChart();
        updatePriceChart();
    }
}

// 注销账号
async function deleteAccount() {
    if (!currentUser) {
        showToast(t('pleaseLoginFirst'), 'warning');
        return;
    }

    // 二次确认
    const confirmed = confirm(
        `⚠️ 警告：此操作将永久删除你的账号及所有数据！\n\n` +
        `即将删除的数据包括：\n` +
        `• 用户信息\n` +
        `• 所有持仓记录\n` +
        `• 所有交易历史\n` +
        `• AI决策日志\n` +
        `• AI对话记录\n\n` +
        `此操作不可恢复，确定要继续吗？`
    );

    if (!confirmed) {
        return;
    }

    // 三次确认（输入用户名）
    const usernameConfirm = prompt(
        `请输入你的用户名 "${currentUser.username}" 以确认删除：`
    );

    if (usernameConfirm !== currentUser.username) {
        showToast(t('usernameMismatch'), 'info');
        return;
    }

    try {
        const response = await fetch(`/api/users/${currentUser.id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            const result = await response.json();
            showToast(`账号已成功注销：${result.username}`, 'success');

            // 清除当前用户
            currentUser = null;
            // 清除 localStorage
            localStorage.removeItem('currentUser');
            localStorage.removeItem('userId');
            if (updateInterval) {
                clearInterval(updateInterval);
            }

            // 更新UI
            document.getElementById('mainContent').classList.add('hidden');
            updateUserArea();

            // 3秒后刷新页面
            setTimeout(() => {
                location.reload();
            }, 3000);
        } else {
            const error = await response.json();
            showToast(error.detail || t('deleteFailed'), 'error');
        }
    } catch (error) {
        console.error('注销账号失败:', error);
        showToast(t('networkError'), 'error');
    }
}

// 初始化应用（登录后）
function initApp() {
    // 显示主内容区域
    document.getElementById('mainContent').classList.remove('hidden');
    // 销毁 BTC 图表，初始化总资产图表
    destroyPriceChart();
    initAssetsChart();
    updateData();
    updateInterval = setInterval(updateData, 3000);
}
