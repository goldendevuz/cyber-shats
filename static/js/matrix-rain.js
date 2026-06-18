// CYBER SHATS — Matritsa kodi yomg'iri (fon effekti)
(function () {
    const canvas = document.getElementById('matrix-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let w, h, columns, drops;
    const chars = '01アイウエオカキクケコサシスセソタチツテト$+-*/=%"\'#&_(),.;:?!\\|{}<>[]^~ABCDEFGHIJKLMNOPQRSTUVWXYZ';

    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
        columns = Math.floor(w / 16);
        drops = new Array(columns).fill(1);
    }
    window.addEventListener('resize', resize);
    resize();

    function draw() {
        ctx.fillStyle = 'rgba(0,0,16,0.07)';
        ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = '#00ff41';
        ctx.font = '14px monospace';
        for (let i = 0; i < drops.length; i++) {
            const text = chars[Math.floor(Math.random() * chars.length)];
            ctx.fillText(text, i * 16, drops[i] * 16);
            if (drops[i] * 16 > h && Math.random() > 0.975) drops[i] = 0;
            drops[i]++;
        }
    }
    setInterval(draw, 45);
})();
