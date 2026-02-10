// ==================== 公开内容加载 ====================

// 加载前十加密货币行情数据（从数据库读取真实数据）
async function loadTopCryptoData() {
    try {
        const response = await fetch('/api/top-crypto');
        if (!response.ok) {
            throw new Error('Failed to fetch crypto data');
        }

        const result = await response.json();
        const topCryptos = result.data || [];

        const container = document.getElementById('topCryptoList');

        if (topCryptos.length === 0) {
            container.innerHTML = `
                <tr><td colspan="5" class="text-center p-4" style="color: var(--text-secondary)">暂无数据，等待价格更新...</td></tr>
            `;
            return;
        }

        container.innerHTML = topCryptos.map(crypto => `
            <tr style="border-bottom: 1px solid var(--border-color)">
                <td class="p-2">#${crypto.rank}</td>
                <td class="p-2">
                    <div class="font-semibold">${crypto.symbol.replace('/USDT', '')}</div>
                    <div class="text-xs" style="color: var(--text-secondary)">${crypto.name}</div>
                </td>
                <td class="p-2 text-right font-mono">$${crypto.price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                <td class="p-2 text-right">
                    <span class="${crypto.change_24h >= 0 ? 'text-green-500' : 'text-red-500'}">
                        ${crypto.change_24h >= 0 ? '+' : ''}${crypto.change_24h.toFixed(2)}%
                    </span>
                </td>
                <td class="p-2 text-right text-xs" style="color: var(--text-secondary)">
                    ${formatMarketCap(crypto.price)}
                </td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('加载加密货币行情失败:', error);
        document.getElementById('topCryptoList').innerHTML = `
            <tr><td colspan="5" class="text-center p-4" style="color: var(--text-secondary)">加载失败，请刷新重试</td></tr>
        `;
    }
}

// 格式化市值（估算值，仅供展示）
function formatMarketCap(price) {
    // 简单估算市值 = 价格 * 流通量（这里使用近似值）
    // 实际应该从API获取真实市值，这里仅做展示
    const estimatedSupply = {
        'BTC': 19.5e6,
        'ETH': 120e6,
        'BNB': 150e6,
        'SOL': 400e6,
        'XRP': 52e9,
        'ADA': 35e9,
        'AVAX': 350e6,
        'DOT': 1.2e9,
        'MATIC': 9e9,
        'LINK': 500e6
    };

    // 从价格推测币种（简化处理）
    let supply = 1e9; // 默认值
    if (price > 10000) supply = estimatedSupply['BTC'] || 19.5e6;
    else if (price > 1000) supply = estimatedSupply['ETH'] || 120e6;
    else if (price > 100) supply = estimatedSupply['BNB'] || 150e6;
    else if (price > 10) supply = estimatedSupply['SOL'] || 400e6;

    const marketCap = price * supply;

    if (marketCap >= 1e12) {
        return `$${(marketCap / 1e12).toFixed(2)}T`;
    } else if (marketCap >= 1e9) {
        return `$${(marketCap / 1e9).toFixed(1)}B`;
    } else if (marketCap >= 1e6) {
        return `$${(marketCap / 1e6).toFixed(1)}M`;
    } else {
        return `$${marketCap.toFixed(0)}`;
    }
}


// 加载公开排行榜（未登录时使用）
async function loadPublicLeaderboard() {
    try {
        const response = await fetch('/api/leaderboard');
        const leaderboard = await response.json();

        const container = document.getElementById('publicLeaderboard');
        if (leaderboard.length === 0) {
            container.innerHTML = '<div class="text-center p-4" style="color: var(--text-secondary)">暂无数据</div>';
            return;
        }

        container.innerHTML = `
            <div class="space-y-2">
                ${leaderboard.slice(0, 10).map((user, index) => {
                    const medal = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : `#${index + 1}`;
                    const roiColor = user.roi >= 0 ? 'text-green-500' : 'text-red-500';

                    return `
                        <div class="flex items-center justify-between p-3 rounded" style="background-color: var(--bg-secondary)">
                            <div class="flex items-center gap-3">
                                <div class="text-xl w-8">${medal}</div>
                                <div>
                                    <div class="font-semibold">${user.username}</div>
                                    <div class="text-xs" style="color: var(--text-secondary)">总资产: ${user.total_assets.toFixed(2)} USDT</div>
                                </div>
                            </div>
                            <div class="${roiColor} font-bold">
                                ${user.roi >= 0 ? '+' : ''}${user.roi.toFixed(2)}%
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } catch (error) {
        console.error('加载排行榜失败:', error);
        document.getElementById('publicLeaderboard').innerHTML = `
            <div class="text-center p-4" style="color: var(--text-secondary)">加载失败</div>
        `;
    }
}
