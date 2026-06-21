// CYBER SHATS — Hero bo'limlardagi kichik aylanuvchi globe (avto-ishga tushish)
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-globe]').forEach(function (el) {
        var speed = parseFloat(el.getAttribute('data-speed')) || 0.0022;
        var cameraZ = parseFloat(el.getAttribute('data-camera-z')) || 5.4;
        csCreateGlobe(el.id, { speed: speed, cameraZ: cameraZ });
    });
});
