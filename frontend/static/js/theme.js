// ==================== 主题切换 ====================

function toggleTheme() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    document.getElementById('themeIcon').textContent = currentTheme === 'light' ? '🌙' : '☀️';
    localStorage.setItem('theme', currentTheme);

    // 更新图表颜色
    updateChartTheme();
}

// 初始化主题
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        toggleTheme();
    }
}

// 更新图表主题
function updateChartTheme() {
    const accentColor = getComputedStyle(document.documentElement).getPropertyValue('--text-primary');
    const chartText = getComputedStyle(document.documentElement).getPropertyValue('--chart-text');
    const chartGrid = getComputedStyle(document.documentElement).getPropertyValue('--chart-grid');

    function applyTheme(chart) {
        chart.data.datasets[0].borderColor = accentColor;
        chart.options.scales.y.ticks.color = chartText;
        chart.options.scales.y.grid.color = chartGrid;
        chart.options.scales.x.ticks.color = chartText;
        chart.options.scales.x.grid.color = chartGrid;
        chart.update();
    }

    if (priceChart) applyTheme(priceChart);
    if (assetsChartInstance) applyTheme(assetsChartInstance);
}
