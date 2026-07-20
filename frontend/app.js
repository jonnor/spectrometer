// app.js — Lab Instrument UI (Preact + htm, no build step)
// Styling lives in styles.css. Inline style="" is used only for values
// computed at runtime (progress width, chevron rotation), never for
// static/reusable rules — those are CSS classes.
import { h, render } from 'https://esm.sh/preact@10.19.6';
import { useState, useEffect } from 'https://esm.sh/preact@10.19.6/hooks';
import htm from 'https://esm.sh/htm@3.1.1';

const html = htm.bind(h);

/* ===========================================================
   Generic reusable components
=========================================================== */

const Icon = {
  menu: () => html`<svg width="22" height="22" viewBox="0 0 24 24" fill="none">
    <path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  </svg>`,
  chevron: () => html`<svg width="18" height="18" viewBox="0 0 24 24" fill="none">
    <path d="M9 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`,
  play: () => html`<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <path d="M8 5v14l11-7z"/>
  </svg>`,
  stop: () => html`<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <rect x="6" y="6" width="12" height="12" rx="2"/>
  </svg>`,
  close: () => html`<svg width="22" height="22" viewBox="0 0 24 24" fill="none">
    <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  </svg>`,
};

function IconButton({ icon, label, onClick }) {
  const IconCmp = Icon[icon];
  return html`
    <button class="icon-btn" aria-label=${label} onClick=${onClick}>
      <${IconCmp} />
    </button>
  `;
}

function StatusDot({ ok }) {
  return html`<span class=${'dot ' + (ok ? 'dot-green' : 'dot-red')}></span>`;
}

// Generic button: variant = 'primary' | 'danger' | 'secondary'
function Button({ variant = 'secondary', icon, disabled, onClick, children }) {
  const IconCmp = icon ? Icon[icon] : null;
  const cls = variant === 'secondary' ? 'btn-secondary' : `btn btn-${variant}`;
  return html`
    <button class=${cls} disabled=${disabled} onClick=${onClick}>
      ${IconCmp && html`<${IconCmp} />`}
      <span>${children}</span>
    </button>
  `;
}

// Small pill used in accordion summaries. tone = 'default' | 'accent'
function Chip({ tone = 'default', children }) {
  return html`<span class=${'chip ' + (tone === 'accent' ? 'chip--accent' : '')}>${children}</span>`;
}

// Labelled form field wrapper: type = 'text' | 'number' | 'select' | 'checkbox'
function Field({ label, type = 'text', children, ...props }) {
  if (type === 'checkbox') {
    return html`
      <label class="field field--checkbox">
        <input type="checkbox" ...${props} />
        <span>${label}</span>
      </label>
    `;
  }
  if (type === 'select') {
    return html`
      <label class="field">
        <span>${label}</span>
        <select ...${props}>${children}</select>
      </label>
    `;
  }
  return html`
    <label class="field">
      <span>${label}</span>
      <input type=${type} ...${props} />
    </label>
  `;
}

// One-shot JSON GET, re-run when `url` changes. Single state object
// keeps this to one useState instead of separate data/error/loading ones.
function useFetchJson(url) {
  const [state, setState] = useState({ data: null, error: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    setState(s => ({ ...s, loading: true }));
    fetch(url)
      .then(res => { if (!res.ok) throw new Error('request failed'); return res.json(); })
      .then(data => { if (!cancelled) setState({ data, error: null, loading: false }); })
      .catch(error => { if (!cancelled) setState({ data: null, error, loading: false }); });
    return () => { cancelled = true; };
  }, [url]);

  return state;
}

// Maps a linear slider index [0, steps-1] to an exponential value in [min, max].
function expSliderValue(index, min, max, steps) {
  const t = index / (steps - 1);
  return min * Math.pow(max / min, t);
}

// Inverse of expSliderValue — used to seed the slider position from a value.
function expSliderIndex(value, min, max, steps) {
  const t = Math.log(value / min) / Math.log(max / min);
  return Math.round(t * (steps - 1));
}

/* ===========================================================
   Layout components
=========================================================== */

function Header({ connected, measuring, progress, onMenu, onMeasure }) {
  console.log('header', connected, measuring, progress)
  return html`
    <header class="app-header">
      <div class="header-row">
        <${IconButton} icon="menu" label="Menu" onClick=${onMenu} />

        <div class="header-title">
          <span class="title-main">SpectraLab X1</span>
          <span class="conn-status">
            <${StatusDot} ok=${connected} />
            ${connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        <${Button}
          variant="primary"
          icon="play"
          disabled=${!connected || measuring}
          onClick=${onMeasure}
        >
          ${measuring ? 'Measuring…' : 'Measure'}
        <//>
      </div>

      <div class="progress-track" aria-hidden=${!measuring}>
        <div class="progress-fill" style=${{ width: (measuring ? progress : 0) + '%' }}></div>
      </div>
    </header>
  `;
}

