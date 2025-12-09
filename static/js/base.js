
// 自定义弹窗函数
function showCustomAlert(message, type = 'info', duration = 3000) {
    // 移除已存在的弹窗，避免叠加
    const oldAlert = document.querySelector('.custom-alert');
    if (oldAlert) oldAlert.remove();

    // 创建新弹窗
    const alertBox = document.createElement('div');
    alertBox.className = `custom-alert ${type}`;
    alertBox.innerText = message;
    document.body.appendChild(alertBox);

    // 显示弹窗
    setTimeout(() => alertBox.classList.add('show'), 10);

    // 自动消失
    setTimeout(() => {
        alertBox.classList.add('fade-out');
        setTimeout(() => alertBox.remove(), 300);
    }, duration);
}
