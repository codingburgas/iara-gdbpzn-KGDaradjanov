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