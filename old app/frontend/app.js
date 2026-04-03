/**
 * Main Application
 * Orchestrates audio capture, transcription, and UI updates
 */

class TabTranscriberApp {
    constructor() {
        this.audioCaptureManager = null;
        this.audioVisualizer = null;
        this.transcriptManager = null;
        this.ws = null;
        this.isRunning = false;

        this.init();
    }

    /**
     * Initialize application
     */
    init() {
        console.log("🚀 Initializing Tab Transcriber...");

        // Initialize managers
        this.audioCaptureManager = new AudioCaptureManager();
        this.audioCaptureManager.setPreviewElement('sharedTabPreview');  // Set up video preview
        this.audioVisualizer = new AudioVisualizer('waveformCanvas');
        this.transcriptManager = new TranscriptManager('transcriptContainer');

        // Setup UI event listeners
        this.setupUIListeners();

        // Check health and initialize WebSocket
        this.checkHealth();
    }

    /**
     * Setup UI event listeners
     */
    setupUIListeners() {
        console.log("🔧 [App] Setting up UI listeners...");
        const shareTabBtn = document.getElementById('shareTabBtn');
        const uploadFileBtn = document.getElementById('uploadFileBtn');
        const stopBtn = document.getElementById('stopBtn');
        const exportTxtBtn = document.getElementById('exportTxtBtn');
        const exportSrtBtn = document.getElementById('exportSrtBtn');
        const clearBtn = document.getElementById('clearBtn');

        console.log("🔍 [App] Button elements found:");
        console.log("   shareTabBtn:", !!shareTabBtn);
        console.log("   uploadFileBtn:", !!uploadFileBtn);
        console.log("   stopBtn:", !!stopBtn);

        // Share Tab button
        if (shareTabBtn) {
            shareTabBtn.addEventListener('click', () => {
                console.log("🔘 [App] Share Tab button clicked");
                this.switchToLiveMode();
                this.startTranscription();
            });
            console.log("✅ [App] Share Tab button listener added");
        } else {
            console.error("❌ [App] Share Tab button not found!");
        }

        // Upload File button
        if (uploadFileBtn) {
            uploadFileBtn.addEventListener('click', () => {
                console.log("🔘 [App] Upload File button clicked");
                this.switchToFileMode();
            });
            console.log("✅ [App] Upload File button listener added");
        } else {
            console.error("❌ [App] Upload File button not found!");
        }

        stopBtn?.addEventListener('click', () => this.stopTranscription());
        exportTxtBtn?.addEventListener('click', () => this.exportTranscript('txt'));
        exportSrtBtn?.addEventListener('click', () => this.exportTranscript('srt'));
        clearBtn?.addEventListener('click', () => this.clearTranscript());
    }

    /**
     * Switch to live transcription mode
     */
    switchToLiveMode() {
        console.log("🔄 Switching to live mode...");
        document.getElementById('liveTabSection')?.classList.add('active');
        document.getElementById('fileUploadSection')?.classList.remove('active');
        document.getElementById('liveCaptionSection')?.style.removeProperty('display');
        document.getElementById('fileTranscriptSection')?.style.setProperty('display', 'none');
    }

    /**
     * Switch to file upload mode
     */
    switchToFileMode() {
        console.log("🔄 Switching to file upload mode...");
        document.getElementById('liveTabSection')?.classList.remove('active');
        document.getElementById('fileUploadSection')?.classList.add('active');
        document.getElementById('liveCaptionSection')?.style.setProperty('display', 'none');
        document.getElementById('fileTranscriptSection')?.style.removeProperty('display');
    }

    /**
     * Check backend health with retries
     */
    async checkHealth() {
        const maxRetries = 15;  // 15 retries = up to 15 seconds
        let retries = 0;
        const retryDelay = 1000;  // 1 second between retries

        const updateStatus = (msg) => {
            const statusEl = document.getElementById('loadingStatus');
            if (statusEl) statusEl.textContent = msg;
        };

        while (retries < maxRetries) {
            try {
                updateStatus(`Connecting to backend... (${retries + 1}/${maxRetries})`);
                const response = await fetch('/health', { timeout: 5000 });
                const health = await response.json();

                // Update status - with folder name for model
                const modelDisplay = health.model_loaded ? `✅ ${health.model_name || 'Loaded'}` : '⏳ Loading...';
                this.updateStatus('modelStatus', modelDisplay, health.model_loaded);
                this.updateStatus('gpuStatus', health.cuda_available ? '✅ CUDA Ready' : '💻 CPU Mode', health.cuda_available);
                this.updateStatus('connectionStatus', '🔌 Ready', true);

                console.log("✅ Backend health check passed");
                console.log(`   Model: ${health.model_loaded ? 'Loaded' : 'Not Loaded'}`);
                console.log(`   Device: ${health.device}`);
                console.log(`   CUDA: ${health.cuda_available ? 'Available' : 'Not Available'}`);

                // Hide loading overlay
                this.hideLoading();
                return;

            } catch (error) {
                retries++;
                if (retries < maxRetries) {
                    console.log(`⏳ Backend not ready, retrying... (${retries}/${maxRetries})`);
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                } else {
                    console.error("❌ Backend connection failed after retries");
                    updateStatus("Backend not responding. Check console.");
                    this.updateStatus('connectionStatus', '❌ Backend Error', false);
                }
            }
        }
    }

