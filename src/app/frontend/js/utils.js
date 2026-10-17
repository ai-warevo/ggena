/**
 * Toast Notification System
 */
export function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // Remove after animation
    setTimeout(() => {
        toast.classList.add('fade-out');
        toast.addEventListener('animationend', () => {
            toast.remove();
            if (container.childNodes.length === 0) {
                container.remove();
            }
        });
    }, 3000);
}

export function applyZoom(element, zoomLevel) {
    element.style.transform = `scale(${zoomLevel})`;
}
