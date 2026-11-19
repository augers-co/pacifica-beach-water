// Explore page: loads the record, starts the drawing code, and ties the board's controls to it.
(() => {
  const $ = id => document.getElementById(id);
  const body = document.body, INK = "#171717";
  const BOARD = window.BOARD;
  const MQ = matchMedia("(max-width:700px) and (orientation:portrait)");
  const reduce = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
  let B = null, phone = false, curQ = "";

  // ---------- Follow the water (the board's own figures) ----------
  const tone = p => p < 25 ? ["#2b78b8", "#ffffff"] : p < 75 ? ["#f2c14e", INK] : p < 88 ? ["#ee7d2b", INK] : ["#d43a24", "#ffffff"];
  function water(dry){
    const rows = BOARD.STOPS.map(s => { const v = dry ? s.dry : s.all, p = dry ? s.overDry : s.overAll, t = tone(p);
      return {s, v, p, bg:t[0], fg:t[1], w:Math.max(2, Math.round(v / 430 * 100)) + "%"}; });
    $("w-markers").innerHTML = rows.map(r => `<div class="marker" style="left:${r.s.mx};top:${r.s.my}"><span style="background:${r.bg};color:${r.fg}">${r.s.n}</span></div>`).join("");
    $("w-stops").innerHTML = rows.map(r => `<div class="stop"><div class="stoprow"><span class="stopnum" style="background:${r.bg};color:${r.fg}">${r.s.n}</span>
      <span class="stopname"><b>${r.s.name}</b><span>${r.s.who}</span></span><span class="stopval">${r.v}</span>
      <span class="stopfail" style="background:${r.bg};color:${r.fg}">${r.p}% fail</span></div>
      <div class="stopbar"><div style="width:${r.w};background:${r.bg}"></div><div class="lim" aria-hidden="true"></div></div></div>`).join("");
    $("w-note").textContent = dry ? BOARD.NOTE_DRY : BOARD.NOTE_ALL;
    $("w-dry").setAttribute("aria-pressed", String(dry)); $("w-all").setAttribute("aria-pressed", String(!dry));
  }
  $("w-dry").onclick = () => water(true); $("w-all").onclick = () => water(false);
  water(true);

  // ---------- Track record ----------
  const LVL = {very_high:["#d43a24","#ffffff"], high:["#ee7d2b",INK], usual:["#f0b46a",INK], lower:["#8fb0c2",INK], lower_than_usual:["#8fb0c2",INK]};
  const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const esc2 = v => String(v ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  fetch("../../api/v1/track_record.json").then(r => r.ok ? r.json() : null).then(tr => {
    const tests = tr && Array.isArray(tr.tests) ? tr.tests : [];
    if(!tests.length) return;            // nothing scored yet: the board's sample rows stay, labelled as samples
    $("tr-samplehead").hidden = true; $("tr-region").setAttribute("aria-label", "Track record, scrolls sideways");
    $("tr-body").innerHTML = tests.map(t => {
      const d = String(t.date || t.test_date || ""), dd = d.length >= 10 ? `${MON[+d.slice(5,7)-1]} ${+d.slice(8,10)}` : esc2(d);
      const key = String(t.level_key || t.level || "").toLowerCase().replace(/ /g, "_"), c = LVL[key] || ["#f5f6f7", INK];
      const ch = t.chance != null ? Math.round(t.chance * 100) + "% chance of failing" : "";
      const v = t.result ?? t.value ?? t.county_result, over = v != null && v > 104;
      return `<tr><td class="d">${dd}</td><td><div class="fc"><span class="lvl" style="background:${c[0]};color:${c[1]}">${esc2(t.level || "")}</span><span class="fine">${ch}</span></div></td>
        <td class="r"><div class="res">${v == null ? "–" : Number(v).toLocaleString("en-US")}</div>${v == null ? "" : `<div class="${over ? "over" : "under"}">${over ? "Over 104" : "Under 104"}</div>`}</td></tr>`; }).join("");
  }).catch(() => {});

  // ---------- question chips ----------
  const Q = BOARD.Q;
  Q.forEach(q => { const b = document.createElement("button"); b.type = "button"; b.className = "chip"; b.textContent = q.q; b.dataset.q = q.id;
    b.setAttribute("aria-pressed", "false"); b.onclick = () => pick(q.id);
    document.querySelector(`.qchips[data-g="${q.g}"]`).appendChild(b); });
  $("q-reset").onclick = () => pick("");
  // which part of the record each question sets up: [guided view, row under the bacteria, explorer question]
  const PRESET = {rain:["storm","rain","Does recent rain matter?"], storms:["storm","rain","Do bigger storms matter?"], warm:["warm","wtemp","Does warm water matter?"],
    tide:["cleanera","rain","Does the tide matter?"], hour:[null,"rain","Does time of day matter?"], chronic:["chronic","rain","Does recent rain matter?"],
    flow:["storm","flow","Does creek flow matter?"], ground:["carry","grnd","Does wet ground matter?"], winter:["carry","wy",null],
    where:["chronic","rain","Does the location matter?"], spills:["spills","sp",null], beach:["cleanera","rain",null]};
  const gm = vals => vals.length ? 10 ** (vals.reduce((a, v) => a + Math.log10(Math.max(v, 1)), 0) / vals.length) : null;
  function liveBars(id){
    const p = PRESET[id]; if(!B || !p) return null;
    if(p[2]){ const xb = [...$("xf").querySelectorAll("button")].find(x => x.textContent === p[2]); if(!xb) return null;
      xb.click(); const S = B.LASTS; return S ? S.map(s => ({v:s.gm, n:s.n})) : null; }
    if(id === "winter"){ const rows = B.summerRows();
      return ["dry","norm","wet"].map(c => { const v = rows.filter(r => r.cls === c).flatMap(r => r.vals); return {v:gm(v), n:v.length}; }); }
    if(id === "beach"){ const bt = B.DATA.beach.filter(x => x.v != null);
      return [[d => d < "2014"], [d => d >= "2014" && d < "2022"], [d => d >= "2022"]].map(([f]) => { const a = bt.filter(x => f(x.d));
        return {v:a.length ? a.filter(x => x.v > 104).length / a.length * 100 : null, n:a.length}; }); }
    return null;
  }
  function renderNums(q){
    const box = $("q-nums-body");
    if(!q.bars.length){ box.innerHTML = `<div class="muted" style="font-size:15px">${q.read}</div>`; return; }
    const live = liveBars(q.id);
    const bars = q.bars.map((b, i) => { const L = live && live[i]; return {label:b[0], v:L && L.v != null ? Math.round(L.v) : b[1], n:L ? L.n : b[2]}; });
    const mx = Math.max(...bars.map(b => b.v), 1);
    box.innerHTML = `<div class="numtitle">${q.title}</div>` + bars.map(b => `<div class="bar"><div class="barhead"><span>${b.label} <span class="n">n=${b.n}</span></span><span class="v">${b.v.toLocaleString("en-US")}</span></div>
      <div class="bartrack"><div class="barfill" style="width:${Math.round(b.v / mx * 100)}%"></div></div></div>`).join("") + `<div style="font-size:15px">${q.read}</div>`;
  }
  function pick(id){
    curQ = id; const q = Q.find(x => x.id === id) || null;
    document.querySelectorAll(".qrow .chip").forEach(b => b.setAttribute("aria-pressed", String((b.dataset.q || "") === id)));
    $("q-heading").textContent = q ? q.q : "The whole record";
    $("q-whole").hidden = !!q; $("q-look").hidden = !q; $("q-nums").hidden = !q || !B;
    if(q) $("q-look-text").textContent = q.look;
    if(!B) return;
    if(q) renderNums(q);
    const p = q ? PRESET[id] : null;
    B.PHONE.lane = p ? p[1] : "rain";
    B.setLayers(q ? (window.LAYERS.Q[id] || window.LAYERS.DEF) : window.LAYERS.DEF);   // the board's layer set for this question
    if(!q) setSpan("all");
    syncAll();
  }

  // ---------- loading ----------
  const getJSON = u => fetch(u).then(r => { if(!r.ok) throw new Error(u); return r.json(); });
  Promise.all([getJSON("data.json"), getJSON("basemap.json")]).then(([DATA, BM]) => {
    window.PBEngine(DATA, BM);
    B = window.__pbw;
    $("ex-loading").hidden = true; $("ex-main").hidden = false;
    start();
  }).catch(() => { $("ex-loading").textContent = "The record could not be loaded."; });

  function start(){
    const sc = $("scroller"), gut = $("gutter"), slider = $("geoslider"), detail = $("detail");
    $("mapbtn").click();                       // shows the map and lets it follow the chart
    // map key into the Layers panel (kept in step with the legend the drawing code writes)
    const mirrorKey = () => { $("ex-mapkey").innerHTML = $("geoleg").innerHTML; };
    new MutationObserver(mirrorKey).observe($("geoleg"), {childList:true, subtree:true, characterData:true}); mirrorKey();
    // play: a copy of the map's play button sits under the chart on phones
    const play = $("geoplay"), play2 = $("ex-play");
    play2.onclick = () => play.click();
    new MutationObserver(() => { play2.textContent = play.textContent; }).observe(play, {childList:true, characterData:true, subtree:true});
    // play / pause keep one size: each button is as wide as its wider label
    const LABELS = ["▶ Play the record", "⏸ Pause"];
    const fixPlay = () => [play, play2].forEach(btn => { const c = btn.cloneNode(true); c.removeAttribute("id");
      c.style.cssText = "position:absolute;visibility:hidden;width:auto;min-width:0;display:inline-flex"; btn.parentNode.appendChild(c);
      const w = Math.max(...LABELS.map(t => { c.textContent = t; return c.getBoundingClientRect().width; })); c.remove();
      if(w > 0) btn.style.width = Math.ceil(w + 2) + "px"; });
    fixPlay(); if(document.fonts && document.fonts.ready) document.fonts.ready.then(fixPlay);

    // companion-row chips, named as on the desktop board's "Weather and water" layers
    const SW = {rain:"--rain", flow:"--flow", grnd:"--ground", wy:"--wy", air:"--temp", wtemp:"--wtemp", sp:"--std"};
    const WEATHER = window.LAYERS.GROUPS.find(g => g[0] === "Weather and water")[1], WNAME = Object.fromEntries(WEATHER.map(w => [w[0], w[1]]));
    const clearQ = () => { if(curQ){ curQ = ""; document.querySelectorAll(".qrow .chip").forEach(x => x.setAttribute("aria-pressed", String(!x.dataset.q))); } };
    WEATHER.forEach(([id, name]) => { const b = document.createElement("button"); b.type = "button"; b.dataset.lane = id;
      b.innerHTML = `<span class="swd" style="background:var(${SW[id]})"></span>${name}`;
      b.onclick = () => { B.PHONE.lane = id; const L = B.layers(); if(!L.includes(id)) B.setLayers(L.concat(id)); else B.rerender(B.centerDate()); syncAll(); };
      $("ex-lanes").appendChild(b); });

    // map show/hide, remembered for the visit
    const mt = $("ex-maptoggle");
    let mapHidden = false; try { mapHidden = sessionStorage.getItem("explore-map-hidden") === "1"; } catch(e) {}
    function setMapHidden(h, keep){
      mapHidden = h; body.classList.toggle("ex-maphidden", h);
      mt.setAttribute("aria-expanded", String(!h)); mt.setAttribute("aria-label", h ? "Show map" : "Hide map");
      try { sessionStorage.setItem("explore-map-hidden", h ? "1" : "0"); } catch(e) {}
      if(keep) return;
      const sp = [...$("ex-spans").querySelectorAll("button")].find(b => b.getAttribute("aria-pressed") === "true");
      if(sp) setSpan(sp.dataset.span); else B.rerender(B.centerDate());   // the chart's width changed
      syncAll();
    }
    mt.onclick = () => setMapHidden(!mapHidden);
    setMapHidden(mapHidden, true);

    // time span: Month = the Storm view's daily scale; Year and All years fit the chart's width
    const fitW = () => Math.max(sc.clientWidth - 24, 100);
    const SPAN = {month:() => 7, year:() => fitW() / 366, all:() => (fitW() - 20) / B.N};
    window.setSpan = k => B.setPPD(SPAN[k](), B.centerDate());
    $("ex-spans").addEventListener("click", e => { const b = e.target.closest("button[data-span]"); if(!b) return; setSpan(b.dataset.span); syncAll(); });

    // one shared date: the day record's date, shown once between map and chart; the marker line stays on it
    const markXH = () => { const l = $("xh"); if(!l || B.curI == null) return; const x = 20 + B.curI * B.PPD; l.setAttribute("x1", x); l.setAttribute("x2", x); };
    new MutationObserver(() => { const f = $("dtext").querySelector("b"); if(f) $("ex-date").textContent = f.textContent; })
      .observe($("dtext"), {childList:true, subtree:true});
    const step = d => { const v = Math.min(Math.max(+slider.value + d, 0), +slider.max); slider.value = v; slider.dispatchEvent(new Event("input", {bubbles:true})); };
    $("ex-prev").onclick = () => step(-1); $("ex-next").onclick = () => step(1);

    // tap a dot or a day (phones): snap to the nearest sample within reach, open the day record
    sc.addEventListener("click", e => {
      if(!phone) return; e.stopPropagation();
      const r = sc.getBoundingClientRect(), x = e.clientX - r.left + sc.scrollLeft, y = e.clientY - r.top, P = B.PPD;
      let i = Math.round((x - 20) / P), bd = 24;
      for(const dp of B.DOTPOS){ const dd = Math.hypot(20 + dp.i * P - x, dp.y - y); if(dd < bd){ bd = dd; i = dp.i; } }
      if(i < 0 || i >= B.N) return;
      B.setPinned(true); B.show(i); markXH(); openDay();
    }, true);
    function openDay(){
      const fr = (mapHidden ? document.querySelector(".daterow") : $("ex-mapframe")).getBoundingClientRect();
      const room = innerHeight - Math.max(fr.bottom, 0) - 8;          // keep the map in view above the panel when there is room
      detail.style.setProperty("--sheetH", Math.round(room >= 260 ? room : innerHeight * 0.56) + "px");
      if(!detail.classList.contains("open")){ detail.classList.add("open"); $("ex-dclose").focus({preventScroll:true}); }
    }
    $("ex-dclose").onclick = () => { detail.classList.remove("open"); B.setPinned(false); };

    // Layers panel
    // Layers: a drop-down section in the page flow, closed by default
    const tip = $("ex-tip"), lrow = $("ex-layers"), lpanel = $("ex-layerpanel");
    lrow.onclick = () => { const open = lpanel.hidden; lpanel.hidden = !open; lrow.setAttribute("aria-expanded", String(open)); if(!open) tip.hidden = true; };
    document.addEventListener("keydown", e => { if(e.key === "Escape" && phone){ detail.classList.remove("open"); B.setPinned(false); } });
    // the desktop board's layer switches: Places, Weather and water, Highlights
    $("ex-lhint").textContent = window.LAYERS.HINT;
    $("ex-layergroups").innerHTML = window.LAYERS.GROUPS.map(([g, items]) => `<div class="lgroup"><div class="kicker">${g}</div>` +
      items.map(([id, label, ic]) => `<button type="button" class="lswitch" data-l="${id}" aria-pressed="false">
        <svg aria-hidden="true" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="${window.LAYERS.ICON[ic]}"></path></svg>
        <span class="llabel">${label}</span><span class="lsw" aria-hidden="true"><span></span></span></button>`).join("") + `</div>`).join("");
    const ENGBTN = id => id === "avg" ? '#spanel button[data-s="AVG"]' : `#spanel button[data-s="${id}"], #panel button[data-t="${id}"], #npanel button[data-n="${id}"]`;
    $("ex-layergroups").addEventListener("click", e => { const b = e.target.closest("button[data-l]"); if(!b) return;
      const id = b.dataset.l, L = B.layers(), isW = id in WNAME, turnOn = !L.includes(id);
      if(isW && turnOn) B.PHONE.lane = id;
      B.setLayers(turnOn ? L.concat(id) : L.filter(x => x !== id));
      if(isW && !turnOn && B.PHONE.lane === id){ const rest = WEATHER.map(w => w[0]).filter(w => B.layers().includes(w)); B.PHONE.lane = rest[0] || null; B.rerender(B.centerDate()); }
      // the drawing code's own explanation for this layer, at the top of the panel
      const eb = document.querySelector(ENGBTN(id)); if(eb) eb.dispatchEvent(new MouseEvent("mouseenter"));
      const cm = $("chipmap"), cap = cm && cm.style.display === "block" && cm.querySelector(".cap"), tc = $("tipcard");
      // shown under the switch, titled with the board's name for the layer (the drawing code's own title is the old site's)
      let txt = "";
      if(cap) txt = cap.innerHTML.replace(/^<b>[^<]*<\/b>\s*—\s*/, "");
      else if(tc && tc.style.display === "block"){ const t = tc.querySelector(".tt"); txt = t && t.nextElementSibling ? t.nextElementSibling.innerHTML : ""; }
      if(txt){ tip.innerHTML = `<div class="tt">${b.querySelector(".llabel").textContent}</div><div>${txt}</div>`; b.after(tip); tip.hidden = false; }
      else tip.hidden = true;
      if(cm) cm.style.display = "none"; if(tc) tc.style.display = "none";
      clearQ(); syncAll(); });

    // lane titles above each lane (phones: the narrow chart keeps only the scale, inside the plot)
    let raf = 0;
    function after(){ raf = 0; markXH();
      const labs = $("ex-lanelabs");
      if(phone){ const subs = [...gut.querySelectorAll(".sub")];
        labs.innerHTML = Object.entries(B.LAY).map(([id, tr], k) => `<div class="ex-lanelab" style="top:${tr.y0 - 22}px"><b>${WNAME[id] || tr.name}</b> ·${subs[k] ? subs[k].textContent : ""}</div>`).join(""); }
      else labs.innerHTML = "";
      syncAll(); }
    const queue = () => { if(!raf) raf = requestAnimationFrame(after); };
    new MutationObserver(queue).observe(sc, {childList:true});
    new MutationObserver(queue).observe(gut, {childList:true});

    window.syncAll = () => {
      $("ex-lanes").querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.lane === B.PHONE.lane)));
      $("ex-spans").querySelectorAll("button").forEach(b => { const v = SPAN[b.dataset.span](); b.setAttribute("aria-pressed", String(Math.abs(B.PPD - v) <= v * 0.03)); });
      body.classList.toggle("ex-tiny", phone && B.PPD < 0.2);
      const L = B.layers();
      $("ex-layergroups").querySelectorAll("button[data-l]").forEach(b => b.setAttribute("aria-pressed", String(L.includes(b.dataset.l))));
      $("ex-oncount").textContent = "· " + L.length + " on";
    };

    function setMode(){
      const was = phone; phone = MQ.matches; B.PHONE.on = phone; body.classList.toggle("ex-phone", phone);
      document.documentElement.style.setProperty("--mapH", Math.round(Math.max(140, Math.min(200, innerHeight * 0.24))) + "px");
      if(!phone){ detail.classList.remove("open"); }
      if(phone && !was) setSpan("year"); else if(!phone && B.PPD < 0.5) B.setPPD(1.3, B.centerDate()); else B.rerender(B.centerDate());
      syncAll();
    }
    if(MQ.addEventListener) MQ.addEventListener("change", setMode); else MQ.addListener(setMode);
    addEventListener("resize", () => document.documentElement.style.setProperty("--mapH", Math.round(Math.max(140, Math.min(200, innerHeight * 0.24))) + "px"));
    setMode();
    // start on the latest sampled week, shared by map and chart
    slider.dispatchEvent(new Event("input", {bubbles:true}));
    if(curQ) pick(curQ);
  }
})();
