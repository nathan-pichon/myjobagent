"""Local dashboard renderer — a single self-contained HTML file served from
the user's machine. Uses the MyJobAgent design tokens (light + dark, AA colors)
and the verdict-first ScoreBreakdown from product/02_DESIGN.md.

No network, no external assets: everything is inlined so it works offline.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jobhunt.config import JobHuntConfig
    from jobhunt.store import Store

_VERDICT = {
    "strong": ("Fort match", "★", "var(--jb-score-strong)"),
    "good": ("Bon match", "◑", "var(--jb-score-good)"),
    "partial": ("Match partiel", "◔", "var(--jb-score-partial)"),
    "weak": ("Hors cible", "·", "var(--jb-text-muted)"),
}

_CSS = """
:root{--jb-bg:#FBFCFE;--jb-surface:#FFF;--jb-surface-alt:#F3F6FB;--jb-text:#0E1A2B;
--jb-text-muted:#4A5A72;--jb-primary:#2E6BFF;--jb-border:#E4EAF2;
--jb-score-strong:#007A6A;--jb-score-good:#4F46E5;--jb-score-partial:#B07000;
--jb-radius:12px;--jb-shadow:0 8px 24px rgba(46,107,255,.10);--jb-beam:linear-gradient(120deg,#2E6BFF,#00C2A8)}
@media(prefers-color-scheme:dark){:root{--jb-bg:#0D1117;--jb-surface:#161B22;
--jb-surface-alt:#1C2333;--jb-text:#E6EDF3;--jb-text-muted:#8B949E;--jb-primary:#4D8EFF;
--jb-border:#30363D;--jb-score-strong:#3DD6BF;--jb-score-good:#8AB4FF;--jb-score-partial:#FFD06B;--jb-shadow:none}}
*{box-sizing:border-box;margin:0}
body{font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:var(--jb-bg);color:var(--jb-text);padding:2rem;line-height:1.5;font-variant-numeric:tabular-nums}
.wrap{max-width:1080px;margin:0 auto}
header{display:flex;align-items:center;gap:.75rem;margin-bottom:.25rem}
.beam{width:28px;height:28px;border-radius:8px;background:var(--jb-beam)}
h1{font-size:1.6rem}
.privacy{font-size:.8rem;color:var(--jb-text-muted);border:1px solid var(--jb-border);
padding:.2rem .6rem;border-radius:999px;margin-left:auto}
.meta{color:var(--jb-text-muted);margin:.5rem 0 1.5rem;font-size:.9rem}
.bar{display:flex;gap:1rem;margin-bottom:1.5rem;flex-wrap:wrap}
.kpi{background:var(--jb-surface-alt);border-radius:var(--jb-radius);padding:.8rem 1.2rem;min-width:120px}
.kpi b{font-size:1.4rem;color:var(--jb-primary)}.kpi span{display:block;font-size:.8rem;color:var(--jb-text-muted)}
.card{background:var(--jb-surface);border:1px solid var(--jb-border);border-radius:var(--jb-radius);
box-shadow:var(--jb-shadow);padding:1.2rem;margin-bottom:1rem}
.card summary{display:flex;align-items:flex-start;gap:1rem;cursor:pointer;list-style:none}
.card summary::-webkit-details-marker{display:none}
.pill{flex-shrink:0;width:74px;text-align:center;border-radius:10px;padding:.5rem .2rem;color:#fff}
.pill b{font-size:1.3rem;display:block}.pill span{font-size:.7rem}
.head{flex:1}.head h3{font-size:1.05rem}.head .sub{color:var(--jb-text-muted);font-size:.85rem;margin-top:.15rem}
.tags{margin-top:.4rem}.tag{display:inline-block;background:var(--jb-surface-alt);border-radius:999px;
padding:.1rem .55rem;font-size:.72rem;margin:.15rem .25rem 0 0;color:var(--jb-text-muted)}
.summary{margin:.6rem 0;font-size:.92rem}
.breakdown{margin-top:.8rem;border-top:1px solid var(--jb-border);padding-top:.8rem}
.seg{margin:.5rem 0}.seg .lbl{display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:.2rem}
.track{height:8px;background:var(--jb-surface-alt);border-radius:999px;overflow:hidden}
.fill{height:100%;border-radius:999px;background:var(--jb-primary)}
.gaps{font-size:.82rem;margin-top:.3rem}
.gap-block{color:var(--jb-score-partial)}.gap-cosmetic{color:var(--jb-text-muted)}
.matched{color:var(--jb-score-strong)}
a.view{color:var(--jb-primary);text-decoration:none;font-size:.85rem}
.empty{text-align:center;padding:3rem;color:var(--jb-text-muted)}
.kbn{display:grid;grid-template-columns:repeat(6,1fr);gap:.6rem;margin-top:1rem;overflow-x:auto}
.kbn-col{background:var(--jb-surface-alt);border-radius:10px;padding:.5rem;min-width:130px}
.kbn-head{font-size:.78rem;font-weight:600;color:var(--jb-text-muted);margin-bottom:.5rem;display:flex;justify-content:space-between}
.kbn-count{background:var(--jb-surface);border-radius:999px;padding:0 .45rem;font-size:.72rem}
.kbn-card{background:var(--jb-surface);border:1px solid var(--jb-border);border-radius:8px;padding:.5rem;margin-bottom:.5rem}
.kbn-card:focus{outline:2px solid var(--jb-primary);outline-offset:2px}
.kbn-score{font-weight:700;font-size:.85rem;color:var(--jb-primary)}
.kbn-title{font-size:.8rem;margin:.1rem 0}.kbn-sub{font-size:.72rem;color:var(--jb-text-muted)}
.kbn-moves{display:flex;flex-wrap:wrap;gap:.2rem;margin-top:.35rem}
.kbn-move{font-size:.65rem;border:1px solid var(--jb-border);background:var(--jb-surface-alt);border-radius:999px;padding:.05rem .4rem;cursor:pointer;color:var(--jb-text-muted)}
.kbn-move:hover,.kbn-move:focus{border-color:var(--jb-primary);color:var(--jb-primary)}
.kbn-empty{font-size:.75rem;color:var(--jb-text-muted);text-align:center;padding:.5rem}
.kbn-cmd{margin-top:.8rem;font-family:'JetBrains Mono',monospace;font-size:.78rem;background:var(--jb-surface-alt);border-radius:8px;padding:.6rem;user-select:all;word-break:break-all}
.kbn-card{cursor:pointer}.kbn-card:hover{border-color:var(--jb-primary)}
.kbn-card[draggable=true]:active{cursor:grabbing}
.kbn-link{display:inline-block;margin-top:.35rem;font-size:.7rem;color:var(--jb-primary);text-decoration:none;font-weight:600}
.kbn-link:hover{text-decoration:underline}
.kbn-drop{min-height:2.5rem}
.kbn-col.kbn-over{outline:2px dashed var(--jb-primary);outline-offset:-2px}
.modal{position:fixed;inset:0;background:rgba(8,12,20,.55);display:flex;align-items:center;justify-content:center;padding:1rem;z-index:100}
.modal[hidden]{display:none}
.modal-box{background:var(--jb-surface);border-radius:var(--jb-radius);max-width:640px;width:100%;max-height:88vh;overflow:auto;padding:1.5rem;position:relative;box-shadow:0 20px 60px rgba(0,0,0,.35)}
.modal-close{position:absolute;top:.8rem;right:.9rem;background:none;border:none;font-size:1.5rem;line-height:1;cursor:pointer;color:var(--jb-text-muted)}
.modal-close:hover,.modal-close:focus{color:var(--jb-text)}
.detail-head{display:flex;gap:1rem;align-items:flex-start;margin-bottom:.8rem;padding-right:1.5rem}
.detail-actions{display:flex;align-items:center;gap:.5rem;margin:.4rem 0}
.btn-offer{display:inline-block;background:var(--jb-primary);color:#fff;text-decoration:none;font-size:.85rem;font-weight:600;padding:.45rem .9rem;border-radius:8px}
.btn-offer:hover{filter:brightness(1.08)}
.fb-btn{font-size:.95rem;background:var(--jb-surface-alt);border:1px solid var(--jb-border);border-radius:8px;padding:.3rem .6rem;cursor:pointer;line-height:1}
.fb-btn:hover,.fb-btn:focus{border-color:var(--jb-primary)}
.flag-btn{font-size:.8rem;background:var(--jb-surface-alt);border:1px solid var(--jb-border);border-radius:8px;padding:.4rem .7rem;cursor:pointer;line-height:1;color:var(--jb-text-muted)}
.flag-btn:hover,.flag-btn:focus{border-color:var(--jb-danger);color:var(--jb-danger)}
.flag-btn.flag-on{background:color-mix(in srgb, var(--jb-danger) 12%, var(--jb-surface));border-color:var(--jb-danger);color:var(--jb-danger);font-weight:600}
@media(max-width:760px){.kbn{grid-template-columns:repeat(2,1fr)}}
.settings-btn{margin-left:auto;background:var(--jb-surface-alt);border:1px solid var(--jb-border);border-radius:999px;padding:.3rem .8rem;font-size:.8rem;cursor:pointer;color:var(--jb-text)}
.settings-btn:hover,.settings-btn:focus{border-color:var(--jb-primary);color:var(--jb-primary)}
.settings-btn+.privacy{margin-left:.5rem}
.set-row{display:flex;align-items:center;gap:.5rem;font-size:.9rem}
.secret-row{margin-bottom:.7rem;display:flex;flex-direction:column;gap:.25rem}
.secret-row label{font-size:.85rem}
.secret-row input{font-family:'JetBrains Mono',monospace;font-size:.8rem;padding:.4rem .6rem;border:1px solid var(--jb-border);border-radius:8px;background:var(--jb-surface);color:var(--jb-text)}
.secret-row input:focus{outline:2px solid var(--jb-primary);outline-offset:1px}
#settings input[type=number]{padding:.3rem .5rem;border:1px solid var(--jb-border);border-radius:8px;background:var(--jb-surface);color:var(--jb-text)}
.live-banner{display:flex;align-items:center;gap:.6rem;background:var(--jb-primary-soft,#E8F0FF);border:1px solid var(--jb-primary);border-radius:10px;padding:.6rem .9rem;margin:.5rem 0;font-size:.85rem;color:var(--jb-text)}
.live-counts{margin-left:auto;color:var(--jb-text-muted);font-size:.8rem;font-variant-numeric:tabular-nums}
.live-dot{width:9px;height:9px;border-radius:999px;background:var(--jb-primary);flex-shrink:0;animation:livepulse 1.2s ease-in-out infinite}
@keyframes livepulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.7)}}
.new-toast{display:flex;align-items:center;gap:.8rem;background:var(--jb-accent-bg,#E6FAF7);border:1px solid var(--jb-accent,#00C2A8);border-radius:10px;padding:.6rem .9rem;margin:.5rem 0;font-size:.88rem;font-weight:600;color:var(--jb-text)}
.toast-btn{margin-left:auto;background:var(--jb-accent,#00C2A8);color:#fff;border:none;border-radius:8px;padding:.35rem .8rem;font-size:.8rem;font-weight:600;cursor:pointer}
.toast-btn:hover{filter:brightness(1.08)}
@media(prefers-reduced-motion:reduce){.live-dot{animation:none}}
"""

_MAX = {"stack": 40, "role": 20, "location": 25, "contract": 15}


def _segment(name: str, seg: dict) -> str:
    score = seg.get("score", 0)
    mx = seg.get("max", _MAX.get(name, 100))
    pct = int(100 * score / mx) if mx else 0
    matched = seg.get("matched", []) or []
    gaps = seg.get("gaps", []) or []
    gap_html = ""
    for g in gaps:
        cls = "gap-block" if g.get("type") == "blocking" else "gap-cosmetic"
        mark = "⛔" if g.get("type") == "blocking" else "△"
        gap_html += f'<div class="{cls}">{mark} {html.escape(str(g.get("item","")))}</div>'
    matched_html = ""
    if matched:
        matched_html = f'<div class="matched">✓ {html.escape(", ".join(str(m) for m in matched))}</div>'
    return f"""<div class="seg">
      <div class="lbl"><span>{name.capitalize()}</span><span>{score}/{mx}</span></div>
      <div class="track"><div class="fill" style="width:{pct}%"></div></div>
      <div class="gaps">{matched_html}{gap_html}</div>
    </div>"""


def _card(job: dict) -> str:
    verdict = job.get("breakdown") and _verdict_from_score(job.get("score", 0))
    label, icon, color = _VERDICT.get(verdict or _verdict_from_score(job.get("score", 0)), _VERDICT["weak"])
    bd = job.get("breakdown") or {}
    segs = "".join(_segment(k, bd.get(k, {})) for k in ("stack", "role", "location", "contract") if bd.get(k))
    sources = job.get("sources", [])
    multi = f'<span class="tag">{len(sources)} sources</span>' if len(sources) > 1 else ""
    return f"""<details class="card">
      <summary>
        <div class="pill" style="background:{color}"><b>{job.get('score',0)}</b><span>{icon} {label}</span></div>
        <div class="head">
          <h3>{html.escape(job.get('title','Sans titre'))}</h3>
          <div class="sub">{html.escape(job.get('company','Inconnue'))} · {html.escape(job.get('location',''))} · {html.escape(job.get('contract',''))}</div>
          <div class="tags"><span class="tag">{html.escape(job.get('source',''))}</span>{multi}</div>
        </div>
        <a class="view" href="{html.escape(job.get('url','#'))}" target="_blank" rel="noopener">Voir →</a>
      </summary>
      <p class="summary">{html.escape(job.get('summary',''))}</p>
      <div class="breakdown">{segs or '<em>Pas de détail disponible.</em>'}</div>
    </details>"""


def _verdict_from_score(score: int) -> str:
    if score >= 75:
        return "strong"
    if score >= 60:
        return "good"
    if score >= 50:
        return "partial"
    return "weak"


_PIPELINE = ["found", "interested", "applied", "interview", "offer", "rejected"]
_PIPELINE_LABEL = {
    "found": "Trouvé", "interested": "Intéressé", "applied": "Postulé",
    "interview": "Entretien", "offer": "Offre", "rejected": "Refusé",
}


def _card_detail(job: dict) -> str:
    """Full offer detail (reused in the modal). Verdict-first ScoreBreakdown."""
    label, icon, color = _VERDICT.get(_verdict_from_score(job.get("score", 0)), _VERDICT["weak"])
    bd = job.get("breakdown") or {}
    segs = "".join(_segment(k, bd.get(k, {})) for k in ("stack", "role", "location", "contract") if bd.get(k))
    sources = job.get("sources", []) or []
    src_links = " · ".join(
        f'<a class="view" href="{html.escape(u)}" target="_blank" rel="noopener">source {i+1} ↗</a>'
        for i, u in enumerate(sources)
    ) if len(sources) > 1 else ""
    return f"""<div class="detail-head">
        <div class="pill" style="background:{color}"><b>{job.get('score',0)}</b><span>{icon} {label}</span></div>
        <div>
          <h2 style="font-size:1.2rem">{html.escape(job.get('title','Sans titre'))}</h2>
          <div class="sub">{html.escape(job.get('company','Inconnue'))} · {html.escape(job.get('location',''))} · {html.escape(job.get('contract',''))}</div>
        </div>
      </div>
      <div class="detail-actions" data-url="{html.escape(job.get('url',''))}" data-kind="{html.escape(job.get('feedback_kind') or '')}">
        <a class="btn-offer" href="{html.escape(job.get('url','#'))}" target="_blank" rel="noopener" data-i18n="detail.view">Voir l'offre ↗</a>
        <button class="flag-btn{' flag-on' if job.get('feedback_kind') == 'irrelevant' else ''}" data-flag="irrelevant" aria-pressed="{'true' if job.get('feedback_kind') == 'irrelevant' else 'false'}" data-i18n="flag.irrelevant" title="L'agent en tiendra compte pour affiner sa stratégie">⊘ Pas pertinent</button>
        <button class="flag-btn{' flag-on' if job.get('feedback_kind') == 'outdated' else ''}" data-flag="outdated" aria-pressed="{'true' if job.get('feedback_kind') == 'outdated' else 'false'}" data-i18n="flag.outdated" title="Offre périmée — l'agent affinera la détection de fraîcheur">⌛ Périmée</button>
      </div>
      <p class="summary">{html.escape(job.get('summary',''))}</p>
      <div class="breakdown">{segs or '<em>Pas de détail disponible.</em>'}</div>
      {f'<div class="sub" style="margin-top:.8rem">Aussi vue sur : {src_links}</div>' if src_links else ''}"""


def _kanban(store: "Store") -> str:
    """Application pipeline: drag & drop between columns, click a card for full
    detail (modal), and a direct link to the offer.

    Persistence stays zero-backend: a drop optimistically updates the column in
    localStorage AND surfaces the exact `mja move` command (auto-copied) so
    the change can be committed to the local SQLite store. Buttons remain as a
    keyboard-accessible fallback to the drag gesture.
    """
    cols = {s: store.get_jobs(status=s) for s in _PIPELINE}
    total = sum(len(v) for v in cols.values())
    if not total:
        return ""

    # Stable id per job for modal lookup; pre-render hidden details.
    details = ""
    idx = 0
    id_of: dict[str, int] = {}
    for s in _PIPELINE:
        for j in cols[s]:
            id_of[j["url"]] = idx
            details += f'<template id="detail-{idx}">{_card_detail(j)}</template>'
            idx += 1

    col_html = ""
    for s in _PIPELINE:
        items = cols[s]
        cards = ""
        for j in items:
            did = id_of[j["url"]]
            nexts = [n for n in _PIPELINE if n != s]
            opts = " ".join(
                f'<button class="kbn-move" data-url="{html.escape(j["url"])}" data-status="{n}" '
                f'aria-label="Déplacer vers {_PIPELINE_LABEL[n]}">{_PIPELINE_LABEL[n]}</button>'
                for n in nexts
            )
            cards += (
                f'<div class="kbn-card" draggable="true" tabindex="0" role="button" '
                f'data-url="{html.escape(j["url"])}" data-detail="detail-{did}" '
                f'aria-label="{html.escape(j.get("title",""))} — cliquer pour le détail">'
                f'<div class="kbn-score">{j.get("score",0)}</div>'
                f'<div class="kbn-title">{html.escape(j.get("title","")[:48])}</div>'
                f'<div class="kbn-sub">{html.escape(j.get("company","")[:30])}</div>'
                f'<a class="kbn-link" href="{html.escape(j.get("url","#"))}" target="_blank" rel="noopener" '
                f'onclick="event.stopPropagation()">Voir l\'offre ↗</a>'
                f'<div class="kbn-moves">{opts}</div></div>'
            )
        col_html += (
            f'<div class="kbn-col" data-status="{s}"><div class="kbn-head">{_PIPELINE_LABEL[s]} '
            f'<span class="kbn-count">{len(items)}</span></div>'
            f'<div class="kbn-drop">{cards or "<div class=kbn-empty>—</div>"}</div></div>'
        )

    return f"""<details class="card" style="margin-top:1.5rem" open>
      <summary style="cursor:pointer"><div class="head"><h3>Pipeline de candidatures</h3>
      <div class="sub">Glisse-dépose une carte entre colonnes, ou clique-la pour le détail. Chaque déplacement copie la commande <code>mja move</code> à coller (zéro serveur — tout reste local).</div></div></summary>
      <div class="kbn">{col_html}</div>
      <div id="kbn-cmd" class="kbn-cmd" role="status" aria-live="polite" hidden></div>
      {details}
    </details>
    <div id="modal" class="modal" hidden role="dialog" aria-modal="true" aria-label="Détail de l'offre">
      <div class="modal-box"><button class="modal-close" aria-label="Fermer">×</button><div id="modal-body"></div></div>
    </div>
    <script>{_KANBAN_JS}</script>"""


_KANBAN_JS = r"""
(function(){
  var cmdBox = document.getElementById('kbn-cmd');
  // If the local server injected a token, we persist moves directly to SQLite
  // via the local API (127.0.0.1 only). Otherwise (static file opened directly)
  // we fall back to localStorage + a copyable `mja move` command.
  var TOKEN = window.__JB_TOKEN__ || null;
  function commit(url, status){
    if(TOKEN){
      fetch('/api/move', {method:'POST', headers:{'Content-Type':'application/json','X-JB-Token':TOKEN},
        body: JSON.stringify({url:url, status:status})})
        .then(function(r){
          cmdBox.hidden=false;
          cmdBox.textContent = r.ok ? '✓ déplacé vers « '+status+' » (enregistré)' : '⚠ échec de l\'enregistrement';
        }).catch(function(){ cmdBox.hidden=false; cmdBox.textContent='⚠ serveur local injoignable'; });
    } else {
      try { saved[url]=status; localStorage.setItem('jb_pipeline', JSON.stringify(saved)); } catch(e){}
      var cmd = 'mja move "' + url + '" ' + status;
      cmdBox.hidden = false;
      cmdBox.textContent = '✓ déplacé — colle pour rendre permanent :  ' + cmd;
      if (navigator.clipboard) navigator.clipboard.writeText(cmd).catch(function(){});
    }
  }
  // recount columns AND keep the empty-placeholder in sync (single source of truth)
  function recount(){
    document.querySelectorAll('.kbn-col').forEach(function(col){
      var drop = col.querySelector('.kbn-drop');
      var cards = drop.querySelectorAll('.kbn-card');
      col.querySelector('.kbn-count').textContent = cards.length;
      var empty = drop.querySelector('.kbn-empty');
      if(cards.length && empty) empty.remove();
      if(!cards.length && !empty){
        var e=document.createElement('div'); e.className='kbn-empty'; e.textContent='—'; drop.appendChild(e);
      }
    });
  }
  function moveCardTo(card, status){
    var drop = document.querySelector('.kbn-col[data-status="'+status+'"] .kbn-drop');
    if(card && drop) drop.appendChild(card);
    recount();
  }
  // In file mode, restore optimistic moves saved locally. In server mode the
  // columns already reflect SQLite, so we don't touch them.
  var saved = {};
  if(!TOKEN){
    try { saved = JSON.parse(localStorage.getItem('jb_pipeline')||'{}'); } catch(e){}
    Object.keys(saved).forEach(function(url){
      moveCardTo(document.querySelector('.kbn-card[data-url="'+CSS.escape(url)+'"]'), saved[url]);
    });
  }
  recount();
  // --- drag & drop ---
  var dragged = null;
  document.querySelectorAll('.kbn-card').forEach(function(card){
    card.addEventListener('dragstart', function(e){ dragged=card; card.style.opacity='.4'; e.dataTransfer.effectAllowed='move'; });
    card.addEventListener('dragend', function(){ card.style.opacity=''; dragged=null; });
  });
  document.querySelectorAll('.kbn-col').forEach(function(col){
    var drop = col.querySelector('.kbn-drop');
    col.addEventListener('dragover', function(e){ e.preventDefault(); col.classList.add('kbn-over'); });
    col.addEventListener('dragleave', function(){ col.classList.remove('kbn-over'); });
    col.addEventListener('drop', function(e){
      e.preventDefault(); col.classList.remove('kbn-over');
      if(!dragged) return;
      var url = dragged.dataset.url, status = col.dataset.status;
      moveCardTo(dragged, status); commit(url, status);
    });
  });
  // --- button fallback (keyboard accessible) ---
  document.querySelectorAll('.kbn-move').forEach(function(b){
    b.addEventListener('click', function(e){
      e.stopPropagation();
      moveCardTo(b.closest('.kbn-card'), b.dataset.status);
      commit(b.dataset.url, b.dataset.status);
    });
  });
  // --- click / keyboard → modal detail ---
  var modal = document.getElementById('modal'), body = document.getElementById('modal-body');
  function openModal(card){
    var tpl = document.getElementById(card.dataset.detail);
    if(!tpl) return;
    body.innerHTML = ''; body.appendChild(tpl.content.cloneNode(true));
    // wire the feedback toggles (irrelevant / outdated) — mutually exclusive.
    // These are the signals the agent uses to refine its strategy (mja tune).
    var actions = body.querySelector('.detail-actions');
    if(actions){
      var url = actions.dataset.url;
      actions.querySelectorAll('.flag-btn').forEach(function(btn){
        btn.addEventListener('click', function(){
          var kind = btn.dataset.flag;
          var wasOn = btn.classList.contains('flag-on');
          // clear all, then set this one unless we're toggling it off
          actions.querySelectorAll('.flag-btn').forEach(function(b){
            b.classList.remove('flag-on'); b.setAttribute('aria-pressed','false');
          });
          var nowKind = wasOn ? '' : kind;
          if(nowKind){ btn.classList.add('flag-on'); btn.setAttribute('aria-pressed','true'); }
          if(TOKEN){
            fetch('/api/feedback-kind',{method:'POST',headers:{'Content-Type':'application/json','X-JB-Token':TOKEN},
              body:JSON.stringify({url:url, kind:nowKind || null})}).catch(function(){});
          } else {
            var cmd = nowKind ? ('mja flag "'+url+'" '+nowKind) : ('mja flag "'+url+'" --undo');
            if(navigator.clipboard) navigator.clipboard.writeText(cmd).catch(function(){});
          }
        });
      });
    }
    modal.hidden = false; modal.querySelector('.modal-close').focus();
  }
  function closeModal(){ modal.hidden = true; }
  document.querySelectorAll('.kbn-card').forEach(function(card){
    card.addEventListener('click', function(e){ if(e.target.closest('a,button')) return; openModal(card); });
    card.addEventListener('keydown', function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); openModal(card); } });
  });
  modal.querySelector('.modal-close').addEventListener('click', closeModal);
  modal.addEventListener('click', function(e){ if(e.target===modal) closeModal(); });
  document.addEventListener('keydown', function(e){ if(e.key==='Escape' && !modal.hidden) closeModal(); });
})();
"""


_SETTINGS_HTML = """
<div id="settings" class="modal" hidden role="dialog" aria-modal="true" aria-label="Réglages">
  <div class="modal-box"><button class="modal-close" data-close-settings aria-label="Fermer">×</button>
    <h2 style="font-size:1.2rem;margin-bottom:1rem">Réglages</h2>

    <section style="margin-bottom:1.5rem">
      <h3 style="font-size:1rem;margin-bottom:.5rem">⏱ Chasse automatique</h3>
      <p class="sub" style="margin-bottom:.6rem">L'agent lance une chasse à intervalle régulier, tout seul, en local.</p>
      <label style="display:flex;align-items:center;gap:.5rem;margin-bottom:.6rem">
        <input type="checkbox" id="sch-enabled"> Activer la chasse automatique
      </label>
      <label class="set-row">Toutes les
        <input type="number" id="sch-hours" min="0.25" max="168" step="0.25" style="width:5rem"> heures
      </label>
      <label style="display:flex;align-items:center;gap:.5rem;margin:.5rem 0">
        <input type="checkbox" id="sch-notify"> Notification système sur nouveaux matches
      </label>
      <div style="display:flex;gap:.5rem;margin-top:.6rem">
        <button class="btn-offer" id="sch-save" style="border:none;cursor:pointer">Enregistrer</button>
        <button class="fb-btn" id="run-now" title="Lancer une chasse maintenant">▶ Lancer maintenant</button>
      </div>
      <div id="sch-status" class="sub" style="margin-top:.5rem" role="status" aria-live="polite"></div>
    </section>

    <section style="margin-bottom:1.5rem">
      <h3 style="font-size:1rem;margin-bottom:.5rem">📡 Flux RSS de recrutement</h3>
      <p class="sub" style="margin-bottom:.6rem">Sources officielles et stables — souvent avec le texte complet de l'offre (pas de scraping). Un flux par ligne, au format <code>Nom | https://url-du-flux</code>.</p>
      <label style="display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem">
        <input type="checkbox" id="rss-enabled"> Activer les flux RSS
      </label>
      <textarea id="rss-feeds" rows="5" placeholder="WeWorkRemotely Backend | https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss" style="width:100%;font-family:'JetBrains Mono',monospace;font-size:.78rem;padding:.5rem;border:1px solid var(--jb-border);border-radius:8px;background:var(--jb-surface);color:var(--jb-text)"></textarea>
      <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.6rem">
        <button class="btn-offer" id="rss-save" style="border:none;cursor:pointer">Enregistrer les flux</button>
        <button class="fb-btn" id="rss-restore" title="Remettre la liste de flux par défaut">↺ Restaurer les flux par défaut</button>
      </div>
      <div id="rss-status" class="sub" style="margin-top:.5rem" role="status" aria-live="polite"></div>
    </section>

    <section>
      <h3 style="font-size:1rem;margin-bottom:.5rem">🔑 Clés &amp; identifiants</h3>
      <p class="sub" style="margin-bottom:.6rem">Stockées en local (fichier 0600 sur ta machine), jamais envoyées en ligne.</p>
      <div id="secrets-list"></div>
      <button class="btn-offer" id="secrets-save" style="border:none;cursor:pointer;margin-top:.6rem">Enregistrer les clés</button>
      <div id="secrets-status" class="sub" style="margin-top:.5rem" role="status" aria-live="polite"></div>
    </section>
  </div>
</div>"""

_SETTINGS_JS = r"""
(function(){
  var TOKEN = window.__JB_TOKEN__ || null;
  var btn = document.getElementById('open-settings');
  if(!TOKEN){ return; }              // settings need the local server
  btn.hidden = false;
  var modal = document.getElementById('settings');
  function api(path, body){
    return fetch(path, {method: body?'POST':'GET',
      headers: body?{'Content-Type':'application/json','X-JB-Token':TOKEN}:{'X-JB-Token':TOKEN},
      body: body?JSON.stringify(body):undefined}).then(function(r){return r.json();});
  }
  function fmtLast(l){
    if(!l) return 'Aucune chasse encore.';
    if(l.error) return 'Dernière chasse : erreur — '+l.error;
    return 'Dernière chasse : '+l.matches+' matches ('+l.new+' nouveaux).';
  }
  function load(){
    api('/api/settings').then(function(s){
      document.getElementById('sch-enabled').checked = s.schedule.enabled;
      document.getElementById('sch-hours').value = s.schedule.every_hours;
      document.getElementById('sch-notify').checked = s.schedule.notify;
      document.getElementById('sch-status').textContent =
        (s.running?'⏳ chasse en cours… ':'') + fmtLast(s.last_run);
      if(s.rss){
        document.getElementById('rss-enabled').checked = s.rss.enabled;
        document.getElementById('rss-feeds').value =
          (s.rss.feeds||[]).map(function(f){ return f.name+' | '+f.url; }).join('\n');
        window.__JB_RSS_DEFAULTS__ = s.rss.defaults || [];
      }
      var list = document.getElementById('secrets-list'); list.innerHTML='';
      Object.keys(s.secrets).forEach(function(name){
        var sec = s.secrets[name];
        var row = document.createElement('div'); row.className='secret-row';
        var status = sec.set ? (sec.source==='env' ? '✓ (variable d\'env)' : '✓ enregistrée') : '— non définie';
        row.innerHTML = '<label>'+sec.label+' <span class="sub">'+status+'</span></label>'+
          '<input type="password" data-secret="'+name+'" placeholder="'+(sec.set?'•••••• (laisser vide pour garder)':'coller la valeur')+'"'+
          (sec.locked?' disabled title="définie par variable d\'environnement"':'')+'>';
        list.appendChild(row);
      });
    });
  }
  btn.addEventListener('click', function(){ load(); modal.hidden=false; modal.querySelector('.modal-close').focus(); });
  modal.querySelector('[data-close-settings]').addEventListener('click', function(){ modal.hidden=true; });
  modal.addEventListener('click', function(e){ if(e.target===modal) modal.hidden=true; });
  document.addEventListener('keydown', function(e){ if(e.key==='Escape' && !modal.hidden) modal.hidden=true; });

  document.getElementById('sch-save').addEventListener('click', function(){
    api('/api/schedule', {
      enabled: document.getElementById('sch-enabled').checked,
      every_hours: parseFloat(document.getElementById('sch-hours').value)||6,
      notify: document.getElementById('sch-notify').checked
    }).then(function(r){
      document.getElementById('sch-status').textContent = r.ok ? '✓ planification enregistrée'+(r.schedule.enabled?' (active)':'') : '⚠ '+(r.error||'erreur');
    });
  });
  document.getElementById('run-now').addEventListener('click', function(){
    document.getElementById('sch-status').textContent = '⏳ chasse lancée…';
    api('/api/run-now', {}).then(function(){ setTimeout(load, 1500); });
  });
  document.getElementById('rss-save').addEventListener('click', function(){
    var feeds = document.getElementById('rss-feeds').value.split('\n').map(function(line){
      var i = line.indexOf('|');
      if(i<0){ var u=line.trim(); return u?{name:u,url:u,enabled:true}:null; }
      return {name:line.slice(0,i).trim()||line.slice(i+1).trim(), url:line.slice(i+1).trim(), enabled:true};
    }).filter(function(f){ return f && f.url; });
    api('/api/rss', {enabled: document.getElementById('rss-enabled').checked, feeds: feeds})
      .then(function(r){ document.getElementById('rss-status').textContent =
        r.ok ? '✓ '+r.rss.feeds.length+' flux enregistré(s)' : '⚠ '+(r.error||'erreur'); });
  });
  document.getElementById('rss-restore').addEventListener('click', function(){
    var defs = window.__JB_RSS_DEFAULTS__ || [];
    document.getElementById('rss-feeds').value =
      defs.map(function(f){ return f.name+' | '+f.url; }).join('\n');
    document.getElementById('rss-enabled').checked = true;
    document.getElementById('rss-status').textContent =
      defs.length+' flux par défaut chargés — clique « Enregistrer les flux » pour valider.';
  });
  document.getElementById('secrets-save').addEventListener('click', function(){
    var updates={};
    document.querySelectorAll('#secrets-list input[data-secret]').forEach(function(i){
      if(!i.disabled && i.value) updates[i.dataset.secret]=i.value;
    });
    if(!Object.keys(updates).length){ document.getElementById('secrets-status').textContent='Rien à enregistrer.'; return; }
    api('/api/secrets', {updates:updates}).then(function(r){
      document.getElementById('secrets-status').textContent = r.ok?'✓ clés enregistrées en local':'⚠ '+(r.error||'erreur');
      load();
    });
  });
})();
"""

# Live auto-refresh: polls /api/state and reflects the hunt in real time.
# SQLite is the realtime bus — the loop writes matches as it finds them, the
# server reads the same DB, so the page only needs to know WHEN to refresh.
_LIVE_JS = r"""
(function(){
  var TOKEN = window.__JB_TOKEN__ || null;
  if(!TOKEN) return;                      // live mode needs the local server
  var banner = document.getElementById('live-banner');
  var phaseEl = document.getElementById('live-phase');
  var countsEl = document.getElementById('live-counts');
  var toast = document.getElementById('new-jobs-toast');
  var toastLabel = document.getElementById('new-jobs-label');
  var runTop = document.getElementById('run-now-top');
  var baseline = null;                    // last_added known at page load
  var wasRunning = false;

  // Surface a "Lancer une chasse" button in the header (server mode only).
  if(runTop){
    runTop.hidden = false;
    runTop.addEventListener('click', function(){
      runTop.disabled = true;
      fetch('/api/run-now', {method:'POST', headers:{'Content-Type':'application/json','X-JB-Token':TOKEN}, body:'{}'})
        .catch(function(){}).finally(function(){ setTimeout(function(){ runTop.disabled=false; }, 1500); });
    });
  }

  function fmtProgress(p){
    if(!p) return 'Chasse en cours…';
    return p.phase || 'Chasse en cours…';
  }
  function showToast(n){
    toastLabel.textContent = '✦ ' + n + ' nouvelle' + (n>1?'s':'') + ' offre' + (n>1?'s':'') + ' — depuis ton ouverture';
    toast.hidden = false;
  }

  function poll(){
    fetch('/api/state', {headers:{'X-JB-Token':TOKEN}})
      .then(function(r){ return r.json(); })
      .then(function(s){
        if(baseline === null) baseline = s.last_added || 0;

        // live banner while a hunt runs
        if(s.running){
          banner.hidden = false;
          phaseEl.textContent = fmtProgress(s.progress);
          if(s.progress){
            countsEl.textContent = s.progress.matches + ' matches · ' +
              s.progress.urls_seen + ' offres vues';
          }
          wasRunning = true;
        } else {
          banner.hidden = true;
          // a hunt just finished → nudge a refresh if new cards landed
          if(wasRunning){
            wasRunning = false;
            if((s.last_added||0) > baseline) showToast(Math.max(1, s.jobs_count - 0));
          }
        }
        // new jobs appeared (even outside a run we started) → offer to show them
        if((s.last_added||0) > baseline && toast.hidden && !s.running){
          showToast(1);
        }
      })
      .catch(function(){ /* server gone; stop quietly */ });
  }

  document.getElementById('new-jobs-reload').addEventListener('click', function(){
    location.reload();
  });

  poll();
  setInterval(poll, 2500);
})();
"""


def render(store: "Store", cfg: "JobHuntConfig", out_path: Path) -> Path:
    jobs = store.get_jobs(min_score=cfg.scoring.threshold)
    qs = store.quality_stats()
    strong = len([j for j in jobs if j.get("score", 0) >= 75])
    avg = sum(j.get("score", 0) for j in jobs) // max(len(jobs), 1)

    cards = "".join(_card(j) for j in jobs) or '<div class="empty">Aucune offre au-dessus du seuil. Essaie d\'élargir le lieu ou de baisser le score minimum dans ta config, puis relance <code>mja run</code>.</div>'
    kanban = _kanban(store)

    # "Why-not": collapsed list of discarded offers, so the user sees nothing
    # important was missed and can tune their criteria.
    rejected = store.get_rejections(limit=50)
    whynot = ""
    if rejected:
        _reason_label = {
            "below_threshold": "Score trop bas", "location": "Lieu hors zone",
            "stack": "Stack hors cible", "role": "Rôle/séniorité", "expired": "Expirée",
            "empty": "Page vide", "not_a_job": "Pas une offre",
        }
        summary = store.rejection_summary()
        chips = " · ".join(f"{_reason_label.get(k, k)} ({v})" for k, v in summary.items())
        rows = "".join(
            f'<tr><td>{html.escape(_reason_label.get(r["reason"], r["reason"]))}</td>'
            f'<td>{r.get("score",0)}</td>'
            f'<td>{html.escape((r.get("detail") or ""))}</td>'
            f'<td><a class="view" href="{html.escape(r["url"])}" target="_blank" rel="noopener">lien</a></td></tr>'
            for r in rejected
        )
        whynot = f"""<details class="card" style="margin-top:1.5rem">
          <summary style="cursor:pointer"><div class="head"><h3>Pourquoi pas ? — {len(rejected)} offre(s) écartée(s)</h3>
          <div class="sub">{html.escape(chips)}</div>
          <div class="sub" style="margin-top:.3rem">Ton agent a bien regardé ces offres mais les a écartées. Si tu vois des écarts injustes, élargis tes critères.</div></div></summary>
          <table style="width:100%;border-collapse:collapse;margin-top:.8rem;font-size:.85rem">
          <thead><tr style="text-align:left;color:var(--jb-text-muted)"><th>Motif</th><th>Score</th><th>Détail</th><th></th></tr></thead>
          <tbody>{rows}</tbody></table>
        </details>"""

    doc = f"""<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MyJobAgent — Dashboard</title><style>{_CSS}</style></head>
<body><div class="wrap">
<header><div class="beam"></div><h1>MyJobAgent</h1>
<button id="run-now-top" class="settings-btn" hidden aria-label="Lancer une chasse">▶ Lancer une chasse</button>
<button id="open-settings" class="settings-btn" hidden aria-label="Réglages">⚙ Réglages</button>
<span class="privacy">🔒 Tes données restent sur ta machine</span></header>
<div id="live-banner" class="live-banner" hidden role="status" aria-live="polite">
  <span class="live-dot"></span>
  <span id="live-phase">Chasse en cours…</span>
  <span id="live-counts" class="live-counts"></span>
</div>
<div id="new-jobs-toast" class="new-toast" hidden role="status" aria-live="polite">
  <span id="new-jobs-label">✦ De nouvelles offres sont arrivées</span>
  <button id="new-jobs-reload" class="toast-btn">Afficher</button>
</div>
<p class="meta">{len(jobs)} offre(s) · score moyen {avg} · {strong} fort(s) match(s){f" · {qs['flagged']} signalée(s)" if qs['flagged'] else ""}</p>
<div class="bar">
  <div class="kpi"><b>{len(jobs)}</b><span>offres ≥ {cfg.scoring.threshold}</span></div>
  <div class="kpi"><b>{strong}</b><span>≥ 75 (forts)</span></div>
  <div class="kpi"><b>{avg}</b><span>score moyen</span></div>
</div>
{kanban}
{cards}
{whynot}
</div>
{_SETTINGS_HTML}
<script>{_SETTINGS_JS}</script>
<script>{_LIVE_JS}</script>
</body></html>"""

    out_path.write_text(doc, encoding="utf-8")
    return out_path
