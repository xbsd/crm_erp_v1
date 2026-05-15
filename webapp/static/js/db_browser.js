// Database Browser ------------------------------------------------------------
(async function () {
    const dbSelect    = document.getElementById('db-select');
    const tblSelect   = document.getElementById('table-select');
    const colSelect   = document.getElementById('col-select');
    const qInput      = document.getElementById('q-input');
    const limitSelect = document.getElementById('limit-select');
    const resetBtn    = document.getElementById('reset-btn');
    const prevBtn     = document.getElementById('prev-btn');
    const nextBtn     = document.getElementById('next-btn');
    const titleTbl    = document.getElementById('title-table');
    const titleCnt    = document.getElementById('title-counts');
    const pageLbl     = document.getElementById('page-label');
    const rowsWrap    = document.getElementById('rows-wrap');

    const inv = await U.fetchJSON('/api/databases');   // {crm:{tables:[…]}, erp:…, qa:…}
    let offset = 0;
    let debounceTimer = null;

    function tablesFor(db) {
        return (inv[db] && inv[db].tables) ? inv[db].tables : [];
    }

    function populateTableSelect() {
        const db = dbSelect.value;
        const tables = tablesFor(db);
        tblSelect.innerHTML = '';
        tables.forEach(t => {
            const o = U.el('option', { value: t.name },
                `${t.name}  (${t.row_count.toLocaleString()} rows)`);
            tblSelect.append(o);
        });
        if (tables.length) tblSelect.value = tables[0].name;
    }

    function populateColumnSelect() {
        const db = dbSelect.value;
        const tbl = tblSelect.value;
        const entry = tablesFor(db).find(t => t.name === tbl);
        colSelect.innerHTML = '<option value="">(all text columns)</option>';
        if (!entry) return;
        entry.columns.forEach(c => {
            colSelect.append(U.el('option', { value: c.name }, `${c.name}  (${c.type || '?'})`));
        });
    }

    async function load() {
        const db = dbSelect.value;
        const tbl = tblSelect.value;
        const col = colSelect.value;
        const q   = qInput.value.trim();
        const limit = parseInt(limitSelect.value, 10) || 50;
        if (!db || !tbl) return;

        titleTbl.textContent = `${db}.${tbl}`;
        rowsWrap.innerHTML = '<div class="muted mono"><span class="spinner"></span> Loading…</div>';

        const params = new URLSearchParams({ limit, offset });
        if (q) params.set('q', q);
        if (col) params.set('col', col);
        let data;
        try {
            data = await U.fetchJSON(`/api/table/${db}/${tbl}?${params}`);
        } catch (e) {
            rowsWrap.innerHTML = `<div class="muted mono">Error: ${e.message}</div>`;
            return;
        }

        const total = data.total_rows;
        const pageStart = total === 0 ? 0 : offset + 1;
        const pageEnd = offset + data.row_count;
        titleCnt.textContent = `${data.row_count} of ${total.toLocaleString()} matching rows · ${data.columns.length} cols`;
        pageLbl.textContent = total === 0
            ? '0'
            : `${pageStart.toLocaleString()}–${pageEnd.toLocaleString()} of ${total.toLocaleString()}`;

        prevBtn.disabled = offset === 0;
        nextBtn.disabled = pageEnd >= total;

        if (!data.rows.length) {
            rowsWrap.innerHTML = '<div class="muted mono" style="padding: 36px 0; text-align:center;">No rows match.</div>';
            return;
        }

        const tbl_el = U.table(data.rows, data.columns.map(c => ({
            label: c,
            key: c,
            num: typeof data.rows[0][c] === 'number',
            value: r => {
                const v = r[c];
                if (v == null) return '<span class="muted">—</span>';
                const s = String(v);
                return s.length > 80
                    ? `<span title="${s.replace(/"/g, '&quot;')}">${s.slice(0, 80)}…</span>`
                    : s;
            },
            html: true,
        })));
        rowsWrap.innerHTML = '';
        rowsWrap.append(U.el('div', { class: 'table-wrap' }, tbl_el));
    }

    function resetOffset() { offset = 0; }

    function debouncedLoad() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(load, 200);
    }

    dbSelect.addEventListener('change', () => {
        populateTableSelect();
        populateColumnSelect();
        resetOffset(); load();
    });
    tblSelect.addEventListener('change', () => {
        populateColumnSelect();
        resetOffset(); load();
    });
    colSelect.addEventListener('change', () => { resetOffset(); load(); });
    qInput.addEventListener('input', () => { resetOffset(); debouncedLoad(); });
    limitSelect.addEventListener('change', () => { resetOffset(); load(); });
    resetBtn.addEventListener('click', () => {
        qInput.value = '';
        colSelect.value = '';
        limitSelect.value = '50';
        resetOffset();
        load();
    });
    prevBtn.addEventListener('click', () => {
        const limit = parseInt(limitSelect.value, 10) || 50;
        offset = Math.max(0, offset - limit);
        load();
    });
    nextBtn.addEventListener('click', () => {
        const limit = parseInt(limitSelect.value, 10) || 50;
        offset += limit;
        load();
    });

    populateTableSelect();
    populateColumnSelect();
    load();
})();
