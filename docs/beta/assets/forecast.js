/* Forecast page: reads the JSON files and fills the page. No libraries. */
(function () {
  "use strict";
  var BASE = document.documentElement.getAttribute("data-api") || "api/v1/";
  var DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var DOWLONG = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var MONLONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  var MM_PER_IN = 25.4;
  var LIMIT = 104; // the ocean standard the board draws as the limit line

  // Colours, meter length and label colour for each level key (from the board).
  var LV = {
    lower:     { word: "Lower than usual", label: "#3f6478", fill: "#8fb0c2", rgb: "143, 176, 194", n: 1, ink: "#171717" },
    usual:     { word: "Usual",            label: "#9a6a1f", fill: "#f0b46a", rgb: "240, 180, 106", n: 2, ink: "#171717" },
    high:      { word: "High",             label: "#c2500a", fill: "#ee7d2b", rgb: "238, 125, 43",  n: 3, ink: "#171717" },
    very_high: { word: "Very high",        label: "#c4281a", fill: "#d43a24", rgb: "212, 58, 36",   n: 4, ink: "#ffffff" }
  };
  // Where each results series was taken and by whom, in the board's words.
  var SERIES = {
    lm5_enterococcus: { place: "Ocean at the mouth", by: "County" },
    surfrider_creek_mouth_enterococcus: { place: "Creek mouth", by: "Surfrider" }
  };
  var BEYOND = "This much rain is beyond what the forecast was built on. Only one of the tests behind it had more than 75 mm of rain in three days, so treat this level as a rough guide.";

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function show(id, on) { var e = $(id); if (e) e.hidden = !on; }
  function isNum(v) { return typeof v === "number" && isFinite(v); }
  function getJSON(name) {
    return fetch(BASE + name, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(name + " " + r.status);
      return r.json();
    });
  }

  // ---- dates (all Pacific calendar dates, handled as plain y-m-d) ----
  function ymd(s) { var p = String(s).split("-"); return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2], 12)); }
  function addDays(s, n) { var d = ymd(s); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  function daysBetween(a, b) { return Math.round((ymd(b) - ymd(a)) / 864e5); }
  function dow(s) { return DOW[ymd(s).getUTCDay()]; }
  function dnum(s) { return ymd(s).getUTCDate(); }
  function mon(s) { return MON[ymd(s).getUTCMonth()]; }
  function longDate(s) { return dow(s) + " " + mon(s) + " " + dnum(s); }
  function shortDate(s) { return mon(s) + " " + dnum(s); }
  function pacificToday() {
    return new Date().toLocaleDateString("en-CA", { timeZone: "America/Los_Angeles" });
  }
  // "mid-November": days 1-10 early, 11-20 mid, the rest late
  function partOfMonth(s) {
    var n = dnum(s), part = n <= 10 ? "early" : (n <= 20 ? "mid" : "late");
    return part + "-" + MONLONG[ymd(s).getUTCMonth()];
  }
  // "Friday" within the past six days, otherwise "Oct 21"
  function sinceWord(s, today) {
    var k = daysBetween(s, today);
    if (k === 0) return "today";
    return k > 0 && k <= 6 ? DOWLONG[ymd(s).getUTCDay()] : shortDate(s);
  }
  function agoText(s, today) {
    var k = daysBetween(s, today);
    return k <= 0 ? "today" : k + (k === 1 ? " day ago" : " days ago");
  }
  function commas(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function inches(mm) { return mm / MM_PER_IN; }
  function in1(mm) { return inches(mm).toFixed(1); }

  // ---- the board's phrasing of odds ("almost 9 in 10", "1 in 3", ...) ----
  var SIMPLE = [[1 / 8, "1 in 8"], [1 / 3, "1 in 3"], [1 / 2, "1 in 2"], [3 / 4, "3 in 4"]];
  function odds(p) {
    if (p < 0.1) return { text: "fewer than 1 in 10", almost: false };
    for (var i = 0; i < SIMPLE.length; i++) {
      if (Math.abs(p - SIMPLE[i][0]) <= 0.035) return { text: SIMPLE[i][1], almost: false };
    }
    var t = Math.round(p * 10);
    return { text: t + " in 10", almost: t / 10 - p >= 0.025 };
  }

  // ---- badges: how an input moves today's chance (forecast.json days[].push) ----
  var UP_ICON = '<svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#c4281a" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"></path></svg>';
  function setBadge(id, p) {
    var b = $(id); if (!b) return;
    if (!p || p.direction === "none" || (p.direction !== "up" && p.direction !== "down")) { b.hidden = true; return; }
    var little = p.size === "a_little";
    b.className = "badge " + p.direction;
    b.innerHTML = p.direction === "up" ? UP_ICON : "";
    b.appendChild(document.createTextNode(p.direction === "up"
      ? (little ? "Pushing risk up a little" : "Pushing risk up")
      : (little ? "Easing risk a little" : "Easing risk")));
    b.hidden = false;
  }

  // ---- small SVG helpers (numbers only, so building strings is safe) ----
  // A frame is {n: slots, t: today's slot}. With conditions.json: 13 days before
  // today, today and 6 after (20 slots). Without it: 2 days before (9 slots).
  function svgOpen(label) {
    return '<svg role="img" aria-label="' + label + '" viewBox="0 0 400 44" preserveAspectRatio="none" class="spark">';
  }
  function shade(fr) {
    var w = 400 / fr.n, x = (fr.t + 1) * w;
    return '<rect x="' + x.toFixed(1) + '" y="0" width="' + (400 - x).toFixed(1) + '" height="44" fill="#f5f6f7"></rect>';
  }
  function todayLine(fr) {
    var lx = (fr.t + 0.5) * 400 / fr.n;
    return '<line x1="' + lx.toFixed(1) + '" x2="' + lx.toFixed(1) + '" y1="0" y2="44" stroke="#171717" stroke-width="1" stroke-dasharray="2 3" vector-effect="non-scaling-stroke"></line>';
  }
  function rainChart(fr, series) {
    var w = 400 / fr.n, bw = w * 0.7, max = 0, i, body = "";
    for (i = 0; i < series.length; i++) if (series[i].mm != null && series[i].mm > max) max = series[i].mm;
    for (i = 0; i < series.length; i++) {
      var r = series[i]; if (r.mm == null) continue;
      var dry = inches(r.mm) < 0.05, h = dry || max === 0 ? 1.5 : Math.max(2, (r.mm / max) * 40);
      var col = dry ? "#d5d9dc" : (r.measured ? "#2b8fd6" : "#a9d0ee");
      body += '<rect x="' + (i * w + (w - bw) / 2).toFixed(1) + '" y="' + (44 - h).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + h.toFixed(1) + '" fill="' + col + '"></rect>';
    }
    return svgOpen("Daily rain, measured and forecast") + shade(fr) + body + todayLine(fr) + "</svg>";
  }
  // Solid up to today, dashed after; optional fill (darker to date, lighter ahead).
  function lineChart(fr, vals, stroke, fillArea, label) {
    var w = 400 / fr.n, ok = vals.filter(isNum);
    if (ok.length < 2) return "";
    var min = fillArea ? 0 : Math.min.apply(null, ok), max = Math.max.apply(null, ok), past = [], ahead = [], i;
    for (i = 0; i < vals.length; i++) {
      if (!isNum(vals[i])) continue;
      var y = max === min ? 22 : 44 - 5 - ((vals[i] - min) / (max - min)) * 34;
      var pt = [(i + 0.5) * w, y];
      if (i <= fr.t) past.push(pt);
      if (i >= fr.t) ahead.push(pt);
    }
    function d(pts) { return pts.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }); }
    function area(pts, col) {
      if (pts.length < 2) return "";
      return '<path d="M' + d(pts).join(" L") + " L" + pts[pts.length - 1][0].toFixed(1) + ",44 L" + pts[0][0].toFixed(1) + ',44 Z" fill="' + col + '"></path>';
    }
    function line(pts, dash) {
      if (pts.length < 2) return "";
      return '<polyline points="' + d(pts).join(" ") + '" fill="none" stroke="' + stroke + '" stroke-width="2"' + (dash ? ' stroke-dasharray="4 4"' : "") + ' vector-effect="non-scaling-stroke"></polyline>';
    }
    var out = svgOpen(label) + shade(fr);
    if (fillArea) out += area(past, "#cfe0ea") + area(ahead, "#e6eff4");
    return out + line(past, false) + line(ahead, true) + todayLine(fr) + "</svg>";
  }
  // Test results inside the window as bars on a log scale, with the limit line.
  function testsChart(fr, first, tests) {
    var w = 400 / fr.n, top = 1000, body = "", i;
    tests.forEach(function (t) { if (t.v > top) top = t.v; });
    function y(v) { return 44 - Math.max(1.5, Math.log(Math.max(v, 1)) / Math.log(top) * 40); }
    for (i = 0; i < tests.length; i++) {
      var k = daysBetween(first, tests[i].date), t = tests[i];
      if (k < 0 || k > fr.t) continue;
      var yy = y(t.v);
      body += '<rect x="' + (k * w + w * 0.2).toFixed(1) + '" y="' + yy.toFixed(1) + '" width="' + (w * 0.6).toFixed(1) + '" height="' + (44 - yy).toFixed(1) + '" fill="' + (t.over ? "#d43a24" : "#9aa0a6") + '"></rect>';
    }
    if (!body) return "";
    var ly = y(LIMIT).toFixed(1);
    return svgOpen("County and Surfrider test results in this window, with the limit of 104") + shade(fr) +
      '<line x1="0" x2="400" y1="' + ly + '" y2="' + ly + '" stroke="#d43a24" stroke-width="1" stroke-dasharray="3 3" vector-effect="non-scaling-stroke"></line>' +
      body + todayLine(fr) + "</svg>";
  }
  function axis(box, fr, firstDate, lastDate) {
    box.textContent = "";
    var a = el("span", null, shortDate(firstDate)); a.style.left = "0";
    var t = el("span", "today", "Today"); t.style.left = ((fr.t + 0.5) / fr.n * 100).toFixed(1) + "%";
    var b = el("span", null, shortDate(lastDate)); b.style.right = "0";
    box.appendChild(a); box.appendChild(t); box.appendChild(b);
  }

  // ---- states ----
  function noForecast(text) {
    show("loading", false); show("fc-today", false); show("fc-rest", false); show("week", false); show("behind", false);
    $("nf-text").textContent = text;
    show("noforecast", true);
  }

  // ---- shared lookups ----
  function findSeries(res, key) {
    var a = (res && res.results) || [];
    for (var i = 0; i < a.length; i++) if (a[i].series === key) return a[i];
    return null;
  }
  // the newest of the county ocean result and the Surfrider creek-mouth result
  function newestResult(res) {
    var best = null;
    Object.keys(SERIES).forEach(function (k) {
      var r = findSeries(res, k);
      if (r && r.date && isNum(r.result_mpn) && (!best || r.date > best.date)) best = r;
    });
    return best;
  }
  // conditions.json is used only when it was made today
  function usableConditions(c, today) {
    return c && c.as_of === today && Array.isArray(c.days) && c.days.length === 20 && c.days[13] && c.days[13].date === today ? c : null;
  }
  function groundWord(days) {
    var a = days[0].inputs && days[0].inputs.ground_idx, b = days[1] && days[1].inputs && days[1].inputs.ground_idx;
    if (!isNum(a) || !isNum(b)) return "";
    if (Math.abs(b - a) < 1) return "Steady";
    return b > a ? "Rising" : "Falling";
  }
  function groundNormalText(d) {
    var g = d.ground_normal;
    if (!g || ["above", "below", "near"].indexOf(g.compared_to_normal) < 0) return "";
    return g.compared_to_normal + " normal for " + partOfMonth(d.date);
  }

  // ---- sections ----
  function renderToday(f, res, cond, today) {
    var d = f.days[0], lv = LV[d.level_key];
    if (!lv) throw new Error("unknown level");
    var card = $("tcard");
    card.style.borderColor = lv.fill;
    card.style.boxShadow = "0 0 0 4px rgba(" + lv.rgb + ", 0.16), 0 10px 32px rgba(" + lv.rgb + ", 0.28)";
    var l = $("t-level"); l.textContent = lv.word; l.style.color = lv.label;
    var m = $("t-meter"); m.textContent = "";
    for (var i = 0; i < 4; i++) { var seg = el("i"); if (i < lv.n) seg.style.background = lv.fill; m.appendChild(seg); }
    show("t-beyond", d.beyond_experience === true);
    $("t-date").textContent = "Today · " + longDate(d.date) + " · forecasted bacteria risk";
    var big = $("t-big"), o = odds(d.fail_share);
    big.textContent = "";
    if (o.almost) big.appendChild(el("span", "almost", "almost "));
    big.appendChild(document.createTextNode(o.text));
    $("t-far").textContent = odds(d.far_over_share).text + " come back far over levels deemed safe for human exposure.";

    // latest measured level: shown as a reference only while a test is under a week old
    var r = newestResult(res);
    if (r && daysBetween(r.date, today) < 7) {
      var sr = SERIES[r.series];
      $("ref-num").textContent = commas(r.result_mpn);
      $("ref-times").textContent = r.result_mpn > LIMIT ? Math.round(r.result_mpn / LIMIT) + " times the limit of " + LIMIT : "";
      $("ref-sub").textContent = sr.place + ", " + sr.by + ", " + longDate(r.date) + ": " +
        agoText(r.date, today) + ". Shown as a reference while a test is under a week old.";
      show("t-ref", true);
    }

    // the board's four small readings
    var stats = $("t-stats"); stats.textContent = "";
    var w = d.weather || {}, inp = d.inputs || {};
    if (isNum(inp.rain3_mm)) {
      stats.appendChild(stat("Rain, last 3 days", in1(inp.rain3_mm), " in",
        (isNum(w.rain_day0_mm) && inp.rain3_mm > 0 && w.rain_day0_mm / inp.rain3_mm > 0.5) ? "most of it today" : ""));
    }
    if (cond && cond.rain_30d && isNum(cond.rain_30d.total_mm)) {
      var st = (cond.rain_30d.storms || []).filter(function (s) { return s && s.start; });
      var sub = st.length ? st.length + (st.length === 1 ? " storm since " : " storms since ") + sinceWord(st[0].start, today) : "";
      stats.appendChild(stat("Rain, last 30 days", in1(cond.rain_30d.total_mm), " in", sub));
    }
    var gtxt = groundWord(f.days);
    if (gtxt) stats.appendChild(stat("Ground wetness", gtxt, "", groundNormalText(d)));
    var lm = findSeries(res, "lm5_enterococcus");
    if (lm && Array.isArray(lm.recent) && lm.recent.length) {
      var fails = lm.recent.filter(function (t) { return t.compared_to_standard === "over"; }).length;
      stats.appendChild(stat("County tests", fails + " of " + lm.recent.length, " failed",
        "latest is " + shortDate(lm.recent[lm.recent.length - 1].date)));
    }
    stats.hidden = !stats.children.length;

    var cut = (f.carried ? "Issued yesterday, " : "Issued ") + longDate(f.issue_date);
    var thru = measuredThrough(f.days[0]);
    if (thru) cut += " · Data through " + longDate(thru);
    if (f.carried) cut += " · Today's forecast is not out yet";
    $("t-issued").textContent = cut;
  }
  function stat(label, val, unit, sub) {
    var s = el("div", "stat");
    s.appendChild(el("div", "cap", label));
    var v = el("div", "statval"), sp = el("span", null, val);
    if (unit) sp.appendChild(el("small", null, unit));
    v.appendChild(sp); s.appendChild(v);
    if (sub) s.appendChild(el("div", "cap", sub));
    return s;
  }
  // the latest day whose rain was measured rather than forecast
  function measuredThrough(d) {
    var w = d.weather; if (!w) return "";
    for (var k = 0; k <= 2; k++) if (w["rain_day" + k + "_src"] && w["rain_day" + k + "_src"] !== "forecast") return addDays(d.date, -k);
    return "";
  }

  function renderWeek(f) {
    var days = $("wk-days"), risk = $("wk-risk"), rain = $("wk-rain"), i, d;
    days.textContent = risk.textContent = rain.textContent = "";
    var maxmm = 0;
    for (i = 0; i < f.days.length; i++) { var wv = f.days[i].weather; if (wv && wv.rain_day0_mm > maxmm) maxmm = wv.rain_day0_mm; }
    for (i = 0; i < f.days.length; i++) {
      d = f.days[i];
      var c = el("div", "wkday" + (i === 0 ? " now" : "")); c.appendChild(el("div", null, dow(d.date))); c.appendChild(el("b", null, String(dnum(d.date)))); days.appendChild(c);

      var lv = LV[d.level_key] || LV.usual, cell = el("div", "rk");
      var words = lv.word.toUpperCase().split(" ");
      words.forEach(function (wd, k) { if (k) cell.appendChild(document.createElement("br")); cell.appendChild(document.createTextNode(wd)); });
      if (d.lead_days <= 3) { cell.style.background = lv.fill; cell.style.color = lv.ink; }
      else { cell.className += " out"; cell.style.borderColor = lv.fill; }
      cell.setAttribute("title", d.beyond_experience === true ? lv.word + ". " + BEYOND : lv.word);
      risk.appendChild(cell);

      var rc = el("div", "rainc"), mm = d.weather ? d.weather.rain_day0_mm : null, v = el("div", "rainv");
      if (isNum(mm)) {
        if (inches(mm) < 0.05) { var dry = el("span", null, "dry"); v.appendChild(dry); }
        else { v.appendChild(document.createTextNode(in1(mm))); v.appendChild(el("span", null, " in")); }
      }
      rc.appendChild(v);
      var bar = el("div", "rainbar"), b = el("div");
      var dryd = !isNum(mm) || inches(mm) < 0.05;
      b.style.height = (dryd ? 2 : Math.max(4, Math.round(mm / (maxmm || 1) * 44))) + "px";
      b.style.background = dryd ? "#d5d9dc" : (mm >= maxmm * 0.5 ? "#2b8fd6" : "#8fc3e8");
      if (dryd) b.style.borderRadius = "0";
      if (isNum(mm)) bar.appendChild(b);
      rc.appendChild(bar); rain.appendChild(rc);
    }
  }

  function renderBehind(f, cond, res, today) {
    var d0 = f.days[0], w0 = d0.weather || {}, i;
    var fr = cond ? { n: 20, t: 13 } : { n: 9, t: 2 };
    var first = addDays(d0.date, -fr.t), last = addDays(d0.date, 6);
    function blank() { var a = []; for (var k = 0; k < fr.n; k++) a.push(null); return a; }

    // rain: conditions.json when it is today's, else the two logged days before today
    var series = [];
    if (cond) {
      cond.days.forEach(function (c) { series.push({ mm: isNum(c.rain_mm) ? c.rain_mm : null, measured: c.rain_src !== "forecast" }); });
    } else {
      series.push({ mm: isNum(w0.rain_day2_mm) ? w0.rain_day2_mm : null, measured: w0.rain_day2_src !== "forecast" });
      series.push({ mm: isNum(w0.rain_day1_mm) ? w0.rain_day1_mm : null, measured: w0.rain_day1_src !== "forecast" });
      for (i = 0; i < f.days.length; i++) {
        var w = f.days[i].weather || {};
        series.push({ mm: isNum(w.rain_day0_mm) ? w.rain_day0_mm : null, measured: w.rain_day0_src && w.rain_day0_src !== "forecast" });
      }
    }
    var rain3 = d0.inputs && d0.inputs.rain3_mm;
    if (isNum(rain3)) {
      $("d-rain-num").textContent = in1(rain3) + " in";
      setBadge("d-rain-badge", d0.push && d0.push.rain3);
      $("d-rain-chart").innerHTML = rainChart(fr, series);
    } else show("d-rain", false);

    // ground: the rule's own values from today on, conditions.json before
    var gw = groundWord(f.days);
    if (gw) {
      $("d-ground-num").textContent = gw;
      $("d-ground-sub").textContent = groundNormalText(d0);
      setBadge("d-ground-badge", d0.push && d0.push.ground);
      var gv = blank();
      if (cond) for (i = 0; i < fr.t; i++) gv[i] = isNum(cond.days[i].ground_idx) ? cond.days[i].ground_idx : null;
      for (i = 0; i < f.days.length; i++) { var g = f.days[i].inputs && f.days[i].inputs.ground_idx; gv[fr.t + i] = isNum(g) ? g : null; }
      $("d-ground-chart").innerHTML = lineChart(fr, gv, "#5b8fae", true, "Estimated ground wetness over the last two weeks and the week ahead");
    } else show("d-ground", false);
    axis($("axis-1"), fr, first, last);

    // storm runoff and water temperature come only from conditions.json
    var FLOW = { peak: "At its peak", rising: "Rising", falling: "Falling" };
    if (cond && FLOW[cond.flow_trend]) {
      $("d-runoff-num").textContent = FLOW[cond.flow_trend];
      $("d-runoff-chart").innerHTML = lineChart(fr, cond.days.map(function (c) { return isNum(c.flow_idx) ? c.flow_idx : null; }),
        "#5b8fae", true, "Estimated storm runoff in the creek over the last two weeks and the week ahead");
    } else show("d-runoff", false);

    var tv = cond ? cond.days.map(function (c) { return isNum(c.water_temp_est_c) ? c.water_temp_est_c * 9 / 5 + 32 : null; }) : [];
    if (cond && isNum(tv[fr.t])) {
      $("d-temp-num").textContent = Math.round(tv[fr.t]) + "°F";
      var tr = { rising: "rising", falling: "falling", steady: "steady" }[cond.water_temp_trend];
      $("d-temp-sub").textContent = "estimated" + (tr ? ", " + tr : "");
      $("d-temp-chart").innerHTML = lineChart(fr, tv, "#b07a12", false, "Estimated creek water temperature over the last two weeks and the week ahead");
    } else show("d-temp", false);

    // recent tests: the newest county or Surfrider result, and those inside the window
    var r = newestResult(res);
    if (r) {
      $("d-recent-num").textContent = commas(r.result_mpn);
      $("d-recent-sub").textContent = SERIES[r.series].place.toLowerCase() + ", " + agoText(r.date, today);
      var pts = [], lm = findSeries(res, "lm5_enterococcus"), sf = findSeries(res, "surfrider_creek_mouth_enterococcus");
      ((lm && lm.recent) || []).forEach(function (t) { if (isNum(t.result_mpn)) pts.push({ date: t.date, v: t.result_mpn, over: t.compared_to_standard === "over" }); });
      if (sf && isNum(sf.result_mpn)) pts.push({ date: sf.date, v: sf.result_mpn, over: sf.compared_to_standard === "over" });
      $("d-recent-chart").innerHTML = testsChart(fr, first, pts);
    } else show("d-recent", false);
    axis($("axis-2"), fr, first, last);
  }

  function resultRow(r) {
    var s = SERIES[r.series], row = el("div", "res"), left = el("div", "colx");
    left.appendChild(el("div", "fb7", s.place));
    left.appendChild(el("div", "t14m", s.by + " · " + longDate(r.date)));
    var right = el("div", "resright");
    right.appendChild(el("div", "resnum", commas(r.result_mpn)));
    var over = r.compared_to_standard === "over";
    right.appendChild(el("div", "pf " + (over ? "fail" : "pass"), over ? "Fail" : "Pass"));
    row.appendChild(left); row.appendChild(right);
    return row;
  }
  function renderResults(res) {
    var rows = $("res-rows"); rows.textContent = "";
    ["surfrider_creek_mouth_enterococcus", "lm5_enterococcus"].forEach(function (k) {
      var r = findSeries(res, k);
      if (!r || !isNum(r.result_mpn)) return;
      if (rows.children.length) rows.appendChild(el("div", "hr"));
      rows.appendChild(resultRow(r));
    });
    var lm = findSeries(res, "lm5_enterococcus");
    if (lm && Array.isArray(lm.recent) && lm.recent.length) {
      var grid = $("last8-grid"); grid.textContent = "";
      lm.recent.forEach(function (t) {
        var c = el("div", t.compared_to_standard === "over" ? "over" : "", commas(t.result_mpn));
        c.setAttribute("title", longDate(t.date));
        grid.appendChild(c);
      });
      grid.style.gridTemplateColumns = "repeat(" + lm.recent.length + ", minmax(0, 1fr))";
      $("last8-cap").textContent = shortDate(lm.recent[0].date) + " to " + shortDate(lm.recent[lm.recent.length - 1].date) +
        ", the latest in the state's public database. Red failed the health standard of " + LIMIT + ".";
      show("last8", true);
    }
  }

  function renderLevels(lv) {
    var box = $("lv-bars"); box.textContent = "";
    var total = 0;
    (lv.levels || []).forEach(function (l) {
      var k = LV[l.key]; if (!k) return;
      total += l.tests || 0;
      var pct = Math.round(l.fail_share * 100 - 1e-9); // a share of exactly .5 rounds down, as on the board
      var item = el("div", "col4"), head = el("div", "barhead");
      head.appendChild(el("span", null, k.word)); head.appendChild(el("span", "fb8", pct + "%"));
      var track = el("div", "track"), fill = el("div", "fill");
      fill.style.width = pct + "%"; fill.style.background = k.fill;
      track.appendChild(fill); item.appendChild(head); item.appendChild(track); box.appendChild(item);
    });
    if (total) { $("lv-cap").textContent = total + " county tests in the ocean at the creek mouth, 2022 to 2026."; show("lv-cap", true); }
  }

  function renderTrack(tr) {
    var tests = (tr.tests || []).filter(function (t) { return t.forecasts && t.forecasts.lead0; });
    if (!tests.length) return; // nothing scored yet: the board's empty state is the card as it stands
    var right = 0;
    tests.forEach(function (t) { if ((t.forecasts.lead0.chance >= 0.5) === (t.compared_to_standard === "over")) right++; });
    $("tr-head").textContent = right + " of " + tests.length + " calls right";
    show("tr-head", true); show("tr-link", true);
    var sec = $("record"); sec.textContent = "";
    sec.appendChild(el("h2", null, "Every forecast, and what the test found"));
    var list = el("div", "col12");
    tests.forEach(function (t) {
      var row = el("div", "res"), left = el("div", "colx");
      left.appendChild(el("div", "fb7", longDate(t.date)));
      var lvn = LV[t.forecasts.lead0.level_key];
      left.appendChild(el("div", "t14m", lvn ? lvn.word : String(t.forecasts.lead0.level)));
      var rt = el("div", "resright"), over = t.compared_to_standard === "over";
      rt.appendChild(el("div", "resnum", commas(t.result_mpn)));
      rt.appendChild(el("div", "pf " + (over ? "fail" : "pass"), over ? "Fail" : "Pass"));
      row.appendChild(left); row.appendChild(rt); list.appendChild(row);
    });
    sec.appendChild(list); sec.hidden = false;
  }

  // survey figures, as on the Learn page: if the file fails, the figures in the HTML stay
  function renderSurvey(s) {
    function set(name, text) { var n = document.querySelectorAll('[data-sv="' + name + '"]'); for (var i = 0; i < n.length; i++) n[i].textContent = text; }
    if (isNum(s.responses)) set("responses", String(s.responses));
    if (isNum(s.headline_pct)) set("headline", Math.round(s.headline_pct) + "%");
    (s.symptoms || []).forEach(function (x) { if (x && isNum(x.pct)) set("sym-" + x.key, Math.round(x.pct) + "%"); });
    var links = s.links || {};
    Object.keys(links).forEach(function (k) {
      if (typeof links[k] !== "string" || !/^https:\/\//.test(links[k])) return;
      var a = document.querySelectorAll('[data-sv-link="' + k + '"]');
      for (var i = 0; i < a.length; i++) a[i].setAttribute("href", links[k]);
    });
  }

  // ---- go ----
  var settled = function (p) { return p.then(function (v) { return { v: v }; }, function () { return { err: 1 }; }); };
  getJSON("health_survey.json").then(function (s) { try { renderSurvey(s); } catch (e) { /* keep the page's figures */ } }, function () {});

  Promise.all(["forecast.json", "levels.json", "latest_results.json", "track_record.json", "conditions.json"].map(function (n) { return settled(getJSON(n)); })).then(function (a) {
    var f = a[0], lv = a[1], res = a[2], tr = a[3], co = a[4];
    var today = pacificToday();

    if (lv.err) { $("lv-fail").textContent = "The level figures could not be loaded."; show("lv-fail", true); }
    else { try { renderLevels(lv.v); } catch (e) { $("lv-fail").textContent = "The level figures could not be loaded."; show("lv-fail", true); } }

    if (res.err) { $("res-fail").textContent = "The test results could not be loaded."; show("res-fail", true); }
    else { try { renderResults(res.v); } catch (e) { $("res-fail").textContent = "The test results could not be loaded."; show("res-fail", true); } }

    if (tr.err) { $("tr-fail").textContent = "The track record could not be loaded."; show("tr-fail", true); }
    else { try { renderTrack(tr.v); } catch (e) { $("tr-fail").textContent = "The track record could not be loaded."; show("tr-fail", true); } }

    if (f.err || !f.v || !Array.isArray(f.v.days) || !f.v.days.length) { noForecast("The forecast could not be loaded."); return; }
    var fv = f.v;
    // Until today's forecast is issued (the daily job can start hours late),
    // show yesterday's forecast for today, labelled as such. Anything older: none.
    if (fv.issue_date !== today && daysBetween(fv.issue_date, today) === 1 && fv.days.length > 1 && fv.days[1].date === today) {
      fv = Object.assign({}, fv, { days: fv.days.slice(1), carried: true });
    } else if (fv.stale === true || fv.issue_date !== today) { noForecast("No current forecast is available."); return; }
    var cond = co.err ? null : usableConditions(co.v, today);
    var resv = res.err ? null : res.v;
    try {
      renderToday(fv, resv, cond, today);
      renderWeek(fv);
      renderBehind(fv, cond, resv, today);
    } catch (e) { noForecast("The forecast could not be loaded."); return; }
    show("loading", false); show("fc-today", true); show("fc-rest", true); show("week", true); show("behind", true);
  });
})();
