// script.js
console.log("Omi Wrapped Frontend Script Loaded!");

// Placeholder for API URL (replace with your actual Cloud Run URL later)
// Make sure to include the /get_reflection path!
const API_ENDPOINT = 'https://omi-to-notion-363551469917.us-west2.run.app/get_reflection'; // <<< REPLACE THIS LATER
const USER_ID = 'ckVQW3MVAoenlOdYhHLt5K3zPpW2'; // <<< REPLACE with your user ID for testing

// Global swiper instance
let swiperInstance;

// Function to initialize Swiper
function initializeSwiper() {
    swiperInstance = new Swiper('.swiper-container', {
        // Optional parameters
        direction: 'vertical', // Make it swipe vertically like stories
        loop: false, // Don't loop back to the beginning

        // Pagination dots
        pagination: {
            el: '.swiper-pagination',
            clickable: true,
        },

        // Keyboard control (optional)
        keyboard: {
            enabled: true,
        },

        // Mousewheel control (optional)
        mousewheel: true,
    });
    console.log('Swiper initialized');
    return swiperInstance; // Return the instance if needed
}

// Calendar button handler function
function setupCalendarButton() {
    const calendarButton = document.getElementById('calendar-button');
    if (calendarButton) {
        calendarButton.addEventListener('click', function() {
            // Show a date picker or custom date selection UI
            const today = new Date();
            const dateStr = prompt('Enter date (YYYY-MM-DD):', 
                `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`);
            
            if (dateStr && isValidDateFormat(dateStr)) {
                loadReflectionData(dateStr);
            } else if (dateStr) {
                alert('Please use the format YYYY-MM-DD');
            }
        });
    }
}

// Validate date format
function isValidDateFormat(dateStr) {
    // Basic validation for YYYY-MM-DD format
    return /^\d{4}-\d{2}-\d{2}$/.test(dateStr);
}

// Enhanced version of loadReflectionData that accepts a date parameter
async function loadReflectionData(customDate = null) {
    // ... existing code ...
}

