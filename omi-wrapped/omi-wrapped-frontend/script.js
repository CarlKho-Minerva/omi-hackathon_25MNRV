// script.js
console.log("Omi Wrapped Frontend Script Loaded!");

// Placeholder for API URL (replace with your actual Cloud Run URL later)
// Make sure to include the /get_reflection path!
const API_ENDPOINT = 'https://omi-to-notion-363551469917.us-west2.run.app/get_reflection'; // <<< REPLACE THIS LATER
const USER_ID = 'ckVQW3MVAoenlOdYhHLt5K3zPpW2'; // <<< REPLACE with your user ID for testing

// Function to initialize Swiper
function initializeSwiper() {
    const swiper = new Swiper('.swiper-container', {
        // Optional parameters
        direction: 'vertical', // Make it swipe vertically like stories
        loop: false, // Don't loop back to the beginning

        // Pagination dots
        pagination: {
            el: '.swiper-pagination',
            clickable: true,
        },

        // Navigation arrows (optional)
        // navigation: {
        //   nextEl: '.swiper-button-next',
        //   prevEl: '.swiper-button-prev',
        // },

        // Keyboard control (optional)
        keyboard: {
            enabled: true,
        },

        // Mousewheel control (optional)
        mousewheel: true,
    });
    console.log('Swiper initialized');
    return swiper; // Return the instance if needed
}

// REPLACE the existing loadReflectionData function with this one:
async function loadReflectionData() {
    const loadingIndicator = document.getElementById('loading-indicator');
    const swiperContainer = document.getElementById('reflection-swiper');
    const swiperWrapper = document.getElementById('swiper-wrapper-main');

    // Clear previous slides
    swiperWrapper.innerHTML = '';
    loadingIndicator.textContent = 'Fetching your reflection... 🧠'; // Update loading text
    loadingIndicator.style.display = 'flex'; // Ensure loading is visible
    swiperContainer.style.display = 'none'; // Hide swiper initially

    // --- Determine Date and User ---
    // For now, using hardcoded USER_ID and today's date
    // TODO: In future, might get USER_ID from Omi context if possible, or implement login
    const today = new Date();
    const dateStr = today.toISOString().split('T')[0]; // Format YYYY-MM-DD
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
             </div>`;

        // Inject the generated HTML into the swiper wrapper
        swiperWrapper.innerHTML = slidesHtml;
        console.log('Slides HTML injected.');

        // --- Populate Task List Separately (for OMIW-9) ---
        // We'll call a function here later to build the interactive list
        populateTaskList(data.action_items || [], data.little_things || []); // Pass both lists

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

// --- Helper Function to Populate Task List (Placeholder for OMIW-9) ---
// This function will be fully built in the next task
function populateTaskList(actionItems, littleThings) {
    const taskListContainer = document.getElementById('task-list-container');
    const copyButton = document.getElementById('copy-tasks-button');

    if (!taskListContainer || !copyButton) {
        console.error('Task list container or copy button not found!');
        return;
    }

    taskListContainer.innerHTML = ''; // Clear placeholder

    const combinedTasks = [
        ...actionItems.map(item => ({ text: item, source: 'direct' })),
        ...littleThings.map(item => ({ text: item.suggested_action, source: 'suggested', mention: item.mention }))
    ];

    if (combinedTasks.length === 0) {
        taskListContainer.innerHTML = '<p>No action items identified for today.</p>';
        copyButton.style.display = 'none'; // Hide copy button if no tasks
        return;
    }

    // Placeholder: Just list them for now. Checkboxes and scrolling added in OMIW-9.
    const listHtml = combinedTasks.map((task, index) => `
        <div class="task-item">
             <input type="checkbox" id="task-${index}" checked data-tasktext="${escapeHtml(task.text)}">
             <label for="task-${index}">${escapeHtml(task.text)} ${task.source === 'suggested' ? '<span class="task-source">(from mention)</span>' : ''}</label>
        </div>
    `).join('');

    taskListContainer.innerHTML = `<div class="scrollable-tasks">${listHtml}</div>`; // Wrap in a div for scrolling later
    copyButton.style.display = 'block'; // Show copy button
    console.log('Task list populated (basic).');
    // TODO OMIW-9: Add checkbox logic, scrolling styles, gradient mask
    // TODO OMIW-10: Add copy button logic & modal
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



// --- Run on Page Load ---
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded and parsed');
    loadReflectionData(); // Load data when the page is ready
});