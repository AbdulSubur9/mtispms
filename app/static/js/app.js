document.addEventListener("DOMContentLoaded", function () {
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("appSidebar");
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", function () {
            sidebar.classList.toggle("show");
        });
    }

    const themeToggle = document.getElementById("themeToggle");
    const html = document.documentElement;
    // restore saved theme preference
    const savedTheme = localStorage.getItem("mtispms-theme");
    if (savedTheme) html.setAttribute("data-bs-theme", savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            const current = html.getAttribute("data-bs-theme");
            const next = current === "dark" ? "light" : "dark";
            html.setAttribute("data-bs-theme", next);
            localStorage.setItem("mtispms-theme", next);
        });
    }

    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll(".alert").forEach(function (alertEl) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });
});

function confirmDelete(message) {
    return confirm(message || "Are you sure you want to delete this item? This action cannot be undone.");
}
