document.addEventListener('DOMContentLoaded', () => {
    // Elements - File upload
    const dropzoneA = document.getElementById('dropzone-a');
    const dropzoneB = document.getElementById('dropzone-b');
    const inputA = document.getElementById('video-file-a');
    const inputB = document.getElementById('video-file-b');
    const metaA = document.getElementById('meta-a');
    const metaB = document.getElementById('meta-b');
    const nameA = document.getElementById('name-a');
    const nameB = document.getElementById('name-b');
    const sizeA = document.getElementById('size-a');
    const sizeB = document.getElementById('size-b');
    const removeA = document.getElementById('remove-a');
    const removeB = document.getElementById('remove-b');

    // Configuration / Submit Button
    const processBtn = document.getElementById('process-btn');
    const validationMsg = document.getElementById('validation-msg');

    // Configuration Elements
    const intervalValue = document.getElementById('interval-value');
    const intervalUnit = document.getElementById('interval-unit');
    const intervalCaption = document.getElementById('interval-caption');

    // Phase Containers
    const uploadPhase = document.getElementById('upload-phase');
    const processingPhase = document.getElementById('processing-phase');
    const resultPhase = document.getElementById('result-phase');

    // Processing Elements
    const statusText = document.getElementById('status-text');
    const progressBar = document.getElementById('progress-bar');
    const progressVal = document.getElementById('progress-val');
    const logConsole = document.getElementById('log-console');

    // Result Elements
    const outputVideoPlayer = document.getElementById('output-video-player');
    const downloadBtn = document.getElementById('download-btn');
    const startNewBtn = document.getElementById('start-new-btn');

    // Local state variables
    let fileA = null;
    let fileB = null;
    let pollingInterval = null;
    let activeTaskId = null;

    // Helper functions
    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function addLog(message, colorClass = '') {
        const time = new Date().toLocaleTimeString();
        const line = document.createElement('div');
        line.className = `log-line ${colorClass}`;
        line.innerHTML = `<span class="text-dark">[${time}]</span> ${message}`;
        logConsole.appendChild(line);
        logConsole.scrollTop = logConsole.scrollHeight;
    }

    function resetLogConsole() {
        logConsole.innerHTML = '<div class="log-line text-cyan">[System] Initializing connection to worker thread...</div>';
    }

    function checkSubmitState() {
        if (fileA && fileB) {
            processBtn.disabled = false;
            validationMsg.style.opacity = 0;
        } else {
            processBtn.disabled = true;
            validationMsg.style.opacity = 1;
        }
    }

    function transitionToPhase(phase) {
        // Remove active class from all sections
        uploadPhase.classList.remove('active');
        processingPhase.classList.remove('active');
        resultPhase.classList.remove('active');

        // Allow layout shifts to finish, then set display active
        setTimeout(() => {
            if (phase === 'upload') {
                uploadPhase.classList.add('active');
            } else if (phase === 'processing') {
                processingPhase.classList.add('active');
            } else if (phase === 'result') {
                resultPhase.classList.add('active');
            }
        }, 50);
    }
    function updateIntervalCaption() {
        const val = parseFloat(intervalValue.value);
        if (isNaN(val) || val <= 0) {
            intervalCaption.textContent = "Please enter a valid positive number.";
            intervalCaption.style.color = "#f87171";
            return;
        }
        intervalCaption.style.color = "var(--text-dark)";

        const unit = intervalUnit.value;
        let frames = 6;
        let seconds = 0.1;

        if (unit === 'frames') {
            frames = Math.max(1, Math.round(val));
            seconds = frames / 60;
        } else {
            seconds = val;
            frames = Math.max(1, Math.round(seconds * 60));
        }

        intervalCaption.textContent = `Stitch swap will occur every ${frames} frame(s) (~${seconds.toFixed(2)}s at 60 FPS)`;
    }

    intervalValue.addEventListener('input', updateIntervalCaption);
    intervalUnit.addEventListener('change', () => {
        if (intervalUnit.value === 'seconds') {
            intervalValue.value = '0.1';
            intervalValue.step = '0.01';
            intervalValue.min = '0.01';
        } else {
            intervalValue.value = '6';
            intervalValue.step = '1';
            intervalValue.min = '1';
        }
        updateIntervalCaption();
    });

    // Run initial update
    updateIntervalCaption();
    // Drag and Drop Event Listeners
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzoneA.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzoneA.classList.add('dragover');
        }, false);
        dropzoneB.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzoneB.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzoneA.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzoneA.classList.remove('dragover');
        }, false);
        dropzoneB.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzoneB.classList.remove('dragover');
        }, false);
    });

    // File Drop & Selection Handlers
    inputA.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileA(e.target.files[0]);
        }
    });

    dropzoneA.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            inputA.files = files; // Sync file input field
            handleFileA(files[0]);
        }
    });

    inputB.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileB(e.target.files[0]);
        }
    });

    dropzoneB.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            inputB.files = files; // Sync file input field
            handleFileB(files[0]);
        }
    });

    function handleFileA(file) {
        if (!file.type.startsWith('video/')) {
            alert('File must be a video.');
            return;
        }
        fileA = file;
        nameA.textContent = file.name;
        sizeA.textContent = formatBytes(file.size);
        metaA.style.display = 'flex';
        checkSubmitState();
    }

    function handleFileB(file) {
        if (!file.type.startsWith('video/')) {
            alert('File must be a video.');
            return;
        }
        fileB = file;
        nameB.textContent = file.name;
        sizeB.textContent = formatBytes(file.size);
        metaB.style.display = 'flex';
        checkSubmitState();
    }

    // File Remove Handlers
    removeA.addEventListener('click', (e) => {
        e.stopPropagation(); // Avoid triggering parent file selector click
        fileA = null;
        inputA.value = '';
        metaA.style.display = 'none';
        checkSubmitState();
    });

    removeB.addEventListener('click', (e) => {
        e.stopPropagation();
        fileB = null;
        inputB.value = '';
        metaB.style.display = 'none';
        checkSubmitState();
    });

    // Start Video Processing
    processBtn.addEventListener('click', async () => {
        if (!fileA || !fileB) return;

        const val = parseFloat(intervalValue.value);
        if (isNaN(val) || val <= 0) {
            alert("Please enter a valid positive interleave interval.");
            return;
        }

        let intervalFrames = 6;
        if (intervalUnit.value === 'frames') {
            intervalFrames = Math.max(1, Math.round(val));
        } else {
            intervalFrames = Math.max(1, Math.round(val * 60));
        }

        transitionToPhase('processing');
        resetLogConsole();
        
        addLog(`Preparing upload payload...`, 'text-cyan');
        addLog(`File A: ${fileA.name} (${formatBytes(fileA.size)})`, 'text-purple');
        addLog(`File B: ${fileB.name} (${formatBytes(fileB.size)})`, 'text-purple');
        addLog(`Stitch swap interval: ${intervalFrames} frames (~${(intervalFrames/60).toFixed(2)}s)`, 'text-cyan');

        const formData = new FormData();
        formData.append('video_a', fileA);
        formData.append('video_b', fileB);
        formData.append('interval_frames', intervalFrames);

        statusText.textContent = "Uploading video files to server...";
        progressBar.style.width = '0%';
        progressVal.textContent = '0%';

        try {
            // Upload videos
            addLog("Uploading files... This may take a moment depending on the size.", 'text-amber');
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Upload failed');
            }

            const data = await response.json();
            activeTaskId = data.task_id;
            
            addLog(`Upload complete. Server task created: ${activeTaskId}`, 'text-green');
            addLog(`Running video synchronization and interleaving algorithms...`, 'text-cyan');
            statusText.textContent = "Processing and interleaving frames...";

            // Start polling status
            startStatusPolling(activeTaskId);
        } catch (error) {
            loggerError(error.message);
        }
    });

    function loggerError(msg) {
        addLog(`ERROR: ${msg}`, 'text-red');
        statusText.textContent = "Stitching failed.";
        progressVal.textContent = "Error";
        progressBar.style.backgroundColor = "#ef4444";
        
        // Show an option to reset back to upload phase after error
        setTimeout(() => {
            const resetContainer = document.createElement('div');
            resetContainer.style.marginTop = '20px';
            resetContainer.innerHTML = `<button type="button" class="reset-btn" id="err-reset-btn">Return to Upload Screen</button>`;
            logConsole.appendChild(resetContainer);
            logConsole.scrollTop = logConsole.scrollHeight;

            document.getElementById('err-reset-btn').addEventListener('click', () => {
                transitionToPhase('upload');
            });
        }, 1500);
    }

    function startStatusPolling(taskId) {
        if (pollingInterval) clearInterval(pollingInterval);

        let lastProgress = -1;

        pollingInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/status/${taskId}`);
                if (!res.ok) throw new Error("Failed to fetch task status.");

                const data = await res.json();
                const progress = data.progress;

                if (progress !== lastProgress) {
                    progressBar.style.width = `${progress}%`;
                    progressVal.textContent = `${progress}%`;
                    
                    if (progress > 0) {
                        addLog(`Processed ${progress}% of video frames.`, 'text-purple');
                    }
                    lastProgress = progress;
                }

                if (data.status === 'processing') {
                    statusText.textContent = "Interleaving video frames...";
                } else if (data.status === 'completed') {
                    clearInterval(pollingInterval);
                    addLog("Video processing complete!", "text-green");
                    addLog("Finalizing download package...", "text-green");
                    
                    // Set up video preview and download links
                    outputVideoPlayer.src = data.download_url;
                    downloadBtn.href = data.download_url;

                    setTimeout(() => {
                        transitionToPhase('result');
                    }, 800);
                } else if (data.status === 'failed') {
                    clearInterval(pollingInterval);
                    throw new Error(data.error || "Video processing failed.");
                }
            } catch (err) {
                clearInterval(pollingInterval);
                loggerError(err.message);
            }
        }, 1000);
    }

    // Reset Application / Create Another Interleaved Video
    startNewBtn.addEventListener('click', () => {
        // Reset states
        fileA = null;
        fileB = null;
        inputA.value = '';
        inputB.value = '';
        metaA.style.display = 'none';
        metaB.style.display = 'none';
        
        outputVideoPlayer.src = '';
        downloadBtn.href = '#';

        // Clear polling interval
        if (pollingInterval) clearInterval(pollingInterval);
        activeTaskId = null;
        
        checkSubmitState();
        transitionToPhase('upload');
    });
});
