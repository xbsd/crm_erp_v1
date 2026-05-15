// Data Model page — live table inventory with sample previews -----------------
(async function () {
    const dbs = await U.fetchJSON('/api/databases');
    const root = document.getElementById('db-tables');
    root.innerHTML = '';

    Object.entries(dbs).forEach(([db, info]) => {
        const header = U.el('h3', { style: { marginTop: '14px' } },
            U.el('span', { html: U.pill(db.toUpperCase(), U.serverPillClass(db)).outerHTML }),
            U.el('span', { style: { marginLeft: '8px', fontWeight: 500 } }, info.tables.length + ' tables'));
        root.append(header);

        info.tables.forEach(t => {
            const det = U.el('details', {
                style: { borderBottom: '1px solid var(--border-soft)', padding: '10px 4px' }
            });
            const sum = U.el('summary', { style: { cursor: 'pointer' } },
                U.el('span', { class: 'mono', style: { fontWeight: 600 } }, t.name),
                U.el('span', { style: { color: 'var(--text-faint)', marginLeft: '8px', fontSize: '12px' } },
                    `${t.row_count.toLocaleString()} rows · ${t.columns.length} columns`));
            det.append(sum);

            // Columns
            const cols = U.el('div', { style: { margin: '8px 0', fontSize: '11.5px', color: 'var(--text-faint)', fontFamily: 'var(--font-mono, JetBrains Mono, ui-monospace)' } },
                t.columns.map(c =>
                    `${c.pk ? '★' : ''}${c.name}<span style="opacity:0.7;">: ${c.type}${c.notnull ? '*' : ''}</span>`,
                ).join('  ·  '));
            cols.innerHTML = cols.innerHTML;
            det.append(cols);

            // Sample preview — lazy load on first expansion
            const previewBox = U.el('div', { style: { marginTop: '6px' } });
            const loadBtn = U.el('button', { class: 'btn ghost sm', type: 'button' }, '👁 Show 10 rows');
            loadBtn.addEventListener('click', async () => {
                loadBtn.replaceWith(U.el('span', { class: 'spinner' }));
                try {
                    const sample = await U.fetchJSON(`/api/table/${db}/${t.name}?limit=10`);
                    if (!sample.rows.length) {
                        previewBox.innerHTML = '<div class="muted">(empty)</div>';
                    } else {
                        const cols0 = Object.keys(sample.rows[0]).slice(0, 7);
                        const tbl = U.table(sample.rows, cols0.map(k => ({
                            label: k, key: k, value: r => {
                                const v = r[k]; return v == null ? '—' : String(v).slice(0, 60);
                            },
                        })));
                        previewBox.innerHTML = '';
                        previewBox.append(U.el('div', { class: 'table-wrap' }, tbl));
                    }
                } catch (e) {
                    previewBox.textContent = 'Error: ' + e.message;
                }
            });
            previewBox.append(loadBtn);
            det.append(previewBox);
            root.append(det);
        });
    });
})();
