/* ============================================================== */
/*  Media OS marketing site                                         */
/*  - timecode ticker (HH:MM:SS:FF @ 30fps)                          */
/*  - dispatch panel cycler                                          */
/*                                                                  */
/*  NOTE: innerHTML is used to render scenario lines with embedded   */
/*  styling. All scenario content is hardcoded above (authored by    */
/*  the site author, never user input), so there is no XSS surface.  */
/*  The page has no form, no URL params, no user-controlled DOM.     */
/* ============================================================== */

(() => {
  'use strict';

  // ----- Timecode (HH:MM:SS:FF, 30fps non-drop) ---------------
  const tcEls = [document.getElementById('tc'), document.getElementById('footTc')].filter(Boolean);
  const start = Date.now();

  function formatTc(elapsedMs) {
    const totalFrames = Math.floor((elapsedMs / 1000) * 30);
    const ff = totalFrames % 30;
    const totalSec = Math.floor(elapsedMs / 1000);
    const ss = totalSec % 60;
    const mm = Math.floor(totalSec / 60) % 60;
    const hh = Math.floor(totalSec / 3600) % 100;
    const p = n => String(n).padStart(2, '0');
    return p(hh) + ':' + p(mm) + ':' + p(ss) + ':' + p(ff);
  }

  function tick() {
    const s = formatTc(Date.now() - start);
    for (const el of tcEls) el.textContent = s;
  }
  if (tcEls.length) {
    setInterval(tick, 1000 / 30);
    tick();
  }

  // ----- Dispatch panel cycler ---------------------------------
  const screen = document.getElementById('dispatch-screen');
  const footBars = document.querySelectorAll('.dispatch-foot-bars i');
  if (!screen) return;

  // Each scenario is an array of [op, parts, opClass]
  // parts is an array of either string or {cls, txt} for safe DOM building.
  const scenarios = [
    {
      lines: [
        ['ROUTE', ['user said: ', {cls: 'quote', txt: '"encode this for HLS, VMAF ≥ 95"'}], 'op-route'],
        ['MATCH', ['→ ', {cls: 'arg', txt: 'streaming-distribution'}], 'op-match'],
        ['READ',  [{cls: 'arg', txt: '_shared.md'}, ' + ', {cls: 'arg', txt: 'streaming-distribution.md'}], 'op-read'],
        ['SPAWN', ['Agent(subagent_type=', {cls: 'arg', txt: 'delivery'}, ')'], 'op-spawn'],
        ['DISPATCH', ['specialist ', {cls: 'spec-tag', txt: 'delivery', color: 'var(--spec-yellow)'}, ' running…'], 'op-dispatch'],
      ]
    },
    {
      lines: [
        ['ROUTE', ['user said: ', {cls: 'quote', txt: '"master Dolby Vision profile 8.4 for HLS"'}], 'op-route'],
        ['MATCH', ['→ ', {cls: 'arg', txt: 'hdr-mastering'}], 'op-match'],
        ['READ',  [{cls: 'arg', txt: '_shared.md'}, ' + ', {cls: 'arg', txt: 'hdr-mastering.md'}], 'op-read'],
        ['CHAIN', ['next: ', {cls: 'arg', txt: 'streaming-distribution'}, ' (after HDR)'], 'op-read'],
        ['SPAWN', ['Agent(subagent_type=', {cls: 'arg', txt: 'hdr'}, ')'], 'op-spawn'],
        ['DISPATCH', ['specialist ', {cls: 'spec-tag', txt: 'hdr', color: 'var(--spec-purple)'}, ' running…'], 'op-dispatch'],
      ]
    },
    {
      lines: [
        ['ROUTE', ['user said: ', {cls: 'quote', txt: '"set up NDI feed from OBS with PTZ on cam-2"'}], 'op-route'],
        ['MATCH', ['→ ', {cls: 'arg', txt: 'live-production'}], 'op-match'],
        ['READ',  [{cls: 'arg', txt: '_shared.md'}, ' + ', {cls: 'arg', txt: 'live-production.md'}], 'op-read'],
        ['SPAWN', ['Agent(subagent_type=', {cls: 'arg', txt: 'live'}, ')'], 'op-spawn'],
        ['DISPATCH', ['specialist ', {cls: 'spec-tag', txt: 'live', color: 'var(--spec-red)'}, ' running…'], 'op-dispatch'],
      ]
    },
    {
      lines: [
        ['ROUTE', ['user said: ', {cls: 'quote', txt: '"QC this encode against the master"'}], 'op-route'],
        ['MATCH', ['→ ', {cls: 'arg', txt: 'analysis-quality'}], 'op-match'],
        ['READ',  [{cls: 'arg', txt: '_shared.md'}, ' + ', {cls: 'arg', txt: 'analysis-quality.md'}], 'op-read'],
        ['SPAWN', ['Agent(subagent_type=', {cls: 'arg', txt: 'qc'}, ')'], 'op-spawn'],
        ['DISPATCH', ['specialist ', {cls: 'spec-tag', txt: 'qc', color: 'var(--spec-teal)'}, ' running…'], 'op-dispatch'],
      ]
    },
    {
      lines: [
        ['ROUTE',   ['user said: ', {cls: 'quote', txt: '"deliver IMF for Netflix"'}], 'op-route'],
        ['MATCH',   ['→ ', {cls: 'arg', txt: 'broadcast-delivery'}, ' (approval-gated)'], 'op-match'],
        ['READ',    [{cls: 'arg', txt: '_shared.md'}, ' + ', {cls: 'arg', txt: 'broadcast-delivery.md'}], 'op-read'],
        ['APPROVE', ['awaiting operator confirmation of target spec…'], 'op-spawn'],
        ['SPAWN',   ['Agent(subagent_type=', {cls: 'arg', txt: 'delivery'}, ')'], 'op-spawn'],
        ['DISPATCH',['specialist ', {cls: 'spec-tag', txt: 'delivery', color: 'var(--spec-yellow)'}, ' running…'], 'op-dispatch'],
      ]
    },
  ];

  let scenarioIdx = 0;
  let activeTimers = [];

  function clearTimers() {
    activeTimers.forEach(t => clearTimeout(t));
    activeTimers = [];
  }

  function tcStamp(secondsFromNow) {
    return formatTc((Date.now() - start) + (secondsFromNow * 1000));
  }

  // Safe DOM builder: every part is either a literal string (textContent)
  // or {cls, txt, color?} (single span with className + textContent).
  function buildRow(op, parts, opClass) {
    const row = document.createElement('div');
    row.className = 'dispatch-line';

    const tcSpan = document.createElement('span');
    tcSpan.className = 'tc';
    tcSpan.textContent = tcStamp(0.18);
    row.appendChild(tcSpan);

    const opSpan = document.createElement('span');
    opSpan.className = 'op ' + opClass;
    opSpan.textContent = op;
    row.appendChild(opSpan);

    const bodySpan = document.createElement('span');
    for (const part of parts) {
      if (typeof part === 'string') {
        bodySpan.appendChild(document.createTextNode(part));
      } else {
        const s = document.createElement('span');
        s.className = part.cls;
        s.textContent = part.txt;
        if (part.color) s.style.color = part.color;
        bodySpan.appendChild(s);
      }
    }
    row.appendChild(bodySpan);
    return row;
  }

  function renderScenario(idx) {
    clearTimers();
    while (screen.firstChild) screen.removeChild(screen.firstChild);

    footBars.forEach((b, i) => b.classList.toggle('on', i === idx));

    const scenario = scenarios[idx];
    const baseDelay = 250;

    scenario.lines.forEach((line, i) => {
      const t = setTimeout(() => {
        screen.appendChild(buildRow(line[0], line[1], line[2]));
      }, i * baseDelay);
      activeTimers.push(t);
    });

    const dwell = scenario.lines.length * baseDelay + 3200;
    const next = setTimeout(() => {
      scenarioIdx = (scenarioIdx + 1) % scenarios.length;
      renderScenario(scenarioIdx);
    }, dwell);
    activeTimers.push(next);
  }

  setTimeout(() => renderScenario(0), 700);

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      clearTimers();
    } else {
      renderScenario(scenarioIdx);
    }
  });
})();
