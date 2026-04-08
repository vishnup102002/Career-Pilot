const fileInput = document.getElementById('resume');
const fileMessage = document.querySelector('.file-message');
const dropArea = document.getElementById('file-drop-area');

// Implement drag and drop styling
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
});
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => dropArea.classList.add('dragover'), false);
});
['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => dropArea.classList.remove('dragover'), false);
});

dropArea.addEventListener('drop', (e) => {
    fileInput.files = e.dataTransfer.files;
    updateFileMessage();
});
fileInput.addEventListener('change', updateFileMessage);

function updateFileMessage() {
    if (fileInput.files.length > 0) {
        fileMessage.textContent = "📄 " + fileInput.files[0].name;
        fileMessage.style.color = '#fff';
    } else {
        fileMessage.textContent = "Drag & drop or Click to upload";
        fileMessage.style.color = 'var(--text-muted)';
    }
}

// Interacting with the FastAPI Backend
const form = document.getElementById('onboarding-form');
const submitBtn = document.getElementById('submit-btn');
const btnText = document.querySelector('.btn-text');
const loader = document.getElementById('loader');
const statusMessage = document.getElementById('status-message');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Set UI to loading state
    btnText.style.display = 'none';
    loader.style.display = 'block';
    submitBtn.disabled = true;
    statusMessage.className = 'hidden';
    
    const formData = new FormData(form);

    try {
        // Send a POST request to our FastAPI backend to initialize LangGraph orchestration
        const response = await fetch('/api/initialize', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (response.ok) {
            statusMessage.className = 'success';
            statusMessage.textContent = "✅ LangGraph agents successfully deployed! You will be notified shortly via Email/WhatsApp.";
            form.reset();
            updateFileMessage();
        } else {
            statusMessage.className = 'error';
            statusMessage.textContent = `❌ Agent deployment failed: ${data.detail || 'Unknown error'}`;
        }
        
    } catch (error) {
        statusMessage.className = 'error';
        statusMessage.textContent = "❌ Failed to reach the Python Multi-Agent server.";
    } finally {
        // Reset UI loading state
        btnText.style.display = 'block';
        loader.style.display = 'none';
        submitBtn.disabled = false;
    }
});
