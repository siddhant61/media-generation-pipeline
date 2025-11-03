/**
 * Media Generation Pipeline - Frontend Application
 * Handles API communication, UI updates, and local storage for API keys
 */

// Configuration
const API_BASE_URL = window.location.origin;
const POLL_INTERVAL = 3000; // Poll every 3 seconds
const LOCAL_STORAGE_KEYS = {
    OPENAI_KEY: 'mgp_openai_key',
    STABILITY_KEY: 'mgp_stability_key',
    MEDIA_API_KEY: 'mgp_media_api_key'
};

// State
let currentJobId = null;
let pollInterval = null;

// DOM Elements
const elements = {
    // Form elements
    generateForm: document.getElementById('generateForm'),
    topicInput: document.getElementById('topic'),
    numScenesInput: document.getElementById('numScenes'),
    numScenesValue: document.getElementById('numScenesValue'),
    generateBtn: document.getElementById('generateBtn'),
    
    // Section elements
    statusSection: document.getElementById('statusSection'),
    resultsSection: document.getElementById('resultsSection'),
    errorSection: document.getElementById('errorSection'),
    
    // Status elements
    statusIcon: document.getElementById('statusIcon'),
    statusText: document.getElementById('statusText'),
    progressFill: document.getElementById('progressFill'),
    progressMessage: document.getElementById('progressMessage'),
    jobId: document.getElementById('jobId'),
    
    // Results elements
    resultVideo: document.getElementById('resultVideo'),
    videoSource: document.getElementById('videoSource'),
    downloadBtn: document.getElementById('downloadBtn'),
    newVideoBtn: document.getElementById('newVideoBtn'),
    
    // Error elements
    errorMessage: document.getElementById('errorMessage'),
    retryBtn: document.getElementById('retryBtn'),
    
    // Modal elements
    settingsBtn: document.getElementById('settingsBtn'),
    settingsModal: document.getElementById('settingsModal'),
    closeModal: document.getElementById('closeModal'),
    openaiKeyInput: document.getElementById('openaiKey'),
    stabilityKeyInput: document.getElementById('stabilityKey'),
    mediaApiKeyInput: document.getElementById('mediaApiKey'),
    saveKeysBtn: document.getElementById('saveKeysBtn'),
    clearKeysBtn: document.getElementById('clearKeysBtn'),
    keyStatus: document.getElementById('keyStatus'),
    keyStatusText: document.getElementById('keyStatusText')
};

/**
 * Initialize the application
 */
function init() {
    // Load saved API keys
    loadApiKeys();
    updateKeyStatus();
    
    // Event listeners
    elements.generateForm.addEventListener('submit', handleGenerate);
    elements.numScenesInput.addEventListener('input', updateSliderValue);
    elements.newVideoBtn.addEventListener('click', resetForm);
    elements.retryBtn.addEventListener('click', resetForm);
    
    // Modal event listeners
    elements.settingsBtn.addEventListener('click', openModal);
    elements.closeModal.addEventListener('click', closeModal);
    elements.saveKeysBtn.addEventListener('click', saveApiKeys);
    elements.clearKeysBtn.addEventListener('click', clearApiKeys);
    
    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === elements.settingsModal) {
            closeModal();
        }
    });
    
    // Close modal with Escape key
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && elements.settingsModal.style.display === 'block') {
            closeModal();
        }
    });
    
    console.log('Media Generation Pipeline initialized');
}

/**
 * Update slider value display
 */
function updateSliderValue() {
    elements.numScenesValue.textContent = elements.numScenesInput.value;
}

/**
 * Load API keys from localStorage
 */
function loadApiKeys() {
    elements.openaiKeyInput.value = localStorage.getItem(LOCAL_STORAGE_KEYS.OPENAI_KEY) || '';
    elements.stabilityKeyInput.value = localStorage.getItem(LOCAL_STORAGE_KEYS.STABILITY_KEY) || '';
    elements.mediaApiKeyInput.value = localStorage.getItem(LOCAL_STORAGE_KEYS.MEDIA_API_KEY) || '';
}

/**
 * Save API keys to localStorage
 */
