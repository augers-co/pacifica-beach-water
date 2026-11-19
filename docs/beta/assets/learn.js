/* Learn page: fills the health-survey figures from health_survey.json.
   If the file cannot be loaded, the figures already in the HTML stay as they are. */
(function () {
  "use strict";
  var BASE = document.documentElement.getAttribute("data-api") || "../api/v1/";
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

  function set(name, text) {
    var n = document.querySelectorAll('[data-sv="' + name + '"]');
    for (var i = 0; i < n.length; i++) n[i].textContent = text;
  }
  function bar(name, pct) {
    var n = document.querySelectorAll('[data-sv-bar="' + name + '"]');
    for (var i = 0; i < n.length; i++) n[i].style.width = pct + "%";
  }
  function longDate(s) {
    var p = String(s).split("-");
    if (p.length !== 3 || !MONTHS[+p[1] - 1]) return null;
    return +p[2] + " " + MONTHS[+p[1] - 1] + " " + p[0];
  }
  function isNum(v) { return typeof v === "number" && isFinite(v); }
  function isUrl(v) { return typeof v === "string" && /^https:\/\//.test(v); }

  fetch(BASE + "health_survey.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error("status " + r.status); return r.json(); })
    .then(function (s) {
      if (isNum(s.responses)) set("responses", String(s.responses));
      var d = s.as_of && longDate(s.as_of); if (d) set("asof", d);
      if (isNum(s.headline_pct)) set("headline", Math.round(s.headline_pct) + "%");
      if (typeof s.headline_repeat === "string" && s.headline_repeat) set("repeat", s.headline_repeat);
      (s.symptoms || []).forEach(function (x) {
        if (!x || !isNum(x.pct)) return;
        set("sym-" + x.key, Math.round(x.pct) + "%"); bar("sym-" + x.key, x.pct);
      });
      var links = s.links || {};
      Object.keys(links).forEach(function (k) {
        if (!isUrl(links[k])) return;
        var a = document.querySelectorAll('[data-sv-link="' + k + '"]');
        for (var i = 0; i < a.length; i++) a[i].setAttribute("href", links[k]);
      });
    })
    .catch(function () { /* keep the figures written in the page */ });
})();
