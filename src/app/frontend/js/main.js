import { connect } from './api.js';
import * as ui from './ui.js';
import { showToast, applyZoom } from './utils.js';

// State
let socket;
let imageHistory = [];
const MAX_IMAGES = 100;
let currentRotationIndex = 0;
let zoomLevel = 1.0;
let currentMode = 'ez';

/**
 * WebSocket Message Handler
 */
function handleMessage(data) {
    if (data.type === 'progress') {
        ui.showProgress(Math.round((data.step / data.total_steps) * 100), data.step, data.total_steps);
    } else if (data.type === 'image') {
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
            ui.updateImage(imageHistory[currentRotationIndex]);

            ui.elements.generateBtn.disabled = false;
            ui.elements.progressContainer.style.display = 'none';
            ui.elements.progressBar.classList.remove('active');

            if (data.positive_prompt) {
                ui.elements.positivePromptInput.value = data.positive_prompt;
            }
            if (data.negative_prompt) {
                ui.elements.negPromptInput.value = data.negative_prompt;
            }

            resetZoom();
            showToast('Image generated successfully!', 'success');
        } else if (data.image_base64) {
            // Fallback for single image without images array
            ui.updateImage(data.image_base64);
            ui.elements.generateBtn.disabled = false;
            ui.elements.progressContainer.style.display = 'none';
            ui.elements.progressBar.classList.remove('active');
            resetZoom();
        }
    } else if (data.type === 'error') {
        console.error('[Frontend] Error message from server:', data.message);
        showToast(`Error: ${data.message}`, 'error');
        ui.resetUI();
        ui.elements.generateBtn.disabled = false;
    }
}

/**
 * Connection Management
 */
function startConnection() {
    ui.updateConnectionStatus('connecting');
    socket = connect(
        handleMessage,
        () => ui.updateConnectionStatus('connected'),
        () => {
            ui.updateConnectionStatus('disconnected');
            setTimeout(startConnection, 3000); // Reconnect after 3 seconds
        },
        (err) => {
            console.error('[Frontend] WebSocket error:', err);
        }
    );
}

/**
 * UI Actions
 */
function generate() {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        showToast('WebSocket is not connected!', 'error');
        return;
    }

    const [width, height] = ui.elements.resolutionSelect.value.split('x').map(Number);
    const numOutputs = parseInt(ui.elements.numOutputsInput.value) || 1;

    const payload = {
        type: 'generate',
        prompt: currentMode === 'ez' ? ui.elements.promptInput.value : null,
        positive_prompt: currentMode === 'advanced' ? ui.elements.positivePromptInput.value || null : null,
        negative_prompt: currentMode === 'advanced' ? ui.elements.negPromptInput.value || null : null,
        steps: parseInt(ui.elements.stepsInput.value),
        cfg_scale: parseFloat(ui.elements.cfgScaleInput.value),
        width: width,
        height: height,
        num_outputs: numOutputs
    };

    console.log('[Frontend] Sending generation payload:', payload);

    ui.resetUI();
    ui.elements.generateBtn.disabled = true;
    socket.send(JSON.stringify(payload));
}

function saveImage() {
    const link = document.createElement('a');
    link.href = ui.elements.resultImage.src;
    link.download = `generated_${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function nextImage() {
    if (imageHistory.length === 0) return;
    currentRotationIndex = (currentRotationIndex + 1) % imageHistory.length;
    ui.updateImage(imageHistory[currentRotationIndex]);
    resetZoom();
}

function prevImage() {
    if (imageHistory.length === 0) return;
    currentRotationIndex = (currentRotationIndex - 1 + imageHistory.length) % imageHistory.length;
    ui.updateImage(imageHistory[currentRotationIndex]);
    resetZoom();
}

function zoomIn() {
    zoomLevel += 0.2;
    applyZoom(ui.elements.resultImage, zoomLevel);
}

function zoomOut() {
    if (zoomLevel > 0.4) {
        zoomLevel -= 0.2;
        applyZoom(ui.elements.resultImage, zoomLevel);
    }
}

function resetZoom() {
    zoomLevel = 1.0;
    applyZoom(ui.elements.resultImage, zoomLevel);
}

/**
 * Initialization
 */
function init() {
    // Tab switching
    ui.elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            ui.elements.tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMode = btn.dataset.mode;
            ui.setMode(currentMode);
        });
    });

    // Slider updates
    ui.elements.stepsInput.addEventListener('input', () => {
        ui.elements.stepsVal.textContent = ui.elements.stepsInput.value;
    });
    ui.elements.cfgScaleInput.addEventListener('input', () => {
        ui.elements.cfgVal.textContent = ui.elements.cfgScaleInput.value;
    });

    // Buttons
    ui.elements.generateBtn.addEventListener('click', generate);
    ui.elements.saveBtn.addEventListener('click', saveImage);
    ui.elements.prevBtn.addEventListener('click', prevImage);
    ui.elements.nextBtn.addEventListener('click', nextImage);

    // Mobile Menu Toggle
    ui.elements.menuToggle.addEventListener('click', () => {
        ui.toggleSettings();
    });

    // Close settings when clicking overlay
    ui.elements.overlay.addEventListener('click', () => {
        ui.toggleSettings();
    });

    // Keyboard
    window.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') prevImage();
        else if (e.key === 'ArrowRight') nextImage();
        else if (e.key === 'ArrowUp') zoomIn();
        else if (e.key === 'ArrowDown') zoomOut();
    });

    startConnection();
}

init();
