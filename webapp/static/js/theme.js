// Theme toggle + server-strip live updates
(function () {
    const btn = document.getElementById('theme-toggle');
    const icon = document.getElementById('theme-icon');
    const label = document.getElementById('theme-label');

    function apply(theme) {
        document.documentElement.dataset.theme = theme;
        if (icon) icon.textContent = theme === 'dark' ? '☾' : '☼';
        if (label) label.textContent = theme === 'dark' ? 'DARK' : 'LIGHT';
        try { localStorage.setItem('theme', theme); } catch (e) {}
    }
    apply(document.documentElement.dataset.theme || 'dark');

    if (btn) {
        btn.addEventListener('click', () => {
            const cur = document.documentElement.dataset.theme;
            apply(cur === 'dark' ? 'light' : 'dark');
            // Re-render plotly charts if present
            if (window.Plotly) {
                document.querySelectorAll('[id^="chart-"]').forEach(el => {
                    if (el && el._fullLayout) Plotly.Plots.resize(el);
                });
            }
            window.dispatchEvent(new CustomEvent('theme-change', { detail: { theme: document.documentElement.dataset.theme } }));
        });
    }

    // Health check updates the live pill
    fetch('/health').then(r => r.json()).then(j => {
        const ok = j.anthropic_api_key && j.tools > 0;
        const pill = document.querySelector('.live-pill');
        if (pill && !ok) {
            pill.style.opacity = 0.4;
            pill.querySelector('.live-dot').style.background = 'var(--neg)';
            pill.style.color = 'var(--neg)';
            pill.lastChild.textContent = ' OFFLINE';
        }
    }).catch(() => {});
})();
