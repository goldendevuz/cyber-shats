/**
 * CYBER SHATS V1.3 — Ovozli bildirishnoma tizimi
 *
 * Foydalanuvchi sahifaga bossanidan keyin ovoz yoqiladi (brauzer xavfsizlik qoidasi).
 * Pastki o'ng burchakda doimo turuvchi tugma orqali ovozni yoqish/o'chirish mumkin.
 *
 * Holat localStorage'da saqlanadi:
 *   cs_sound_pref = "on" / "off" / "" (boshlang'ich, foydalanuvchi hali tanlamagan)
 */
(function() {
    'use strict';

    var pollIntervalMs = 15000;
    var seenNotifIds = new Set();
    var seenAnnIds = new Set();
    var audioCtx = null;

    function isLoggedIn() {
        return document.body.classList.contains('has-sidebar') ||
               document.querySelector('[data-current-user]') !== null ||
               document.body.classList.contains('treasury-session');
    }
    if (!isLoggedIn()) return;

    var isTreasury = document.body.classList.contains('treasury-session');

    // ---- Sozlamalar (localStorage) ----
    function getPref() { return localStorage.getItem('cs_sound_pref') || ''; }
    function setPref(v) { localStorage.setItem('cs_sound_pref', v); }
    function isSoundOn() { return getPref() === 'on'; }

    // ---- Toast konteyner ----
    var container = document.createElement('div');
    container.id = 'voice-notif-container';
    container.style.cssText =
        'position:fixed; top:80px; right:20px; z-index:9999; ' +
        'display:flex; flex-direction:column; gap:10px; max-width:380px; ' +
        'pointer-events:none;';
    document.body.appendChild(container);

    // ---- O'ng pastdagi doimiy boshqaruv tugmasi ----
    var ctrlBtn = document.createElement('button');
    ctrlBtn.id = 'cs-sound-toggle';
    ctrlBtn.title = 'Ovozli bildirishnomalar';
    ctrlBtn.style.cssText =
        'position:fixed; bottom:20px; right:20px; z-index:9998; ' +
        'width:50px; height:50px; border-radius:50%; cursor:pointer; ' +
        'border:0; font-size:22px; ' +
        'box-shadow:0 4px 16px rgba(0,0,0,.3); ' +
        'transition:transform .15s, box-shadow .15s;';
    ctrlBtn.onmouseenter = function() { ctrlBtn.style.transform = 'scale(1.08)'; };
    ctrlBtn.onmouseleave = function() { ctrlBtn.style.transform = 'scale(1)'; };
    document.body.appendChild(ctrlBtn);

    function refreshBtn() {
        if (isSoundOn()) {
            ctrlBtn.style.background = 'linear-gradient(135deg,#00ff41,#00cc33)';
            ctrlBtn.style.color = '#000';
            ctrlBtn.innerHTML = '🔔';
            ctrlBtn.title = 'Ovoz yoqilgan — o\'chirish uchun bosing';
        } else if (getPref() === 'off') {
            ctrlBtn.style.background = 'rgba(40,40,50,.95)';
            ctrlBtn.style.color = '#888';
            ctrlBtn.innerHTML = '🔕';
            ctrlBtn.title = 'Ovoz o\'chirilgan — yoqish uchun bosing';
        } else {
            ctrlBtn.style.background = 'linear-gradient(135deg,#ffd23f,#ffb800)';
            ctrlBtn.style.color = '#000';
            ctrlBtn.innerHTML = '🔔';
            ctrlBtn.title = 'Ovozli bildirishnomalarni yoqish uchun bosing';
        }
    }

    ctrlBtn.addEventListener('click', function() {
        if (isSoundOn()) {
            setPref('off');
            // To'xtatib qo'yamiz, agar gapirayotgan bo'lsa
            try { window.speechSynthesis.cancel(); } catch(e) {}
            refreshBtn();
            showToast('Ovoz', 'Ovozli bildirishnomalar o\'chirildi', 'info', null);
        } else {
            setPref('on');
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                if (audioCtx.state === 'suspended') audioCtx.resume();
                var u = new SpeechSynthesisUtterance(' ');
                window.speechSynthesis.speak(u);
            } catch(e) {}
            refreshBtn();
            showToast('Ovoz', 'Ovozli bildirishnomalar yoqildi', 'success', 'notification');
            checkAnnouncements();
            checkNotifications();
            // Saytdan chiqib ketganda ham bildirishnoma kelishi uchun Web Push so'raymiz
            if (window.CyberShatsPush && window.CyberShatsPush.isSupported) {
                window.CyberShatsPush.subscribe().then(function(ok) {
                    if (ok) {
                        showToast('Push bildirishnoma', 'Saytdan chiqib ketsangiz ham xabar olasiz', 'success', null);
                    }
                });
            }
        }
    });
    refreshBtn();

    // ---- Toast kartochka ----
    function showToast(title, body, type, soundType) {
        var card = document.createElement('div');
        var colors = {
            announcement: { bg:'linear-gradient(135deg,#ffd23f,#ffb800)', text:'#000', border:'#ffd23f' },
            urgent:       { bg:'linear-gradient(135deg,#ff3366,#cc0033)', text:'#fff', border:'#ff3366' },
            success:      { bg:'rgba(0,255,65,.95)', text:'#000', border:'#00ff41' },
            error:        { bg:'rgba(255,85,85,.95)', text:'#fff', border:'#ff5555' },
            info:         { bg:'rgba(20,30,40,.95)', text:'#fff', border:'#00ff41' }
        };
        var style = colors[type] || colors.info;
        card.style.cssText =
            'background:' + style.bg + '; color:' + style.text + '; ' +
            'padding:14px 16px; border-radius:8px; border-left:4px solid ' + style.border + '; ' +
            'box-shadow:0 6px 24px rgba(0,0,0,.3); font-size:13px; ' +
            'animation:csSlideIn .3s ease-out; max-width:380px; cursor:pointer; ' +
            'pointer-events:auto;';
        card.innerHTML =
            '<div style="font-weight:700; margin-bottom:4px;">' + esc(title) + '</div>' +
            (body ? '<div style="font-size:12px; opacity:.92; line-height:1.45;">' + esc(body) + '</div>' : '');
        card.onclick = function() { fadeOut(card); };
        container.appendChild(card);

        if (isSoundOn() && soundType) {
            playBeep(soundType);
            speak(title + '. ' + (body || ''));
        }
        setTimeout(function() { fadeOut(card); }, 8000);
    }

    function fadeOut(el) {
        el.style.transition = 'opacity .3s, transform .3s';
        el.style.opacity = '0';
        el.style.transform = 'translateX(20px)';
        setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 300);
    }
    function esc(s) {
        if (!s) return '';
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    // ---- Ovoz signali (Web Audio) ----
    function playBeep(type) {
        if (!isSoundOn()) return;
        try {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            if (audioCtx.state === 'suspended') audioCtx.resume();
            var osc = audioCtx.createOscillator();
            var gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            // Mayinroq, sokinroq ohang — kamroq baland chastota, sekinroq fade-in/out
            var freq = type === 'announcement' ? 660 : (type === 'urgent' ? 880 : 520);
            osc.frequency.value = freq;
            osc.type = 'sine';
            var now = audioCtx.currentTime;
            gain.gain.setValueAtTime(0.0001, now);
            gain.gain.exponentialRampToValueAtTime(0.08, now + 0.08);  // sekin ko'tariladi
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.6); // sekin pasayadi
            osc.start(now);
            osc.stop(now + 0.6);
        } catch(e) {}
    }

    // ---- TTS (o'zbek tilini izlash, fallback turk/rus/ingliz) ----
    var preferredVoice = null;
    function findUzbekVoice() {
        if (!window.speechSynthesis) return null;
        var voices = window.speechSynthesis.getVoices();
        if (!voices.length) return null;
        // Avval aniq o'zbek (uz-UZ)
        var uz = voices.find(function(v) { return v.lang.toLowerCase().startsWith('uz'); });
        if (uz) return uz;
        // Keyin turk (yaqin)
        var tr = voices.find(function(v) { return v.lang.toLowerCase().startsWith('tr'); });
        if (tr) return tr;
        // Keyin rus
        var ru = voices.find(function(v) { return v.lang.toLowerCase().startsWith('ru'); });
        if (ru) return ru;
        // Keyin ingliz
        var en = voices.find(function(v) { return v.lang.toLowerCase().startsWith('en'); });
        if (en) return en;
        return voices[0];
    }
    if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = function() { preferredVoice = findUzbekVoice(); };
        setTimeout(function() { if (!preferredVoice) preferredVoice = findUzbekVoice(); }, 500);
    }

    function speak(text) {
        if (!isSoundOn() || !window.speechSynthesis) return;
        if (!text || text.trim().length === 0) return;
        try {
            window.speechSynthesis.cancel();
            var utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'uz-UZ';
            utterance.rate = 0.8;
            utterance.pitch = 0.95;
            utterance.volume = 0.8;
            if (!preferredVoice) preferredVoice = findUzbekVoice();
            if (preferredVoice) utterance.voice = preferredVoice;
            window.speechSynthesis.speak(utterance);
        } catch(e) {}
    }

    // ---- Polling: e'lonlar va bildirishnomalar (oddiy foydalanuvchi) ----
    function checkAnnouncements() {
        if (isTreasury) return;
        fetch('/api/announcements/pending', { credentials:'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (!d.success || !d.data || !d.data.announcements) return;
                d.data.announcements.forEach(function(a) {
                    if (seenAnnIds.has(a.id)) return;
                    seenAnnIds.add(a.id);
                    var soundType = a.priority === 'urgent' ? 'urgent' : 'announcement';
                    var toastType = a.priority === 'urgent' ? 'urgent' : 'announcement';
                    showToast('📢 ' + a.title, a.body, toastType, soundType);
                    fetch('/api/announcements/' + a.id + '/seen',
                          { method:'POST', credentials:'same-origin' });
                });
            }).catch(function() {});
    }
    function checkNotifications() {
        if (isTreasury) {
            checkTreasuryNotifications();
            return;
        }
        fetch('/api/notifications/pending', { credentials:'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (!d.success || !d.data || !d.data.notifications) return;
                d.data.notifications.forEach(function(n) {
                    if (seenNotifIds.has(n.id)) return;
                    if (n.type === 'announcement') return;
                    seenNotifIds.add(n.id);
                    var ttype = n.type === 'error' ? 'error' :
                                (n.type === 'success' ? 'success' : 'info');
                    showToast('🔔 ' + n.title, n.body, ttype, 'notification');
                    fetch('/api/notifications/' + n.id + '/read',
                          { method:'POST', credentials:'same-origin' });
                });
            }).catch(function() {});
    }

    // ---- G'azna uchun: yangi bot to'lov so'rovlari haqida ovozli xabar ----
    function checkTreasuryNotifications() {
        fetch('/api/treasury/notifications/pending', { credentials:'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (!d.success || !d.data || !d.data.items) return;
                d.data.items.forEach(function(n) {
                    if (seenNotifIds.has('t' + n.id)) return;
                    seenNotifIds.add('t' + n.id);
                    showToast('🔔 ' + n.title, n.body, 'info', 'notification');
                });
            }).catch(function() {});
    }

    var styleEl = document.createElement('style');
    styleEl.textContent =
        '@keyframes csSlideIn {' +
        '  from { opacity:0; transform:translateX(50px); }' +
        '  to { opacity:1; transform:translateX(0); }' +
        '}';
    document.head.appendChild(styleEl);

    // Birinchi marta yoqilgan bo'lsa — boshqa sahifaga o'tganda ham gapirsin
    if (isSoundOn()) {
        var onFirstAct = function() {
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                if (audioCtx.state === 'suspended') audioCtx.resume();
                var u = new SpeechSynthesisUtterance(' ');
                window.speechSynthesis.speak(u);
            } catch(e) {}
            document.removeEventListener('click', onFirstAct);
        };
        document.addEventListener('click', onFirstAct, { once: true });
    }

    setTimeout(function() {
        checkAnnouncements();
        checkNotifications();
    }, 2500);
    setInterval(checkAnnouncements, pollIntervalMs);
    setInterval(checkNotifications, pollIntervalMs);

    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            checkAnnouncements();
            checkNotifications();
        }
    });
})();
