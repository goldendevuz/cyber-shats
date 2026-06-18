/* ============================================================
   CYBER SHATS — KIRISH ANIMATSIYASI (4 bosqichli intro)
   1) 0-2s qora fon + aylanuvchi globus
   2) 1-3s matrix kod yomg'iri + "CYBER SHATS" matni
   3) 2-4s globus ochiladi, yo'nalish ikonkalari orbitaga chiqadi
   4) 4-6s ENTER tugmasi va HUD ko'rinadi
   ============================================================ */
(function () {
    var overlay = document.getElementById('intro-overlay');
    if (!overlay) return;

    var SKIP_KEY = 'cs_intro_seen';
    if (sessionStorage.getItem(SKIP_KEY)) {
        overlay.style.display = 'none';
        document.body.classList.add('intro-done');
        return;
    }

    var bootLines = document.querySelector('.boot-lines');
    var introText = document.querySelector('.intro-text');
    var skipBtn = document.querySelector('.skip-intro');
    var enterBtn = document.getElementById('intro-enter-btn');
    var globeHandle = null;

    var bootMessages = [
        '> tizim ishga tushirilmoqda...',
        '> xavfsizlik protokollari yuklanmoqda...',
        '> CYBER SHATS yadrosi initsializatsiya qilinmoqda...',
        '> aloqa o\'rnatildi: cyber.shats.uz'
    ];

    function typeBootLines() {
        if (!bootLines) return;
        var i = 0;
        function next() {
            if (i >= bootMessages.length) return;
            var line = document.createElement('div');
            bootLines.appendChild(line);
            var text = bootMessages[i];
            var j = 0;
            var iv = setInterval(function () {
                line.textContent = text.slice(0, j + 1);
                j++;
                if (j >= text.length) {
                    clearInterval(iv);
                    i++;
                    setTimeout(next, 220);
                }
            }, 18);
        }
        next();
    }

    function finishIntro() {
        sessionStorage.setItem(SKIP_KEY, '1');
        overlay.classList.add('hide');
        document.body.classList.add('intro-done');
        setTimeout(function () {
            if (globeHandle && globeHandle.destroy) globeHandle.destroy();
            overlay.style.display = 'none';
        }, 850);
    }

    // Bosqich 1: globus yaratish
    if (window.csCreateGlobe) {
        globeHandle = window.csCreateGlobe('globe-container', { speed: 0.006, cameraZ: 4.2, dense: true });
    }
    typeBootLines();

    // Bosqich 2: matn paydo bo'lishi (~1.4s)
    setTimeout(function () {
        if (introText) introText.classList.add('show');
    }, 1400);

    // Bosqich 3: orbita ikonkalari (~2.8s) — CSS klass orqali
    setTimeout(function () {
        overlay.classList.add('stage-orbit');
        if (globeHandle && globeHandle.setSpeed) globeHandle.setSpeed(0.0025);
    }, 2800);

    // Bosqich 4: ENTER tugmasi va HUD (~4.4s)
    setTimeout(function () {
        overlay.classList.add('stage-final');
    }, 4400);

    // Avtomatik o'tish (foydalanuvchi bosmasa ham 7.5s da davom etadi)
    var autoTimer = setTimeout(finishIntro, 7500);

    if (enterBtn) {
        enterBtn.addEventListener('click', function () {
            clearTimeout(autoTimer);
            finishIntro();
        });
    }
    if (skipBtn) {
        skipBtn.addEventListener('click', function () {
            clearTimeout(autoTimer);
            finishIntro();
        });
    }
})();
