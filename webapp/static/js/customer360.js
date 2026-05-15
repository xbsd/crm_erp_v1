// Customer 360 -----------------------------------------------------------------
(async function () {
    const sel = document.getElementById('account-select');
    const heroBody = document.getElementById('hero-body');
    const kpiStrip = document.getElementById('kpi-strip');

    // Load account list
    const accs = await U.fetchJSON('/api/accounts?limit=500');
    const rows = accs.rows.sort((a, b) => (b.is_key_account || 0) - (a.is_key_account || 0)
        || (b.annual_revenue || 0) - (a.annual_revenue || 0));
    sel.innerHTML = '';
    sel.append(U.el('option', { value: '' }, 'Select an account…'));
    rows.forEach(r => {
        const o = U.el('option', { value: r.id }, `${r.name}${r.is_key_account ? ' ★' : ''}`);
        sel.append(o);
    });

    sel.addEventListener('change', (e) => {
        const id = e.target.value;
        if (id) loadAccount(id);
    });

    async function loadAccount(id) {
        heroBody.innerHTML = '<span class="spinner"></span> Loading…';
        const data = await U.fetchJSON(`/api/account/${id}`);
        renderHero(data);
        renderKPIs(data);
        renderBookingChart(data);
        renderOpps(data.opportunities);
        renderQuotes(data.quotes);
        renderOrders(data.orders, data.invoices);
    }

    function renderHero(d) {
        const s = d.summary;
        const flag = s.is_key_account ? '<span class="pill warning">★ Key account</span>' : '';
        heroBody.innerHTML = `
            <div style="display: flex; align-items: center; gap: 18px;">
                <div style="width: 64px; height: 64px; border-radius: 14px; background: linear-gradient(135deg, var(--brand) 0%, var(--qa) 100%); display: grid; place-items: center; color: white; font-weight: 700; font-size: 22px;">${(s.name||'?').slice(0,2).toUpperCase()}</div>
                <div style="flex: 1;">
                    <div style="font-size: 22px; font-weight: 700; letter-spacing: -0.015em;">${s.name}</div>
                    <div style="display:flex; gap: 6px; margin-top: 6px;">
                        <span class="pill">${s.industry}</span>
                        <span class="pill info">${s.segment}</span>
                        <span class="pill">${s.billing_country || ''}</span>
                        ${flag}
                    </div>
                </div>
                <div style="display:flex; gap: 22px; align-items: center; font-size: 12px; color: var(--text-tertiary);">
                    <div><div>Annual revenue</div><div style="font-size:18px; font-weight:600; color: var(--text);">${U.fmt.money(s.annual_revenue)}</div></div>
                    <div><div>Employees</div><div style="font-size:18px; font-weight:600; color: var(--text);">${U.fmt.num(s.employee_count)}</div></div>
                </div>
            </div>
        `;
    }

    function renderKPIs(d) {
        const s = d.summary;
        kpiStrip.innerHTML = '';
        const items = [
            { label: 'Open pipeline', val: U.fmt.money(s.open_pipeline_amount), sub: `${s.total_opportunities} opportunities`, accent: 'crm' },
            { label: 'Closed won (life)', val: U.fmt.money(s.closed_won_amount), accent: 'analytics' },
            { label: 'Quotes', val: U.fmt.num(d.quotes.length), sub: `${d.quotes.filter(q=>q.status==='Accepted').length} accepted`, accent: 'info' },
            { label: 'Returns (life)', val: U.fmt.num(d.returns.reduce((a,r)=>a+(r.rma_count||0),0)), sub: `${d.returns.length} accounts grouped`, accent: 'qa' },
        ];
        items.forEach(k => {
            const c = U.el('div', { class: `kpi accent-${k.accent}` });
            c.append(U.el('div', { class: 'kpi-label' }, k.label));
            c.append(U.el('div', { class: 'kpi-value' }, String(k.val)));
            if (k.sub) c.append(U.el('div', { class: 'kpi-sub' }, k.sub));
            kpiStrip.append(c);
        });
    }

    function renderBookingChart(d) {
        const css = getComputedStyle(document.documentElement);
        const erpColor = css.getPropertyValue('--erp').trim();
        const text = css.getPropertyValue('--text').trim();
        const grid = css.getPropertyValue('--border-subtle').trim();
        const tertiary = css.getPropertyValue('--text-tertiary').trim();
        const data = d.booking_by_quarter || [];
        Plotly.newPlot('chart-booking', [{
            type: 'bar',
            x: data.map(r => r.period), y: data.map(r => r.booked_amount),
            marker: { color: erpColor, opacity: 0.85 },
            hovertemplate: '%{x}<br>$%{y:,.0f}<br>%{customdata} orders<extra></extra>',
            customdata: data.map(r => r.order_count),
        }], {
            paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
            font: { color: text, family: getComputedStyle(document.body).fontFamily, size: 12 },
            margin: { l: 50, r: 20, t: 10, b: 40 },
            xaxis: { gridcolor: grid, linecolor: grid, zerolinecolor: grid, tickfont: { color: tertiary } },
            yaxis: { gridcolor: grid, linecolor: grid, zerolinecolor: grid, tickfont: { color: tertiary }, tickformat: '$,.2s' },
        }, { displayModeBar: false, responsive: true });
    }

    function renderOpps(opps) {
        const open = opps.filter(o => !(o.stage || '').startsWith('Closed')).slice(0, 50);
        const t = U.table(open, [
            { label: 'Opportunity', key: 'name' },
            { label: 'Stage', value: r => U.pill(r.stage, '').outerHTML, html: true },
            { label: 'Amount', num: true, value: r => U.fmt.money(r.amount) },
            { label: 'Close', value: r => U.fmt.date(r.close_date) },
            { label: 'Family', value: r => `<span class="muted">${r.primary_product_family||''}</span>`, html: true },
        ]);
        const wrap = document.getElementById('opps-table');
        wrap.innerHTML = '';
        if (open.length === 0) wrap.innerHTML = '<div class="muted">No open opportunities.</div>';
        else wrap.append(U.el('div', { class: 'table-wrap' }, t));
    }

    function renderQuotes(qs) {
        const t = U.table(qs.slice(0, 30), [
            { label: 'Quote #', value: r => `<span class="mono">${r.quote_number}</span>`, html: true },
            { label: 'Status', value: r => U.pill(r.status, r.status === 'Accepted' ? 'success' : '').outerHTML, html: true },
            { label: 'Amount', num: true, value: r => U.fmt.money(r.grand_total) },
            { label: 'Created', value: r => U.fmt.date(r.created_date) },
            { label: 'Accepted', value: r => U.fmt.date(r.accepted_date) },
        ]);
        const wrap = document.getElementById('quotes-table');
        wrap.innerHTML = '';
        if (qs.length === 0) wrap.innerHTML = '<div class="muted">No quotes.</div>';
        else wrap.append(U.el('div', { class: 'table-wrap' }, t));
    }

    function renderOrders(orders, invoices) {
        const t = U.table(orders.slice(0, 30), [
            { label: 'Order #', value: r => `<span class="mono">${r.order_number}</span>`, html: true },
            { label: 'Status', value: r => U.pill(r.status, r.status === 'Delivered' ? 'success' : '').outerHTML, html: true },
            { label: 'Total', num: true, value: r => U.fmt.money(r.grand_total) },
            { label: 'Ordered', value: r => U.fmt.date(r.order_date) },
            { label: 'Delivery', value: r => U.fmt.date(r.actual_delivery_date) },
        ]);
        const wrap = document.getElementById('orders-table');
        wrap.innerHTML = '';
        if (orders.length === 0) wrap.innerHTML = '<div class="muted">No orders.</div>';
        else wrap.append(U.el('div', { class: 'table-wrap' }, t));
    }

    // Auto-load first key account
    const firstKey = rows.find(r => r.is_key_account);
    if (firstKey) {
        sel.value = firstKey.id;
        loadAccount(firstKey.id);
    }
})();
