// static/js/script.js

// Fetch the weather data from the Flask app (which fetches it from Ambient Weather)
function fetchUpdates() {
    fetch('/weather')
        .then(response => response.json())        
        ;
}

// Checks for alerts and display them if we have some. 
function fetchAlerts() {
    fetch('/alerts')
        .then(response => response.json())
        .then(data => {
            const alertDiv = document.getElementById('alert-box');
            const scrollingTextElement = document.getElementById('scrolling-text');

            if (data.alert && data.alert !== "No active weather alerts.") {
                alertDiv.style.display = 'block';  // Show alert div
                scrollingTextElement.textContent = data.alert;
            } else {
                alertDiv.style.display = 'none';  // Hide alert div
            }
        })
        .catch(error => {
            console.error("Error fetching alerts:", error);
        });
}

// Function to update the scrolling text with new content
function updateScrollingText(text) {
    const scrollingTextElement = document.getElementById('scrolling-text');
    scrollingTextElement.textContent = text;
}

// Update scrolling text with the alert (from Python template)
window.onload = function() {
    const alertText = '{{ alert }}';  // This is the dynamic alert passed from the backend (Flask)

    // If there's an alert, update the scrolling text
    if (alertText) {
        updateScrollingText(alertText);
    }
};

window.onload = fetchUpdates;
