function logout(){
    document.location.href = "/logout";
}

// Timeout for flash messages
setTimeout(() => {
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(flash => {
        flash.style.display = 'none';
    });
}, 5000);

function toggleSidebar() {
    var sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('-translate-x-full');
}
