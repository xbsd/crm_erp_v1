// System Health ----------------------------------------------------------------
(async function () {
    const [health, catalog, dbs] = await Promise.all([
        U.fetchJSON('/health'),
        U.fetchJSON('/api/catalog'),
        U.fetchJSON('/api/databases'),
    ]);

    const cards = document.getElementById('server-cards');
    cards.innerHTML = '';
    catalog.servers.forEach(s => {
        const count = catalog.tools.filter(t => t.server_name === s.name).length;
        const c = U.el('div', { class: `kpi accent-${s.name}` });
        c.append(U.el('div', { class: 'kpi-label' }, s.label));
        c.append(U.el('div', { class: 'kpi-value' }, count + ' tools'));
        c.append(U.el('div', { class: 'kpi-sub' }, 'stdio · live'));
        cards.append(c);
    });

    const r = document.getElementById('runtime-card');
    r.innerHTML = `
        <table class="data" style="font-size: 13px;">
            <tr><th>Property</th><th>Value</th></tr>
            <tr><td>Anthropic API Key</td><td>${health.anthropic_api_key ? '<span class="pill success">set</span>' : '<span class="pill danger">missing</span>'}</td></tr>
            <tr><td>Total tools loaded</td><td><span class="mono">${health.tools}</span></td></tr>
            <tr><td>MCP servers</td><td>${health.servers.map(s => `<span class="pill ${U.serverPillClass(s.name)}">${s.label} · ${s.tools} tools</span>`).join(' ')}</td></tr>
        </table>
    `;

    const inv = document.getElementById('db-inventory');
    inv.innerHTML = '';
    Object.entries(dbs).forEach(([db, info]) => {
        const card = U.el('details', { open: db === 'crm' ? true : null,
            style: { borderBottom: '1px solid var(--border-subtle)', padding: '10px 0' }});
        const sum = U.el('summary', { style: { cursor: 'pointer', display: 'flex', gap: '10px', alignItems: 'center' } },
            U.el('span', { html: U.pill(db.toUpperCase(), U.serverPillClass(db)).outerHTML }),
            U.el('span', { class: 'mono', style: { color: 'var(--text-tertiary)', fontSize: '12px' } }, info.path),
            U.el('span', { style: { marginLeft: 'auto', color: 'var(--text-tertiary)' } },
                `${info.tables.length} tables · ${info.tables.reduce((a, t) => a + t.row_count, 0).toLocaleString()} rows`),
        );
        card.append(sum);
        info.tables.forEach(t => {
            const block = U.el('div', { style: { padding: '10px 0 4px', borderTop: '1px dashed var(--border-subtle)', marginTop: '10px' } });
            block.append(U.el('div', { style: { fontWeight: 600, marginBottom: '4px' } },
                `${t.name} `,
                U.el('span', { style: { color: 'var(--text-tertiary)', fontSize: '12px', marginLeft: '6px' } },
                    `${t.row_count.toLocaleString()} rows · ${t.columns.length} columns`)));
            block.append(U.el('div', { style: { fontSize: '11px', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' } },
                t.columns.map(c => `${c.pk ? '★' : ''}${c.name}: ${c.type}${c.notnull ? '*' : ''}`).join(' · ')));
            card.append(block);
        });
        inv.append(card);
    });
})();
