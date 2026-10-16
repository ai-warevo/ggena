const MODULE_NAME = 'image';

let socket;
const statusDot = document.querySelector('#connection-status .dot');
const statusText = document.querySelector('#connection-status .text');
const progressBar = document.getElementById('progress-bar');
const progressContainer = document.getElementById('progress-container');
const statusTextProgress = document.getElementById('status-text');
const resultImage = document.getElementById('result-image');
const placeholder = document.getElementById('placeholder');
const actionArea = document.getElementById('action-area');
const generateBtn = document.getElementById('generate-btn');
const saveBtn = document.getElementById('save-btn');

const imageWrapper = document.getElementById('image-wrapper');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');

// Image rotator state
let imageHistory = [];
const MAX_IMAGES = 100;
let currentRotationIndex = 0;
let zoomLevel = 1.0;

// Form elements
const promptInput = document.getElementById('prompt');
const positivePromptInput = document.getElementById('positive_prompt');
const negPromptInput = document.getElementById('negative_prompt');
const stepsInput = document.getElementById('steps');
const cfgScaleInput = document.getElementById('cfg_scale');
const resolutionSelect = document.getElementById('resolution');
const numOutputsInput = document.getElementById('num_outputs');

// Tab switching logic
let currentMode = 'ez';
const tabBtns = document.querySelectorAll('.tab-btn');
const ezContainer = document.getElementById('ez-mode-container');
const advancedContainer = document.getElementById('advanced-mode-container');

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentMode = btn.dataset.mode;
        
        if (currentMode === 'ez') {
            ezContainer.style.display = 'block';
            advancedContainer.style.display = 'none';
        } else {
            ezContainer.style.display = 'none';
            advancedContainer.style.display = 'block';
        }
    });
});

// Update UI values when sliders move
stepsInput.addEventListener('input', () => {
    document.getElementById('steps-val').textContent = stepsInput.value;
});
cfgScaleInput.addEventListener('input', () => {
    document.getElementById('cfg-val').textContent = cfgScaleInput.value;
});

function updateConnectionStatus(status) {
    console.log(`[Frontend] Connection status changed to: ${status}`);
    if (status === 'connected') {
        statusDot.className = 'dot connected';
        statusText.textContent = 'Connected';
    } else if (status === 'connecting') {
        statusDot.className = 'dot connecting';
        statusText.textContent = 'Connecting...';
    } else if (status === 'disconnected') {
        statusDot.className = 'dot disconnected';
        statusText.textContent = 'Disconnected';
    }
}

