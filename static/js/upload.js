document.addEventListener('DOMContentLoaded', function() {
    // ─────────────────────────────────────────────
    // DOM Elements
    // ─────────────────────────────────────────────
    const fileInput = document.getElementById('file-upload');
    const previewContainer = document.querySelector('#file-preview-container');
    const clearAllBtn = document.getElementById('clear-all-btn');
    const createBtn = document.getElementById('create-assessments-btn');
    const successBanner = document.getElementById('upload-success-banner');
    const errorBanner = document.getElementById('upload-error-banner');

    // ─────────────────────────────────────────────
    // State
    // ─────────────────────────────────────────────
    let selectedFiles = [];

    // ─────────────────────────────────────────────
    // File Input Change Handler
    // ─────────────────────────────────────────────
    fileInput.addEventListener('change', function() {
        let addedPDF = false;
        const newFiles = [];

        for (const file of fileInput.files) {
            if (file.type !== 'application/pdf') {
                const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
                showFileError(`'${ext}' is not a supported file type.`);
                continue;
            }

            if (selectedFiles.some(f => f.name === file.name && f.size === file.size)) continue;

            selectedFiles.push(file);
            const previewElement = createPreviewElement(file);
            previewContainer.appendChild(previewElement);
            newFiles.push(file);
            addedPDF = true;
        }

        if (addedPDF) {
            const emptyState = previewContainer.querySelector('.text-center');
            if (emptyState) emptyState.remove();
            uploadMultipleFiles(newFiles);
        }
    });

    // ─────────────────────────────────────────────
    // Clear All Files
    // ─────────────────────────────────────────────
    clearAllBtn.addEventListener('click', () => {
        selectedFiles = [];
        showEmptyState();
        updateCreateButtonState();

        fetch('/clear-parsed', {
                method: 'POST'
            })
            .then(res => res.json())
            .then(data => {
                if (!data) console.error('Failed to clear parsed assessments from session');
            });
    });

    // ─────────────────────────────────────────────
    // Create Assessments Button
    // ─────────────────────────────────────────────
    createBtn.addEventListener('click', () => {
        const processedFilenames = Array.from(document.querySelectorAll('[data-status="processed"]'))
            .map(el => el.dataset.filename);

        if (processedFilenames.length === 0) {
            showBanner(errorBanner);
            return;
        }

        fetch('/commit-assessments', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filenames: processedFilenames
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    const countText = document.getElementById('upload-committed-count');
                    countText.textContent = `${data.message}`;
                    showBanner(successBanner);
                } else {
                    showBanner(errorBanner);
                }
            })
            .catch(() => showBanner(errorBanner));
    });

    function updateCreateButtonState() {
        const processedCount = document.querySelectorAll('[data-status="processed"]').length;
        if (processedCount > 0) {
            createBtn.disabled = false;
            createBtn.classList.remove('bg-gray-300', 'cursor-not-allowed');
            createBtn.classList.add('bg-wcc-blue', 'hover:bg-blue-700', 'cursor-pointer');
        } else {
            createBtn.disabled = true;
            createBtn.classList.add('bg-gray-300', 'cursor-not-allowed');
            createBtn.classList.remove('bg-wcc-blue', 'hover:bg-blue-700', 'cursor-pointer');
        }
    }

    // ─────────────────────────────────────────────
    // Upload Files to Backend
    // ─────────────────────────────────────────────
    function uploadMultipleFiles(files) {
        const formData = new FormData();
        for (const file of files) formData.append('file', file);

        fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(results => {
                for (const file of files) {
                    const previewElement = document.querySelector(`[data-filename="${file.name}"]`);
                    if (!previewElement) continue;

                    if (results[file.name]) {
                        updateStatus(previewElement, 'success');
                        previewElement.dataset.status = 'processed';
                        updateCreateButtonState();
                    } else {
                        updateStatus(previewElement, 'error');
                        updateCreateButtonState();
                    }
                }
            })
            .catch(() => {
                for (const file of files) {
                    const previewElement = document.querySelector(`[data-filename="${file.name}"]`);
                    if (previewElement) {
                        updateStatus(previewElement, 'failed');
                        updateCreateButtonState();
                    }
                }
            });
    }

    // ─────────────────────────────────────────────
    // Create Preview Element
    // ─────────────────────────────────────────────
    function createPreviewElement(file) {
        const container = document.createElement('div');
        container.className = 'flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200';
        container.dataset.filename = file.name;

        container.innerHTML = `
            <div class="flex items-center">
                <div class="flex-shrink-0">
                    <svg class="w-8 h-8 text-red-500" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z"></path>
                    </svg>
                </div>
                <div class="ml-3">
                    <p class="text-sm font-medium text-gray-900">${file.name}</p>
                    <p class="text-xs text-gray-500">${(file.size / (1024 * 1024)).toFixed(1)} MB</p>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                <span class="status-pill inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                    <svg class="status-icon w-3 h-3 mr-1 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span class="status-text">Processing</span>
                </span>
                <button class="delete-btn p-1 rounded-full text-red-600 hover:bg-red-100 hover:text-red-800 transition-colors duration-200">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                    </svg>
                </button>
            </div>
        `;

        const deleteBtn = container.querySelector('.delete-btn');
        deleteBtn.addEventListener('click', () => {
            container.remove();
            selectedFiles = selectedFiles.filter(f => !(f.name === file.name && f.size === file.size));
            if (selectedFiles.length === 0 && previewContainer.querySelectorAll('[data-filename]').length === 0) {
                showEmptyState();
            }
            updateCreateButtonState();
        });

        return container;
    }

    // ─────────────────────────────────────────────
    // UI Helper Functions
    // ─────────────────────────────────────────────
    function updateStatus(previewElement, status) {
        const badge = previewElement.querySelector('.status-pill');
        const text = badge.querySelector('.status-text');
        const icon = badge.querySelector('.status-icon');

        const config = {
            success: {
                classes: 'bg-green-100 text-green-800',
                text: 'Processed',
                icon: `<svg class="status-icon w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path></svg>`
            },
            error: {
                classes: 'bg-red-100 text-red-800',
                text: 'Error',
                icon: `<svg class="status-icon w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>`
            },
            failed: {
                classes: 'bg-red-100 text-red-800',
                text: 'Upload Failed',
                icon: `<svg class="status-icon w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>`
            }
        };

        badge.className = `status-pill inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config[status].classes}`;
        icon.outerHTML = config[status].icon;
        text.textContent = config[status].text;
    }

    function showEmptyState() {
        previewContainer.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <svg class="w-12 h-12 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <p class="text-sm">No files selected yet</p>
            </div>
        `;
    }

    function showBanner(bannerElement) {
        [successBanner, errorBanner].forEach(b => b.classList.add('hidden'));
        bannerElement.classList.remove('hidden');
        setTimeout(() => {
            bannerElement.classList.add('hidden');
        }, 6000);
    }

    function showFileError(message) {
        const banner = document.getElementById('file-error-banner');
        banner.textContent = message;
        banner.classList.remove('hidden');
        setTimeout(() => {
            banner.classList.add('hidden');
            banner.textContent = '';
        }, 4000);
    }
});