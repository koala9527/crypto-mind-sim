// ==================== 公开内容加载 ====================

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
