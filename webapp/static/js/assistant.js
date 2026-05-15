// AI Assistant — WebSocket streaming agent ----------------------------------
(function () {
    const composer = document.getElementById('composer');
    const input = document.getElementById('composer-input');
    const sendBtn = document.getElementById('send-btn');
    const sendLbl = document.getElementById('send-label');
    const modelSelect = document.getElementById('model-select');
    const personaSelect = document.getElementById('persona-select');
    const resetBtn = document.getElementById('reset-btn');
    const thread = document.getElementById('chat-thread');
    const empty = document.getElementById('chat-empty');
    const traceBody = document.getElementById('trace-body');
    const traceStatus = document.getElementById('trace-status');

    let ws = null;
    let running = false;
    let currentAssistantBubble = null;
    let currentTimeline = null;
    let runStartTs = 0;
    let toolCallCount = 0;

    // ----- WebSocket -----
    function connectWS() {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        ws = new WebSocket(`${proto}://${location.host}/ws/agent`);
        ws.onopen = () => { traceStatus.textContent = 'Idle · connected'; };
        ws.onclose = () => {
            traceStatus.textContent = 'Disconnected — reconnecting…';
            setTimeout(connectWS, 1500);
        };
        ws.onerror = () => { traceStatus.textContent = 'Connection error'; };
        ws.onmessage = (e) => {
            let ev; try { ev = JSON.parse(e.data); } catch (_) { return; }
            handleEvent(ev);
        };
    }
    connectWS();

    // ----- Event handling -----
    function handleEvent(ev) {
        switch (ev.type) {
            case 'run_start':
                runStartTs = ev.ts; toolCallCount = 0;
                traceBody.innerHTML = '';
                currentTimeline = U.el('div', { class: 'timeline' });
                traceBody.append(currentTimeline);
                appendEvent('run_start', '🚀 Run started', `Model: ${ev.model || ''} · ${ev.tool_count} tools available`, ev.ts);
                traceStatus.textContent = 'Running…';
                break;
            case 'iteration_start':
                appendEvent('iteration_start', `Iteration ${ev.iteration}`, 'Claude is planning the next step…', ev.ts);
                break;
            case 'model_response':
                renderModelResponse(ev);
                break;
            case 'tool_call':
                toolCallCount += 1;
                renderToolCall(ev);
                break;
            case 'tool_result':
                renderToolResult(ev);
                break;
            case 'final':
                renderFinal(ev);
                break;
            case 'error':
                appendEvent('error', '❌ Error', ev.error || 'Agent failed', ev.ts);
                setRunning(false);
                traceStatus.textContent = 'Error';
                break;
        }
        scrollTrace();
    }

    function elapsed(ts) {
        if (!runStartTs) return '';
        return `+${(ts - runStartTs).toFixed(1)}s`;
    }

    function appendEvent(type, title, detail, ts, extra) {
        if (!currentTimeline) {
            traceBody.innerHTML = '';
            currentTimeline = U.el('div', { class: 'timeline' });
            traceBody.append(currentTimeline);
        }
        const head = U.el('div', { class: 'event-head' },
            U.el('span', { class: 'event-type' }, type.replace(/_/g, ' ')),
            U.el('span', { class: 'event-time' }, elapsed(ts || Date.now() / 1000)),
        );
        const body = U.el('div', {}, U.el('div', { class: 'event-title' }, title));
        if (detail) body.append(U.el('div', { class: 'event-detail' }, detail));
        const ev = U.el('div', { class: `event ${type}` }, head, body);
        if (extra) ev.append(extra);
        currentTimeline.append(ev);
        return ev;
    }

    function renderModelResponse(ev) {
        let title = `🧠 Claude thinking step ${ev.iteration}`;
        const tcp = ev.tool_calls_planned || [];
        const detail = `${U.fmt.secs(ev.duration_s)} · ${ev.tokens?.input || 0} in · ${ev.tokens?.output || 0} out · ${ev.stop_reason}`;
        const e = appendEvent('model_response', title, detail, ev.ts);
        if (ev.text) {
            const txt = ev.text.length > 300 ? ev.text.slice(0, 300) + '…' : ev.text;
            e.append(U.el('div', { class: 'event-detail', style: { marginTop: '6px', fontStyle: 'italic' } }, `"${txt}"`));
        }
        if (tcp.length) {
            const pre = U.el('div', { class: 'event-args' },
                tcp.map(c => `→ ${c.tool_name}(${Object.keys(c.arguments || {}).join(', ') || '∅'})`).join('\n'));
            e.append(pre);
        }
    }

    function renderToolCall(ev) {
        const serverClass = U.serverPillClass(ev.server_name);
        const title = U.el('div', { class: 'event-title' },
            `🔧 `,
            U.el('span', { html: U.pill(ev.server_label, serverClass).outerHTML }),
            U.el('span', { style: { marginLeft: '6px' } }, ev.tool_name),
        );
        const detail = U.el('div', { class: 'event-detail' }, `Iter ${ev.iteration} · args:`);
        const args = U.el('div', { class: 'event-args' }, JSON.stringify(ev.arguments, null, 2));
        const ee = appendEvent('tool_call', '', '', ev.ts);
        const body = ee.lastChild;
        body.innerHTML = '';
        body.append(title, detail, args);
    }

    function renderToolResult(ev) {
        const serverClass = U.serverPillClass(ev.server_name);
        const title = U.el('div', { class: 'event-title' },
            `✓ `,
            U.el('span', { html: U.pill(ev.server_label, serverClass).outerHTML }),
            U.el('span', { style: { marginLeft: '6px' } }, ev.tool_name),
        );
        const detail = U.el('div', { class: 'event-detail' },
            `${U.fmt.secs(ev.duration_s)} · ${U.fmt.num(ev.result_size)} bytes${ev.error ? ' · ERROR' : ''}`);
        const result = U.el('div', { class: 'event-result' }, (ev.result_preview || '').slice(0, 1000));
        const ee = appendEvent(ev.error ? 'error' : 'tool_result', '', '', ev.ts);
        const body = ee.lastChild;
        body.innerHTML = '';
        body.append(title, detail, result);
    }

    function renderFinal(ev) {
        appendEvent('final', '✅ Answer produced', `${ev.iterations} iterations · ${U.fmt.secs(ev.duration_s)} · ${toolCallCount} tool calls`, ev.ts);
        if (currentAssistantBubble) {
            currentAssistantBubble.querySelector('.msg-body').innerHTML = U.markdown(ev.answer);
            currentAssistantBubble.querySelector('.msg-meta-pills').innerHTML = `
                <span class="pill info">${ev.iterations} iter</span>
                <span class="pill success">${U.fmt.secs(ev.duration_s)}</span>
                <span class="pill">${toolCallCount} tool call${toolCallCount === 1 ? '' : 's'}</span>
            `;
        }
        setRunning(false);
        traceStatus.textContent = `Done · ${U.fmt.secs(ev.duration_s)}`;
    }

    function scrollTrace() { traceBody.scrollTop = traceBody.scrollHeight; }

    function scrollChat() { thread.scrollTop = thread.scrollHeight; }

    function appendUserMsg(text) {
        if (empty) empty.style.display = 'none';
        const wrap = U.el('div', { class: 'chat-msg user' },
            U.el('div', { class: 'msg-bubble' }, text),
            U.el('div', { class: 'msg-meta' }, new Date().toLocaleTimeString()),
        );
        thread.append(wrap);
        scrollChat();
    }

    function appendAssistantPlaceholder() {
        const bubble = U.el('div', { class: 'msg-bubble markdown' },
            U.el('div', { class: 'msg-body' }, U.el('span', { class: 'spinner' }), ' Thinking…'));
        const meta = U.el('div', { class: 'msg-meta' },
            U.el('strong', {}, 'AI Assistant'),
            U.el('span', { class: 'msg-meta-pills', style: { marginLeft: 'auto', display: 'flex', gap: '6px' } }));
        const wrap = U.el('div', { class: 'chat-msg assistant' }, bubble, meta);
        thread.append(wrap);
        scrollChat();
        currentAssistantBubble = wrap;
        return wrap;
    }

    function setRunning(v) {
        running = v;
        sendBtn.disabled = v;
        if (v) { sendLbl.innerHTML = '<span class="spinner"></span> Working…'; }
        else { sendLbl.textContent = 'Send'; }
    }

    function send(text) {
        if (!text || running) return;
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            alert('Agent connection not ready — reconnecting, please try again.');
            return;
        }
        appendUserMsg(text);
        appendAssistantPlaceholder();
        setRunning(true);
        traceStatus.textContent = 'Sending…';
        ws.send(JSON.stringify({
            action: 'ask',
            question: text,
            model: modelSelect.value,
            max_iterations: 10,
        }));
        input.value = '';
    }

    // Wire up form
    composer.addEventListener('submit', (e) => {
        e.preventDefault();
        send(input.value.trim());
    });
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            send(input.value.trim());
        }
    });

    // Suggestion chips
    document.querySelectorAll('.suggestion-chip').forEach(btn => {
        btn.addEventListener('click', () => {
            const q = btn.getAttribute('data-q');
            input.value = q;
            send(q);
        });
    });

    // Reset
    resetBtn.addEventListener('click', () => {
        if (running) return;
        thread.querySelectorAll('.chat-msg').forEach(m => m.remove());
        empty.style.display = '';
        traceBody.innerHTML = '<div class="trace-empty">Tool calls, model thoughts, and inter-server hops will stream here in real time.</div>';
        currentTimeline = null;
        currentAssistantBubble = null;
        toolCallCount = 0;
        traceStatus.textContent = 'Idle';
    });
})();
