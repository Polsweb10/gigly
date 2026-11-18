// Gigly Global JavaScript Utilities
window.Gigly = {
    // Switch between Buyer and Seller mode
    async switchRole(targetMode) {
        try {
            const res = await fetch('/api/auth/switch-mode', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: targetMode })
            });
            const data = await res.json();
            if (data.success) {
                window.location.reload();
            } else {
                alert(data.error || 'Error al cambiar de rol');
            }
        } catch (e) {
            console.error('Switch role error:', e);
        }
    },

    // Simple toast notification
    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-5 right-5 z-50 px-4 py-3 rounded-lg text-sm font-medium shadow-xl transition-all duration-300 transform translate-y-2 border ${
            type === 'success' ? 'bg-[#1A1D24] text-teal-400 border-teal-500/40' : 'bg-[#1A1D24] text-red-400 border-red-500/40'
        }`;
        toast.innerHTML = `<div class="flex items-center space-x-2"><span>${type === 'success' ? '✓' : '⚠️'}</span><span>${message}</span></div>`;
        document.body.appendChild(toast);
        setTimeout(() => toast.classList.remove('translate-y-2'), 10);
        setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-2');
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }
};
