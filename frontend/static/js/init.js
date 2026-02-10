// ==================== 页面初始化 ====================

// 唯一的 DOMContentLoaded 入口点
document.addEventListener('DOMContentLoaded', () => {
    // 初始化主题
    if (typeof initTheme === 'function') initTheme();

    // 尝试从 localStorage 恢复用户登录状态
    const savedUser = localStorage.getItem('currentUser');
    if (savedUser) {
        try {
            currentUser = JSON.parse(savedUser);
            // 验证用户是否仍然存在
            fetch(`/api/users/${currentUser.id}`)
                .then(response => {
                    if (!response.ok) {
                        // 用户不存在，清除本地数据
                        console.log('用户不存在，清除本地缓存');
                        currentUser = null;
                        localStorage.removeItem('currentUser');
                        localStorage.removeItem('userId');
                        updateUserArea();
                    }
                })
                .catch(() => {
                    // 网络错误，保留本地数据
                });
        } catch (e) {
            console.error('恢复用户信息失败:', e);
            localStorage.removeItem('currentUser');
            localStorage.removeItem('userId');
        }
    }

    // 更新用户区域
    updateUserArea();

    // 如果已登录，初始化应用并同步配置
    if (currentUser) {
        initApp();
        // 同步 AI 配置到服务器
        if (typeof syncConfigOnLogin === 'function') {
            syncConfigOnLogin().catch(err => {
                console.error('自动同步配置失败:', err);
                if (err.message && err.message.includes('用户不存在')) {
                    currentUser = null;
                    localStorage.removeItem('currentUser');
                    localStorage.removeItem('userId');
                    updateUserArea();
                }
            });
        }
    } else {
        // 如果未登录，初始化 BTC 图表并加载公开内容
        initPriceChart();
        updatePriceChart();
        if (typeof loadTopCryptoData === 'function') loadTopCryptoData();
        if (typeof loadPublicLeaderboard === 'function') loadPublicLeaderboard();
    }

    // 预加载策略相关数据（交易对、模型、预设策略）
    if (typeof initStrategyManagement === 'function') initStrategyManagement();

    // 模态框回车登录
    const passwordInput = document.getElementById('modalPassword');
    if (passwordInput) {
        passwordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleLogin();
        });
    }
});
