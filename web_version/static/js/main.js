// Excel Consolidator Web - Main JavaScript

// State
let templateFile = null;
let sourceFiles = [];
let currentJobId = null;
let statusCheckInterval = null;

// DOM Elements
const templateDropzone = document.getElementById('templateDropzone');
const templateInput = document.getElementById('templateInput');
const templateInfo = document.getElementById('templateInfo');
const templateName = document.getElementById('templateName');
const removeTemplate = document.getElementById('removeTemplate');

const sourcesDropzone = document.getElementById('sourcesDropzone');
const sourcesInput = document.getElementById('sourcesInput');
const sourcesList = document.getElementById('sourcesList');

const startButton = document.getElementById('startConsolidation');
const uploadSection = document.getElementById('uploadSection');
const progressSection = document.getElementById('progressSection');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');

// Settings
const convertTextCheckbox = document.getElementById('convertText');
const convertPercentCheckbox = document.getElementById('convertPercent');
const createBackupCheckbox = document.getElementById('createBackup');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeDropzones();
    initializeEventListeners();
});

// Dropzone Initialization
function initializeDropzones() {
    // Template dropzone
    templateDropzone.addEventListener('click', () => templateInput.click());
    templateDropzone.addEventListener('dragover', handleDragOver);
    templateDropzone.addEventListener('dragleave', handleDragLeave);
    templateDropzone.addEventListener('drop', (e) => handleTemplateDrop(e));
    templateInput.addEventListener('change', (e) => handleTemplateSelect(e));
    
    // Sources dropzone
    sourcesDropzone.addEventListener('click', () => sourcesInput.click());
    sourcesDropzone.addEventListener('dragover', handleDragOver);
    sourcesDropzone.addEventListener('dragleave', handleDragLeave);
    sourcesDropzone.addEventListener('drop', (e) => handleSourcesDrop(e));
    sourcesInput.addEventListener('change', (e) => handleSourcesSelect(e));
}

function initializeEventListeners() {
    removeTemplate.addEventListener('click', (e) => {
        e.stopPropagation();
        clearTemplate();
    });
    
    startButton.addEventListener('click', startConsolidation);
    
    document.getElementById('downloadBtn').addEventListener('click', downloadResult);
    document.getElementById('newConsolidation').addEventListener('click', resetApp);
    document.getElementById('retryBtn').addEventListener('click', resetApp);
}

// Drag and Drop Handlers
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    e.currentTarget.classList.remove('dragover');
}

function handleTemplateDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    templateDropzone.classList.remove('dragover');
    
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
    sourcesDropzone.classList.remove('dragover');
    
    const files = Array.from(e.dataTransfer.files);
    addSourceFiles(files);
}

function handleSourcesSelect(e) {
    const files = Array.from(e.target.files);
    addSourceFiles(files);
}

// File Management
function setTemplateFile(file) {
    if (!isExcelFile(file)) {
        showError('Please select a valid Excel file (.xlsx or .xls)');
        return;
    }
    
    templateFile = file;
    templateName.textContent = file.name;
    templateDropzone.querySelector('.dropzone-content').style.display = 'none';
    templateInfo.style.display = 'flex';
    
    updateStartButton();
}

function clearTemplate() {
    templateFile = null;
    templateDropzone.querySelector('.dropzone-content').style.display = 'block';
    templateInfo.style.display = 'none';
    templateInput.value = '';
    
    updateStartButton();
}

function addSourceFiles(files) {
    const validFiles = files.filter(isExcelFile);
    
    if (validFiles.length === 0) {
        showError('Please select valid Excel files (.xlsx or .xls)');
        return;
    }
    
    // Add to existing files (prevent duplicates)
    validFiles.forEach(file => {
        if (!sourceFiles.some(f => f.name === file.name && f.size === file.size)) {
            sourceFiles.push(file);
        }
    });
    
    renderSourceFiles();
    updateStartButton();
}

function removeSourceFile(index) {
    sourceFiles.splice(index, 1);
    renderSourceFiles();
    updateStartButton();
}

