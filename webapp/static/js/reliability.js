// Product Reliability Hub ------------------------------------------------------
(async function () {
    const sel = document.getElementById('product-select');
    const kpiStrip = document.getElementById('kpi-strip');

    const prods = (await U.fetchJSON('/api/products')).rows;
    // Sort: lowest score (most concerning) first
    prods.sort((a, b) => (a.reliability_score ?? 100) - (b.reliability_score ?? 100));
    sel.innerHTML = '';
    sel.append(U.el('option', { value: '' }, 'Select a product…'));
    prods.forEach(p => {
        const tag = p.reliability_score != null ? ` [${p.reliability_grade || '?'} · ${(+p.reliability_score).toFixed(1)}]` : '';
        sel.append(U.el('option', { value: p.id }, `${p.name} (${p.sku})${tag}`));
    });

    sel.addEventListener('change', e => { if (e.target.value) load(e.target.value); });

    async function load(pid) {
        kpiStrip.innerHTML = '<div class="kpi"><div class="kpi-label">Loading…</div></div>';
        const d = await U.fetchJSON(`/api/product/${pid}/reliability`);
        renderKPIs(d);
        renderReturnsTrend(d);
        renderMTBF(d);
        renderModes(d);
        renderReasons(d);
        renderCompliance(d);
    }

    function renderKPIs(d) {
        kpiStrip.innerHTML = '';
        const rs = d.reliability_score || {};
        const grade = rs.score_grade || '—';
        const score = rs.score != null ? Number(rs.score).toFixed(1) : '—';
        const rmas = d.customer_returns?.summary?.rma_count ?? 0;
        const cost = d.customer_returns?.summary?.replacement_cost ?? 0;
        const failures = (d.failures?.by_severity || []).reduce((a, r) => a + (r.n || 0), 0);
        const items = [
            { label: 'Reliability score', val: score, sub: `Grade ${grade}`,
              accent: rs.score >= 80 ? 'success' : rs.score >= 65 ? 'warning' : 'danger' },
            { label: 'Customer returns', val: U.fmt.num(rmas), sub: U.fmt.money(cost) + ' replacement cost', accent: 'qa' },
            { label: 'Failure records', val: U.fmt.num(failures), accent: 'warning' },
            { label: 'Test runs', val: U.fmt.num(d.test_runs_summary?.runs || 0), sub: `pass rate ${((d.test_runs_summary?.avg_pass_rate||0)*100).toFixed(1)}%`, accent: 'info' },
        ];
        items.forEach(k => {
            const c = U.el('div', { class: `kpi accent-${k.accent}` });
            c.append(U.el('div', { class: 'kpi-label' }, k.label));
            c.append(U.el('div', { class: 'kpi-value' }, String(k.val)));
            if (k.sub) c.append(U.el('div', { class: 'kpi-sub' }, k.sub));
            kpiStrip.append(c);
        });
    }

    function commonLayout() {
        const css = getComputedStyle(document.documentElement);
        return {
            paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
            font: { color: css.getPropertyValue('--text').trim(), family: getComputedStyle(document.body).fontFamily, size: 12 },
            margin: { l: 50, r: 40, t: 10, b: 40 },
            xaxis: { gridcolor: css.getPropertyValue('--border-subtle').trim(), tickfont: { color: css.getPropertyValue('--text-tertiary').trim() } },
            yaxis: { gridcolor: css.getPropertyValue('--border-subtle').trim(), tickfont: { color: css.getPropertyValue('--text-tertiary').trim() } },
        };
    }

    function renderReturnsTrend(d) {
        const data = d.returns_trend || [];
        const qa = getComputedStyle(document.documentElement).getPropertyValue('--qa').trim();
        Plotly.newPlot('chart-returns', [{
            type: 'scatter', mode: 'lines+markers',
            x: data.map(r => r.period), y: data.map(r => r.rma_count),
            line: { color: qa, width: 2 }, marker: { color: qa, size: 7 },
            hovertemplate: '%{x}<br>%{y} RMAs<extra></extra>',
        }], commonLayout(), { displayModeBar: false, responsive: true });
    }

    function renderMTBF(d) {
        const data = (d.metrics_by_quarter || []).slice().reverse();
        const erp = getComputedStyle(document.documentElement).getPropertyValue('--erp').trim();
        const warn = getComputedStyle(document.documentElement).getPropertyValue('--warning').trim();
        Plotly.newPlot('chart-mtbf', [
            { type: 'scatter', mode: 'lines+markers', name: 'MTBF (hrs)', x: data.map(r => r.period_label), y: data.map(r => r.mtbf_hours), yaxis: 'y', line: { color: erp, width: 2 } },
            { type: 'scatter', mode: 'lines+markers', name: 'Failure rate (ppm)', x: data.map(r => r.period_label), y: data.map(r => r.failure_rate_ppm), yaxis: 'y2', line: { color: warn, width: 2 } },
        ], {
            ...commonLayout(),
            yaxis: { ...commonLayout().yaxis, title: { text: 'MTBF hours', font: { color: erp } } },
            yaxis2: { overlaying: 'y', side: 'right', title: { text: 'Failure rate ppm', font: { color: warn } }, gridcolor: 'transparent' },
            showlegend: true, legend: { orientation: 'h', x: 0, y: 1.1 },
        }, { displayModeBar: false, responsive: true });
    }

    function renderModes(d) {
        const rows = d.failures?.by_mode || [];
        const t = U.table(rows, [
            { label: 'Failure mode', key: 'failure_mode' },
            { label: 'Count', num: true, value: r => U.fmt.num(r.n) },
        ]);
        const w = document.getElementById('modes');
        w.innerHTML = '';
        if (rows.length === 0) w.innerHTML = '<div class="muted">No failures recorded.</div>';
        else w.append(U.el('div', { class: 'table-wrap' }, t));
    }

    function renderReasons(d) {
        const rows = d.customer_returns?.by_reason || [];
        const t = U.table(rows, [
            { label: 'Reason', key: 'return_reason' },
            { label: 'Count', num: true, value: r => U.fmt.num(r.n) },
        ]);
        const w = document.getElementById('reasons');
        w.innerHTML = '';
        if (rows.length === 0) w.innerHTML = '<div class="muted">No customer returns.</div>';
        else w.append(U.el('div', { class: 'table-wrap' }, t));
    }

    function renderCompliance(d) {
        const rows = d.compliance || [];
        const t = U.table(rows, [
            { label: 'Standard', key: 'standard' },
            { label: 'Status', value: r => U.pill(r.status, r.status==='Active'?'success': r.status==='Expired'?'danger':'warning').outerHTML, html: true },
            { label: 'Issued', value: r => U.fmt.date(r.issue_date) },
            { label: 'Expiry', value: r => U.fmt.date(r.expiry_date) },
            { label: 'Cert #', value: r => `<span class="mono">${r.certificate_number || ''}</span>`, html: true },
        ]);
        const w = document.getElementById('compliance');
        w.innerHTML = '';
        if (rows.length === 0) w.innerHTML = '<div class="muted">No compliance records.</div>';
        else w.append(U.el('div', { class: 'table-wrap' }, t));
    }

    // Auto-load first
    if (prods.length) { sel.value = prods[0].id; load(prods[0].id); }
})();
