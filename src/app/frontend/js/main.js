import { connect } from './api.js';
import * as ui from './ui.js';
import { showToast, applyZoom } from './utils.js';
import { AppState } from './state.js';

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
            AppState.imageHistory = [...AppState.imageHistory, ...newImages];

            // Handle overflow: keep only the last MAX_IMAGES
            if (AppState.imageHistory.length > AppState.maxImages) {
                const overflow = AppState.imageHistory.length - AppState.maxImages;
                AppState.imageHistory = AppState.imageHistory.slice(overflow);
            }

            // Set current index to the first of the new images
            AppState.currentRotationIndex = AppState.imageHistory.length - newImages.length;
            ui.updateImage(AppState.imageHistory[AppState.currentRotationIndex]);

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
    AppState.socket = connect(
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
    if (!AppState.socket || AppState.socket.readyState !== WebSocket.OPEN) {
        showToast('WebSocket is not connected!', 'error');
        return;
    }

    const [width, height] = ui.elements.resolutionSelect.value.split('x').map(Number);
    const numOutputs = parseInt(ui.elements.numOutputsInput.value) || 1;

    const payload = {
        type: 'generate',
        prompt: AppState.currentMode === 'ez' ? ui.elements.promptInput.value : null,
        positive_prompt: AppState.currentMode === 'advanced' ? ui.elements.positivePromptInput.value || null : null,
        negative_prompt: AppState.currentMode === 'advanced' ? ui.elements.negPromptInput.value || null : null,
        steps: parseInt(ui.elements.stepsInput.value),
        cfg_scale: parseFloat(ui.elements.cfgScaleInput.value),
        width: width,
        height: height,
        num_outputs: numOutputs
    };

    console.log('[Frontend] Sending generation payload:', payload);

    ui.resetUI();
    ui.elements.generateBtn.disabled = true;
    AppState.socket.send(JSON.stringify(payload));
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
    if (AppState.imageHistory.length === 0) return;
    AppState.currentRotationIndex = (AppState.currentRotationIndex + 1) % AppState.imageHistory.length;
    ui.updateImage(AppState.imageHistory[AppState.currentRotationIndex]);
    resetZoom();
}

function prevImage() {
    if (AppState.imageHistory.length === 0) return;
    AppState.currentRotationIndex = (AppState.currentRotationIndex - 1 + AppState.imageHistory.length) % AppState.imageHistory.length;
    ui.updateImage(AppState.imageHistory[AppState.currentRotationIndex]);
    resetZoom();
}

function zoomIn() {
    AppState.zoomLevel += 0.2;
    applyZoom(ui.elements.resultImage, AppState.zoomLevel);
}

function zoomOut() {
    if (AppState.zoomLevel > 0.4) {
        AppState.zoomLevel -= 0.2;
        applyZoom(ui.elements.resultImage, AppState.zoomLevel);
    }
}

function resetZoom() {
    AppState.zoomLevel = 1.0;
    applyZoom(ui.elements.resultImage, AppState.zoomLevel);
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
            AppState.currentMode = btn.dataset.mode;
            ui.setMode(AppState.currentMode);
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
