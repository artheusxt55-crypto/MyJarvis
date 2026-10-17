// Static JS for additional functionality
document.addEventListener('DOMContentLoaded', function() {
    // Auto-resize textareas
    document.querySelectorAll('textarea[auto-resize]').forEach(textarea => {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    });
});

// Toast notification system
window.showToast = function(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `glass px-4 py-3 rounded-xl border-l-4 ${type === 'error' ? 'border-red-500' : 'border-cyan-500'} animate-slide-up`;
    toast.innerHTML = `<div class="flex items-center gap-2"><span class="text-slate-200">${message}</span></div>`;
    
    const container_el = document.getElementById('toast-container');
    if (container_el) {
        container_el.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slide-up 0.3s ease-in reverse forwards';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
};