// REPLACE the existing loadReflectionData function with this one:
async function loadReflectionData(customDate = null) {
    const loadingIndicator = document.getElementById('loading-indicator');
    const swiperContainer = document.getElementById('reflection-swiper');
    const swiperWrapper = document.getElementById('swiper-wrapper-main');

    // Clear previous slides
    swiperWrapper.innerHTML = '';
    loadingIndicator.textContent = 'Fetching your reflection... 🧠'; // Update loading text
    loadingIndicator.style.display = 'flex'; // Ensure loading is visible
    swiperContainer.style.display = 'none'; // Hide swiper initially

    // --- Determine Date and User ---
    // Use customDate if provided, otherwise use today's date
    const today = new Date();
    let dateStr;
    
    if (customDate) {
        dateStr = customDate;
    } else {
        // Construct YYYY-MM-DD from local date components to avoid timezone issues with toISOString()
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
        const day = String(today.getDate()).padStart(2, '0');
        dateStr = `${year}-${month}-${day}`;
    }
    
    const userId = USER_ID; // Using the constant defined above

    // --- Construct API URL ---
    const url = new URL(API_ENDPOINT);
    url.searchParams.append('uid', userId);
    url.searchParams.append('date', dateStr);
    console.log(`Fetching data from: ${url}`);

    try {
        const response = await fetch(url);

        if (!response.ok) {
            // Handle HTTP errors (like 404 Not Found, 500 Internal Server Error)
            const errorText = await response.text();
            console.error(`API Error ${response.status}: ${errorText}`);
            loadingIndicator.textContent = `Error: Could not load reflection (${response.status}). Try again later.`;
            return; // Stop execution
        }

        const data = await response.json();
        console.log('Successfully fetched data:', data);

        // --- Data Validation (Basic) ---
        if (!data || typeof data !== 'object') {
            console.error('Invalid data format received from API.');
            loadingIndicator.textContent = 'Error: Received invalid data.';
            return;
        }

        // --- Dynamically Create Slides ---
        let slidesHtml = '';

        // Slide 1: Intro/Mood
        slidesHtml += `
            <div class="swiper-slide story-slide-intro" id="slide-intro">
                <span class="slide-emoji">${data.daily_emoji || '🤔'}</span>
                <h1>Your Day Wrapped</h1>
                <p class="summary">${data.summary || 'No summary available for today.'}</p>
                <p class="slide-hint">Swipe up to continue</p>
            </div>`;

        // Slide 2: Gratitude Journal
        slidesHtml += `
            <div class="swiper-slide story-slide-gratitude" id="slide-gratitude">
                <h1>Gratitude Journal</h1>
                <ul class="points-list">
                    ${data.gratitude_points && data.gratitude_points.length > 0
                ? data.gratitude_points.map(point => `<li>${escapeHtml(point)}</li>`).join('')
                : '<li>Nothing specific noted today. What are you grateful for now?</li>'
            }
                </ul>
            </div>`;

        // Slide 3: Knowledge Gap Filled
        slidesHtml += `
            <div class="swiper-slide story-slide-knowledge" id="slide-knowledge">
                <h1>Knowledge Gaps Filled</h1>
                <ul class="terms-list">
                     ${data.learned_terms && data.learned_terms.length > 0
                ? data.learned_terms.map(item => `<li><strong>${escapeHtml(item.term || 'Term?')}</strong>: ${escapeHtml(item.definition || 'No definition.')}</li>`).join('')
                : '<li>No specific new terms or concepts highlighted today.</li>'
            }
                </ul>
            </div>`;

        // Slide 4: It's the Little Things
        slidesHtml += `
            <div class="swiper-slide story-slide-littlethings" id="slide-littlethings">
                <h1>It's the Little Things</h1>
                <ul class="points-list">
                     ${data.little_things && data.little_things.length > 0
                ? data.little_things.map(item => `<li>${escapeHtml(item.mention || 'Observation?')}<br><small><em>Suggested Action: ${escapeHtml(item.suggested_action || 'None')}</em></small></li>`).join('')
                : '<li>No specific "little things" noted today.</li>'
            }
                </ul>
                <p class="slide-note"><em>Suggested actions based on these may appear in your Task List next.</em></p>
            </div>`;

        // Slide 5: Advice from your Omi Mentor
        slidesHtml += `
            <div class="swiper-slide story-slide-advice" id="slide-advice">
                <h1>Your Mentor's Advice</h1>
                <p class="advice-quote">"${escapeHtml(data.mentor_advice || 'Keep reflecting and growing!')}"</p>
            </div>`;

        // Slide 6: Task List (Structure only - UI refinement in next tasks)
        slidesHtml += `
            <div class="swiper-slide story-slide-tasks" id="slide-tasks">
                <h1>Today's Action Items</h1>
                <p>Review items from today's conversations & mentions.</p>
                <div id="task-list-container">
                    <!-- Task list items will be loaded here -->
                    <p>Loading tasks...</p>
                </div>
                <button id="copy-tasks-button" style="margin-top: 20px; padding: 10px 20px; display: none;">Copy Selected Tasks</button> <!-- Initially hidden -->
                <button id="back-button" class="back-button">Return to Previous Slide</button>
             </div>`;

        // Inject the generated HTML into the swiper wrapper
        swiperWrapper.innerHTML = slidesHtml;
        console.log('Slides HTML injected.');

        // --- Populate Task List Separately (for OMIW-9) ---
        // We'll call a function here later to build the interactive list
        populateTaskList(data.action_items || [], data.little_things || []); // Pass both lists

        // Add event listener for back button
        setupBackButton();

        // Hide loading, show swiper
        loadingIndicator.style.display = 'none';
        swiperContainer.style.display = 'block';
        console.log('Swiper container shown.');

        // Initialize Swiper *after* slides are in the DOM
        initializeSwiper();

    } catch (error) {
        console.error('Error fetching or processing reflection data:', error);
        loadingIndicator.textContent = `Error loading reflection: ${error.message}. Please try again later.`;
        // Optionally display error details for debugging
        // loadingIndicator.innerHTML += `<br><small>${error.stack}</small>`;
    }
}

// Setup back button functionality
function setupBackButton() {
    const backButton = document.getElementById('back-button');
    if (backButton) {
        backButton.addEventListener('click', function() {
            if (swiperInstance) {
                // Go to the previous slide (advice slide)
                swiperInstance.slideTo(4); // Index 4 is the advice slide (5th slide)
            }
        });
    }
}

