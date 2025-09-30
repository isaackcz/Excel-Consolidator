/**
 * Excel Consolidator Pro - Main Application Script
 * Professional UI/UX with Enhanced Interactions
 */

// ========================================
// Application State
// ========================================
const AppState = {
    templateFile: null,
    sourceFiles: [],
    currentJobId: null,
    statusCheckInterval: null,
    startTime: null,
    settings: {
        convertText: true,
        convertPercent: true,
        createBackup: false,
        skipValidation: true
    }
};

// ========================================
// DOM Elements Cache
// ========================================
const DOM = {
    // Sections
    uploadSection: document.getElementById('uploadSection'),
    progressSection: document.getElementById('progressSection'),
    resultsSection: document.getElementById('resultsSection'),
    errorSection: document.getElementById('errorSection'),
    
    // Template elements
    templateDropzone: document.getElementById('templateDropzone'),
    templateDropContent: document.getElementById('templateDropContent'),
    templateInput: document.getElementById('templateInput'),
    templatePreview: document.getElementById('templatePreview'),
    templateName: document.getElementById('templateName'),
    templateSize: document.getElementById('templateSize'),
    removeTemplate: document.getElementById('removeTemplate'),
    
    // Sources elements
    sourcesDropzone: document.getElementById('sourcesDropzone'),
    sourcesDropContent: document.getElementById('sourcesDropContent'),
    sourcesInput: document.getElementById('sourcesInput'),
    sourcesList: document.getElementById('sourcesList'),

// Settings
    settingsToggle: document.getElementById('settingsToggle'),
    settingsContent: document.getElementById('settingsContent'),
    convertTextCheck: document.getElementById('convertText'),
    convertPercentCheck: document.getElementById('convertPercent'),
    createBackupCheck: document.getElementById('createBackup'),
    skipValidationCheck: document.getElementById('skipValidation'),
    
    // Buttons
    startBtn: document.getElementById('startConsolidation'),
    downloadBtn: document.getElementById('downloadBtn'),
    newConsolidationBtn: document.getElementById('newConsolidation'),
    retryBtn: document.getElementById('retryBtn'),
    
    // Theme & Help
    themeToggle: document.getElementById('themeToggle'),
    helpBtn: document.getElementById('helpBtn'),
    helpModal: document.getElementById('helpModal'),
    closeHelpModal: document.getElementById('closeHelpModal'),
    
    // Progress elements
    statTotalFiles: document.getElementById('statTotalFiles'),
    statProcessed: document.getElementById('statProcessed'),
    statProgress: document.getElementById('statProgress'),
    progressBar: document.getElementById('progressBar'),
    progressStatus: document.getElementById('progressStatus'),
    progressPercentage: document.getElementById('progressPercentage'),
    progressSubtitle: document.getElementById('progressSubtitle'),
    currentFileCard: document.getElementById('currentFileCard'),
    currentFileName: document.getElementById('currentFileName'),
    processedLogList: document.getElementById('processedLogList'),
    
    // Results elements
    resultsMessage: document.getElementById('resultsMessage'),
    resultFilesCount: document.getElementById('resultFilesCount'),
    resultProcessTime: document.getElementById('resultProcessTime'),
    
    // Error elements
    errorMessage: document.getElementById('errorMessage'),
    
    // Toast container
    toastContainer: document.getElementById('toastContainer')
};

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    initializeEventListeners();
    initializeDropzones();
    console.log('Excel Consolidator Pro initialized successfully');
});

// ========================================
// Theme Management
// ========================================
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    showToast(
        'Theme Updated',
        `Switched to ${newTheme} mode`,
        'success'
    );
}