// One collapsible section. Accordion (below) owns which id is open.
function AccordionSection({ id, title, summary, openId, setOpenId, children }) {
  const isOpen = openId === id;
  return html`
    <section class=${'acc-section' + (isOpen ? ' acc-section--open' : '')}>
      <button class="acc-header" onClick=${() => setOpenId(isOpen ? null : id)} aria-expanded=${isOpen}>
        <span class="acc-header-left">
          <span class=${'acc-chevron' + (isOpen ? ' acc-chevron--open' : '')}><${Icon.chevron} /></span>
          <span class="acc-title">${title}</span>
        </span>
        ${summary && html`<span onClick=${e => e.stopPropagation()}>${summary}</span>`}
      </button>
      ${isOpen && html`<div class="acc-body-inner">${children}</div>`}
    </section>
  `;
}

// Owns the single-open-section state and renders a list of sections.
function Accordion({ sections, openId, setOpenId }) {
  return html`
    <div class="accordion">
      ${sections.map(s => html`
        <${AccordionSection}
          key=${s.id}
          id=${s.id}
          title=${s.title}
          summary=${s.summary}
          openId=${openId}
          setOpenId=${setOpenId}
        >
          ${s.content}
        <//>
      `)}
    </div>
  `;
}

function SideMenu({ open, onClose }) {
  const links = ['Instrument settings', 'Calibration', 'Export data', 'User accounts'];
  return html`
    <div class=${'drawer-backdrop ' + (open ? 'is-open' : '')} onClick=${onClose}></div>
    <nav class=${'drawer ' + (open ? 'is-open' : '')}>
      <div class="drawer-header">
        <span>Menu</span>
        <${IconButton} icon="close" label="Close menu" onClick=${onClose} />
      </div>
      <ul class="drawer-list">
        ${links.map(l => html`<li key=${l}><a href="#">${l}</a></li>`)}
      </ul>
    </nav>
  `;
}

function Footer() {
  return html`
    <footer class="app-footer">
      <span>SpectraLab X1 &middot; fw 2.4.1</span>
      <span class="footer-links">
        <a href="#" target="_blank" rel="noopener">Docs</a>
        <a href="#" target="_blank" rel="noopener">Support</a>
      </span>
    </footer>
  `;
}

/* ===========================================================
   Section contents (feature-specific, not generic components)
=========================================================== */

// Range input driven by a linear index but displaying/emitting an
// exponentially-spaced value. `steps` is the number of discrete positions.
function ExpSlider({ label, value, onChange, min, max, steps }) {
  const index = expSliderIndex(value, min, max, steps);
  return html`
    <div class="field">
      <span>${label} <span style=${{ color: 'var(--text)' }}>${value.toFixed(2)}</span></span>
      <input
        type="range"
        min="0"
        max=${steps - 1}
        step="1"
        value=${index}
        onInput=${e => onChange(expSliderValue(Number(e.target.value), min, max, steps))}
      />
    </div>
  `;
}

const SAMPLES_JUPYTER_NOTEBOOK = '/static/notebook.ipynb';

