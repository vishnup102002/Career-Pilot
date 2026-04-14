// ===== File Upload Drag & Drop =====
const fileInput = document.getElementById('resume');
const fileMessage = document.querySelector('.file-message');
const dropArea = document.getElementById('file-drop-area');

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

// ===== City Autocomplete Data =====
const CITY_LIST = [
    "Remote", "Work From Home",
    // India — Major Cities
    "Bangalore", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Pune", "Kolkata",
    "Ahmedabad", "Jaipur", "Lucknow", "Chandigarh", "Noida", "Gurgaon", "Indore",
    "Bhopal", "Kochi", "Coimbatore", "Thiruvananthapuram", "Nagpur", "Visakhapatnam",
    "Mysore", "Mangalore", "Vadodara", "Surat", "Patna", "Ranchi", "Bhubaneswar",
    "Guwahati", "Dehradun", "Amritsar", "Agra", "Varanasi", "Madurai", "Tiruchirappalli",
    "Salem", "Thrissur", "Kozhikode", "Navi Mumbai", "Thane", "Faridabad", "Ghaziabad",
    // International
    "New York", "San Francisco", "London", "Berlin", "Toronto", "Dubai",
    "Singapore", "Sydney", "Tokyo", "Amsterdam", "Paris", "Austin", "Seattle",
    "Boston", "Chicago", "Los Angeles", "Denver", "Atlanta", "Dallas",
    "Vancouver", "Melbourne", "Dublin", "Zurich", "Stockholm", "Helsinki",
];

// ===== Multi-Location Tag Input with Autocomplete =====
const tagsContainer = document.getElementById('tags-container');
const locationInput = document.getElementById('location-input');
const hiddenLocations = document.getElementById('locations');
let locations = [];

// Create the autocomplete dropdown
const dropdown = document.createElement('div');
dropdown.className = 'autocomplete-dropdown';
dropdown.id = 'autocomplete-dropdown';
// Position relative to the input-group
const locationGroup = tagsContainer.closest('.input-group');
locationGroup.style.position = 'relative';
locationGroup.appendChild(dropdown);

// Click anywhere on the container to focus the input
tagsContainer.addEventListener('click', () => locationInput.focus());

// Show suggestions as user types
locationInput.addEventListener('input', () => {
    const query = locationInput.value.trim().toLowerCase();
    if (query.length === 0) {
        dropdown.classList.remove('visible');
        return;
    }
    
    const matches = CITY_LIST.filter(city => 
        city.toLowerCase().includes(query) && !locations.includes(city)
    ).slice(0, 6); // Show max 6 suggestions
    
    if (matches.length === 0) {
        dropdown.classList.remove('visible');
        return;
    }
    
    dropdown.innerHTML = matches.map(city => {
        // Highlight the matching part
        const idx = city.toLowerCase().indexOf(query);
        const before = city.slice(0, idx);
        const match = city.slice(idx, idx + query.length);
        const after = city.slice(idx + query.length);
        return `<div class="autocomplete-item" data-city="${city}">${before}<strong>${match}</strong>${after}</div>`;
    }).join('');
    
    dropdown.classList.add('visible');
    
    // Add click handlers to each suggestion
    dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
        item.addEventListener('mousedown', (e) => {
            e.preventDefault(); // Prevent blur from firing
            addLocation(item.dataset.city);
            dropdown.classList.remove('visible');
        });
    });
});

locationInput.addEventListener('keydown', (e) => {
    const value = locationInput.value.trim();
    
    // Enter or comma adds a tag
    if ((e.key === 'Enter' || e.key === ',') && value) {
        e.preventDefault();
        // If dropdown is visible, pick the first suggestion
        const firstItem = dropdown.querySelector('.autocomplete-item');
        if (firstItem && dropdown.classList.contains('visible')) {
            addLocation(firstItem.dataset.city);
        } else {
            addLocation(value.replace(/,/g, ''));
        }
        dropdown.classList.remove('visible');
    }
    
    // Backspace removes the last tag when input is empty
    if (e.key === 'Backspace' && !locationInput.value && locations.length > 0) {
        removeLocation(locations.length - 1);
    }
    
    // Escape closes dropdown
    if (e.key === 'Escape') {
        dropdown.classList.remove('visible');
    }
});

// Close dropdown on blur
locationInput.addEventListener('blur', () => {
    // Small delay to allow click events on dropdown items
    setTimeout(() => {
        dropdown.classList.remove('visible');
    }, 150);
});

function addLocation(name) {
    if (!name || locations.includes(name)) return;
    locations.push(name);
    updateLocationTags();
    locationInput.value = '';
}

function removeLocation(index) {
    locations.splice(index, 1);
    updateLocationTags();
}

function updateLocationTags() {
    // Remove existing tags
    tagsContainer.querySelectorAll('.tag').forEach(t => t.remove());
    
    // Create new tags
    locations.forEach((loc, i) => {
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.innerHTML = `${loc} <span class="remove-tag" data-index="${i}">&times;</span>`;
        tagsContainer.insertBefore(tag, locationInput);
    });
    
    // Update hidden input value for form submission
    hiddenLocations.value = locations.join(', ');
    
    // Bind remove events
    tagsContainer.querySelectorAll('.remove-tag').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            removeLocation(parseInt(btn.dataset.index));
        });
    });
}

// ===== Form Submission =====
const form = document.getElementById('onboarding-form');
const submitBtn = document.getElementById('submit-btn');
const btnText = document.querySelector('.btn-text');
const loader = document.getElementById('loader');
const statusMessage = document.getElementById('status-message');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Validate at least one location
    if (locations.length === 0) {
        statusMessage.className = 'error';
        statusMessage.textContent = "⚠️ Please add at least one preferred job location.";
        return;
    }
    
    // Set UI to loading state
    btnText.style.display = 'none';
    loader.style.display = 'block';
    submitBtn.disabled = true;
    statusMessage.className = 'hidden';
    
    const formData = new FormData(form);

    try {
        const response = await fetch('/api/initialize', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (response.ok) {
            statusMessage.className = 'success';
            statusMessage.textContent = "✅ LangGraph agents successfully deployed! You will be notified shortly via Email.";
            form.reset();
            locations = [];
            updateLocationTags();
            updateFileMessage();
        } else {
            statusMessage.className = 'error';
            statusMessage.textContent = `❌ Agent deployment failed: ${data.detail || 'Unknown error'}`;
        }
        
    } catch (error) {
        statusMessage.className = 'error';
        statusMessage.textContent = "❌ Failed to reach the Python Multi-Agent server.";
    } finally {
        btnText.style.display = 'block';
        loader.style.display = 'none';
        submitBtn.disabled = false;
    }
});