function renderSourceFiles() {
    if (sourceFiles.length === 0) {
        sourcesDropzone.querySelector('.dropzone-content').style.display = 'block';
        sourcesList.style.display = 'none';
        return;
    }
    
    sourcesDropzone.querySelector('.dropzone-content').style.display = 'none';
    sourcesList.style.display = 'block';
    
    sourcesList.innerHTML = '<h3 style="margin-bottom: 15px; color: #1e293b;">Selected Files (' + sourceFiles.length + ')</h3>';
    
    sourceFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span class="file-item-name">${file.name}</span>
            <span class="file-item-size">${formatFileSize(file.size)}</span>
            <button class="btn-remove" onclick="removeSourceFile(${index})">✕</button>
        `;
        sourcesList.appendChild(fileItem);
    });
}

// Utilities
function isExcelFile(file) {
    const validExtensions = ['.xlsx', '.xls'];
    const fileName = file.name.toLowerCase();
    return validExtensions.some(ext => fileName.endsWith(ext));
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function updateStartButton() {
    startButton.disabled = !(templateFile && sourceFiles.length > 0);
}

// Consolidation Process
async function startConsolidation() {
    // Prepare form data
    const formData = new FormData();
    formData.append('template', templateFile);
    
    sourceFiles.forEach(file => {
        formData.append('sources', file);
    });
    
    // Add settings
    formData.append('convert_text_to_numbers', convertTextCheckbox.checked);
    formData.append('convert_percentages', convertPercentCheckbox.checked);
    formData.append('create_backup', createBackupCheckbox.checked);
    
    // Show progress section
    uploadSection.style.display = 'none';
    progressSection.style.display = 'block';
    
    try {
        // Upload and start consolidation
        const response = await fetch('/api/consolidate', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to start consolidation');
        }
        
        const result = await response.json();
        currentJobId = result.job_id;
        
        // Start polling for status
        startStatusPolling();
        
    } catch (error) {
        showError(error.message);
    }
}

function startStatusPolling() {
    // Poll every second
    statusCheckInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${currentJobId}`);
            
            if (!response.ok) {
                throw new Error('Failed to get status');
            }
            
            const status = await response.json();
            updateProgress(status);
            
            // Check if complete or error
            if (status.status === 'completed') {
                clearInterval(statusCheckInterval);
                showResults(status);
            } else if (status.status === 'error') {
                clearInterval(statusCheckInterval);
                showError(status.error || 'An error occurred during consolidation');
            }
            
        } catch (error) {
            clearInterval(statusCheckInterval);
            showError('Lost connection to server');
        }
    }, 1000);
}

function updateProgress(status) {
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const currentFile = document.getElementById('currentFile');
    const processedFiles = document.getElementById('processedFiles');
    
    // Update progress bar
    progressBar.style.width = status.progress + '%';
    
    // Update text
    progressText.textContent = status.message;
    
    if (status.current_file) {
        currentFile.textContent = `Processing: ${status.current_file}`;
    }
    
    // Show processed files count
    if (status.processed_files > 0) {
        const fileItem = document.createElement('div');
        fileItem.className = 'processed-file-item';
        fileItem.textContent = `${status.current_file}`;
        
        // Only add if not already added
        const existing = Array.from(processedFiles.children).some(
            child => child.textContent === fileItem.textContent
        );
        
        if (!existing) {
            processedFiles.appendChild(fileItem);
            // Scroll to bottom
            processedFiles.scrollTop = processedFiles.scrollHeight;
        }
    }
}

function showResults(status) {
    progressSection.style.display = 'none';
    resultsSection.style.display = 'block';
    
    const successMessage = document.getElementById('successMessage');
    successMessage.textContent = `Successfully consolidated ${status.total_files} files!`;
}

function showError(message) {
    uploadSection.style.display = 'none';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'block';
    
    document.getElementById('errorMessage').textContent = message;
    
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
}

async function downloadResult() {
    if (!currentJobId) {
        showError('No job ID found');
        return;
    }
    
    try {
        // Open download in new window
        window.location.href = `/api/download/${currentJobId}`;
    } catch (error) {
        showError('Failed to download file');
    }
}

function resetApp() {
    // Clear state
    templateFile = null;
    sourceFiles = [];
    currentJobId = null;
    
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    
    // Reset UI
    clearTemplate();
    sourcesList.innerHTML = '';
    sourcesDropzone.querySelector('.dropzone-content').style.display = 'block';
    sourcesList.style.display = 'none';
    
    // Reset file inputs
    templateInput.value = '';
    sourcesInput.value = '';
    
    // Clear progress
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('progressText').textContent = '';
    document.getElementById('currentFile').textContent = '';
    document.getElementById('processedFiles').innerHTML = '';
    
    // Show upload section
    uploadSection.style.display = 'block';
    progressSection.style.display = 'none';
    resultsSection.style.display = 'none';
    errorSection.style.display = 'none';
    
    updateStartButton();
}

// Make removeSourceFile globally accessible
window.removeSourceFile = removeSourceFile;