function SamplesSection({ dataset, label, onDatasetChange, onLabelChange }) {
  const { data, loading, error } = useFetchJson('/samples.json');
  const samples = Array.isArray(data) ? data : [];

  const notebookUrl = `${window.location.origin}${SAMPLES_JUPYTER_NOTEBOOK}`;
  const jupyterHref = `https://scikit-learn.org/stable/lite/lab/?fromURL=${notebookUrl}`;

  return html`
    <div class="field-grid">
      <${Field}
        label="Dataset"
        value=${dataset}
        onInput=${e => onDatasetChange(e.target.value)}
      />
      <${Field}
        label="Label"
        value=${label}
        onInput=${e => onLabelChange(e.target.value)}
      />
    </div>

    <div class="samples-actions">
      <a class="btn-secondary" href="/samples.json" download>Download samples.json</a>
      <a class="btn-secondary" href=${jupyterHref} target="_blank" rel="noopener">Open in Jupyter</a>
    </div>

    <div class="samples-list">
      ${loading && html`<p class="hint-text">Loading samples…</p>`}
      ${error && html`<p class="hint-text">Couldn't load samples.</p>`}
      ${!loading && !error && samples.length === 0 && html`<p class="hint-text">No samples yet.</p>`}
      ${samples.map((s, i) => html`<div class="sample-row" key=${s.id ?? i}>${s.name ?? JSON.stringify(s)}</div>`)}
    </div>
  `;
}

const ANALYSIS_METHOD = 'PCA logreg classification';
const ALPHA_MIN = 0.01;
const ALPHA_MAX = 10.0;
const ALPHA_STEPS = 40;

function AnalysisSection({ alpha, onAlphaChange }) {
  return html`
    <div class="field-grid">
      <${Field} label="Method" type="select" value=${ANALYSIS_METHOD} disabled>
        <option>${ANALYSIS_METHOD}</option>
      <//>
      <${ExpSlider}
        label="Alpha"
        value=${alpha}
        onChange=${onAlphaChange}
        min=${ALPHA_MIN}
        max=${ALPHA_MAX}
        steps=${ALPHA_STEPS}
      />
    </div>
  `;
}

function VisualizationSection() {
  return html`
    <div class="viz-placeholder">
      <p>Chart / plot output will render here.</p>
      <div class="field-grid">
        <${Field} label="Plot type" type="select">
          <option>Line</option>
          <option>Bar</option>
          <option>Scatter</option>
        <//>
      </div>
    </div>
  `;
}

/* ===========================================================
   Status polling
   GET /status is the single source of truth for connection,
   measuring, and progress. Polled at a fixed interval; a 200
   response means connected, any failure means disconnected.
   Expected JSON shape: { measuring: bool, progress: 0-100 }
=========================================================== */

const POLL_MS = 1000;

// One state object instead of three separate useStates, since
// connected/measuring/progress all update together on each poll.
function useStatus(url = '/status', intervalMs = POLL_MS) {
  const [status, setStatus] = useState({ connected: false, measuring: false, progress: 0 });

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error('bad status');
        const data = await res.json();
        console.log('status-poll-returned', data)
        if (!cancelled) {
          setStatus({ connected: true, measuring: !!data.measuring, progress: data.progress ?? 0 });
        }
      } catch (e) {
        console.log('status-poll-exception', e)
        if (!cancelled) setStatus({ connected: false, measuring: false, progress: 0 });
      }
    }

    poll();
    const id = setInterval(poll, intervalMs);
    return () => { cancelled = true; clearInterval(id); };
  }, [url, intervalMs]);

  return status;
}

async function startMeasurement(params) {
  try {
    await fetch('/measure', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  } catch {
    // Next poll will reflect the actual device state either way.
  }
}

/* ===========================================================
   Root App
=========================================================== */

function App() {
  const { connected, measuring, progress } = useStatus();
  const [openId, setOpenId] = useState('visualization');
  const [menuOpen, setMenuOpen] = useState(false);

  // Everything the measure endpoint needs, as one object.
  const [measureParams, setMeasureParams] = useState({
    dataset: 'data2',
    label: 'unknown',
    alpha: 1.0,
  });

  const sections = [
    {
      id: 'samples',
      title: 'Samples',
      summary: html`<${Chip}>${measureParams.dataset}<//>`,
      content: html`
        <${SamplesSection}
          dataset=${measureParams.dataset}
          label=${measureParams.label}
          onDatasetChange=${dataset => setMeasureParams(p => ({ ...p, dataset }))}
          onLabelChange=${label => setMeasureParams(p => ({ ...p, label }))}
        />
      `,
    },
    {
      id: 'analysis',
      title: 'Analysis',
      summary: html`<${Chip}>${ANALYSIS_METHOD}<//>`,
      content: html`
        <${AnalysisSection}
          alpha=${measureParams.alpha}
          onAlphaChange=${alpha => setMeasureParams(p => ({ ...p, alpha }))}
        />
      `,
    },
    {
      id: 'visualization',
      title: 'Visualization',
      summary: measuring ? html`<${Chip} tone="accent">Live<//>` : null,
      content: html`<${VisualizationSection} />`,
    },
  ];

  return html`
    <${Header}
      connected=${connected}
      measuring=${measuring}
      progress=${progress}
      onMenu=${() => setMenuOpen(true)}
      onMeasure=${() => startMeasurement(measureParams)}
    />

    <main class="app-main">
      <${Accordion} sections=${sections} openId=${openId} setOpenId=${setOpenId} />
    </main>

    <${Footer} />
    <${SideMenu} open=${menuOpen} onClose=${() => setMenuOpen(false)} />
  `;
}

render(html`<${App} />`, document.getElementById('app'));