// ========================================
// Event Listeners
// ========================================
function initializeEventListeners() {
    // Theme toggle
    DOM.themeToggle?.addEventListener('click', toggleTheme);
    
    // Help modal
    DOM.helpBtn?.addEventListener('click', () => {
        DOM.helpModal.style.display = 'flex';
    });
    
    DOM.closeHelpModal?.addEventListener('click', () => {
        DOM.helpModal.style.display = 'none';
    });
    
    DOM.helpModal?.addEventListener('click', (e) => {
        if (e.target === DOM.helpModal) {
            DOM.helpModal.style.display = 'none';
        }
    });
    
    // Settings toggle
    DOM.settingsToggle?.addEventListener('click', () => {
        DOM.settingsToggle.classList.toggle('active');
        DOM.settingsContent.classList.toggle('expanded');
    });
    
    // Settings checkboxes
    DOM.convertTextCheck?.addEventListener('change', (e) => {
        AppState.settings.convertText = e.target.checked;
    });
    
    DOM.convertPercentCheck?.addEventListener('change', (e) => {
        AppState.settings.convertPercent = e.target.checked;
    });
    
    DOM.createBackupCheck?.addEventListener('change', (e) => {
        AppState.settings.createBackup = e.target.checked;
    });
    
    DOM.skipValidationCheck?.addEventListener('change', (e) => {
        AppState.settings.skipValidation = e.target.checked;
    });
    
    // File removal
    DOM.removeTemplate?.addEventListener('click', (e) => {
        e.stopPropagation();
        clearTemplate();
    });
    
    // Action buttons
    DOM.startBtn?.addEventListener('click', startConsolidation);
    DOM.downloadBtn?.addEventListener('click', downloadResult);
    DOM.newConsolidationBtn?.addEventListener('click', resetApplication);
    DOM.retryBtn?.addEventListener('click', resetApplication);
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Escape key to close modal
        if (e.key === 'Escape' && DOM.helpModal.style.display === 'flex') {
            DOM.helpModal.style.display = 'none';
        }
        
        // Ctrl/Cmd + K for theme toggle
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            toggleTheme();
        }
    });
}

// ========================================
// Dropzone Initialization
// ========================================
function initializeDropzones() {
    // Template dropzone
    DOM.templateDropzone.addEventListener('click', () => {
        if (!AppState.templateFile) {
            DOM.templateInput.click();
        }
    });
    
    DOM.templateDropzone.addEventListener('dragover', handleDragOver);
    DOM.templateDropzone.addEventListener('dragleave', handleDragLeave);
    DOM.templateDropzone.addEventListener('drop', handleTemplateDrop);
    DOM.templateInput.addEventListener('change', handleTemplateSelect);
    
    // Sources dropzone
    DOM.sourcesDropzone.addEventListener('click', (e) => {
        if (e.target.closest('.file-remove-btn')) return;
        DOM.sourcesInput.click();
    });
    
    DOM.sourcesDropzone.addEventListener('dragover', handleDragOver);
    DOM.sourcesDropzone.addEventListener('dragleave', handleDragLeave);
    DOM.sourcesDropzone.addEventListener('drop', handleSourcesDrop);
    DOM.sourcesInput.addEventListener('change', handleSourcesSelect);
}

// ========================================
// Drag & Drop Handlers
// ========================================
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget)) return;
    e.currentTarget.classList.remove('dragover');
}

function handleTemplateDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    DOM.templateDropzone.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        setTemplateFile(files[0]);
    }
}

function handleTemplateSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        setTemplateFile(files[0]);
    }
}

function handleSourcesDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    DOM.sourcesDropzone.classList.remove('dragover');
    
    const files = Array.from(e.dataTransfer.files);
    addSourceFiles(files);
}

function handleSourcesSelect(e) {
    const files = Array.from(e.target.files);
    addSourceFiles(files);
}

