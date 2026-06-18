// CYBER SHATS — Umumiy interaktivlik (mobil sidebar, parol ko'rsatish va h.k.)
(function () {
    const toggleBtns = document.querySelectorAll('[data-toggle="sidebar"]');
    const sidebar = document.querySelector('.cs-sidebar');
    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            sidebar && sidebar.classList.toggle('open');
            document.body.classList.toggle('sidebar-open');
        });
    });
    document.body.addEventListener('click', (e) => {
        if (document.body.classList.contains('sidebar-open') && sidebar && !sidebar.contains(e.target) && !e.target.closest('[data-toggle="sidebar"]')) {
            sidebar.classList.remove('open');
            document.body.classList.remove('sidebar-open');
        }
    });

    // Parolni ko'rsatish/yashirish
    document.querySelectorAll('.toggle-eye').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = btn.parentElement.querySelector('input');
            if (!input) return;
            input.type = input.type === 'password' ? 'text' : 'password';
        });
    });

    // Tab almashtirish (data-tabs komponenti)
    document.querySelectorAll('[data-tabs]').forEach(group => {
        const tabs = group.querySelectorAll('.cs-tab');
        const panels = document.querySelectorAll('[data-tab-panel="' + group.dataset.tabs + '"]');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                panels.forEach(p => p.style.display = (p.dataset.panel === tab.dataset.panel) ? '' : 'none');
            });
        });
    });

    // Mobil topbar qidiruv ochish/yopish (agar mavjud bo'lsa)
    document.querySelectorAll('[data-mobile-search]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelector('.app-topbar .search-box')?.classList.toggle('show-mobile');
        });
    });
})();
