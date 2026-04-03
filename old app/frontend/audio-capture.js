/**
 * Audio Capture Module
 * Handles browser tab audio sharing via Web Audio API
 */

class AudioCaptureManager {
    constructor() {
        this.mediaStream = null;
        this.audioContext = null;
        this.analyser = null;
        this.processor = null;
        this.isCapturing = false;
        this.audioBuffer = new Float32Array(0);
        this.onAudioData = null;
        this.onError = null;
        this.previewElement = null;  // For video preview
    }

    /**
     * Set preview element for displaying shared tab
     */
    setPreviewElement(elementId) {
        this.previewElement = document.getElementById(elementId);
        if (!this.previewElement) {
            console.warn("⚠️ [AudioCapture] Preview element not found:", elementId);
        }
    }

    /**
     * Start capturing audio from selected browser tab
     * Uses getDisplayMedia() to capture tab audio
     */
    async startCapture(onAudioCallback, onErrorCallback) {
        try {
            console.log("🎬 [AudioCapture] Starting capture...");
            this.onAudioData = onAudioCallback;
            this.onError = onErrorCallback;

            // Check if getDisplayMedia is supported
            if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
                throw new Error("getDisplayMedia not supported in this browser. Use Chrome, Edge, or Firefox.");
            }

            console.log("📡 [AudioCapture] Requesting display media with audio and video...");
            
            // Request both audio and video (required by most browsers)
            // We'll immediately stop the video track and keep only audio
            const mediaStream = await navigator.mediaDevices.getDisplayMedia({
                audio: true,
                video: { 
                    cursor: "never"  // Minimize video quality since we don't need it
                }
            });

            console.log("✅ [AudioCapture] Display media obtained");
            
            // Display video preview if element is available (like Google Meet)
            if (this.previewElement && mediaStream.getVideoTracks().length > 0) {
                console.log("📺 [AudioCapture] Setting up video preview...");
                this.previewElement.srcObject = mediaStream;
                this.previewElement.style.display = 'block';
                
                // Hide placeholder message
                const placeholder = document.getElementById('noPreviewMessage');
                if (placeholder) {
                    placeholder.style.display = 'none';
                }
            } else if (mediaStream.getVideoTracks().length === 0) {
                console.warn("⚠️ [AudioCapture] No video track available for preview");
            }

            this.mediaStream = mediaStream;

            // Set up audio context
            console.log("🔧 [AudioCapture] Setting up audio context...");
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });

            // Create source from media stream
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            console.log("✅ [AudioCapture] Media stream source created");

            // Add Gain Node for hardware-level boost
            const gainNode = this.audioContext.createGain();
            gainNode.gain.value = 20.0; // 20x hardware boost at the source (up from 10x)
            console.log("🔊 [AudioCapture] Source gain set to 20.0x");

            // Create analyser for visualization
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 2048;

            // Create script processor for audio chunks
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

            // Connect nodes
            source.connect(gainNode);
            gainNode.connect(this.processor);
            gainNode.connect(this.analyser); // Connect to analyser AFTER boost
            this.processor.connect(this.audioContext.destination);

            console.log("✅ [AudioCapture] Audio graph connected");

            // Handle audio data
            this.processor.onaudioprocess = (event) => {
                const inputData = event.inputBuffer.getChannelData(0);
                
                // Convert to Float32Array
                const audioData = new Float32Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    audioData[i] = inputData[i];
                }

                // Send to callback
                if (this.onAudioData) {
                    this.onAudioData(audioData);
                }
            };

            // Handle stream end
            this.mediaStream.getTracks().forEach(track => {
                track.onended = () => {
                    console.log("⏹️ [AudioCapture] Media stream ended");
                    this.stopCapture();
                };
            });

            this.isCapturing = true;
            console.log("✅ [AudioCapture] Audio capture started successfully");
            return true;

        } catch (error) {
            console.error("❌ [AudioCapture] Capture failed:", error);
            console.error("   Error name:", error.name);
            console.error("   Error message:", error.message);
            
            // Provide helpful error messages
            if (error.name === "NotSupportedError") {
                console.error("   💡 HINT: Your browser doesn't support getDisplayMedia for tab audio.");
                console.error("   Try: Chrome 72+, Edge 79+, or Firefox 66+");
            } else if (error.name === "NotAllowedError") {
                console.error("   💡 HINT: Permission denied. Click 'Share Tab & Start' and select a tab to share.");
            } else if (error.name === "TypeError") {
                console.error("   💡 HINT: Browser requires both audio AND video. Make sure to share a tab.");
            }
            
            if (this.onError) {
                this.onError(error);
            }
            return false;
        }
    }

    /**
     * Stop capturing audio
     */
    stopCapture() {
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        // Stop video preview
        if (this.previewElement) {
            this.previewElement.srcObject = null;
            this.previewElement.style.display = 'none';
            
            // Show placeholder message
            const placeholder = document.getElementById('noPreviewMessage');
            if (placeholder) {
                placeholder.style.display = 'flex';
            }
        }

        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }

        if (this.analyser) {
            this.analyser.disconnect();
            this.analyser = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        this.isCapturing = false;
        console.log("⏹️ Audio capture stopped");
    }

    /**
     * Get analyser for visualization
     */
    getAnalyser() {
        return this.analyser;
    }

    /**
     * Get audio context
     */
    getAudioContext() {
        return this.audioContext;
    }

    /**
     * Check if currently capturing
     */
    getIsCapturing() {
        return this.isCapturing;
    }
}

// Export as global
window.AudioCaptureManager = AudioCaptureManager;