// ========================================
// File Management
// ========================================
function setTemplateFile(file) {
    if (!isValidExcelFile(file)) {
        showToast(
            'Invalid File Type',
            'Please select a valid Excel file (.xlsx or .xls)',
            'error'
        );
        return;
    }
    
    AppState.templateFile = file;
    
    // Update UI
    DOM.templateName.textContent = file.name;
    DOM.templateSize.textContent = formatFileSize(file.size);
    DOM.templateDropContent.style.display = 'none';
    DOM.templatePreview.style.display = 'flex';
    
    updateStartButton();
    
    showToast(
        'Template Added',
        file.name,
        'success'
    );
}

function clearTemplate() {
    AppState.templateFile = null;
    DOM.templateDropContent.style.display = 'block';
    DOM.templatePreview.style.display = 'none';
    DOM.templateInput.value = '';
    updateStartButton();
}

function addSourceFiles(files) {
    const validFiles = files.filter(isValidExcelFile);
    
    if (validFiles.length === 0) {
        showToast(
            'Invalid Files',
            'Please select valid Excel files (.xlsx or .xls)',
            'error'
        );
        return;
    }
    
    let addedCount = 0;
    
    // Add files, avoiding duplicates
    validFiles.forEach(file => {
        const isDuplicate = AppState.sourceFiles.some(
            f => f.name === file.name && f.size === file.size
        );
        
        if (!isDuplicate) {
            AppState.sourceFiles.push(file);
            addedCount++;
        }
    });
    
    if (addedCount > 0) {
    renderSourceFiles();
    updateStartButton();
        showToast(
            'Files Added',
            `${addedCount} file(s) added successfully`,
            'success'
        );
    } else {
        showToast(
            'Duplicate Files',
            'These files were already added',
            'warning'
        );
    }
}

function removeSourceFile(index) {
    const removedFile = AppState.sourceFiles[index];
    AppState.sourceFiles.splice(index, 1);
    renderSourceFiles();
    updateStartButton();
    
    showToast(
        'File Removed',
        removedFile.name,
        'warning'
    );
}

function renderSourceFiles() {
    if (AppState.sourceFiles.length === 0) {
        DOM.sourcesDropContent.style.display = 'block';
        DOM.sourcesList.style.display = 'none';
        DOM.sourcesList.innerHTML = '';
        return;
    }
    
    DOM.sourcesDropContent.style.display = 'none';
    DOM.sourcesList.style.display = 'block';
    
    // Create header
    const header = document.createElement('div');
    header.className = 'files-list-header';
    header.textContent = `${AppState.sourceFiles.length} file(s) selected`;
    
    DOM.sourcesList.innerHTML = '';
    DOM.sourcesList.appendChild(header);
    
    // Render file items
    AppState.sourceFiles.forEach((file, index) => {
        const fileItem = createFileItem(file, index);
        DOM.sourcesList.appendChild(fileItem);
    });
}

function createFileItem(file, index) {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.innerHTML = `
        <div class="file-item-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
        </div>
        <div class="file-item-info">
            <div class="file-item-name">${escapeHtml(file.name)}</div>
            <div class="file-item-size">${formatFileSize(file.size)}</div>
        </div>
        <button class="file-remove-btn" onclick="removeSourceFile(${index})" title="Remove file">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <line x1="18" y1="6" x2="6" y2="18" stroke-width="2"/>
                <line x1="6" y1="6" x2="18" y2="18" stroke-width="2"/>
            </svg>
        </button>
    `;
    return item;
}

