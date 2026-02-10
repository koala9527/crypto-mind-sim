// ==================== 价格图表 ====================

// 初始化 BTC 价格图表（未登录时使用）
function initPriceChart() {
    if (priceChart) return;

    const ctx = document.getElementById('priceChart');
    if (!ctx) return;

    priceChart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'BTC/USDT',
                data: [],
                borderColor: getComputedStyle(document.documentElement).getPropertyValue('--text-primary'),
                backgroundColor: 'rgba(0, 0, 0, 0.05)',
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--chart-text') },
                    grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid') }
                },
                x: {
                    ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--chart-text') },
                    grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid') }
                }
            }
        }
    });
}

// 销毁 BTC 价格图表
function destroyPriceChart() {
    if (priceChart) {
        priceChart.destroy();
        priceChart = null;
    }
}

// 更新 BTC 价格图表（未登录时使用）
async function updatePriceChart() {
    if (currentUser) return;

    try {
        const [currentResponse, historyResponse] = await Promise.all([
            fetch('/api/price/current'),
            fetch('/api/price/history?hours=1')
        ]);

        const current = await currentResponse.json();
        const history = await historyResponse.json();

        latestBtcPrice = current.price;
        document.getElementById('currentPrice').textContent = '$' + current.price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});

        if (history.data && history.data.length > 0) {
            const labels = history.data.map(d => new Date(d.timestamp).toLocaleTimeString());
            const prices = history.data.map(d => d.price);

            priceChart.data.labels = labels;
            priceChart.data.datasets[0].data = prices;
            priceChart.update('none');
        }
    } catch (error) {
        console.error('更新价格图表失败:', error);
    }
}

// 初始化总资产图表（登录后使用）
function initAssetsChart() {
    if (assetsChartInstance) return;

    const ctx = document.getElementById('assetsChart');
    if (!ctx) return;

    assetsChartInstance = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '总资产 (USDT)',
                data: [],
                borderColor: getComputedStyle(document.documentElement).getPropertyValue('--text-primary'),
                backgroundColor: 'rgba(0, 0, 0, 0.05)',
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--chart-text') },
                    grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid') }
                },
                x: {
                    ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--chart-text') },
                    grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid') }
                }
            }
        }
    });
}

// 销毁总资产图表
function destroyAssetsChart() {
    if (assetsChartInstance) {
        assetsChartInstance.destroy();
        assetsChartInstance = null;
    }
}

// 更新总资产图表（登录后使用）
async function updateAssetsChart() {
    if (!currentUser) return;

    try {
        const response = await fetch(`/api/users/${currentUser.id}/assets-history`);
        if (!response.ok) return;

        const result = await response.json();
        const dataPoints = result.data || [];

        if (dataPoints.length === 0) return;

        const labels = dataPoints.map(d => {
            const date = new Date(d.timestamp);
            const now = new Date();
            if (date.toDateString() !== now.toDateString()) {
                return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }) + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
            }
            return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        });
        const values = dataPoints.map(d => d.total_assets);

        // 更新当前总资产显示
        const currentAssets = values[values.length - 1];
        document.getElementById('assetsCurrentValue').textContent = currentAssets.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' USDT';

        // 更新图表
        if (assetsChartInstance) {
            assetsChartInstance.data.labels = labels;
            assetsChartInstance.data.datasets[0].data = values;
            assetsChartInstance.update('none');
        }
    } catch (error) {
        console.error('更新总资产图表失败:', error);
    }
}
