// TubeFetch Async Download Logic

let progressModal;
let activeInterval = null;

document.addEventListener('DOMContentLoaded', function() {
    progressModal = new bootstrap.Modal(document.getElementById('progressModal'));
    hideInvalidFormats();
});

/**
 * Defensive check to hide any formats that appear broken or zero-size
 */
function hideInvalidFormats() {
    // Select elements that might contain filesize texts
    // This is broad, but we can target specific list items
    const listItems = document.querySelectorAll('.list-group-item');
    
    listItems.forEach(item => {
        const text = item.innerText || item.textContent;
        // Check for 0 B, 0 KB, etc.
        // Regex: 0\.?0?\s*(B|KB|MB|GB) inside the text
        if (/(^|\s)0\.?0?\s*(B|KB|MB|GB)/i.test(text) || text.includes('Unknown')) {
            // Check if it's actually describing a filesize
            // The template uses format: "MP4 • 0.0 B" or similar
            if (item.querySelector('.text-muted')?.textContent.includes('0.0 B')) {
                console.warn('Hiding invalid format item:', text);
                item.style.display = 'none';
            }
        }
    });
}

/**
 * Initiate a download job
 * @param {string} url - YouTube URL
 * @param {string} formatId - Format ID for single download
 * @param {string} mode - 'single' or 'merge'
 * @param {string} audioFormatId - Optional audio format ID for merge
 */
async function initiateDownload(url, formatId, mode = 'single', audioFormatId = null) {
    if (activeInterval) clearInterval(activeInterval);
    
    // Show modal
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.getElementById('progress-text');
    progressBar.style.width = '0%';
    progressBar.className = 'progress-bar bg-primary';
    progressText.textContent = 'Starting job...';
    progressModal.show();

    try {
        const payload = {
            url: url,
            mode: mode,
            format_id: formatId
        };
        
        if (mode === 'merge') {
            payload.video_format_id = formatId;
            payload.audio_format_id = audioFormatId;
        }

        const response = await fetch('/api/download/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error('Failed to start download');
        
        const data = await response.json();
        const jobId = data.job_id;
        
        startPolling(jobId);

    } catch (e) {
        console.error(e);
        progressText.textContent = 'Error starting download.';
        progressBar.classList.add('bg-danger');
    }
}

function startPolling(jobId) {
    activeInterval = setInterval(async () => {
        try {
            const res = await fetch(`/api/download/status/${jobId}`);
            if (!res.ok) return; // Retry next tick
            
            const status = await res.json();
            updateUI(status);
            
            if (status.status === 'completed') {
                clearInterval(activeInterval);
                triggerFileDownload(jobId);
            } else if (status.status === 'error') {
                clearInterval(activeInterval);
                // Error handled in updateUI
            }
            
        } catch (e) {
            console.error("Polling error", e);
        }
    }, 1000); // 1-second polling
}

function updateUI(status) {
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.getElementById('progress-text');
    
    if (status.progress) {
        progressBar.style.width = `${status.progress}%`;
    }
    
    if (status.status_text) {
        progressText.textContent = status.status_text;
    }
    
    if (status.status === 'error') {
        progressBar.classList.remove('bg-primary');
        progressBar.classList.add('bg-danger');
        progressText.textContent = `Error: ${status.error || 'Unknown error'}`;
    } else if (status.status === 'completed') {
        progressBar.classList.remove('bg-primary');
        progressBar.classList.add('bg-success');
        progressText.textContent = "Download starting...";
    }
}

function triggerFileDownload(jobId) {
    // Hidden iframe or simple window location change
    // window.location.href triggers the browser's download manager, remaining on the page logic is fine for most browsers
    // forcing a slight delay to let the UI show "Done"
    setTimeout(() => {
        window.location.href = `/api/download/file/${jobId}`;
        setTimeout(() => {
            progressModal.hide();
        }, 3000);
    }, 1000);
}

// Helpers currently unused by new logic but kept if needed
function formatFileSize(bytes) {
    return bytes; 
}
