// ==================== 总资产曲线图 ====================

// 初始化资产图表
function initPriceChart() {
    if (priceChart) return;

    const ctx = document.getElementById('priceChart').getContext('2d');
    priceChart = new Chart(ctx, {
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
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => '$' + ctx.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    }
                }
            },
            scales: {
                y: {
                    ticks: {
                        color: getComputedStyle(document.documentElement).getPropertyValue('--chart-text'),
                        callback: v => '$' + v.toLocaleString('en-US', { maximumFractionDigits: 0 })
                    },
                    grid: {
                        color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid')
                    }
                },
                x: {
                    ticks: {
                        color: getComputedStyle(document.documentElement).getPropertyValue('--chart-text'),
                        maxTicksLimit: 8
                    },
                    grid: {
                        color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid')
                    }
                }
            }
        }
    });
}

// 更新资产曲线图
async function updatePriceChart() {
    // 未登录时不显示资产曲线
    if (!currentUser) return;

    try {
        const userId = currentUser.id;
        const [historyResponse, priceResponse] = await Promise.all([
            fetch(`/api/users/${userId}/asset-history?hours=24`),
            fetch('/api/price/current')
        ]);
        const result = await historyResponse.json();
        const priceData = await priceResponse.json();

        // 更新全局 BTC 价格供保证金计算使用
        if (priceData && priceData.price) {
            latestBtcPrice = priceData.price;
        }

        // 右上角显示当前总资产
        const priceEl = document.getElementById('currentPrice');
        if (priceEl) {
            const latestAsset = result.data && result.data.length > 0
                ? result.data[result.data.length - 1].total_assets
                : (currentUser.total_assets ?? currentUser.balance ?? 0);
            priceEl.textContent = '总资产 $' + latestAsset.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }

        if (result.data && result.data.length > 0) {
            const labels = result.data.map(d => {
                const t = new Date(d.timestamp);
                return t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            });
            const values = result.data.map(d => d.total_assets);

            if (!priceChart) initPriceChart();
            priceChart.data.labels = labels;
            priceChart.data.datasets[0].data = values;
            priceChart.update('none');
        } else {
            // 暂无历史数据时，用当前总资产显示一个点
            const totalAssets = currentUser.total_assets ?? currentUser.balance ?? 0;
            if (!priceChart) initPriceChart();
            priceChart.data.labels = [new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })];
            priceChart.data.datasets[0].data = [totalAssets];
            priceChart.update('none');
        }
    } catch (error) {
        console.error('更新资产曲线失败:', error);
    }
}

// 兼容函数（auth.js 调用）
function destroyPriceChart() {}
function initAssetsChart() { initPriceChart(); }
