// Reports active time and clicks to /api/v1/track for logged-in users.
// Time only counts while the tab is visible and the person did something in the last minute.
(function () {
  var URL = '/api/v1/track';
  var page = location.pathname;
  var lastAction = Date.now(), pending = 0, clicks = 0, MAX_CLICKS = 80;

  function send(body) {
    var data = JSON.stringify(body);
    try {
      if (navigator.sendBeacon && navigator.sendBeacon(URL, new Blob([data], {type: 'application/json'}))) return;
    } catch (e) {}
    try { fetch(URL, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: data, keepalive: true}); } catch (e) {}
  }
  function flush() {
    if (pending > 0) { send({t: 'time', page: page, secs: pending}); pending = 0; }
  }

  ['mousemove', 'keydown', 'scroll', 'touchstart', 'click'].forEach(function (ev) {
    window.addEventListener(ev, function () { lastAction = Date.now(); }, {passive: true, capture: true});
  });
  setInterval(function () {
    if (document.visibilityState === 'visible' && Date.now() - lastAction < 60000) pending += 5;
    if (pending >= 60) flush();
  }, 5000);
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') flush(); });
  window.addEventListener('pagehide', flush);

  document.addEventListener('click', function (e) {
    if (clicks >= MAX_CLICKS || !e.target.closest) return;
    var el = e.target.closest('a, button, input, label, select, [role=button], .btn');
    if (!el) return;
    var label = (el.getAttribute('aria-label') || el.innerText || el.value || el.id || el.name || el.tagName || '')
      .replace(/\s+/g, ' ').trim().slice(0, 80);
    if (el.type === 'password' || el.type === 'text' || el.type === 'email' || el.type === 'search') label = 'typing in ' + (el.name || el.id || el.type);
    if (!label) return;
    clicks++;
    send({t: 'click', page: page, label: label});
  }, true);
})();
