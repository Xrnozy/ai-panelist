/**
 * File Upload and Transcription Handler
 * Manages drag-and-drop, file validation, and transcription of audio files
 */

class FileUploadManager {
    constructor() {
        this.currentFile = null;
        this.abortController = null;
        this.currentTranscript = null;
        this.currentLanguage = null;
        this.initializeElements();
        this.attachEventListeners();
    }

    initializeElements() {
        // Main elements
        this.dropZone = document.getElementById('dropZone');
        this.fileInput = document.getElementById('fileInput');
        this.uploadProgress = document.getElementById('uploadProgress');

        // File info
        this.uploadFileName = document.getElementById('uploadFileName');
        this.uploadFileSize = document.getElementById('uploadFileSize');

        // Progress
        this.progressText = document.querySelector('#progressText');
        this.progressFill = document.getElementById('progressFill');

        // Transcript display
        this.fileTranscriptText = document.getElementById('fileTranscriptText');
        this.transcriptLanguage = document.getElementById('transcriptLanguage');
        this.transcriptConfidence = document.getElementById('transcriptConfidence');
        this.fileTranscriptSection = document.getElementById('fileTranscriptSection');

        // Buttons
        this.cancelUploadBtn = document.getElementById('cancelUploadBtn');
    }

    attachEventListeners() {
        // Drag and drop
        if (!this.dropZone) {
            console.error('❌ [FileUpload] Drop zone element not found');
            return;
        }

        console.log('✅ [FileUpload] Attaching drag-drop event listeners to drop zone');
        this.dropZone.addEventListener('dragover', (e) => {
            console.log('📤 [FileUpload] Drag over detected');
            this.handleDragOver(e);
        });
        this.dropZone.addEventListener('dragleave', (e) => {
            console.log('📤 [FileUpload] Drag leave detected');
            this.handleDragLeave(e);
        });
        this.dropZone.addEventListener('drop', (e) => {
            console.log('📥 [FileUpload] Drop detected, files:', e.dataTransfer?.files?.length);
            this.handleDrop(e);
        });
        this.dropZone.addEventListener('click', () => {
            console.log('🖱️ [FileUpload] Drop zone clicked, opening file picker');
            this.fileInput.click();
        });
        
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                console.log('📋 [FileUpload] File input changed, file:', file?.name, 'size:', file?.size);
                if (file) this.handleFileSelect(file);
            });
        }

        // Button events
        if (this.cancelUploadBtn) {
            this.cancelUploadBtn.addEventListener('click', () => this.cancelUpload());
        }

        if (this.copyTranscriptBtn) {
            console.warn('⚠️ [FileUpload] copyTranscriptBtn found but not used');
        }
        
        console.log('✅ [FileUpload] All event listeners attached successfully');
    }

    // ========== Drag and Drop Handlers ==========
    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        this.dropZone.classList.add('drag-over');
        console.log('🎯 [FileUpload] Drop zone activated');
    }

    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        this.dropZone.classList.remove('drag-over');
        console.log('🎯 [FileUpload] Drop zone deactivated');
    }

    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        this.dropZone.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        console.log('📥 [FileUpload] Drop handler triggered, files:', files.length);
        if (files.length > 0) {
            console.log('📄 [FileUpload] Processing dropped file:', files[0].name);
            this.handleFileSelect(files[0]);
        } else {
            console.warn('⚠️ [FileUpload] No files in drop event');
        }
    }

    // ========== File Handling ==========
    handleFileSelect(file) {
        if (!file) {
            console.warn('⚠️ [FileUpload] No file provided');
            return;
        }

        console.log('📄 [FileUpload] Handling file select:', {
            name: file.name,
            size: file.size,
            type: file.type,
            lastModified: file.lastModified
        });

        // Validate file
        if (!this.isValidAudioFile(file)) {
            console.error('❌ [FileUpload] Invalid file type:', file.type, 'Extension:', file.name.split('.').pop());
            this.showError(`Invalid file type. Supported formats: MP3, WAV, M4A, FLAC, OGG, AAC, WMA, OPUS`);
            return;
        }

        console.log('✅ [FileUpload] File format is valid');

        if (file.size > 500 * 1024 * 1024) {
            console.error('❌ [FileUpload] File too large:', file.size, 'bytes (max 500MB)');
            this.showError('File is too large (max 500MB)');
            return;
        }

        console.log('✅ [FileUpload] File size is valid:', (file.size / 1024 / 1024).toFixed(2), 'MB');

        this.currentFile = file;
        console.log('🚀 [FileUpload] Starting file upload...');
        this.uploadFile(file);
    }

    isValidAudioFile(file) {
        const supportedTypes = [
            'audio/mpeg', 'audio/mp3',
            'audio/wav', 'audio/wave',
            'audio/mp4', 'audio/x-m4a',
            'audio/flac',
            'audio/ogg',
            'audio/aac',
            'audio/x-aac',
            'audio/x-wav',
            'audio/x-opus'
        ];

        const supportedExtensions = [
            '.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus'
        ];

        const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        return supportedTypes.includes(file.type) || supportedExtensions.includes(ext);
    }

    // ========== Upload and Transcription ==========
    async uploadFile(file) {
        console.log('📤 [FileUpload] uploadFile() called for:', file.name);
        
        // Reset states
        this.abortController = new AbortController();
        console.log('✅ [FileUpload] AbortController created');
        
        if (!this.uploadProgress) {
            console.error('❌ [FileUpload] uploadProgress element not found!');
            return;
        }
        
        this.uploadProgress.style.display = 'block';
        console.log('✅ [FileUpload] Progress display shown');
        
        this.dropZone.style.display = 'none';
        console.log('✅ [FileUpload] Drop zone hidden');

        try {
            // Update file info
            if (this.uploadFileName) {
                this.uploadFileName.textContent = file.name;
                console.log('✅ [FileUpload] File name set:', file.name);
            }
            if (this.uploadFileSize) {
                this.uploadFileSize.textContent = this.formatFileSize(file.size);
                console.log('✅ [FileUpload] File size set:', this.formatFileSize(file.size));
            }
            this.updateProgressStatus('Preparing file...', 0);

            // Create FormData
            const formData = new FormData();
            formData.append('file', file);
            console.log('✅ [FileUpload] FormData created with file');

            // Upload and transcribe
            console.log('📡 [FileUpload] Sending POST request to /api/transcribe-file');
            const response = await fetch('/api/transcribe-file', {
                method: 'POST',
                body: formData,
                signal: this.abortController.signal
            });
            
            console.log('📡 [FileUpload] Response received, status:', response.status);

            if (!response.ok) {
                const error = await response.json();
                console.error('❌ [FileUpload] Server error response:', error);
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('✅ [FileUpload] Response parsed successfully:', result);

            if (result.status === 'success') {
                console.log('✅ [FileUpload] Transcription successful!');
                
                // Store transcript
                this.currentTranscript = result.text;
                this.currentLanguage = result.language;
                console.log('📝 [FileUpload] Transcript stored:', {
                    length: result.text.length,
                    language: result.language,
                    confidence: result.confidence
                });

                // Display results
                this.displayTranscript(result);
                this.updateProgressStatus('Transcription complete!', 100);

                setTimeout(() => {
                    this.uploadProgress.style.display = 'none';
                    if (this.fileTranscriptSection) {
                        this.fileTranscriptSection.style.display = 'block';
                    }
                    console.log('✅ [FileUpload] UI updated to show results');
                }, 500);
            } else {
                console.error('❌ [FileUpload] Transcription failed:', result.error);
                throw new Error(result.error || 'Transcription failed');
            }

        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('❌ [FileUpload] Upload error:', error.message);
                this.showError(`Error: ${error.message}`);
            } else {
                console.log('⚠️ [FileUpload] Upload cancelled by user');
            }
        }
    }

    displayTranscript(result) {
        // Update language and confidence badges
        const langMap = {
            'en': '🇺🇸 English',
            'tl': '🇵🇭 Tagalog',
            'other': '🌐 Other',
            'unknown': '❓ Unknown'
        };

        this.transcriptLanguage.textContent = langMap[result.language] || result.language;
        this.transcriptLanguage.className = `lang-badge lang-${result.language}`;

        const confidence = Math.round((result.confidence || 0) * 100);
        this.transcriptConfidence.textContent = `${confidence}% confidence`;

        // Display full transcript text (support long files/podcasts)
        const lines = result.text.split('\n').filter(line => line.trim());
        this.fileTranscriptText.innerHTML = lines
            .map((line, idx) => `<p class="transcript-line">${this.escapeHtml(line)}</p>`)
            .join('');

        // Store full text for copy functionality
        this.fileTranscriptText.dataset.fullText = result.text;
        console.log(`✅ [FileUpload] Full transcript stored (${result.text.length} characters)`);

        // Show copy button
        const copyBtn = document.getElementById('copyTranscriptBtn');
        if (copyBtn) {
            copyBtn.style.display = 'inline-flex';
            console.log('✅ [FileUpload] Copy button shown');
        }

        // Also add to transcript history
        const container = document.getElementById('transcriptContainer');
        if (container) {
            const timestamp = new Date().toLocaleTimeString();
            const item = document.createElement('div');
            item.className = 'transcript-item';
            const preview = result.text.substring(0, 200);
            const duration = result.duration_seconds ? ` • ${(result.duration_seconds / 60).toFixed(1)} min` : '';
            item.innerHTML = `
                <div class="transcript-item-text">${this.escapeHtml(preview)}${result.text.length > 200 ? '...' : ''}</div>
                <div class="transcript-item-meta">📁 ${result.filename || 'Uploaded file'}${duration} • ${timestamp}</div>
            `;
            container.appendChild(item);

            // Scroll to bottom
            container.scrollTop = container.scrollHeight;
        }
    }

    // ========== Progress Updates ==========
    updateProgressStatus(message, percent) {
        this.progressText.textContent = message;
        this.progressFill.style.width = `${Math.min(100, percent)}%`;
    }

    // ========== Cancel Upload ==========
    cancelUpload() {
        if (this.abortController) {
            this.abortController.abort();
        }
        this.resetUpload();
    }

    // ========== Download Functions ==========
    downloadTranscript(format) {
        if (!this.currentTranscript) return;

        let content = this.currentTranscript;
        let filename = `transcript_${new Date().toISOString().split('T')[0]}`;

        if (format === 'srt') {
            content = this.generateSRT(this.currentTranscript);
            filename += '.srt';
        } else {
            filename += '.txt';
        }

        // Create blob and download
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    generateSRT(text) {
        // Simple SRT generation - split by sentences
        const sentences = text.match(/[^.!?]+[.!?]+/g) || [text];
        let srtContent = '';
        let timeMs = 0;
        const wordsPerSecond = 150 / 60; // Average speech rate

        sentences.forEach((sentence, idx) => {
            const words = sentence.trim().split(/\s+/).length;
            const duration = Math.max(1, Math.round((words / wordsPerSecond) * 1000));

            const startTime = this.msToSRT(timeMs);
            const endTime = this.msToSRT(timeMs + duration);

            srtContent += `${idx + 1}\n`;
            srtContent += `${startTime} --> ${endTime}\n`;
            srtContent += `${sentence.trim()}\n\n`;

            timeMs += duration;
        });

        return srtContent;
    }

    msToSRT(ms) {
        const totalSeconds = Math.floor(ms / 1000);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        const milliseconds = ms % 1000;

        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')},${String(milliseconds).padStart(3, '0')}`;
    }

    // ========== Copy to Clipboard ==========
    copyTranscript() {
        if (!this.currentTranscript) {
            console.warn('⚠️ [FileUpload] No transcript to copy');
            return;
        }

        // Use the full text from data attribute if available
        const fullText = this.fileTranscriptText.dataset.fullText || this.currentTranscript;
        
        navigator.clipboard.writeText(fullText).then(() => {
            console.log(`✅ [FileUpload] Copied ${fullText.length} characters to clipboard`);
            const btn = document.getElementById('copyTranscriptBtn');
            if (btn) {
                const original = btn.textContent;
                btn.textContent = '✅ Copied!';
                setTimeout(() => {
                    btn.textContent = original;
                }, 2000);
            }
        }).catch(err => {
            console.error('❌ [FileUpload] Copy failed:', err);
            alert('Failed to copy transcript. Try using Export instead.');
        });
    }

    // ========== Reset and Cleanup ==========
    resetUpload() {
        this.currentFile = null;
        this.currentTranscript = null;
        this.currentLanguage = null;
        this.fileInput.value = '';
        this.uploadProgress.style.display = 'none';
        this.fileTranscriptSection.style.display = 'none';
        this.dropZone.style.display = 'block';

        // Reset progress
        this.progressFill.style.width = '0%';
        this.progressText.textContent = 'Processing...';
        this.uploadFileName.textContent = '-';
        this.uploadFileSize.textContent = '-';
    }

    // ========== Error Handling ==========
    showError(message) {
        console.error(`❌ ${message}`);
        
        // Ensure upload progress is visible
        this.uploadProgress.style.display = 'block';
        this.dropZone.style.display = 'none';
        
        // Show error in progress text
        this.progressText.textContent = `❌ ${message}`;
        this.progressFill.style.width = '0%';

        // Reset after 5 seconds
        setTimeout(() => {
            this.resetUpload();
        }, 5000);
    }

    // ========== Utility Functions ==========
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.round(seconds % 60);

        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    }

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

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 [FileUpload] Initializing FileUploadManager...');
    try {
        const uploadManager = new FileUploadManager();
        window.fileUploadManager = uploadManager;
        console.log('✅ [FileUpload] File upload manager initialized successfully');
        
        // Setup copy button listener
        const copyBtn = document.getElementById('copyTranscriptBtn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                uploadManager.copyTranscript();
            });
            console.log('✅ [FileUpload] Copy button listener attached');
        }
        
        // Verify drop zone is accessible
        if (uploadManager.dropZone) {
            console.log('✅ [FileUpload] Drop zone is accessible');
        } else {
            console.error('❌ [FileUpload] Drop zone element not found!');
        }
    } catch (error) {
        console.error('❌ [FileUpload] Error initializing FileUploadManager:', error);
    }
});
