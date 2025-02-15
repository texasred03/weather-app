// static/js/script.js

let currentSegment = 0;
const segments = document.querySelectorAll('.weather-segment');

// Fetch the weather data from the Flask app (which fetches it from Ambient Weather)
function fetchUpdates() {
    fetch('/weather')
        .then(response => response.json())
        .then(data => {
            // Update the forecast, hourly forecast, almanac, and radar on the page
            document.getElementById("forecast").innerHTML = `<div class="weather-box">${data.forecast}</div>`;
            document.getElementById("hourly-forecast").innerHTML = `
                <div class="weather-box">
                    <h2>Hourly Forecast</h2>
                    ${data.hourly_forecast.map((forecast, index) => {
                        return `<p>${forecast.time}: ${forecast.temp}°F</p>`;
                    }).join('')}
                </div>`;
            document.getElementById("almanac").innerHTML = `
                <div class="weather-box">
                    <h2>Almanac</h2>
                    <p>Avg High: ${data.almanac.avg_high}°F</p>
                    <p>Avg Low: ${data.almanac.avg_low}°F</p>
                    <p>Record High: ${data.almanac.record_high}°F</p>
                    <p>Record Low: ${data.almanac.record_low}°F</p>
                </div>`;
        });
}

window.onload = fetchUpdates;

function showNextSegment() {
    segments[currentSegment].classList.remove('active');
    currentSegment = (currentSegment + 1) % segments.length;
    segments[currentSegment].classList.add('active');
}

setInterval(showNextSegment, 30000); // Change segment every 30 seconds

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

// Fetch alerts on page load and update every 60 seconds
window.onload = function() {
    playRandomMusic(); 
    fetchUpdates(); // Fetch weather data
    fetchAlerts();  // Fetch alerts
    setInterval(fetchAlerts, 60000 * 15);  // Refresh alerts every 15 minutes
};

function playRandomMusic() {
    fetch('/music')
        .then(response => response.json())
        .then(data => {
            if (data.music_files.length > 0) {
                const randomIndex = Math.floor(Math.random() * data.music_files.length);
                const musicFile = data.music_files[randomIndex];

                const audioElement = document.getElementById('background-music');
                audioElement.src = `/static/music/${musicFile}`;
                audioElement.play();
            }
        })
        .catch(error => console.error("Error fetching music files:", error));
}

// Play new song when the current one ends
document.addEventListener('DOMContentLoaded', function() {
    const audioElement = document.getElementById('background-music');
    audioElement.addEventListener('ended', playRandomMusic);

    playRandomMusic(); // Start music on page load
});
