/**
 * Visualization Module
 * Handles waveform and audio level visualization
 */

class AudioVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.canvasCtx = this.canvas.getContext('2d');
        this.analyser = null;
        this.dataArray = null;
        this.animationId = null;
        this.isAnimating = false;

        // Set canvas resolution
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }

    /**
     * Resize canvas to fit container
     */
    resizeCanvas() {
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.canvasCtx.scale(window.devicePixelRatio, window.devicePixelRatio);
    }

    /**
     * Initialize with analyser node
     */
    init(analyser) {
        this.analyser = analyser;
        if (this.analyser) {
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        }
    }

    /**
     * Start drawing waveform
     */
    start() {
        if (this.isAnimating) return;
        this.isAnimating = true;
        this.draw();
    }

    /**
     * Stop drawing waveform
     */
    stop() {
        this.isAnimating = false;
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        this.clear();
    }

    /**
     * Draw waveform
     */
    draw() {
        if (!this.isAnimating) return;

        const width = this.canvas.width;
        const height = this.canvas.height;

        // Clear canvas
        this.canvasCtx.fillStyle = 'rgba(240, 249, 255, 0.5)';
        this.canvasCtx.fillRect(0, 0, width, height);

        if (!this.analyser || !this.dataArray) {
            this.animationId = requestAnimationFrame(() => this.draw());
            return;
        }

        // Get frequency data
        this.analyser.getByteFrequencyData(this.dataArray);

        // Draw waveform
        const barWidth = (width / this.dataArray.length) * 2.5;
        let barHeight;
        let x = 0;

        this.canvasCtx.fillStyle = 'rgb(37, 99, 235)';
        this.canvasCtx.globalAlpha = 0.8;

        for (let i = 0; i < this.dataArray.length; i++) {
            barHeight = (this.dataArray[i] / 255) * height * 0.8;

            this.canvasCtx.fillRect(x, height - barHeight, barWidth, barHeight);
            x += barWidth + 1;
        }

        this.canvasCtx.globalAlpha = 1.0;

        // Draw center line
        this.canvasCtx.strokeStyle = 'rgba(37, 99, 235, 0.3)';
        this.canvasCtx.lineWidth = 1;
        this.canvasCtx.beginPath();
        this.canvasCtx.moveTo(0, height / 2);
        this.canvasCtx.lineTo(width, height / 2);
        this.canvasCtx.stroke();

        this.animationId = requestAnimationFrame(() => this.draw());
    }

    /**
     * Clear canvas
     */
    clear() {
        const width = this.canvas.width;
        const height = this.canvas.height;
        this.canvasCtx.fillStyle = 'rgba(224, 242, 254, 0.3)';
        this.canvasCtx.fillRect(0, 0, width, height);

        // Draw idle state
        this.canvasCtx.strokeStyle = 'rgba(156, 163, 175, 0.3)';
        this.canvasCtx.lineWidth = 2;
        this.canvasCtx.beginPath();
        this.canvasCtx.moveTo(0, height / 2);
        this.canvasCtx.lineTo(width, height / 2);
        this.canvasCtx.stroke();
    }
}

/**
 * Transcript Manager
 * Handles transcript history and export
 */
class TranscriptManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.items = [];
        this.itemCount = 0;
    }

    /**
     * Add transcript item
     */
    addItem(text, metadata = {}) {
        this.itemCount++;

        const item = {
            id: this.itemCount,
            text: text,
            timestamp: metadata.timestamp || new Date().toLocaleTimeString(),
            language: metadata.language || 'unknown',
            confidence: metadata.confidence || 0,
            chunkId: metadata.chunk_id || 0
        };

        this.items.push(item);
        this.renderItem(item);

        // Auto-scroll if enabled
        if (document.getElementById('autoScrollCheckbox')?.checked) {
            this.container.scrollTop = this.container.scrollHeight;
        }

        return item;
    }

    /**
     * Render transcript item to DOM
     */
    renderItem(item) {
        // Remove empty message if present
        const emptyMsg = this.container.querySelector('.empty-message');
        if (emptyMsg) {
            emptyMsg.remove();
        }

        // Create item element
        const itemEl = document.createElement('div');
        itemEl.className = 'transcript-item';
        itemEl.id = `transcript-${item.id}`;

        const textEl = document.createElement('div');
        textEl.className = 'transcript-item-text';
        textEl.textContent = item.text;

        const metaEl = document.createElement('div');
        metaEl.className = 'transcript-item-meta';

        if (document.getElementById('timestampCheckbox')?.checked) {
            const timeSpan = document.createElement('span');
            timeSpan.textContent = `⏱️ ${item.timestamp}`;
            metaEl.appendChild(timeSpan);
        }

        const langSpan = document.createElement('span');
        langSpan.textContent = `🌐 ${item.language.toUpperCase()}`;
        metaEl.appendChild(langSpan);

        const confSpan = document.createElement('span');
        confSpan.textContent = `✓ ${(item.confidence * 100).toFixed(0)}%`;
        metaEl.appendChild(confSpan);

        itemEl.appendChild(textEl);
        itemEl.appendChild(metaEl);
        this.container.appendChild(itemEl);
    }

    /**
     * Export transcript as TXT
     */
    exportAsText() {
        let content = 'Tab Audio Transcript\n';
        content += `Generated: ${new Date().toLocaleString()}\n`;
        content += '=' .repeat(50) + '\n\n';

        this.items.forEach((item, idx) => {
            content += `[${item.timestamp}] ${item.text}\n`;
        });

        return content;
    }

    /**
     * Export transcript as SRT (SubRip)
     */
    exportAsSRT() {
        let content = '';
        const itemsPerSubtitle = Math.ceil(this.items.length / 10) || 1;

        this.items.forEach((item, idx) => {
            const subtitleNum = Math.floor(idx / itemsPerSubtitle) + 1;
            const startTime = this.indexToTimecode(idx * itemsPerSubtitle);
            const endTime = this.indexToTimecode((idx + 1) * itemsPerSubtitle);

            if (idx % itemsPerSubtitle === 0) {
                if (idx > 0) content += '\n';
                content += `${subtitleNum}\n`;
                content += `${startTime} --> ${endTime}\n`;
            }

            content += item.text + ' ';
        });

        content += '\n';
        return content;
    }

    /**
     * Convert index to SRT timecode
     */
    indexToTimecode(index) {
        const seconds = index * 5; // 5 seconds per item
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')},000`;
    }

    /**
     * Download file
     */
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    /**
     * Clear all items
     */
    clear() {
        this.items = [];
        this.itemCount = 0;
        this.container.innerHTML = '<div class="empty-message">Transcript will appear here...</div>';
    }

    /**
     * Get all items
     */
    getItems() {
        return this.items;
    }
}

// Export as globals
window.AudioVisualizer = AudioVisualizer;
window.TranscriptManager = TranscriptManager;
