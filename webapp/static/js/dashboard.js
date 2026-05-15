// Executive Dashboard --------------------------------------------------------
(async function () {
    const data = await U.fetchJSON('/api/dashboard');

    // ----- KPI strip -----
    const yoy = data.totals.yoy_growth_pct;
    const yoyKind = yoy == null ? 'flat' : (yoy >= 0 ? 'up' : 'down');
    const keyCount = data.top_key_accounts.length;
    const topConcerns = data.low_reliability.length;
    const arOverdue = (data.ar_aging.find(r => r.bucket && r.bucket.includes('90+')) || {}).amount || 0;

    const strip = document.getElementById('kpi-strip');
    strip.innerHTML = '';
    const kpis = [
        {
            label: `Revenue · ${data.period}`, val: U.fmt.money(data.totals.revenue, 2),
            sub: `vs ${data.prior_period} ${U.fmt.money(data.totals.prior_year_revenue, 2)}`,
            delta: U.fmt.pct(yoy), deltaKind: yoyKind, accent: 'analytics',
        },
        {
            label: 'Open pipeline', val: U.fmt.money(data.pipeline_total, 2),
            sub: `${U.fmt.num(data.pipeline_count)} opportunities`,
            accent: 'crm',
        },
        {
            label: 'Top accounts (key)', val: keyCount,
            sub: `Top: ${data.top_key_accounts[0]?.account_name || '—'}`,
            accent: 'info',
        },
        {
            label: 'AR overdue · 90+', val: U.fmt.money(arOverdue, 2),
            sub: 'Past due collections',
            accent: 'warning',
        },
        {
            label: 'Reliability watch', val: topConcerns,
            sub: 'products below score 75',
            accent: 'qa',
        },
    ];
    kpis.forEach(k => {
        const card = U.el('div', { class: `kpi accent-${k.accent}` });
        card.append(U.el('div', { class: 'kpi-label' }, k.label));
        card.append(U.el('div', { class: 'kpi-value' }, String(k.val)));
        if (k.sub) card.append(U.el('div', { class: 'kpi-sub' }, k.sub));
        if (k.delta) card.append(U.el('div', { class: `kpi-delta ${k.deltaKind}` }, k.delta));
        strip.append(card);
    });

    // ----- Revenue trend -----
    const ts = data.revenue_quarterly_series
        .map(r => ({ period: r.period, amount: r.revenue ?? r.amount }))
        .filter(r => r.period && r.amount != null);
    const css = getComputedStyle(document.documentElement);
    const palette = {
        bg: css.getPropertyValue('--surface').trim(),
        text: css.getPropertyValue('--text').trim(),
        textTertiary: css.getPropertyValue('--text-faint').trim(),
        grid: css.getPropertyValue('--border-soft').trim(),
        brand: css.getPropertyValue('--accent').trim(),
        crm: css.getPropertyValue('--crm').trim(),
        erp: css.getPropertyValue('--erp').trim(),
        qa: css.getPropertyValue('--qa').trim(),
        analytics: css.getPropertyValue('--analytics').trim(),
    };
    const commonLayout = {
        paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
        font: { family: '"JetBrains Mono", ui-monospace, monospace', color: palette.text, size: 11 },
        margin: { l: 55, r: 20, t: 10, b: 40 },
        xaxis: { gridcolor: palette.grid, linecolor: palette.grid, zerolinecolor: palette.grid, tickfont: { color: palette.textTertiary, size: 10 } },
        yaxis: { gridcolor: palette.grid, linecolor: palette.grid, zerolinecolor: palette.grid, tickfont: { color: palette.textTertiary, size: 10 } },
        showlegend: false,
    };
    Plotly.newPlot('chart-revenue-trend', [{
        type: 'bar', x: ts.map(r => r.period), y: ts.map(r => r.amount),
        marker: { color: palette.analytics, opacity: 0.8 },
        hovertemplate: '%{x}<br>$%{y:,.0f}<extra></extra>',
    }], { ...commonLayout, xaxis: { ...commonLayout.xaxis, tickangle: -45 } }, { displayModeBar: false, responsive: true });

    // ----- Pipeline funnel -----
    const stages = data.pipeline_by_stage;
    Plotly.newPlot('chart-pipeline', [{
        type: 'bar', orientation: 'h',
        y: stages.map(s => s.stage), x: stages.map(s => s.amount),
        marker: { color: palette.crm, opacity: 0.85 },
        hovertemplate: '%{y}<br>$%{x:,.0f}<br>weighted: $%{customdata:,.0f}<extra></extra>',
        customdata: stages.map(s => s.weighted_amount),
    }], {
        ...commonLayout,
        xaxis: { ...commonLayout.xaxis, tickformat: '$,.2s' },
        yaxis: { ...commonLayout.yaxis, type: 'category', automargin: true },
        margin: { ...commonLayout.margin, l: 110 },
    }, { displayModeBar: false, responsive: true });

    // ----- Top accounts -----
    const top = data.top_key_accounts;
    Plotly.newPlot('chart-top-accounts', [{
        type: 'bar', orientation: 'h',
        y: top.map(r => r.account_name).reverse(),
        x: top.map(r => r.total_revenue).reverse(),
        marker: { color: palette.brand, opacity: 0.85 },
        hovertemplate: '%{y}<br>Revenue: $%{x:,.0f}<br>Pipeline: $%{customdata:,.0f}<extra></extra>',
        customdata: top.map(r => r.open_pipeline).reverse(),
    }], {
        ...commonLayout,
        xaxis: { ...commonLayout.xaxis, tickformat: '$,.2s' },
        yaxis: { ...commonLayout.yaxis, type: 'category', automargin: true },
        margin: { ...commonLayout.margin, l: 150 },
    }, { displayModeBar: false, responsive: true });

    // ----- Industry donut -----
    const ind = data.revenue_by_industry;
    Plotly.newPlot('chart-industry', [{
        type: 'pie', hole: 0.55,
        labels: ind.map(r => r.industry), values: ind.map(r => r.revenue),
        textinfo: 'label+percent', textposition: 'outside',
        marker: { colors: [palette.crm, palette.erp, palette.qa, palette.analytics, palette.brand, '#06b6d4', '#84cc16', '#f43f5e', '#a855f7'] },
        hovertemplate: '%{label}<br>$%{value:,.0f}<br>%{percent}<extra></extra>',
    }], { ...commonLayout, margin: { l: 10, r: 10, t: 10, b: 10 } },
        { displayModeBar: false, responsive: true });

    // ----- YoY table -----
    const yoyRows = data.yoy_changes.slice(0, 8);
    const yoyTable = U.table(yoyRows, [
        { label: 'Account', key: 'account_name' },
        { label: 'Industry', key: 'industry', value: r => U.pill(r.industry, '').outerHTML, html: true },
        { label: 'Q1-25', num: true, value: r => U.fmt.money(r.revenue_a) },
        { label: 'Q1-26', num: true, value: r => U.fmt.money(r.revenue_b) },
        { label: 'Δ%', num: true, value: r => {
            if (r.delta_pct == null) return r.change_type || '—';
            const k = r.delta_pct >= 0 ? 'success' : 'danger';
            return `<span class="pill ${k}">${U.fmt.pct(r.delta_pct)}</span>`;
        }, html: true },
    ]);
    const yoyWrap = document.getElementById('yoy-table');
    yoyWrap.innerHTML = '';
    yoyWrap.append(U.el('div', { class: 'table-wrap' }, yoyTable));

    // ----- Reliability watch -----
    const watch = data.low_reliability;
    const watchTable = U.table(watch, [
        { label: 'Product ID', key: 'external_product_id', value: r => `<span class="mono">${r.external_product_id}</span>`, html: true },
        { label: 'Score', num: true, value: r => `<span class="pill ${r.score < 60 ? 'danger' : 'warning'}">${(+r.score).toFixed(1)}</span>`, html: true },
        { label: 'Grade', key: 'score_grade', value: r => U.pill(r.score_grade || '—', '').outerHTML, html: true },
        { label: 'Recommendation', key: 'recommendation', value: r => `<span class="muted">${r.recommendation || ''}</span>`, html: true },
    ]);
    const watchWrap = document.getElementById('reliability-watch');
    watchWrap.innerHTML = '';
    watchWrap.append(U.el('div', { class: 'table-wrap' }, watchTable));

    // ----- AR aging -----
    const ar = data.ar_aging;
    const arTable = U.table(ar, [
        { label: 'Bucket', key: 'bucket' },
        { label: 'Count', num: true, value: r => U.fmt.num(r.invoice_count) },
        { label: 'Outstanding', num: true, value: r => U.fmt.money(r.amount) },
    ]);
    const arWrap = document.getElementById('ar-aging-card');
    arWrap.innerHTML = '';
    arWrap.append(U.el('div', { class: 'table-wrap' }, arTable));
})();
