// CYBER SHATS — HUD jonli ma'lumotlari (vaqt, uptime, online sonlar)
(function () {
    const BUILD_DATE = new Date('2026-01-01T00:00:00');

    function pad(n) { return n.toString().padStart(2, '0'); }

    function tick() {
        const now = new Date();
        const timeEl = document.getElementById('hud-time');
        if (timeEl) timeEl.textContent = 'VAQT: ' + pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());

        const diffMs = now - BUILD_DATE;
        const days = Math.floor(diffMs / 86400000);
        const hrs = Math.floor((diffMs % 86400000) / 3600000);
        const mins = Math.floor((diffMs % 3600000) / 60000);
        const secs = Math.floor((diffMs % 60000) / 1000);
        const uptimeEl = document.getElementById('hud-uptime');
        if (uptimeEl) uptimeEl.textContent = 'UPTIME: ' + days + 'D ' + pad(hrs) + ':' + pad(mins) + ':' + pad(secs);
    }
    setInterval(tick, 1000);
    tick();

    // Online foydalanuvchilar sonini biroz "tirik" ko'rsatish (vizual effekt, demo)
    const onlineEl = document.getElementById('hud-online');
    if (onlineEl) {
        let base = parseInt(onlineEl.dataset.base || '1248', 10);
        setInterval(() => {
            const delta = Math.floor(Math.random() * 7) - 3;
            base = Math.max(900, base + delta);
            onlineEl.textContent = base.toLocaleString('en-US');
        }, 3500);
    }
})();
