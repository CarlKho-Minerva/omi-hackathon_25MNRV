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

// Function to fetch data and display (will be expanded in next task)
async function loadReflectionData() {
    const loadingIndicator = document.getElementById('loading-indicator');
    const swiperContainer = document.getElementById('reflection-swiper');
    const swiperWrapper = document.getElementById('swiper-wrapper-main');

    // Clear previous slides if any (for potential refresh logic later)
    swiperWrapper.innerHTML = '';

    // TODO: Fetch data from API_ENDPOINT in OMIW-8
    console.log('Simulating data load...');
    // Simulate a delay
    await new Promise(resolve => setTimeout(resolve, 1000));

    // --- Simulated Data (Replace with actual fetched data in OMIW-8) ---
    const dummyData = {
        daily_emoji: "🤔",
        summary: "A day of coding and debugging.",
        gratitude_points: ["Fixed that tricky bug!", "Learned about Docker platforms."],
        learned_terms: [{ term: "Cloud Run", definition: "GCP service for running containers." }, { term: "Firestore", definition: "NoSQL Database on GCP." }],
        little_things: [{ mention: "Wanted coffee", suggested_action: "Make coffee" }],
        mentor_advice: "Remember to take breaks while coding!",
        action_items: ["Deploy updated webhook.", "Test frontend API call."]
    };
    console.log('Dummy data generated:', dummyData);
    // --------------------------------------------------------------------

    // TODO: Populate swiperWrapper with slides based on fetched data in OMIW-8
    // For now, let's just add a placeholder slide
    swiperWrapper.innerHTML = `
         <div class="swiper-slide" style="background-color: #2a2a3e;">
             <h1>${dummyData.daily_emoji} Daily Reflection Placeholder</h1>
             <p>${dummyData.summary}</p>
             <p><em>(Real content coming soon!)</em></p>
         </div>
         <div class="swiper-slide" style="background-color: #3a3a4e;">
             <h1>Gratitude</h1>
             <p><em>(Gratitude points here)</em></p>
         </div>
         <div class="swiper-slide" style="background-color: #4a4a5e;">
              <h1>Knowledge</h1>
              <p><em>(Learned terms here)</em></p>
          </div>
          <div class="swiper-slide" style="background-color: #5a5a6e;">
              <h1>Little Things</h1>
               <p><em>(Little things mentions here)</em></p>
           </div>
            <div class="swiper-slide" style="background-color: #6a6a7e;">
               <h1>Mentor Advice</h1>
               <p><em>(Mentor advice here)</em></p>
           </div>
           <div class="swiper-slide" style="background-color: #7a7a8e;">
               <h1>Tasks</h1>
               <p><em>(Task list UI here)</em></p>
           </div>
     `;
    console.log('Placeholder slides added.');

    // Hide loading, show swiper
    loadingIndicator.style.display = 'none';
    swiperContainer.style.display = 'block';
    console.log('Swiper container shown.');

    // Initialize Swiper *after* slides are in the DOM
    initializeSwiper();
}

// --- Run on Page Load ---
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded and parsed');
    loadReflectionData(); // Load data when the page is ready
});