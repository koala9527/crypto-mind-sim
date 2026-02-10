// 多语言配置
const translations = {
    zh: {
        // 头部
        title: "CryptoMindSim",
        subtitle: "加密货币智能交易模拟平台 · 初始资金 10,000 USDT",
        login: "登录",
        logout: "退出",

        // 登录/注册模态框
        loginTitle: "登录",
        registerTitle: "注册",
        username: "用户名",
        password: "密码",
        usernamePlaceholder: "请输入用户名",
        passwordPlaceholder: "请输入密码",
        loginBtn: "登录",
        registerBtn: "注册",
        noAccount: "还没有账号？",
        hasAccount: "已有账号？",
        toRegister: "立即注册",
        toLogin: "立即登录",

        // 顶部统计卡片
        accountBalance: "账户余额",
        positionValue: "持仓总值",
        totalAssets: "总资产",
        roi: "收益率",

        // 标签页
        tabTrade: "手动交易",
        tabAI: "AI 决策",
        tabPositions: "持仓管理",
        tabHistory: "交易历史",

        // 交易面板
        tradeDirection: "交易方向",
        leverage: "杠杆倍数",
        quantity: "交易数量",
        estimatedMargin: "预估保证金",
        openPosition: "开仓",
        long: "做多",
        short: "做空",

        // AI 决策
        marketAnalysis: "市场分析",
        marketTrend: "市场趋势",
        volatility: "波动率",
        suggestion: "建议操作",
        aiStrategy: "AI 策略配置",
        runAnalysis: "运行分析",
        executeAI: "执行AI交易",
        analyzing: "分析中...",
        uptrend: "上涨趋势",
        downtrend: "下跌趋势",
        sideways: "震荡整理",
        suggestLong: "建议做多",
        suggestShort: "建议做空",
        suggestHold: "建议观望",

        // 持仓管理
        noPositions: "暂无持仓",
        symbol: "交易对",
        entryPrice: "开仓价",
        positionQuantity: "数量",
        pnl: "盈亏",
        closePosition: "平仓",
        confirmClose: "确认平仓？",

        // 交易历史
        noTrades: "暂无交易记录",
        tradeType: "类型",
        open: "开仓",
        close: "平仓",

        // 排行榜
        leaderboard: "排行榜",

        // 系统统计
        systemStats: "系统统计",
        totalUsers: "总用户数",
        activePositions: "活跃持仓",
        totalTrades: "总交易数",

        // 风险提示
        riskWarning: "风险提示",
        risk1: "模拟交易仅供学习",
        risk2: "杠杆交易风险较高",
        risk3: "合理控制仓位",
        risk4: "及时止损止盈",

        // 通知消息
        toastSuccess: "成功",
        toastError: "错误",
        toastWarning: "警告",
        toastInfo: "提示",

        // 错误提示
        pleaseLogin: "请先登录后再进行交易",
        pleaseLoginFirst: "请先登录",
        enterCredentials: "请输入用户名和密码",
        passwordTooShort: "密码长度至少4位",
        welcomeBack: "欢迎回来",
        welcomeNew: "注册成功，欢迎加入！",
        networkError: "网络错误，请重试",
        invalidQuantity: "请输入有效的交易数量",
        openSuccess: "开仓成功！",
        openFailed: "开仓失败",
        closeSuccess: "平仓成功！",
        closeFailed: "平仓失败",
        strategyActivated: "AI 策略已激活！",
        activationFailed: "激活失败",
        aiTradingComingSoon: "AI 自动交易功能开发中，敬请期待",
        activated: "已激活",
        activate: "激活",
        noStrategy: "暂无策略配置",
        usernameMismatch: "用户名不匹配，取消注销",
        strategyStarted: "策略已启动！",
        strategyDeactivated: "策略已停用",
        strategyDeleted: "策略已删除",
        startFailed: "启动失败",
        deactivateFailed: "停用失败",
        deleteFailed: "删除失败",
        strategyNameRequired: "请输入策略名称",
        modelRequired: "请选择AI模型",
        promptRequired: "请输入策略提示词",
        strategySaved: "策略保存成功！",
        saveFailed: "保存失败",
        resetAfterSave: "请先保存策略后才能重置",
        noPresetTemplate: "该策略没有对应的预设模板",
        resetToDefaultSuccess: "已重置为默认预设（保留了交易对和AI模型设置）",
        loadStrategyFailed: "加载策略失败",
        configSyncedToServer: "AI 配置已保存并同步到服务器",
        configSyncFailed: "配置已保存到本地，但同步到服务器失败",
        configSavedLocally: "AI 配置已保存到本地（登录后将自动同步）",
        apiKeyRequired: "请输入 API Key",
        saveConfigFailed: "保存配置失败",
        configureApiKey: "请先在设置中配置 AI API Key",

        // 价格图表
        realtimePrice: "实时行情",

        // 重置数据
        dangerZone: "危险操作",
        resetAllData: "一键重置所有数据",
        resetAllDesc: "清除所有交易历史、持仓、策略和AI对话，余额恢复为初始值",
        resetConfirm: "确认重置？\n\n这将清除：\n• 所有交易历史\n• 所有持仓记录\n• 所有策略配置\n• AI决策日志和对话\n\n余额将恢复为 10,000 USDT\n\n此操作不可撤销！",
        resetSuccess: "数据已重置，余额恢复为初始值",
        resetFailed: "重置失败",

        // 分页
        totalRecords: "共",
        records: "条记录"
    },
    en: {
        // Header
        title: "CryptoMindSim",
        subtitle: "Crypto Trading Simulator · Initial Balance 10,000 USDT",
        login: "Login",
        logout: "Logout",

        // Login/Register Modal
        loginTitle: "Login",
        registerTitle: "Register",
        username: "Username",
        password: "Password",
        usernamePlaceholder: "Enter username",
        passwordPlaceholder: "Enter password",
        loginBtn: "Login",
        registerBtn: "Register",
        noAccount: "Don't have an account?",
        hasAccount: "Already have an account?",
        toRegister: "Sign Up",
        toLogin: "Sign In",

        // Top Stats Cards
        accountBalance: "Balance",
        positionValue: "Position Value",
        totalAssets: "Total Assets",
        roi: "ROI",

        // Tabs
        tabTrade: "Manual Trade",
        tabAI: "AI Decision",
        tabPositions: "Positions",
        tabHistory: "History",

        // Trading Panel
        tradeDirection: "Direction",
        leverage: "Leverage",
        quantity: "Quantity",
        estimatedMargin: "Est. Margin",
        openPosition: "Open Position",
        long: "Long",
        short: "Short",

        // AI Decision
        marketAnalysis: "Market Analysis",
        marketTrend: "Trend",
        volatility: "Volatility",
        suggestion: "Suggestion",
        aiStrategy: "AI Strategy",
        runAnalysis: "Analyze",
        executeAI: "Execute AI Trade",
        analyzing: "Analyzing...",
        uptrend: "Uptrend",
        downtrend: "Downtrend",
        sideways: "Sideways",
        suggestLong: "Suggest Long",
        suggestShort: "Suggest Short",
        suggestHold: "Suggest Hold",

        // Position Management
        noPositions: "No positions",
        symbol: "Symbol",
        entryPrice: "Entry Price",
        positionQuantity: "Qty",
        pnl: "P&L",
        closePosition: "Close",
        confirmClose: "Confirm close?",

        // Trade History
        noTrades: "No trades",
        tradeType: "Type",
        open: "Open",
        close: "Close",

        // Leaderboard
        leaderboard: "Leaderboard",

        // System Stats
        systemStats: "System Stats",
        totalUsers: "Total Users",
        activePositions: "Active Positions",
        totalTrades: "Total Trades",

        // Risk Warning
        riskWarning: "Risk Warning",
        risk1: "Simulation only",
        risk2: "High leverage risk",
        risk3: "Control position size",
        risk4: "Set stop loss/profit",

        // Toast Messages
        toastSuccess: "Success",
        toastError: "Error",
        toastWarning: "Warning",
        toastInfo: "Info",

        // Error Messages
        pleaseLogin: "Please login first",
        pleaseLoginFirst: "Please login first",
        enterCredentials: "Please enter username and password",
        passwordTooShort: "Password must be at least 4 characters",
        welcomeBack: "Welcome back",
        welcomeNew: "Welcome! Registration successful",
        networkError: "Network error, please retry",
        invalidQuantity: "Please enter valid quantity",
        openSuccess: "Position opened!",
        openFailed: "Failed to open position",
        closeSuccess: "Position closed!",
        closeFailed: "Failed to close position",
        strategyActivated: "AI strategy activated!",
        activationFailed: "Activation failed",
        aiTradingComingSoon: "AI auto-trading coming soon",
        activated: "Activated",
        activate: "Activate",
        noStrategy: "No strategy configured",
        usernameMismatch: "Username mismatch, account deletion cancelled",
        strategyStarted: "Strategy started!",
        strategyDeactivated: "Strategy deactivated",
        strategyDeleted: "Strategy deleted",
        startFailed: "Failed to start",
        deactivateFailed: "Failed to deactivate",
        deleteFailed: "Failed to delete",
        strategyNameRequired: "Please enter strategy name",
        modelRequired: "Please select AI model",
        promptRequired: "Please enter strategy prompt",
        strategySaved: "Strategy saved successfully!",
        saveFailed: "Failed to save",
        resetAfterSave: "Please save the strategy before resetting",
        noPresetTemplate: "No preset template for this strategy",
        resetToDefaultSuccess: "Reset to default preset (kept symbol and AI model settings)",
        loadStrategyFailed: "Failed to load strategy",
        configSyncedToServer: "AI config saved and synced to server",
        configSyncFailed: "Config saved locally, but failed to sync to server",
        configSavedLocally: "AI config saved locally (will auto-sync after login)",
        apiKeyRequired: "Please enter API Key",
        saveConfigFailed: "Failed to save config",
        configureApiKey: "Please configure AI API Key in settings",

        // Price Chart
        realtimePrice: "Real-time",

        // Reset Data
        dangerZone: "Danger Zone",
        resetAllData: "Reset All Data",
        resetAllDesc: "Clear all trades, positions, strategies and AI conversations. Balance resets to initial value.",
        resetConfirm: "Confirm reset?\n\nThis will clear:\n• All trade history\n• All positions\n• All strategy configs\n• AI decision logs and conversations\n\nBalance will reset to 10,000 USDT\n\nThis action cannot be undone!",
        resetSuccess: "Data reset. Balance restored to initial value.",
        resetFailed: "Reset failed",

        // Pagination
        totalRecords: "Total",
        records: "records"
    }
};

