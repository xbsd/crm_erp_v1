// Tool Catalog -----------------------------------------------------------------
(async function () {
    const data = await U.fetchJSON('/api/catalog');
    const root = document.getElementById('catalog');
    const search = document.getElementById('search');

    const grouped = {};
    data.tools.forEach(t => {
        if (!grouped[t.server_name]) grouped[t.server_name] = { label: t.server_label, name: t.server_name, tools: [] };
        grouped[t.server_name].tools.push(t);
    });

    function render(filter = '') {
        root.innerHTML = '';
        const f = filter.toLowerCase();
        Object.values(grouped).forEach(g => {
            const matching = g.tools.filter(t => !f || t.name.toLowerCase().includes(f) || (t.description || '').toLowerCase().includes(f));
            if (matching.length === 0) return;
            const card = U.el('div', { class: 'card', style: { marginBottom: '20px' } });
            const head = U.el('div', { class: 'card-header' },
                U.el('div', { class: 'card-title' },
                    U.el('span', { html: U.pill(g.label, U.serverPillClass(g.name)).outerHTML }),
                    ` · ${matching.length} tools`,
                ),
            );
            card.append(head);
            const body = U.el('div', { class: 'card-body' });
            matching.forEach(t => body.append(toolRow(t)));
            card.append(body);
            root.append(card);
        });
    }

    function toolRow(t) {
        const row = U.el('details', { style: {
            borderBottom: '1px solid var(--border-subtle)', padding: '12px 0',
        }});
        const summary = U.el('summary', { style: { cursor: 'pointer', userSelect: 'none' } });
        summary.innerHTML = `<span class="mono" style="font-weight:600;">${t.name}</span>
            <div style="color: var(--text-tertiary); font-size: 12.5px; margin-top: 4px;">${t.description}</div>`;
        row.append(summary);
        // Form + try it
        const form = U.el('form', { style: { marginTop: '12px' } });
        const props = (t.input_schema && t.input_schema.properties) || {};
        const required = new Set((t.input_schema && t.input_schema.required) || []);
        Object.entries(props).forEach(([key, sch]) => {
            const label = U.el('label', { class: 'field' });
            label.append(U.el('span', {}, `${key}${required.has(key) ? ' *' : ''}${sch.description ? ` — ${sch.description}` : ''}`));
            let input;
            if (sch.enum) {
                input = U.el('select', { class: 'select', name: key });
                input.append(U.el('option', { value: '' }, '—'));
                sch.enum.forEach(v => input.append(U.el('option', { value: String(v) }, String(v))));
            } else {
                input = U.el('input', {
                    class: 'input', name: key,
                    type: sch.type === 'integer' || sch.type === 'number' ? 'number' : 'text',
                    placeholder: sch.default != null ? `default: ${sch.default}` : '',
                });
            }
            label.append(input);
            form.append(label);
        });
        const result = U.el('pre', { class: 'code', style: { display: 'none', marginTop: '12px' } });
        const btn = U.el('button', { class: 'btn primary sm', type: 'submit' }, '▶ Invoke');
        const status = U.el('span', { style: { marginLeft: '10px', fontSize: '12px', color: 'var(--text-tertiary)' } });
        const actionRow = U.el('div', { style: { display: 'flex', alignItems: 'center' } }, btn, status);
        form.append(actionRow);
        form.append(result);

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const args = {};
            const fd = new FormData(form);
            for (const [k, v] of fd.entries()) {
                if (v === '') continue;
                const sch = props[k];
                if (sch.type === 'integer') args[k] = parseInt(v, 10);
                else if (sch.type === 'number') args[k] = parseFloat(v);
                else if (sch.type === 'boolean') args[k] = v === 'true';
                else args[k] = v;
            }
            status.textContent = 'Running…';
            result.style.display = 'none';
            try {
                const t0 = performance.now();
                const r = await U.fetchJSON('/api/invoke-tool', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tool_name: t.name, arguments: args }),
                });
                const dt = ((performance.now() - t0) / 1000).toFixed(2);
                status.textContent = `✓ ${dt}s`;
                result.style.display = '';
                result.textContent = JSON.stringify(r.result, null, 2);
            } catch (err) {
                status.textContent = '✗ ' + err.message;
            }
        });
        row.append(form);
        return row;
    }

    search.addEventListener('input', () => render(search.value));
    render();
})();
