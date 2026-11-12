// koha-review-walkthrough driver TEMPLATE.
//
// Do not edit by hand: build-driver.py injects scenarios.json, the side and the
// scenario ids into the three marked lines below, and writes a ready-to-run file.
// The Playwright MCP sandbox has no `require`, `import` or file access, so the
// configuration has to be embedded in the code.
//
// Run the generated file through the Playwright MCP tool browser_run_code_unsafe
// (`filename`, the file must sit under the MCP's allowed roots, normally the
// session's workspace root, e.g. <workspace>/.playwright-mcp/).
//
// It records ONE video per scenario (1920x1080) for ONE side (before or after),
// with a title card, a caption bar narrating each step, a visible mouse pointer
// with a red click ripple, and fixed pauses so the video can be followed. It
// returns the observed page state per scenario as JSON; save that as
// verify-<side>.json yourself.
async (page) => {
  const CFG = /*CFG*/ {} /*END*/;
  const SIDE = /*SIDE*/ 'after' /*END*/; // 'before' (unpatched instance) or 'after' (patched instance)
  const RUN = /*RUN*/ null /*END*/;      // list of scenario ids, or null for all

  const S = CFG.sides[SIDE];
  const OUT = CFG.root + '/' + SIDE;
  const SIZE = CFG.size || { width: 1920, height: 1080 };
  const PAUSE = CFG.pause ?? 5000;     // ms to linger after every result
  const CARD = CFG.cardMs ?? 7000;     // ms the title card stays up
  const ids = RUN || Object.keys(CFG.scenarios);

  const browser = page.context().browser();
  if (!browser) throw new Error('No browser handle (persistent context). Restart the Playwright MCP without a user-data-dir.');
  const esc = (s) => String(s ?? '').replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

  // Log in once and reuse the session for every scenario's own recording context.
  const lctx = await browser.newContext();
  const lp = await lctx.newPage();
  await lp.goto(S.base + (CFG.login?.path || '/cgi-bin/koha/mainpage.pl'));
  if (await lp.locator('#userid').count()) {
    await lp.fill('#userid', CFG.login?.user || 'koha');
    await lp.fill('#password', CFG.login?.pass || 'koha');
    await Promise.all([lp.waitForNavigation(), lp.click('input[type=submit]')]);
  }
  const state = await lctx.storageState();
  await lctx.close();

  // Injected into every document. The caption lives in sessionStorage so it
  // survives full page reloads (legacy Koha pages reload on every action).
  const CAPJS = `(() => {
    const render = () => {
      let t = null; try { t = sessionStorage.getItem('wtcap'); } catch (e) {}
      if (!t || !document.body) return;
      let d = document.getElementById('wt-caption');
      if (!d) { d = document.createElement('div'); d.id = 'wt-caption';
        d.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:2147483645;background:rgba(18,38,58,.93);color:#fff;font:600 20px system-ui,sans-serif;padding:12px 22px;border-top:3px solid ${S.color}';
        document.body.appendChild(d); }
      d.textContent = '\\u25CF  ' + t;
    };
    window.__wtRender = render;
    document.addEventListener('DOMContentLoaded', render);
    if (document.readyState !== 'loading') render();
  })();`;
  const POINTER_JS = `(() => {
    if (window.__wtPointer) return; window.__wtPointer = true;
    const make = () => {
      if (document.getElementById('wt-cursor') || !document.documentElement) return;
      const c = document.createElement('div'); c.id = 'wt-cursor';
      c.style.cssText = 'position:fixed;left:0;top:0;width:30px;height:30px;z-index:2147483647;pointer-events:none;display:none;transform:translate(-4px,-3px)';
      c.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M3 2l7 19 3-8 8-3z" fill="#fff" stroke="#000" stroke-width="1.6" stroke-linejoin="round"/></svg>';
      document.documentElement.appendChild(c);
      try { const p = JSON.parse(sessionStorage.getItem('wtpos') || 'null'); if (p) { c.style.left = p.x + 'px'; c.style.top = p.y + 'px'; c.style.display = 'block'; } } catch (e) {}
    };
    const ripple = (x, y) => {
      const r = document.createElement('div');
      r.style.cssText = 'position:fixed;z-index:2147483646;pointer-events:none;width:12px;height:12px;border-radius:50%;border:4px solid #ff3b30;left:' + (x - 6) + 'px;top:' + (y - 6) + 'px;transition:all .6s ease-out;opacity:.95';
      document.documentElement.appendChild(r);
      requestAnimationFrame(() => { r.style.width = '60px'; r.style.height = '60px'; r.style.left = (x - 30) + 'px'; r.style.top = (y - 30) + 'px'; r.style.opacity = '0'; });
      setTimeout(() => r.remove(), 700);
    };
    addEventListener('mousemove', (e) => { make(); const c = document.getElementById('wt-cursor'); if (!c) return; c.style.display = 'block'; c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; try { sessionStorage.setItem('wtpos', JSON.stringify({ x: e.clientX, y: e.clientY })); } catch (_) {} }, true);
    addEventListener('mousedown', (e) => ripple(e.clientX, e.clientY), true);
    document.addEventListener('DOMContentLoaded', make);
  })();`;

  const caption = (p, text) => p.evaluate((t) => { try { sessionStorage.setItem('wtcap', t); } catch (e) {} if (window.__wtRender) window.__wtRender(); }, text).catch(() => {});
  const moveTo = async (p, x, y, steps = 35) => { await p.mouse.move(x, y, { steps }); await p.waitForTimeout(350); };
  const clickAt = async (p, x, y) => { await moveTo(p, x, y); await p.mouse.down(); await p.waitForTimeout(90); await p.mouse.up(); };
  const clickEl = async (p, loc) => { const b = await loc.boundingBox(); if (!b) throw new Error('element has no box'); await clickAt(p, b.x + b.width / 2, b.y + b.height / 2); };
  const settle = async (p) => { await p.waitForLoadState('load').catch(() => {}); await p.waitForTimeout(1800); };

  const titleCard = async (p, id, sc) => {
    const prefs = Object.entries(sc.prefs || CFG.baselinePrefs || {}).map(([k, v]) => `<code style="background:#0003;padding:2px 8px;border-radius:4px">${esc(k)} = ${esc(v)}</code>`).join(' &nbsp; ') || 'baseline';
    await p.setContent(`<body style="margin:0;background:${S.bg};color:#eee;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh">
      <div style="max-width:1100px;padding:40px">
        <div style="color:${S.color};font-size:22px;letter-spacing:2px">${esc(id)} &nbsp;|&nbsp; ${esc(S.label)}</div>
        <h1 style="font-size:46px;margin:14px 0 26px">${esc(sc.title)}</h1>
        <div style="font-size:24px;line-height:1.5"><b style="color:${S.color}">Situation</b><br>${esc(sc.pre)}</div>
        <div style="font-size:24px;line-height:1.5;margin-top:22px"><b style="color:${S.color}">What this shows</b><br>${esc(sc.what)}</div>
        <div style="font-size:20px;margin-top:22px;line-height:1.9"><b style="color:${S.color}">Settings</b> &nbsp; ${prefs}</div>
      </div>
      <style>@keyframes g{from{width:0}to{width:100%}}</style>
      <div style="position:fixed;left:0;bottom:0;height:8px;background:${S.color};animation:g ${CARD}ms linear forwards"></div></body>`);
    await p.waitForTimeout(CARD);
  };

  // Visible state: current URL, open modal title and buttons, first rows of a table, extra selector texts.
  const observe = (p, o) => p.evaluate((o) => {
    const vis = (e) => !!e && e.getClientRects().length > 0;
    const m = [...document.querySelectorAll('.modal.show, [role=dialog]')].filter(vis)[0];
    const rows = [...document.querySelectorAll(o.rows || 'table tbody tr')].filter(vis).slice(0, o.maxRows || 3)
      .map((r) => r.innerText.replace(/\s+/g, ' ').trim().slice(0, 240));
    const text = {};
    for (const s of o.text || []) { const e = document.querySelector(s); text[s] = e ? e.innerText.replace(/\s+/g, ' ').trim().slice(0, 240) : null; }
    return {
      url: location.pathname.split('/').pop() + location.search,
      modalTitle: m ? (m.querySelector('.modal-title, h1, h2, h3')?.innerText || '').trim() : null,
      modalButtons: m ? [...m.querySelectorAll('button, input[type=submit]')].filter(vis).map((b) => (b.innerText || b.value || '').trim()).filter(Boolean) : [],
      rows, text,
    };
  }, o);

  // One step of a scenario. Steps are plain objects; see SKILL.md for the list.
  const runStep = async (p, st, log) => {
    if (st.caption) await caption(p, st.caption);
    if (st.goto) {
      await p.goto(S.base + st.goto);
      if (st.waitFor) await p.waitForSelector(st.waitFor, { timeout: 20000 });
      await moveTo(p, 960, 540, 5);
    }
    if (st.type) {
      const loc = p.locator(st.type).first();
      await clickEl(p, loc);
      if (st.clear) await p.keyboard.press('Control+A');
      await p.keyboard.type(st.text, { delay: 45 });
      await p.waitForTimeout(500);
    }
    if (st.click) {
      const loc = p.locator(st.click).first();
      const go = () => clickEl(p, loc);
      // Legacy pages navigate on click; wait for it. Vue pages don't.
      if (st.nav) await Promise.all([p.waitForNavigation({ timeout: 9000 }).catch(() => {}), go()]); else await go();
      await settle(p);
    }
    if (st.press) { await p.waitForTimeout(800); await p.keyboard.press(st.press); await p.waitForTimeout(1500); }
    if (st.waitForSelector) await p.waitForSelector(st.waitForSelector, { timeout: st.timeout || 9000 }).catch(() => log.push({ step: 'timeout waiting for ' + st.waitForSelector }));
    if (st.wait) await p.waitForTimeout(st.wait);
    if (st.observe) {
      const o = await observe(p, st);
      log.push({ step: st.observe, state: o });
      await caption(p, st.captionResult || (o.modalTitle ? `Prompt: ${o.modalTitle}   Buttons: ${o.modalButtons.join('  |  ')}` : (o.rows[0] ? `Result: ${o.rows[0].slice(0, 120)}` : st.observe)));
      await p.waitForTimeout(PAUSE);
    }
  };

  const results = {};
  for (const id of ids) {
    const sc = CFG.scenarios[id];
    const steps = sc['steps_' + SIDE] || sc.steps;
    const ctx = await browser.newContext({ storageState: state, recordVideo: { dir: OUT + '/' + id, size: SIZE }, viewport: SIZE });
    await ctx.addInitScript(POINTER_JS);
    await ctx.addInitScript(CAPJS);
    const p = await ctx.newPage();
    const popups = [];
    ctx.on('page', async (pg) => { if (pg === p) return; popups.push(pg.url()); await pg.waitForTimeout(3000).catch(() => {}); await pg.close().catch(() => {}); });
    p.on('dialog', (d) => d.dismiss().catch(() => {}));
    const log = [];
    try {
      await titleCard(p, id, sc);
      for (const st of steps) await runStep(p, st, log);
      await p.screenshot({ path: `${OUT}/${id}/${id}-final.png` }).catch(() => {});
    } catch (e) { log.push({ ERROR: String(e.message || e).slice(0, 300) }); }
    log.push({ popups });
    const vid = p.video();
    await p.close(); await ctx.close();
    results[id] = { video: vid ? await vid.path() : null, log };
  }
  return results;
}
