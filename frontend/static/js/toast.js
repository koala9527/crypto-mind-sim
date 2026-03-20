// ==================== 通知系统 ====================

function showToast(message, type = 'info', title = '') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };

    const titles = {
        success: title || '成功',
        error: title || '错误',
        warning: title || '警告',
        info: title || '提示'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = document.createElement('div');
    icon.className = 'toast-icon';
    icon.textContent = icons[type] || icons.info;

    const content = document.createElement('div');
    content.className = 'toast-content';

    const titleEl = document.createElement('div');
    titleEl.className = 'toast-title';
    titleEl.textContent = titles[type] || titles.info;

    const messageEl = document.createElement('div');
    messageEl.className = 'toast-message';
    messageEl.textContent = String(message ?? '');

    const close = document.createElement('div');
    close.className = 'toast-close';
    close.textContent = '×';
    close.addEventListener('click', () => toast.remove());

    content.appendChild(titleEl);
    content.appendChild(messageEl);
    toast.appendChild(icon);
    toast.appendChild(content);
    toast.appendChild(close);

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('hiding');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
