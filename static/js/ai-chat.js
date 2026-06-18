/* ============================================================
   CYBER SHATS — AI Yordamchi chat interfeysi (frontend logikasi)
   ============================================================ */
(function () {
    var msgsBox = document.querySelector('[data-chat-msgs]');
    var form = document.querySelector('[data-chat-form]');
    var input = document.querySelector('[data-chat-input]');
    var typeInput = document.querySelector('[data-chat-type]');
    if (!form || !msgsBox) return;

    function addMsg(role, text) {
        var div = document.createElement('div');
        div.className = 'msg ' + (role === 'user' ? 'user' : 'bot');
        div.textContent = text;
        msgsBox.appendChild(div);
        msgsBox.scrollTop = msgsBox.scrollHeight;
        return div;
    }

    function addTyping() {
        var div = document.createElement('div');
        div.className = 'msg bot typing-dots';
        div.innerHTML = '<span></span><span></span><span></span>';
        msgsBox.appendChild(div);
        msgsBox.scrollTop = msgsBox.scrollHeight;
        return div;
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        var text = (input.value || '').trim();
        if (!text) return;
        addMsg('user', text);
        input.value = '';
        var typingEl = addTyping();

        fetch('/api/ai/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, type: typeInput ? typeInput.value : 'umumiy' })
        })
            .then(function (r) { return r.json(); })
            .then(function (res) {
                typingEl.remove();
                if (res.success) {
                    addMsg('assistant', res.data.reply);
                } else {
                    addMsg('assistant', 'Xatolik yuz berdi: ' + (res.error || 'noma\'lum xato'));
                }
            })
            .catch(function () {
                typingEl.remove();
                addMsg('assistant', 'Tarmoq xatosi yuz berdi. Internetingizni tekshirib, qayta urinib ko\'ring.');
            });
    });
})();