// ========================================
// Consolidation Process
// ========================================
async function startConsolidation() {
    if (!AppState.templateFile || AppState.sourceFiles.length === 0) {
        showToast(
            'Missing Files',
            'Please upload both template and source files',
            'error'
        );
        return;
    }
    
    // Prepare form data
    const formData = new FormData();
    formData.append('template', AppState.templateFile);
    
    AppState.sourceFiles.forEach(file => {
        formData.append('sources', file);
    });
    
    // Add settings
    formData.append('convert_text_to_numbers', AppState.settings.convertText);
    formData.append('convert_percentages', AppState.settings.convertPercent);
    formData.append('create_backup', AppState.settings.createBackup);
    formData.append('skip_validation', AppState.settings.skipValidation);
    
    // Show progress section
    showSection('progress');
    AppState.startTime = Date.now();
    
    // Initialize progress stats
    DOM.statTotalFiles.textContent = AppState.sourceFiles.length;
    DOM.statProcessed.textContent = '0';
    DOM.statProgress.textContent = '0%';
    
    try {
        const response = await fetch('/api/consolidate', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to start consolidation');
        }
        
        const result = await response.json();
        AppState.currentJobId = result.job_id;
        
        // Start status polling
        startStatusPolling();
        
        showToast(
            'Processing Started',
            `Processing ${result.total_files} files...`,
            'success'
        );
        
    } catch (error) {
        console.error('Consolidation error:', error);
        showError(error.message);
    }
}

function startStatusPolling() {
    let pollCount = 0;
    const maxPolls = 600; // 10 minutes max (600 seconds at 1s interval)
    
    AppState.statusCheckInterval = setInterval(async () => {
        pollCount++;
        
        if (pollCount > maxPolls) {
            clearInterval(AppState.statusCheckInterval);
            showError('Request timed out. The process may still be running.');
            return;
        }
        
        try {
            const response = await fetch(`/api/status/${AppState.currentJobId}`);
            
            if (!response.ok) {
                throw new Error('Failed to get status');
            }
            
            const status = await response.json();
            updateProgress(status);
            
            if (status.status === 'completed') {
                clearInterval(AppState.statusCheckInterval);
                showResults(status);
            } else if (status.status === 'error') {
                clearInterval(AppState.statusCheckInterval);
                showError(status.error || 'An error occurred during consolidation');
            }
            
        } catch (error) {
            console.error('Status check error:', error);
            clearInterval(AppState.statusCheckInterval);
            showError('Lost connection to server. Please check your network.');
        }
    }, 1000); // Poll every second
}

function updateProgress(status) {
    // Update stats
    DOM.statProcessed.textContent = status.processed_files || 0;
    DOM.statProgress.textContent = Math.round(status.progress) + '%';
    
    // Update progress bar
    DOM.progressBar.style.width = status.progress + '%';
    DOM.progressPercentage.textContent = Math.round(status.progress) + '%';
    DOM.progressStatus.textContent = status.message || 'Processing...';
    
    // Update subtitle with elapsed time
    if (AppState.startTime) {
        const elapsed = Math.floor((Date.now() - AppState.startTime) / 1000);
        DOM.progressSubtitle.textContent = `Elapsed time: ${formatDuration(elapsed)}`;
    }
    
    // Show/update current file
    if (status.current_file) {
        DOM.currentFileCard.style.display = 'block';
        DOM.currentFileName.textContent = status.current_file;
        
        // Add to processed log (avoid duplicates)
        const existingItems = Array.from(DOM.processedLogList.children);
        const alreadyLogged = existingItems.some(
            item => item.textContent === status.current_file
        );
        
        if (!alreadyLogged && status.processed_files > 0) {
            const logItem = document.createElement('div');
            logItem.className = 'processed-log-item';
            logItem.innerHTML = `<span>${escapeHtml(status.current_file)}</span>`;
            DOM.processedLogList.appendChild(logItem);
            
            // Auto-scroll to bottom
            DOM.processedLogList.scrollTop = DOM.processedLogList.scrollHeight;
        }
    }
}

function showResults(status) {
    showSection('results');
    
    const processTime = AppState.startTime 
        ? Math.floor((Date.now() - AppState.startTime) / 1000)
        : 0;
    
    DOM.resultFilesCount.textContent = status.total_files || AppState.sourceFiles.length;
    DOM.resultProcessTime.textContent = formatDuration(processTime);
    DOM.resultsMessage.textContent = `Successfully consolidated ${status.total_files} files into one workbook`;
    
    showToast(
        'Consolidation Complete!',
        'Your file is ready to download',
        'success'
    );
}

