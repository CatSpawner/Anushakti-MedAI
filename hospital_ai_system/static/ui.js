// Shared UI utilities: api(), modal(), popup(), tables.
// Light-theme compatible popup system (matches your UI + fixes close/ESC/focus issues).
(function () {
  async function api(path, opts = {}) {
    const headers = opts.headers || {};
    headers["Content-Type"] = "application/json";

    const res = await fetch(path, { ...opts, headers, credentials: "include" });
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch { data = { raw: text }; }

    if (!res.ok) {
      const msg = data?.detail || data?.raw || ("HTTP " + res.status);
      throw new Error(msg);
    }
    return data;
  }

  function qs(sel, root=document){ return root.querySelector(sel); }
  function qsa(sel, root=document){ return Array.from(root.querySelectorAll(sel)); }
  function setText(el, v){ if (el) el.textContent = v ?? ""; }

  function formatDate(iso){
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return String(iso ?? "");
      return d.toLocaleString();
    } catch {
      return String(iso ?? "");
    }
  }

  function escapeHtml(s){
    return String(s ?? "")
      .replaceAll("&","&amp;")
      .replaceAll("<","&lt;")
      .replaceAll(">","&gt;")
      .replaceAll('"',"&quot;");
  }

  // ---------- Modal helpers (overlay) ----------
  function openModal(el){
    if (!el) return;
    el.classList.add("open");
    el.setAttribute("aria-hidden", "false");

    // focus first focusable
    const focusable = el.querySelector(
      'button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])'
    );
    if (focusable) setTimeout(() => focusable.focus(), 0);
  }

  function closeModal(el){
    if (!el) return;
    el.classList.remove("open");
    el.setAttribute("aria-hidden", "true");
  }

  // ---------- Popup system (your "center modal style") ----------
  // Requirements fixed:
  // - Backdrop click closes
  // - X closes
  // - OK closes
  // - ESC closes (scoped per popup)
  // - Prevent multiple listeners leaking
  // - Focus goes to OK button
  // - Clean DOM removal

  function ensurePopupStyles() {
    if (document.getElementById("hsPopupStyle")) return;

    const css = `
/* ==========================
   Hospital Popup (center)
   ========================== */
.hs-popup-root[hidden]{ display:none; }
.hs-popup-root{
  position: fixed;
  inset: 0;
  z-index: 5000;
  font-family: var(--sans);
}
.hs-popup-backdrop{
  position:absolute;
  inset:0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
}
.hs-popup{
  position:absolute;
  left:50%;
  top:50%;
  transform: translate(-50%, -50%);
  width: min(720px, calc(100vw - 28px));
  max-height: min(82vh, 760px);
  overflow: hidden;
  border-radius: 18px;
  background: rgba(255,255,255,.985);
  border: 1px solid rgba(15,23,42,.14);
  box-shadow: 0 22px 60px rgba(15,23,42, 0.18);
  border-left: 10px solid var(--primary);
}
.hs-popup-head{
  display:flex;
  gap: 12px;
  align-items:flex-start;
  padding: 16px 16px 12px;
  background: linear-gradient(180deg, rgba(15,23,42,.02), rgba(255,255,255,.98));
  border-bottom: 1px solid rgba(15,23,42,.10);
}
.hs-popup-icon{
  width: 42px;
  height: 42px;
  border-radius: 14px;
  flex: 0 0 42px;
  background: var(--primary);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.22);
  position: relative;
}
.hs-popup-icon::after{
  content: "";
  position:absolute;
  inset: 11px;
  border-radius: 9px;
  background: rgba(255,255,255,0.22);
}
.hs-popup-title{
  font-weight: 950;
  font-size: 16px;
  letter-spacing: -0.2px;
  color: var(--text);
}
.hs-popup-subtitle{
  margin-top: 4px;
  color: var(--muted);
  font-weight: 850;
  font-size: 13px;
  line-height: 1.35;
  white-space: pre-wrap;
}
.hs-popup-x{
  margin-left:auto;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: 1px solid rgba(15,23,42,.14);
  background: rgba(15,23,42,.03);
  cursor:pointer;
  font-weight: 950;
  font-size: 20px;
  color: var(--text);
}
.hs-popup-x:hover{ background: rgba(15,23,42,.06); }
.hs-popup-x:focus-visible{
  outline: 4px solid var(--ring);
  outline-offset: 2px;
}
.hs-popup-body{
  padding: 14px 16px 4px;
  overflow:auto;
  max-height: calc(82vh - 150px);
}
.hs-msg{
  font-weight: 850;
  color: var(--text);
  white-space: pre-wrap;
  line-height: 1.45;
}
.hs-pre{
  background: #0b1220;
  color: #e2e8f0;
  padding: 12px;
  border-radius: 12px;
  overflow:auto;
  border: 1px solid rgba(255,255,255,0.08);
}
.hs-kv{
  display:grid;
  grid-template-columns: 180px 1fr;
  gap: 8px 12px;
  padding: 12px;
  border: 1px solid rgba(15,23,42,.12);
  border-radius: 14px;
  background: rgba(255,255,255,.92);
}
@media (max-width: 520px){
  .hs-kv{ grid-template-columns: 1fr; }
}
.hs-k{ color: var(--muted); font-weight: 950; font-size: 12px; }
.hs-v{ font-weight: 950; font-size: 13px; overflow-wrap:anywhere; }
.hs-popup-foot{
  display:flex;
  gap: 10px;
  justify-content: space-between;
  align-items:center;
  padding: 12px 16px 16px;
  border-top: 1px solid rgba(15,23,42,.10);
  background: rgba(255,255,255,.98);
}
.hs-popup-foot-left, .hs-popup-foot-right{ display:flex; gap: 10px; flex-wrap:wrap; }
.hs-btn{
  appearance:none;
  border:1px solid rgba(15,23,42,.16);
  cursor:pointer;
  border-radius: 12px;
  padding:10px 12px;
  font-weight: 950;
  font-size: 13px;
  background: #fff;
  color: var(--text);
}
.hs-btn.primary{
  border-color: transparent;
  background: linear-gradient(180deg, var(--primary), var(--primary2));
  color:#fff;
}
.hs-btn.subtle{ background: rgba(15,23,42,.04); }
.hs-btn.danger{
  border-color: transparent;
  background: linear-gradient(180deg, var(--bad), #b91c1c);
  color:#fff;
}
.hs-btn:focus-visible{
  outline: 4px solid var(--ring);
  outline-offset: 2px;
}
/* type variants */
.hs-type-info .hs-popup{ border-left-color: var(--primary); }
.hs-type-info .hs-popup-icon{ background: var(--primary); }

.hs-type-success .hs-popup{ border-left-color: var(--accent); }
.hs-type-success .hs-popup-icon{ background: var(--accent); }

.hs-type-warning .hs-popup{ border-left-color: var(--warn); }
.hs-type-warning .hs-popup-icon{ background: var(--warn); }

.hs-type-error .hs-popup{ border-left-color: var(--bad); }
.hs-type-error .hs-popup-icon{ background: var(--bad); }

.hs-type-result .hs-popup{ border-left-color: #0ea5e9; }
.hs-type-result .hs-popup-icon{ background: #0ea5e9; }

.hs-type-confirm .hs-popup{ border-left-color: #7c3aed; }
.hs-type-confirm .hs-popup-icon{ background: #7c3aed; }
`;

    const style = document.createElement("style");
    style.id = "hsPopupStyle";
    style.textContent = css;
    document.head.appendChild(style);
  }

  function popup(type, title, message, opts = {}) {
    ensurePopupStyles();

    // Close existing popups if you want "single popup at a time"
    // (prevents stacking issues on mobile)
    const existing = document.querySelectorAll(".hs-popup-root");
    existing.forEach(el => el.remove());

    const {
      pre = null,
      kv = null,         // array of [k,v]
      okText = "OK",
      closeOnBackdrop = true,
      closeOnEsc = true,
    } = opts;

    const root = document.createElement("div");
    root.className = `hs-popup-root hs-type-${type}`;
    root.innerHTML = `
      <div class="hs-popup-backdrop"></div>
      <div class="hs-popup" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}">
        <div class="hs-popup-head">
          <div class="hs-popup-icon"></div>
          <div style="min-width:0;">
            <div class="hs-popup-title">${escapeHtml(title)}</div>
            <div class="hs-popup-subtitle">${escapeHtml(message)}</div>
          </div>
          <button class="hs-popup-x" type="button" aria-label="Close">×</button>
        </div>
        <div class="hs-popup-body">
          <div class="hs-msg" hidden></div>
        </div>
        <div class="hs-popup-foot">
          <div class="hs-popup-foot-left muted small">Press ESC to close</div>
          <div class="hs-popup-foot-right">
            <button class="hs-btn primary" type="button">${escapeHtml(okText)}</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(root);

    const backdrop = qs(".hs-popup-backdrop", root);
    const xBtn = qs(".hs-popup-x", root);
    const okBtn = qs(".hs-btn.primary", root);
    const body = qs(".hs-popup-body", root);

    // Optional additional content
    if (kv && Array.isArray(kv) && kv.length) {
      const kvBox = document.createElement("div");
      kvBox.className = "hs-kv";
      for (const [k, v] of kv) {
        const kEl = document.createElement("div");
        kEl.className = "hs-k";
        kEl.textContent = String(k);
        const vEl = document.createElement("div");
        vEl.className = "hs-v";
        vEl.textContent = String(v ?? "");
        kvBox.appendChild(kEl);
        kvBox.appendChild(vEl);
      }
      body.appendChild(kvBox);
    }

    if (pre !== null && pre !== undefined) {
      const preEl = document.createElement("pre");
      preEl.className = "hs-pre";
      preEl.textContent = String(pre);
      body.appendChild(preEl);
    }

    let closed = false;
    const close = () => {
      if (closed) return;
      closed = true;
      document.removeEventListener("keydown", onKeyDown);
      if (root && root.parentNode) root.parentNode.removeChild(root);
    };

    // Click handlers
    xBtn.addEventListener("click", close);
    okBtn.addEventListener("click", close);
    if (closeOnBackdrop) backdrop.addEventListener("click", close);

    // ESC handler (scoped)
    function onKeyDown(e){
      if (!closeOnEsc) return;
      if (e.key === "Escape") close();
    }
    document.addEventListener("keydown", onKeyDown);

    // Focus OK by default
    setTimeout(() => okBtn.focus(), 0);

    return { close };
  }

  // Tables: adds data-labels for mobile stacked mode (matches your CSS)
  function renderTable(columns, rows) {
    const table = document.createElement("table");

    const thead = document.createElement("thead");
    const trh = document.createElement("tr");
    for (const c of columns) {
      const th = document.createElement("th");
      th.textContent = c.label;
      trh.appendChild(th);
    }
    thead.appendChild(trh);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    for (const r of rows) {
      const tr = document.createElement("tr");
      for (const c of columns) {
        const td = document.createElement("td");
        const val = c.render ? c.render(r) : String(r[c.key] ?? "");
        td.textContent = val;
        td.setAttribute("data-label", c.label);
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    return table;
  }

  window.UI = {
    api, qs, qsa, setText,
    popup, openModal, closeModal,
    renderTable, formatDate, escapeHtml
  };
})();