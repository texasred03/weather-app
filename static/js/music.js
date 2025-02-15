// static/js/music.js

let audioElement = new Audio(); // Create an audio object
let musicFiles = []; // Store the list of songs

// Fetch the music list from Flask
function fetchMusicList() {
    fetch('/music')
        .then(response => response.json())
        .then(data => {
            musicFiles = data.music_files;
        })
        .catch(error => console.error("Error fetching music files:", error));
}

// Play a random song from the list
function playRandomMusic() {
    if (musicFiles.length === 0) return; // No music files loaded

    let randomIndex = Math.floor(Math.random() * musicFiles.length);
    let musicFile = musicFiles[randomIndex];

    audioElement.src = `/music/${encodeURIComponent(musicFile)}`;
    audioElement.play().catch(error => console.error("Playback blocked:", error));
}

// When the song ends, play another
audioElement.addEventListener("ended", playRandomMusic);

// User must click to allow autoplay
function setupMusicControls() {
    document.getElementById("play-music").addEventListener("click", function() {
        if (musicFiles.length === 0) {
            fetchMusicList();
            setTimeout(playRandomMusic, 500); // Slight delay to ensure list loads
        } else {
            playRandomMusic();
        }
    });
}

// Initialize music system on page load
document.addEventListener("DOMContentLoaded", function () {
    fetchMusicList();
    setupMusicControls();
});
