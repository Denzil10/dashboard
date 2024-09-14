const visionBoard = document.getElementById('vision-board');
const apiEndpoint = 'http://localhost:5000/photo'; // Adjust this URL to your local server's endpoint

// Function to fetch photo URLs from the local server
function fetchPhotosFromLocal() {
    fetch(apiEndpoint)
        .then(response => response.json())
        .then(data => {
            const photoUrls = data; 
            console.log("data returned", data)// Assuming the server returns an object with a 'urls' array
            displayPhotos(photoUrls);
        })
        .catch(error => console.error('Error fetching photos:', error));
}

// Function to display photos on the vision board
function displayPhotos(photoUrls) {
    photoUrls.forEach(url => {
        console.log("url", url)
        if(url!=null){
            const img = document.createElement('img');
            img.src = url;
            img.classList.add('vision-photo');
            img.style.transform = `rotate(${Math.random() * 10 - 5}deg) scale(${Math.random() * 0.3 + 0.85})`;
            visionBoard.appendChild(img);
        }
    });
}

// Fetch photos and display them
fetchPhotosFromLocal();