function connect() {
    updateConnectionStatus('connecting');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/generate/${MODULE_NAME}`;
    console.log(`[Frontend] Attempting to connect to WebSocket: ${wsUrl}`);
    
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log('[Frontend] WebSocket connection opened successfully');
        updateConnectionStatus('connected');
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('[Frontend] Received message from server:', data);

        if (data.type === 'progress') {
            console.log(`[Frontend] Progress update: ${data.step}/${data.total_steps}`);
            progressContainer.style.display = 'block';
            const percent = Math.round((data.step / data.total_steps) * 100);
            progressBar.style.width = `${percent}%`;
            statusTextProgress.textContent = `Generating: ${percent}% (${data.step}/${data.total_steps})`;
        } else if (data.type === 'image') {
            console.log('[Frontend] Image(s) received from server');
            
            const newImages = data.images && data.images.length > 0 ? data.images : (data.image_base64 ? [data.image_base64] : []);
            
            if (newImages.length > 0) {
                // Add to history
                imageHistory = [...imageHistory, ...newImages];

                // Handle overflow: keep only the last MAX_IMAGES
                if (imageHistory.length > MAX_IMAGES) {
                    const overflow = imageHistory.length - MAX_IMAGES;
                    imageHistory = imageHistory.slice(overflow);
                }

                // Set current index to the first of the new images
                currentRotationIndex = imageHistory.length - newImages.length;
                resultImage.src = imageHistory[currentRotationIndex];

                imageWrapper.style.display = 'block';
                placeholder.style.display = 'none';
                actionArea.style.display = 'block';
                progressContainer.style.display = 'none';
                generateBtn.disabled = false;

                if (data.positive_prompt) {
                    positivePromptInput.value = data.positive_prompt;
                }
                if (data.negative_prompt) {
                    negPromptInput.value = data.negative_prompt;
                }

                resetZoom();
            } else if (data.image_base64) {
                // Fallback for single image without images array
                resultImage.src = data.image_base64;
                imageWrapper.style.display = 'block';
                placeholder.style.display = 'none';
                actionArea.style.display = 'block';
                progressContainer.style.display = 'none';
                generateBtn.disabled = false;
                resetZoom();
            }
        } else if (data.type === 'error') {
            console.error('[Frontend] Error message from server:', data.message);
            alert(`Error: ${data.message}`);
            resetUI();
            generateBtn.disabled = false;
        }
    };

    socket.onclose = (event) => {
        console.warn(`[Frontend] WebSocket connection closed. Code: ${event.code}, Reason: ${event.reason}`);
        updateConnectionStatus('disconnected');
        setTimeout(connect, 3000); // Reconnect after 3 seconds
    };

    socket.onerror = (error) => {
        console.error('[Frontend] WebSocket error occurred:', error);
        socket.close();
    };
}

function resetUI() {
    console.log('[Frontend] Resetting UI');
    progressContainer.style.display = 'none';
    progressBar.style.width = '0%';
    imageWrapper.style.display = 'none';
    placeholder.style.display = 'block';
    actionArea.style.display = 'none';
}

function nextImage() {
    if (imageHistory.length === 0) return;
    currentRotationIndex = (currentRotationIndex + 1) % imageHistory.length;
    resultImage.src = imageHistory[currentRotationIndex];
    resetZoom();
}

function prevImage() {
    if (imageHistory.length === 0) return;
    currentRotationIndex = (currentRotationIndex - 1 + imageHistory.length) % imageHistory.length;
    resultImage.src = imageHistory[currentRotationIndex];
    resetZoom();
}

function zoomIn() {
    zoomLevel += 0.2;
    applyZoom();
}

function zoomOut() {
    if (zoomLevel > 0.4) {
        zoomLevel -= 0.2;
        applyZoom();
    }
}

function applyZoom() {
    resultImage.style.transform = `scale(${zoomLevel})`;
}

function resetZoom() {
    zoomLevel = 1.0;
    applyZoom();
}

function generate() {
    console.log('[Frontend] Generate button clicked');
    if (socket.readyState !== WebSocket.OPEN) {
        console.error('[Frontend] Cannot generate: WebSocket is not open. Current state:', socket.readyState);
        alert('WebSocket is not connected!');
        return;
    }

    const [width, height] = resolutionSelect.value.split('x').map(Number);
    const numOutputs = parseInt(numOutputsInput.value) || 1;

    const payload = {
        type: 'generate',
        prompt: currentMode === 'ez' ? promptInput.value : null,
        positive_prompt: currentMode === 'advanced' ? positivePromptInput.value || null : null,
        negative_prompt: currentMode === 'advanced' ? negPromptInput.value || null : null,
        steps: parseInt(stepsInput.value),
        cfg_scale: parseFloat(cfgScaleInput.value),
        width: width,
        height: height,
        num_outputs: numOutputs
    };

    console.log('[Frontend] Sending generation payload:', payload);

    resetUI();
    generateBtn.disabled = true;
    socket.send(JSON.stringify(payload));
}

function saveImage() {
    console.log('[Frontend] Save button clicked');
    const link = document.createElement('a');
    link.href = resultImage.src;
    link.download = `generated_${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

generateBtn.addEventListener('click', generate);
saveBtn.addEventListener('click', saveImage);
prevBtn.addEventListener('click', prevImage);
nextBtn.addEventListener('click', nextImage);

window.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') prevImage();
    else if (e.key === 'ArrowRight') nextImage();
    else if (e.key === 'ArrowUp') zoomIn();
    else if (e.key === 'ArrowDown') zoomOut();
});

// Initialize connection
connect();
