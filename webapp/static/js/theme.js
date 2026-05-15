// Theme toggle
(function () {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    function apply(theme) {
        document.documentElement.dataset.theme = theme;
        btn.textContent = theme === 'dark' ? '☾' : '☼';
        try { localStorage.setItem('theme', theme); } catch (e) {}
    }
    apply(document.documentElement.dataset.theme || 'light');

    btn.addEventListener('click', () => {
        const cur = document.documentElement.dataset.theme;
        apply(cur === 'dark' ? 'light' : 'dark');
    });

    // Health check — show server pills correctly
    fetch('/health').then(r => r.json()).then(j => {
        const ok = j.anthropic_api_key && j.tools > 0;
        document.querySelectorAll('.server-pill').forEach(p => p.style.opacity = ok ? 1 : 0.4);
    }).catch(() => {});
})();
