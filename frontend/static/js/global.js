// ==================== 全局变量 ====================

let currentUser = null;
let priceChart = null;
let updateInterval = null;
let currentTheme = 'light';
let isLoginMode = true; // true: 登录模式, false: 注册模式
let tradeHistoryPage = 1; // 交易历史当前页
let latestBtcPrice = 0; // 最新 BTC/USDT 价格（供保证金计算使用）

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}