// 当前语言
let currentLang = localStorage.getItem('language') || 'zh';

// 获取翻译文本
function t(key) {
    return translations[currentLang][key] || key;
}

// 切换语言
function toggleLanguage() {
    currentLang = currentLang === 'zh' ? 'en' : 'zh';
    localStorage.setItem('language', currentLang);
    updateLanguage();
}

// 更新页面语言
function updateLanguage() {
    // 更新语言切换按钮
    document.getElementById('langBtn').textContent = currentLang === 'zh' ? 'EN' : '中文';

    // 更新头部
    document.querySelector('[data-i18n="title"]').textContent = t('title');
    document.querySelector('[data-i18n="subtitle"]').textContent = t('subtitle');

    // 更新登录按钮
    const loginButton = document.querySelector('[data-i18n="login"]');
    if (loginButton) {
        loginButton.textContent = t('login');
    }

    // 更新所有带 data-i18n 属性的元素
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (element.tagName === 'INPUT' && element.placeholder) {
            element.placeholder = t(key);
        } else {
            element.textContent = t(key);
        }
    });

    // 更新模态框
    updateModalLanguage();

    // 如果已登录，重新加载数据以更新显示
    if (currentUser) {
        updateData();
    }
}

// 更新模态框语言
function updateModalLanguage() {
    if (isLoginMode) {
        document.getElementById('modalTitle').textContent = t('loginTitle');
        document.getElementById('loginBtn').textContent = t('loginBtn');
        document.getElementById('switchText').textContent = t('noAccount');
        document.getElementById('switchBtn').textContent = t('toRegister');
    } else {
        document.getElementById('modalTitle').textContent = t('registerTitle');
        document.getElementById('loginBtn').textContent = t('registerBtn');
        document.getElementById('switchText').textContent = t('hasAccount');
        document.getElementById('switchBtn').textContent = t('toLogin');
    }
}
