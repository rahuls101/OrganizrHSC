window.addEventListener('DOMContentLoaded', () => {
        const urlParams = new URLSearchParams(window.location.search);
        const message = urlParams.get('message');
        const type = urlParams.get('type');

        if (message) {
            const toast = document.getElementById('toast-message');
            const toastText = document.getElementById('toast-text');

            toastText.textContent = decodeURIComponent(message);

            // Apply styles based on type
            if (type === 'success') {
                toast.classList.add('bg-green-100', 'border', 'border-green-400', 'text-green-800');
            } else if (type === 'error') {
                toast.classList.add('bg-red-100', 'border', 'border-red-400', 'text-red-800');
            } else {
                toast.classList.add('bg-gray-100', 'border', 'border-gray-400', 'text-gray-800');
            }

            toast.classList.remove('hidden');

            // Auto-hide
            setTimeout(() => {
                toast.classList.add('opacity-0');
                setTimeout(() => toast.classList.add('hidden'), 500);
            }, 4000);
        }
});