function saveApiKeys() {
    const openaiKey = elements.openaiKeyInput.value.trim();
    const stabilityKey = elements.stabilityKeyInput.value.trim();
    const mediaApiKey = elements.mediaApiKeyInput.value.trim();
    
    if (openaiKey) {
        localStorage.setItem(LOCAL_STORAGE_KEYS.OPENAI_KEY, openaiKey);
    }
    if (stabilityKey) {
        localStorage.setItem(LOCAL_STORAGE_KEYS.STABILITY_KEY, stabilityKey);
    }
    if (mediaApiKey) {
        localStorage.setItem(LOCAL_STORAGE_KEYS.MEDIA_API_KEY, mediaApiKey);
    }
    
    updateKeyStatus();
    closeModal();
    showNotification('API keys saved successfully!', 'success');
}

/**
 * Clear all API keys from localStorage
 */
function clearApiKeys() {
    // Simple confirmation - could be enhanced with custom modal for better accessibility
    const confirmed = confirm('Are you sure you want to clear all API keys? This action cannot be undone.');
    if (confirmed) {
        localStorage.removeItem(LOCAL_STORAGE_KEYS.OPENAI_KEY);
        localStorage.removeItem(LOCAL_STORAGE_KEYS.STABILITY_KEY);
        localStorage.removeItem(LOCAL_STORAGE_KEYS.MEDIA_API_KEY);
        
        elements.openaiKeyInput.value = '';
        elements.stabilityKeyInput.value = '';
        elements.mediaApiKeyInput.value = '';
        
        updateKeyStatus();
        showNotification('All API keys cleared', 'warning');
    }
}

/**
 * Update key status indicator
 */
function updateKeyStatus() {
    const hasOpenAI = !!localStorage.getItem(LOCAL_STORAGE_KEYS.OPENAI_KEY);
    const hasStability = !!localStorage.getItem(LOCAL_STORAGE_KEYS.STABILITY_KEY);
    const hasMediaKey = !!localStorage.getItem(LOCAL_STORAGE_KEYS.MEDIA_API_KEY);
    
    const statusDot = elements.keyStatus.querySelector('.status-dot');
    
    if (hasOpenAI && hasStability) {
        statusDot.classList.add('active');
        elements.keyStatusText.textContent = hasMediaKey 
            ? 'All keys configured' 
            : 'OpenAI & Stability keys configured';
    } else if (hasOpenAI || hasStability) {
        statusDot.classList.remove('active');
        elements.keyStatusText.textContent = 'Partial configuration - some keys missing';
    } else {
        statusDot.classList.remove('active');
        elements.keyStatusText.textContent = 'No keys configured';
    }
}

/**
 * Open settings modal
 */
function openModal() {
    elements.settingsModal.style.display = 'block';
}

/**
 * Close settings modal
 */
function closeModal() {
    elements.settingsModal.style.display = 'none';
}

/**
 * Show notification message
 */
function showNotification(message, type = 'info') {
    // Simple console notification for now
    // Could be enhanced with toast notifications
    console.log(`[${type.toUpperCase()}] ${message}`);
}

/**
 * Handle video generation form submission
 */
async function handleGenerate(e) {
    e.preventDefault();
    
    const topic = elements.topicInput.value.trim();
    const numScenes = parseInt(elements.numScenesInput.value);
    
    // Get API keys from localStorage
    const openaiKey = localStorage.getItem(LOCAL_STORAGE_KEYS.OPENAI_KEY);
    const stabilityKey = localStorage.getItem(LOCAL_STORAGE_KEYS.STABILITY_KEY);
    const mediaApiKey = localStorage.getItem(LOCAL_STORAGE_KEYS.MEDIA_API_KEY);
    
    // Check if required keys are present
    if (!openaiKey || !stabilityKey) {
        // Using alert for simplicity - could be enhanced with custom accessible notification
        alert('⚠️ API Keys Required\n\nPlease configure your OpenAI and Stability AI API keys in Settings before generating a video.\n\nClick OK to open Settings.');
        openModal();
        return;
    }
    
    // Disable form
    elements.generateBtn.disabled = true;
    elements.generateBtn.innerHTML = '<span class="btn-icon loading">⏳</span> Generating...';
    
    // Show status section
    showSection('status');
    
    try {
        // Call API
        const response = await callGenerateAPI(topic, numScenes, openaiKey, stabilityKey, mediaApiKey);
        
        if (response.job_id) {
            currentJobId = response.job_id;
            elements.jobId.textContent = `Job ID: ${currentJobId}`;
            
            // Start polling for status
            startPolling();
        } else {
            throw new Error('No job ID received from server');
        }
    } catch (error) {
        showError(error.message);
        resetFormButton();
    }
}

