// Enlace de alta de la newsletter (página de suscripción de Substack).
// Mientras esté vacío, el formulario avisa de que la newsletter arranca pronto.
var NEWSLETTER_URL = "https://eleuroclaro.substack.com/subscribe";

(function () {
  var list = document.getElementById("video-list");
  var empty = document.getElementById("video-empty");
  var videos = (window.VIDEOS || []).slice(0, 6);
  if (videos.length) {
    empty.hidden = true;
    videos.forEach(function (v) {
      var a = document.createElement("a");
      a.className = "video";
      a.href = v.url;
      a.rel = "noopener";
      var thumb = document.createElement("div");
      thumb.className = "thumb";
      if (v.miniatura) thumb.style.backgroundImage = "url('" + v.miniatura + "')";
      var meta = document.createElement("span");
      meta.className = "meta";
      var d = new Date(v.fecha + "T12:00:00");
      meta.textContent = v.plataforma + " · " + d.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
      var h = document.createElement("h3");
      h.textContent = v.titulo;
      a.append(thumb, meta, h);
      list.append(a);
    });
  }

  var form = document.getElementById("signup");
  var msg = document.getElementById("signup-msg");
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var email = form.email.value.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { msg.textContent = "Revisa el correo: falta algo (por ejemplo, la @)."; return; }
    if (!form.consent.checked) { msg.textContent = "Marca la casilla de privacidad para apuntarte."; return; }
    if (!NEWSLETTER_URL) { msg.textContent = "La newsletter arranca en octubre. Vuelve en unos días para apuntarte."; return; }
    window.location.href = NEWSLETTER_URL + (NEWSLETTER_URL.indexOf("?") < 0 ? "?" : "&") + "email=" + encodeURIComponent(email);
  });
})();

// Ofertas con fecha de fin: se muestran solo hasta la fecha de data-hasta (hora de Madrid).
(function () {
  var ahora = Date.now();
  document.querySelectorAll("[data-hasta]").forEach(function (el) {
    var fin = Date.parse(el.getAttribute("data-hasta"));
    if (!isNaN(fin) && ahora <= fin) el.hidden = false;
  });
})();

// Titulares de prensa económica: los guarda cada hora una tarea de GitHub en prensa.json (misma web, sin llamadas a terceros).
(function () {
  var caja = document.getElementById("prensa");
  var lista = document.getElementById("prensa-list");
  if (!caja || !lista || !window.fetch) return;
  function hace(fecha) {
    var min = Math.round((Date.now() - Date.parse(fecha)) / 60000);
    if (isNaN(min)) return "";
    if (min < 60) return "hace " + Math.max(min, 1) + " min";
    var h = Math.round(min / 60);
    if (h < 24) return "hace " + h + " h";
    return h < 48 ? "ayer" : "hace " + Math.round(h / 24) + " días";
  }
  fetch("prensa.json", { cache: "no-cache" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      var items = (d && d.items) || [];
      items.filter(function (it) { return /^https:\/\//.test(it.u || "") && it.t; }).slice(0, 6).forEach(function (it) {
        var li = document.createElement("li");
        var meta = document.createElement("span");
        meta.className = "p-meta";
        meta.textContent = it.m + (it.f ? " · " + hace(it.f) : "");
        var a = document.createElement("a");
        a.href = it.u;
        a.rel = "noopener";
        a.textContent = it.t;
        li.append(meta, a);
        lista.append(li);
      });
      if (lista.children.length) caja.hidden = false;
    })
    .catch(function () {});
})();
