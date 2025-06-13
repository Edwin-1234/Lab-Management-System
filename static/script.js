const signInPopup = document.getElementById('signInPopup');

function showSignInPopup() {
    signInPopup.style.display = 'flex';
}

function closeSignInPopup() {
    signInPopup.style.display = 'none';
}

window.onclick = function(event) {
    if (event.target == signInPopup) {
        signInPopup.style.display = "none";
    }
}
