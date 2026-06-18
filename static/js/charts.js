/* ============================================================
   CYBER SHATS — Admin panel grafiklari (Chart.js)
   Ma'lumotlar window.CS_ADMIN_DATA orqali shablon ichida uzatiladi.
   ============================================================ */
(function () {
    if (typeof Chart === 'undefined' || !window.CS_ADMIN_DATA) return;
    var d = window.CS_ADMIN_DATA;

    Chart.defaults.color = '#007a20';
    Chart.defaults.font.family = "'Share Tech Mono', monospace";

    var lineCanvas = document.getElementById('activityChart');
    if (lineCanvas) {
        new Chart(lineCanvas, {
            type: 'line',
            data: {
                labels: d.dayLabels,
                datasets: [{
                    label: 'Faol foydalanuvchilar',
                    data: d.activitySeries,
                    borderColor: '#00ff41',
                    backgroundColor: 'rgba(0,255,65,0.12)',
                    pointBackgroundColor: '#00ff41',
                    tension: 0.35,
                    fill: true,
                }]
            },
            options: {
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: 'rgba(0,255,65,0.08)' } },
                    y: { grid: { color: 'rgba(0,255,65,0.08)' }, beginAtZero: true }
                }
            }
        });
    }

    var donutCanvas = document.getElementById('sourceDonut');
    if (donutCanvas) {
        new Chart(donutCanvas, {
            type: 'doughnut',
            data: {
                labels: d.sourceLabels,
                datasets: [{
                    data: d.sourceSeries,
                    backgroundColor: ['#00ff41', '#00ccff', '#ffd23f', '#007a20'],
                    borderColor: '#000010',
                    borderWidth: 2,
                }]
            },
            options: {
                plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } },
                cutout: '68%'
            }
        });
    }
})();
