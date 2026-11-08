(function () {
  "use strict";
  var MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  var $ = function (id) { return document.getElementById(id); };
  function get(url) { return fetch(url, { cache: "no-cache" }).then(function (r) { if (!r.ok) throw new Error(url); return r.json(); }); }
  function fmt(iso) { var d = new Date(iso); return isNaN(d) ? "" : d.getDate() + " " + MONTHS[d.getMonth()] + " " + d.getFullYear(); }

  /* ---------- next event ---------- */
  get("data/event.json").then(function (ev) {
    var d = ev.date ? new Date(ev.date + "T00:00:00") : null;
    var today = new Date(); today.setHours(0, 0, 0, 0);
    var days = d ? Math.round((d - today) / 864e5) : -1;
    if (d && days >= 0) {
      $("ev-date").textContent = d.getDate() + " " + MONTHS[d.getMonth()] + ".";
      $("ev-tape").hidden = false;
      $("ev-count").textContent = days === 0 ? "Today" : days === 1 ? "Tomorrow" : "In " + days + " days";
      $("ev-title").textContent = ev.title || "";
      var meta = [ev.time, ev.place].filter(Boolean).join(" · ");
      $("ev-meta").textContent = meta || ev.note || "";
    } else {
      $("ev-date").textContent = "Soon.";
      $("ev-title").textContent = "The next event is not announced yet.";
      $("ev-meta").textContent = "It will be on Instagram first.";
    }
    if (ev.signup_url) { $("ev-btn").href = ev.signup_url; }
    if (ev.signup_label) { $("ev-btn").textContent = ev.signup_label; }
  }).catch(function () {});

  /* ---------- feed ---------- */
  var posts = [], cur = null, idx = 0;
  var grid = $("grid"), dlg = $("dlg"), stage = $("stage");

  function el(tag, attrs) { var e = document.createElement(tag); for (var k in attrs) e.setAttribute(k, attrs[k]); return e; }

  function render() {
    grid.textContent = "";
    $("empty").hidden = posts.length > 0;
    posts.forEach(function (p, i) {
      var m = p.media[0] || {};
      var b = el("button", { "class": "tile", type: "button", "aria-label": (p.caption || "Post").slice(0, 80) });
      var img = el("img", { src: m.poster || m.src, alt: "", loading: "lazy", decoding: "async" });
      b.appendChild(img);
      if (p.type === "CAROUSEL" || p.type === "VIDEO") {
        var t = el("span", { "class": "tag" });
        t.textContent = p.type === "CAROUSEL" ? "1/" + p.media.length : "Video";
        b.appendChild(t);
      }
      if (p.caption) { var c = el("span", { "class": "cap" }); c.textContent = p.caption.slice(0, 110); b.appendChild(c); }
      b.addEventListener("click", function () { open(i); });
      grid.appendChild(b);
    });
  }

  function show() {
    var m = cur.media[idx];
    stage.textContent = "";
    var node;
    if (m.type === "VIDEO") {
      node = el("video", { src: m.src, poster: m.poster || "", controls: "", playsinline: "", loop: "", autoplay: "", muted: "" });
      node.muted = true;
    } else {
      node = el("img", { src: m.src, alt: "" });
    }
    stage.appendChild(node);
    $("d-count").textContent = (idx + 1) + " / " + cur.media.length;
    $("d-nav").hidden = cur.media.length < 2;
  }
  function open(i) {
    cur = posts[i]; idx = 0;
    $("d-date").textContent = fmt(cur.timestamp);
    $("d-cap").textContent = cur.caption || "";
    $("d-link").href = cur.permalink || "https://www.instagram.com/notanother.run/";
    show();
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
  }
  function shut() { stage.textContent = ""; if (dlg.close) dlg.close(); else dlg.removeAttribute("open"); }
  $("close").addEventListener("click", shut);
  dlg.addEventListener("click", function (e) { if (e.target === dlg) shut(); });
  dlg.addEventListener("close", function () { stage.textContent = ""; });
  $("next").addEventListener("click", function () { idx = (idx + 1) % cur.media.length; show(); });
  $("prev").addEventListener("click", function () { idx = (idx - 1 + cur.media.length) % cur.media.length; show(); });
  document.addEventListener("keydown", function (e) {
    if (!dlg.open || !cur) return;
    if (e.key === "ArrowRight") $("next").click();
    if (e.key === "ArrowLeft") $("prev").click();
  });

  get("data/posts.json").then(function (d) {
    posts = (d.posts || []).slice().sort(function (a, b) { return a.timestamp < b.timestamp ? 1 : -1; });
    if (d.source === "instagram" && d.updated) $("feed-updated").textContent = "Synced " + fmt(d.updated);
    render();
  }).catch(function () { $("empty").hidden = false; });
})();