    /**
     * Hide loading overlay
     */
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.add('hidden');
            // Remove from DOM after animation
            setTimeout(() => {
                if (overlay && overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 300);
        }
    }

    /**
     * Start audio transcription
     */
    async startTranscription() {
        console.log("🎬 [App] Starting transcription...");

        try {
            // Start audio capture
            console.log("📊 [App] Calling audio capture...");
            const captureStarted = await this.audioCaptureManager.startCapture(
                (audioData) => this.onAudioData(audioData),
                (error) => this.onCaptureError(error)
            );

            if (!captureStarted) {
                console.error("❌ [App] Audio capture failed to start");
                this.updateStatus('audioStatus', '❌ Capture Failed', false);
                alert("Failed to start audio capture. Check console for details.");
                return;
            }

            console.log("✅ [App] Audio capture started, connecting WebSocket...");

            // Connect to WebSocket
            this.connectWebSocket();

            // Initialize visualizer
            const analyser = this.audioCaptureManager.getAnalyser();
            if (analyser) {
                this.audioVisualizer.init(analyser);
                this.audioVisualizer.start();
                console.log("✅ [App] Visualizer started");
            }

            // Update UI
            this.isRunning = true;
            document.getElementById('shareTabBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            this.updateStatus('audioStatus', '🔴 Recording', true);

            console.log("✅ [App] Transcription started successfully");

        } catch (error) {
            console.error("❌ [App] Failed to start transcription:", error);
            this.updateStatus('audioStatus', '❌ Error', false);
            alert("Error: " + error.message);
        }
    }

    /**
     * Stop audio transcription
     */
    stopTranscription() {
        console.log("⏹️ Stopping transcription...");

        // Stop audio capture
        this.audioCaptureManager.stopCapture();

        // Close WebSocket
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        // Stop visualizer
        this.audioVisualizer.stop();

        // Update UI
        this.isRunning = false;
        document.getElementById('shareTabBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        this.updateStatus('audioStatus', '⏸️ Stopped', false);

        // Update live caption
        const liveCaption = document.getElementById('liveCaption');
        liveCaption.innerHTML = '<span class="placeholder">Ready to capture...</span>';

        console.log("✅ Transcription stopped");
    }

    /**
     * Connect to WebSocket
     */
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/transcribe`;

        console.log(`🔗 [App] Connecting to WebSocket: ${wsUrl}`);

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log("✅ [App] WebSocket connected");
            this.updateStatus('connectionStatus', '🔌 Connected', true);
        };

        this.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                console.log(`📨 [App] Received message:`, message.type);
                this.handleWebSocketMessage(message);
            } catch (error) {
                console.error("❌ [App] Failed to parse WebSocket message:", error);
                console.error("   Raw data:", event.data);
            }
        };

        this.ws.onerror = (error) => {
            console.error("❌ [App] WebSocket error:", error);
            this.updateStatus('connectionStatus', '❌ Disconnected', false);
        };

        this.ws.onclose = (event) => {
            console.log("🔌 [App] WebSocket closed", event);
            this.updateStatus('connectionStatus', '⏸️ Disconnected', false);
        };
    }

    /**
     * Handle audio data from capture
     */
    onAudioData(audioData) {
        if (!this.ws) {
            console.error("❌ [App] WebSocket is null");
            return;
        }

        const readyState = this.ws.readyState;
        const readyStateMap = {
            0: 'CONNECTING',
            1: 'OPEN',
            2: 'CLOSING',
            3: 'CLOSED'
        };

        console.debug(`📤 [App] WebSocket state: ${readyStateMap[readyState]} (${readyState})`);

        if (readyState !== WebSocket.OPEN) {
            console.warn(`⚠️ [App] WebSocket not ready (${readyStateMap[readyState]}), dropping audio chunk`);
            return;
        }

        try {
            console.debug(`📤 [App] Sending ${audioData.length} audio samples to backend...`);
            
            // Send audio data to backend
            this.ws.send(audioData);
            
            console.debug(`✅ [App] Successfully sent ${audioData.length} samples`);
        } catch (error) {
            console.error("❌ [App] Failed to send audio:", error);
            console.error("   Error message:", error.message);
            console.error("   WebSocket state:", readyStateMap[this.ws.readyState]);
        }
    }

    /**
     * Handle capture error
     */
    onCaptureError(error) {
        console.error("❌ Audio capture error:", error);
        
        if (error.name === 'NotAllowedError') {
            console.log("   User denied permission or closed dialog");
        } else if (error.name === 'NotFoundError') {
            console.log("   No input device found");
        }

        this.stopTranscription();
    }

    /**
     * Handle WebSocket messages
     */
    handleWebSocketMessage(message) {
        console.log(`📨 [App] WebSocket message received:`, message);
        
        if (message.type === 'caption') {
            console.log(`💬 [App] Caption message:`, message.text);
            this.handleCaption(message);
        } else if (message.type === 'audio_level') {
            console.log(`📊 [App] Audio level:`, message.level);
            this.handleAudioLevel(message);
        } else if (message.type === 'status') {
            console.log(`ℹ️ [App] Status message:`, message.status);
            this.handleStatusMessage(message);
        } else {
            console.warn(`⚠️ [App] Unknown message type:`, message.type);
        }
    }

    /**
     * Handle caption message
     */
    handleCaption(message) {
        const text = message.text?.trim();
        console.log(`🔤 [App] Caption text:`, text);

        if (!text) {
            console.warn(`⚠️ [App] Empty caption text`);
            return;
        }

        console.log(`✅ [App] Adding caption to transcript:`, text);

        // Update live caption
        const liveCaption = document.getElementById('liveCaption');
        if (liveCaption) {
            liveCaption.innerHTML = `<span>${this.escapeHtml(text)}</span>`;
            console.log(`✏️ [App] Updated live caption element`);
        } else {
            console.error(`❌ [App] Live caption element not found`);
        }

        // Add to transcript
        this.transcriptManager.addItem(text, {
            language: message.language,
            confidence: message.confidence,
            timestamp: message.timestamp,
            chunk_id: message.chunk_id
        });
        console.log(`📝 Caption added to transcript: ${text}`);
    }

    /**
     * Handle audio level message
     */
    handleAudioLevel(message) {
        const level = message.level || 0;

        // Update level bar
        const levelBar = document.getElementById('levelBar');
        levelBar.style.width = level + '%';

        // Update level text
        document.getElementById('levelValue').textContent = level;

        // Update audio status
        if (level > 20) {
            this.updateStatus('audioStatus', '🔴 Audio Detected', true);
        } else if (level > 5) {
            this.updateStatus('audioStatus', '🟡 Low Audio', true);
        } else {
            this.updateStatus('audioStatus', '🔵 Silence', false);
        }
    }

    /**
     * Handle status message from backend
     */
    handleStatusMessage(message) {
        if (message.model_loaded !== undefined) {
            this.updateStatus('modelStatus', message.model_loaded ? '✅ Loaded' : '⏳ Loading...', message.model_loaded);
        }

        if (message.cuda_available !== undefined) {
            this.updateStatus('gpuStatus', message.cuda_available ? '✅ CUDA Ready' : '💻 CPU Mode', message.cuda_available);
        }
    }

    /**
     * Export transcript
     */
    exportTranscript(format) {
        if (this.transcriptManager.getItems().length === 0) {
            alert('No transcript to export');
            return;
        }

        let content, filename, mimeType;

        if (format === 'txt') {
            content = this.transcriptManager.exportAsText();
            filename = `transcript_${new Date().getTime()}.txt`;
            mimeType = 'text/plain';
        } else if (format === 'srt') {
            content = this.transcriptManager.exportAsSRT();
            filename = `transcript_${new Date().getTime()}.srt`;
            mimeType = 'text/plain';
        }

        this.transcriptManager.downloadFile(content, filename, mimeType);
        console.log(`📥 Exported as ${format.toUpperCase()}: ${filename}`);
    }

    /**
     * Clear transcript
     */
    clearTranscript() {
        if (confirm('Are you sure you want to clear the transcript?')) {
            this.transcriptManager.clear();
            const liveCaption = document.getElementById('liveCaption');
            liveCaption.innerHTML = '<span class="placeholder">Waiting for audio...</span>';
            console.log("🗑️ Transcript cleared");
        }
    }

    /**
     * Update status indicator
     */
    updateStatus(elementId, text, isActive) {
        const el = document.getElementById(elementId);
        if (el) {
            el.textContent = text;
            el.className = 'status-value ' + (isActive ? 'success' : 'warning');
        }
    }

    /**
     * Escape HTML special characters
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new TabTranscriberApp();
    console.log("✅ Application ready");
});