// REPLACE the existing populateTaskList function with this one:
function populateTaskList(actionItems = [], littleThings = []) { // Add default empty arrays
    const taskListContainer = document.getElementById('task-list-container');
    const copyButton = document.getElementById('copy-tasks-button');

    if (!taskListContainer || !copyButton) {
        console.error('Task list container or copy button not found!');
        return;
    }

    taskListContainer.innerHTML = ''; // Clear placeholder/previous content

    // Combine tasks, adding a source and initial checked state
    const combinedTasks = [
        ...actionItems.map((item, index) => ({
            id: `task-direct-${index}`, // Unique ID for the checkbox/label pair
            text: item,
            source: 'direct',
            checked: true // Default to included
        })),
        ...littleThings.map((item, index) => ({
            id: `task-suggested-${index}`, // Unique ID
            text: item.suggested_action || 'Suggested action missing',
            source: 'suggested',
            mention: item.mention || '', // Keep the original mention for context if needed
            checked: true // Default to included
        }))
    ];

    // Store task state globally (or scoped if using modules/classes)
    // This allows the copy function (in next task) to access checked state
    window.omiWrappedTasks = combinedTasks; // Simple global storage for POC

    if (combinedTasks.length === 0) {
        taskListContainer.innerHTML = '<p>No action items identified for today.</p>';
        copyButton.style.display = 'none';
        return;
    }

    // Generate HTML for each task item with checkbox
    const listHtml = combinedTasks.map(task => `
        <div class="task-item ${task.checked ? 'checked' : ''}" data-taskid="${task.id}">
            <input
                type="checkbox"
                id="${task.id}"
                ${task.checked ? 'checked' : ''}
            >
            <label for="${task.id}">
                ${escapeHtml(task.text)}
                ${task.source === 'suggested' ? '<span class="task-source">(Suggestion based on: "' + escapeHtml(task.mention) + '")</span>' : ''}
             </label>
         </div>
     `).join('');

    // Add a wrapper for scrolling and gradient mask
    taskListContainer.innerHTML = `<div class="scrollable-tasks">${listHtml}</div>`;
    copyButton.style.display = 'block'; // Show copy button
    console.log('Interactive task list populated.');

    // --- Add Event Listeners for Checkboxes ---
    const taskItems = taskListContainer.querySelectorAll('.task-item');
    taskItems.forEach(item => {
        const checkbox = item.querySelector('input[type="checkbox"]');
        const taskId = item.dataset.taskid;

        checkbox.addEventListener('change', (event) => {
            // Find the corresponding task in our global state and update its checked status
            const taskIndex = window.omiWrappedTasks.findIndex(t => t.id === taskId);
            if (taskIndex !== -1) {
                window.omiWrappedTasks[taskIndex].checked = event.target.checked;
                // Optional: Add/remove a class for visual feedback if needed
                item.classList.toggle('checked', event.target.checked);
                console.log(`Task ${taskId} checked state: ${event.target.checked}`);
            }
        });
    });
    // INSIDE populateTaskList, AFTER the task list HTML is set:

    // --- Add Copy Button Logic ---
    const copyBtn = document.getElementById('copy-tasks-button');
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            // 1. Filter tasks based on current checked state in window.omiWrappedTasks
            const selectedTasks = window.omiWrappedTasks.filter(task => task.checked);

            if (selectedTasks.length === 0) {
                alert("No tasks selected to copy!"); // Simple feedback
                return;
            }

            // 2. Format the selected tasks as a markdown list
            const formattedList = selectedTasks.map(task => `- ${task.text}`).join('\n');
            console.log("Formatted tasks to copy:\n", formattedList);

            // 3. Use Clipboard API
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(formattedList)
                    .then(() => {
                        console.log('Tasks copied successfully!');
                        // Optional: Give feedback on button itself
                        copyBtn.textContent = 'Copied! ✅';
                        setTimeout(() => { copyBtn.textContent = 'Copy Selected Tasks'; }, 2000); // Reset button text
                        // 4. Show the confirmation modal
                        showModal();
                    })
                    .catch(err => {
                        console.error('Failed to copy tasks: ', err);
                        alert('Could not copy tasks. Your browser might not support this feature or permission was denied.');
                    });
            } else {
                console.error('Clipboard API not supported by this browser.');
                alert('Sorry, copying to clipboard is not supported by your browser.');
            }
        });
    } else {
        console.error("Copy button not found after populating task list.");
    }
}

// --- Utility function to prevent HTML injection ---
function escapeHtml(unsafe) {
    if (typeof unsafe !== 'string') return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// --- Modal Control Functions ---
function showModal() {
    const modal = document.getElementById('copy-confirmation-modal');
    if (modal) {
        modal.style.display = 'flex'; // Change display to flex to show it
        // Timeout needed to allow display change before transition starts
        setTimeout(() => {
            modal.classList.add('visible');
        }, 10); // Small delay
        console.log('Showing modal');
    } else {
        console.error('Modal element not found!');
    }
}

function hideModal() {
    const modal = document.getElementById('copy-confirmation-modal');
    if (modal) {
        modal.classList.remove('visible');
        // Wait for transition to finish before setting display none
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300); // Should match transition duration in CSS (0.3s)
        console.log('Hiding modal');
    }
}


// --- Run on Page Load ---
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded and parsed');
    loadReflectionData(); // Load data when the page is ready
    
    // Setup the calendar button functionality
    setupCalendarButton();

    // --- Add Modal Close Listener ---
    const modalCloseButton = document.getElementById('modal-close-button');
    const modalOverlay = document.getElementById('copy-confirmation-modal');

    if (modalCloseButton) {
        modalCloseButton.addEventListener('click', hideModal);
    }
    if (modalOverlay) {
        // Optional: Close modal if user clicks outside the content area
        modalOverlay.addEventListener('click', (event) => {
            if (event.target === modalOverlay) { // Check if click was directly on the overlay
                hideModal();
            }
        });
    }
});