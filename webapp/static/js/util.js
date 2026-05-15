// Shared helpers ---------------------------------------------------------------
const U = {
    fmt: {
        money(v, digits = 1) {
            if (v == null || isNaN(v)) return '—';
            const abs = Math.abs(v);
            if (abs >= 1e9) return '$' + (v / 1e9).toFixed(digits) + 'B';
            if (abs >= 1e6) return '$' + (v / 1e6).toFixed(digits) + 'M';
            if (abs >= 1e3) return '$' + (v / 1e3).toFixed(digits) + 'K';
            return '$' + v.toFixed(0);
        },
        num(v) {
            if (v == null || isNaN(v)) return '—';
            return new Intl.NumberFormat().format(v);
        },
        pct(v, digits = 1) {
            if (v == null || isNaN(v)) return '—';
            const sign = v > 0 ? '+' : '';
            return sign + v.toFixed(digits) + '%';
        },
        date(d) { return d ? d.slice(0, 10) : '—'; },
        time(ts) {
            const d = new Date(ts * 1000);
            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        },
        secs(s) { return s == null ? '—' : (s < 1 ? (s * 1000).toFixed(0) + ' ms' : s.toFixed(2) + ' s'); },
    },

    el(tag, attrs = {}, ...children) {
        const e = document.createElement(tag);
        for (const [k, v] of Object.entries(attrs)) {
            if (k === 'class') e.className = v;
            else if (k === 'style' && typeof v === 'object') Object.assign(e.style, v);
            else if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2).toLowerCase(), v);
            else if (k === 'html') e.innerHTML = v;
            else if (v != null) e.setAttribute(k, v);
        }
        for (const c of children.flat()) {
            if (c == null) continue;
            e.append(typeof c === 'string' ? document.createTextNode(c) : c);
        }
        return e;
    },

    table(rows, cols) {
        const tbl = U.el('table', { class: 'data' });
        const thead = U.el('thead');
        const tr = U.el('tr');
        cols.forEach(c => tr.append(U.el('th', { class: c.num ? 'num' : '' }, c.label)));
        thead.append(tr);
        tbl.append(thead);
        const tb = U.el('tbody');
        rows.forEach(r => {
            const tr = U.el('tr');
            cols.forEach(c => {
                const v = typeof c.value === 'function' ? c.value(r) : r[c.key];
                const td = U.el('td', { class: c.num ? 'num' : '' });
                if (c.html) td.innerHTML = v == null ? '—' : v;
                else td.textContent = v == null ? '—' : v;
                tr.append(td);
            });
            tb.append(tr);
        });
        tbl.append(tb);
        return tbl;
    },

    pill(text, kind = '') {
        return U.el('span', { class: `pill ${kind}` }, text);
    },

    serverPillClass(serverName) {
        const map = { crm: 'crm', erp: 'erp', qa: 'qa', analytics: 'analytics' };
        return map[serverName] || '';
    },

    async fetchJSON(url, options = {}) {
        const r = await fetch(url, options);
        if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
        return r.json();
    },

    // Minimal markdown renderer — handles headings, lists, bold, italic, code, tables, links
    markdown(text) {
        if (!text) return '';
        // Escape HTML
        let html = text.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
        // Code blocks
        html = html.replace(/```([\s\S]*?)```/g, (_, c) => `<pre><code>${c.trim()}</code></pre>`);
        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Headings
        html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
                   .replace(/^## (.+)$/gm,  '<h2>$1</h2>')
                   .replace(/^# (.+)$/gm,   '<h1>$1</h1>');
        // Tables  | a | b |\n|---|---|\n| 1 | 2 |
        html = html.replace(/(\|[^\n]+\|\n\|[ \-:|]+\|\n(?:\|[^\n]+\|\n?)+)/g, (block) => {
            const lines = block.trim().split('\n');
            const header = lines[0].split('|').slice(1, -1).map(s => s.trim());
            const body = lines.slice(2).map(line => line.split('|').slice(1, -1).map(s => s.trim()));
            const headHtml = '<tr>' + header.map(h => `<th>${h}</th>`).join('') + '</tr>';
            const bodyHtml = body.map(row => '<tr>' + row.map(c => `<td>${c}</td>`).join('') + '</tr>').join('');
            return `<table>${headHtml}${bodyHtml}</table>`;
        });
        // Bold, italic
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                   .replace(/(?<!\*)\*(?!\*)([^*]+)\*/g, '<em>$1</em>');
        // Links
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
        // Lists: convert lines that start with - or 1.
        html = html.replace(/(^|\n)((?:- .+\n?)+)/g, (_, pre, block) => {
            const items = block.trim().split(/\n/).map(l => l.replace(/^- /, '')).map(l => `<li>${l}</li>`).join('');
            return `${pre}<ul>${items}</ul>`;
        });
        html = html.replace(/(^|\n)((?:\d+\. .+\n?)+)/g, (_, pre, block) => {
            const items = block.trim().split(/\n/).map(l => l.replace(/^\d+\. /, '')).map(l => `<li>${l}</li>`).join('');
            return `${pre}<ol>${items}</ol>`;
        });
        // Paragraphs (double newlines)
        html = html.split(/\n{2,}/).map(p => /^<(h\d|ul|ol|pre|table)/.test(p.trim()) ? p : `<p>${p.trim()}</p>`).join('\n');
        return html;
    },
};

window.U = U;
