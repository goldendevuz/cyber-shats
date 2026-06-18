// CYBER SHATS — Hero bo'limlardagi kichik aylanuvchi globe (avto-ishga tushish)
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-globe]').forEach(function (el) {
        csCreateGlobe(el.id, { speed: 0.0022, cameraZ: 5.4 });
    });
});
