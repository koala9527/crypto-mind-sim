// ==================== 全局变量 ====================

let currentUser = null;
let priceChart = null;
let assetsChartInstance = null;
let updateInterval = null;
let currentTheme = 'light';
let isLoginMode = true; // true: 登录模式, false: 注册模式
let tradeHistoryPage = 1; // 交易历史当前页
let latestBtcPrice = 0; // 最新 BTC 价格（用于保证金计算）
