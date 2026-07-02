// Function to switch between pages
function showPage(pageId) {
    // 1. Find all elements with the class 'page'
    const pages = document.querySelectorAll('.page');
    
    // 2. Remove the 'active' class from all of them so they hide
    pages.forEach(page => {
        page.classList.remove('active');
    });
 
    // 3. Add the 'active' class to the page we want to show
    const targetPage = document.getElementById(pageId);
    if (targetPage) {
        targetPage.classList.add('active');
    }
}
document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;

    // Проверяваме дали вече има запазена тема в localStorage
    const currentTheme = localStorage.getItem('theme');

    if (currentTheme === 'dark') {
        body.classList.add('dark-mode');
        if (themeToggle) themeToggle.textContent = '☀️';
    }

    // Add event when clicked
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            body.classList.toggle('dark-mode');

            // Проверяваме коя тема е активна и я запазваме
            if (body.classList.contains('dark-mode')) {
                localStorage.setItem('theme', 'dark');
                themeToggle.textContent = '☀️';
            } else {
                localStorage.setItem('theme', 'light');
                themeToggle.textContent = '🌙';
            }
        });
    }
});