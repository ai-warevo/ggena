export const elements = {
    statusDot: document.querySelector('#connection-status .dot'),
    statusText: document.querySelector('#connection-status .text'),
    progressBar: document.getElementById('progress-bar'),
    progressContainer: document.getElementById('progress-container'),
    statusTextProgress: document.getElementById('status-text'),
    resultImage: document.getElementById('result-image'),
    placeholder: document.getElementById('placeholder'),
    actionArea: document.getElementById('action-area'),
    generateBtn: document.getElementById('generate-btn'),
    saveBtn: document.getElementById('save-btn'),
    imageWrapper: document.getElementById('image-wrapper'),
    prevBtn: document.getElementById('prev-btn'),
    nextBtn: document.getElementById('next-btn'),
    promptInput: document.getElementById('prompt'),
    positivePromptInput: document.getElementById('positive_prompt'),
    negPromptInput: document.getElementById('negative_prompt'),
    stepsInput: document.getElementById('steps'),
    cfgScaleInput: document.getElementById('cfg_scale'),
    resolutionSelect: document.getElementById('resolution'),
    numOutputsInput: document.getElementById('num_outputs'),
    ezContainer: document.getElementById('ez-mode-container'),
    advancedContainer: document.getElementById('advanced-mode-container'),
    tabBtns: document.querySelectorAll('.tab-btn'),
    stepsVal: document.getElementById('steps-val'),
    cfgVal: document.getElementById('cfg-val')
};

export function updateConnectionStatus(status) {
    if (status === 'connected') {
        elements.statusDot.className = 'dot connected';
        elements.statusText.textContent = 'Connected';
    } else if (status === 'connecting') {
        elements.statusDot.className = 'dot connecting';
        elements.statusText.textContent = 'Connecting...';
    } else if (status === 'disconnected') {
        elements.statusDot.className = 'dot disconnected';
        elements.statusText.textContent = 'Disconnected';
    }
}

export function resetUI() {
    elements.progressContainer.style.display = 'none';
    elements.progressBar.classList.remove('active');
    elements.progressBar.style.width = '0%';
    elements.imageWrapper.style.display = 'none';
    elements.placeholder.style.display = 'block';
    elements.actionArea.style.display = 'none';
}

export function showProgress(percent, step, total) {
    elements.progressContainer.style.display = 'block';
    elements.progressBar.classList.add('active');
    const p = Math.round((step / total) * 100);
    elements.progressBar.style.width = `${p}%`;
    elements.progressBar.setAttribute('aria-valuenow', p);
    elements.statusTextProgress.textContent = `Generating: ${p}% (${step}/${total})`;
}

export function setMode(mode) {
    if (mode === 'ez') {
        elements.ezContainer.style.display = 'block';
        elements.advancedContainer.style.display = 'none';
    } else {
        elements.ezContainer.style.display = 'none';
        elements.advancedContainer.style.display = 'block';
    }
}

export function updateImage(src) {
    elements.resultImage.src = src;
    elements.imageWrapper.style.display = 'block';
    elements.placeholder.style.display = 'none';
    elements.actionArea.style.display = 'block';
}