/**
 * Call the /generate API endpoint
 */
async function callGenerateAPI(topic, numScenes, openaiKey, stabilityKey, mediaApiKey) {
    const headers = {
        'Content-Type': 'application/json'
    };
    
    // Add Media API key if configured
    if (mediaApiKey) {
        headers['X-API-Key'] = mediaApiKey;
    }
    
    const body = {
        topic,
        num_scenes: numScenes
    };
    
    // Add optional API keys to request body for UI-provided keys
    if (openaiKey) {
        body.openai_api_key = openaiKey;
    }
    if (stabilityKey) {
        body.stability_api_key = stabilityKey;
    }
    
    const response = await fetch(`${API_BASE_URL}/generate`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
    });
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

/**
 * Start polling for job status
 */
function startPolling() {
    // Clear any existing interval
    if (pollInterval) {
        clearInterval(pollInterval);
    }
    
    // Poll immediately
    pollStatus();
    
    // Then poll every 3 seconds
    pollInterval = setInterval(pollStatus, POLL_INTERVAL);
}

/**
 * Stop polling for job status
 */
function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

/**
 * Poll the /status/{job_id} endpoint
 */
async function pollStatus() {
    if (!currentJobId) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/status/${currentJobId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const status = await response.json();
        updateStatus(status);
        
        // Stop polling if job is complete or failed
        if (status.status === 'complete') {
            stopPolling();
            showResults(status);
        } else if (status.status === 'failed') {
            stopPolling();
            showError(status.error || 'Video generation failed');
        }
    } catch (error) {
        console.error('Error polling status:', error);
        // Continue polling on error (might be temporary network issue)
    }
}

/**
 * Update status display
 */
function updateStatus(status) {
    // Update status text and icon
    const statusMap = {
        'queued': { icon: '⏳', text: 'Queued', progress: 10 },
        'generating_scenes': { icon: '🎬', text: 'Generating Scenes', progress: 25 },
        'generating_content': { icon: '🎨', text: 'Creating Images', progress: 50 },
        'generating_audio': { icon: '🎙️', text: 'Synthesizing Audio', progress: 75 },
        'assembling_video': { icon: '🎞️', text: 'Assembling Video', progress: 90 },
        'complete': { icon: '✅', text: 'Complete', progress: 100 },
        'failed': { icon: '❌', text: 'Failed', progress: 0 }
    };
    
    const statusInfo = statusMap[status.status] || statusMap['queued'];
    
    elements.statusIcon.textContent = statusInfo.icon;
    elements.statusText.textContent = statusInfo.text;
    elements.progressFill.style.width = `${statusInfo.progress}%`;
    elements.progressMessage.textContent = status.progress || statusInfo.text;
}

/**
 * Show results section with generated video
 */
function showResults(status) {
    if (!status.video_url) {
        showError('Video URL not available');
        return;
    }
    
    // Update video source
    const videoUrl = `${API_BASE_URL}${status.video_url}`;
    elements.videoSource.src = videoUrl;
    elements.resultVideo.load();
    
    // Update download button
    elements.downloadBtn.href = videoUrl;
    elements.downloadBtn.download = status.video_url.split('/').pop();
    
    // Show results section
    showSection('results');
    resetFormButton();
}

/**
 * Show error section
 */
function showError(message) {
    elements.errorMessage.textContent = message;
    showSection('error');
    resetFormButton();
}

/**
 * Show specific section and hide others
 */
function showSection(section) {
    elements.statusSection.style.display = section === 'status' ? 'block' : 'none';
    elements.resultsSection.style.display = section === 'results' ? 'block' : 'none';
    elements.errorSection.style.display = section === 'error' ? 'block' : 'none';
}

/**
 * Reset form button to initial state
 */
function resetFormButton() {
    elements.generateBtn.disabled = false;
    elements.generateBtn.innerHTML = '<span class="btn-icon">🎥</span> Generate Video';
}

/**
 * Reset form and UI to initial state
 */
function resetForm() {
    // Stop polling
    stopPolling();
    
    // Reset state
    currentJobId = null;
    
    // Hide all sections
    showSection(null);
    
    // Reset form
    elements.generateForm.reset();
    updateSliderValue();
    resetFormButton();
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