async function downloadResult() {
    if (!AppState.currentJobId) {
        showToast('Error', 'No job ID found', 'error');
        return;
    }
    
    try {
        // Trigger download
        window.location.href = `/api/download/${AppState.currentJobId}`;
        
        showToast(
            'Download Started',
            'Your file is being downloaded',
            'success'
        );
    } catch (error) {
        console.error('Download error:', error);
        showToast('Download Failed', error.message, 'error');
    }
}

function showError(message) {
    showSection('error');
    DOM.errorMessage.textContent = message;
    
    if (AppState.statusCheckInterval) {
        clearInterval(AppState.statusCheckInterval);
    }
}

// ========================================
// UI Navigation
// ========================================
function showSection(section) {
    DOM.uploadSection.style.display = 'none';
    DOM.progressSection.style.display = 'none';
    DOM.resultsSection.style.display = 'none';
    DOM.errorSection.style.display = 'none';
    
    switch (section) {
        case 'upload':
            DOM.uploadSection.style.display = 'block';
            break;
        case 'progress':
            DOM.progressSection.style.display = 'block';
            break;
        case 'results':
            DOM.resultsSection.style.display = 'block';
            break;
        case 'error':
            DOM.errorSection.style.display = 'block';
            break;
    }
}

function updateStartButton() {
    const isValid = AppState.templateFile && AppState.sourceFiles.length > 0;
    DOM.startBtn.disabled = !isValid;
}

function resetApplication() {
    // Clear state
    AppState.templateFile = null;
    AppState.sourceFiles = [];
    AppState.currentJobId = null;
    AppState.startTime = null;
    
    if (AppState.statusCheckInterval) {
        clearInterval(AppState.statusCheckInterval);
    }
    
    // Reset UI
    clearTemplate();
    DOM.sourcesList.innerHTML = '';
    DOM.sourcesDropContent.style.display = 'block';
    DOM.sourcesList.style.display = 'none';
    
    // Reset inputs
    DOM.templateInput.value = '';
    DOM.sourcesInput.value = '';
    
    // Reset progress
    DOM.progressBar.style.width = '0%';
    DOM.processedLogList.innerHTML = '';
    DOM.currentFileCard.style.display = 'none';
    
    // Show upload section
    showSection('upload');
    updateStartButton();
}

// ========================================
// Toast Notifications
// ========================================
function showToast(title, message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const iconMap = {
        success: '✓',
        error: '✕',
        warning: '⚠'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">${iconMap[type] || '✓'}</div>
        <div class="toast-content">
            <div class="toast-title">${escapeHtml(title)}</div>
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
    `;
    
    DOM.toastContainer.appendChild(toast);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ========================================
// Utility Functions
// ========================================
function isValidExcelFile(file) {
    if (!file) return false;
    const validExtensions = ['.xlsx', '.xls'];
    const fileName = file.name.toLowerCase();
    return validExtensions.some(ext => fileName.endsWith(ext));
}

function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(unitIndex > 0 ? 1 : 0)} ${units[unitIndex]}`;
}

function formatDuration(seconds) {
    if (seconds < 60) {
        return `${seconds}s`;
    }
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    if (minutes < 60) {
        return `${minutes}m ${remainingSeconds}s`;
    }
    
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    
    return `${hours}h ${remainingMinutes}m ${remainingSeconds}s`;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// ========================================
// Global Exposure for Inline Handlers
// ========================================
window.removeSourceFile = removeSourceFile;

// ========================================
// Performance Monitoring (Optional)
// ========================================
if (window.performance && window.performance.timing) {
    window.addEventListener('load', () => {
        setTimeout(() => {
            const timing = window.performance.timing;
            const loadTime = timing.loadEventEnd - timing.navigationStart;
            console.log(`Page load time: ${loadTime}ms`);
        }, 0);
    });
}