/* ============================================================
   CYBER SHATS — AMALIYOT LABORATORIYASI (lab-sim.js)
   MUHIM: Bu fayl FAQAT vizual/o'quv maqsadli simulyatsiya skripti.
   Hech qanday haqiqiy tarmoq so'rovi, ekspluatatsiya yoki zaiflikdan
   foydalanish kodi YO'Q. Barcha "natijalar" oldindan yozilgan matn
   bo'lib, faqat interfeysni jonlantirish uchun ishlatiladi.
   ============================================================ */
(function () {
    var termBody = document.querySelector('[data-term-body]');
    var flagForm = document.querySelector('[data-flag-form]');
    var flagInput = document.querySelector('[data-flag-input]');
    var flagResult = document.querySelector('[data-flag-result]');
    var runBtn = document.querySelector('[data-run-attack]');
    var fakeForm = document.querySelector('[data-fake-login]');

    var SCRIPTED_OUTPUT = [
        { t: 'cmd', text: '$ sqlmap -u "http://demo-lab.local/login" --forms --batch' },
        { t: 'dim', text: '        ___' },
        { t: 'dim', text: '       __H__' },
        { t: 'dim', text: 'sqlmap demo-rejimi (o\'quv simulyatsiyasi)' },
        { t: 'ok', text: '[*] starting @ demo-mode' },
        { t: 'ok', text: '[*] testing connection to the target URL' },
        { t: 'ok', text: "[*] forma maydonlari aniqlandi: 'username', 'password'" },
        { t: 'ok', text: "[*] 'username' parametri SQL Injection ga moslikni tekshirish..." },
        { t: 'ok', text: "[+] parametr zaif (demo): boolean-based blind SQLi topildi" },
        { t: 'ok', text: '[*] backend DBMS: MySQL (demo ma\'lumotlar bazasi)' },
        { t: 'dim', text: '[*] jadval nomlari olinmoqda (faqat demo namuna)...' },
        { t: 'ok', text: 'users, courses, sessions' },
        { t: 'dim', text: '--- BU YERDA HAQIQIY HUJUM AMALGA OSHIRILMAYDI ---' },
        { t: 'ok', text: '[+] simulyatsiya yakunlandi. FLAG{demo_sqli_tushundim} ni topish uchun pastdagi maydonga kiriting.' },
    ];

    function appendLine(line) {
        if (!termBody) return;
        var div = document.createElement('div');
        div.className = 'line-' + (line.t || 'dim');
        div.textContent = line.text;
        termBody.appendChild(div);
        termBody.scrollTop = termBody.scrollHeight;
    }

    function runScriptedAttack() {
        if (!termBody) return;
        termBody.innerHTML = '';
        var i = 0;
        function next() {
            if (i >= SCRIPTED_OUTPUT.length) return;
            appendLine(SCRIPTED_OUTPUT[i]);
            i++;
            setTimeout(next, 260);
        }
        next();
    }

    if (runBtn) {
        runBtn.addEventListener('click', function (e) {
            e.preventDefault();
            runScriptedAttack();
        });
    }

    // Soxta login forma — faqat oldindan belgilangan demo payload kiritilganda
    // "muvaffaqiyatli" deb ko'rsatadigan klient tomonidagi animatsiya.
    if (fakeForm) {
        fakeForm.addEventListener('submit', function (e) {
            e.preventDefault();
            var userVal = (fakeForm.querySelector('[name="demo_user"]') || {}).value || '';
            var msgEl = fakeForm.querySelector('[data-fake-msg]');
            if (!msgEl) return;
            if (userVal.includes("' OR '1'='1")) {
                msgEl.textContent = '✓ Demo: autentifikatsiya chetlab o\'tildi (faqat o\'quv simulyatsiyasi)';
                msgEl.style.color = '#00ff41';
            } else {
                msgEl.textContent = '✗ Kirish rad etildi — SQLi payload\'ni sinab ko\'ring (masalan: \' OR \'1\'=\'1)';
                msgEl.style.color = '#ff4444';
            }
        });
    }

    if (flagForm) {
        flagForm.addEventListener('submit', function (e) {
            e.preventDefault();
            var val = (flagInput && flagInput.value || '').trim().toLowerCase();
            if (!flagResult) return;
            if (val === 'flag{demo_sqli_tushundim}') {
                flagResult.textContent = '✓ To\'g\'ri! Topshiriq yakunlandi, XP qo\'shildi.';
                flagResult.className = 'cs-alert';
                flagResult.style.color = '#00ff41';
                if (window.csMarkPracticeDone) window.csMarkPracticeDone();
            } else {
                flagResult.textContent = '✗ Noto\'g\'ri flag. Terminal natijasini diqqat bilan o\'qing.';
                flagResult.style.color = '#ff4444';
            }
        });
    }
})();
