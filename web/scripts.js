document.addEventListener('DOMContentLoaded', function() {
    updateTime();
});

function updateTime() {
    const now = new Date();
    document.getElementById("updateTime").textContent = now.toLocaleString("en-GB", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false
    });
}
