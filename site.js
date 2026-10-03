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
// Solo se enseñan los de las últimas 36 horas: si la tarea se para, el bloque desaparece en vez de quedarse viejo.
(function () {
  var caja = document.getElementById("prensa");
  var lista = document.getElementById("prensa-list");
  if (!caja || !lista || !window.fetch) return;
  var MAX = 36 * 3600e3;
  function dia(ms) { return new Date(ms).toLocaleDateString("es-ES", { timeZone: "Europe/Madrid" }); }
  function hace(ms) {
    var min = Math.max(1, Math.round((Date.now() - ms) / 60000));
    if (min < 60) return "hace " + min + " min";
    if (dia(ms) === dia(Date.now())) return "hace " + Math.round(min / 60) + " h";
    if (dia(ms) === dia(Date.now() - 864e5)) return "ayer";
    return "hace " + Math.round(min / 1440) + " días";
  }
  fetch("prensa.json", { cache: "no-cache" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      var items = (d && Array.isArray(d.items)) ? d.items : [];
      items.filter(function (it) {
        var ms = Date.parse(it && it.f);
        return it && typeof it.t === "string" && typeof it.m === "string" && typeof it.u === "string" &&
          /^https:\/\//.test(it.u) && !isNaN(ms) && Date.now() - ms < MAX;
      }).slice(0, 6).forEach(function (it) {
        var ms = Math.min(Date.parse(it.f), Date.now());
        var li = document.createElement("li");
        var meta = document.createElement("span");
        meta.className = "p-meta";
        meta.textContent = it.m + " · " + hace(ms);
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

// Próximas fechas: las que ya han pasado se ocultan solas (solo las que tienen día exacto).
(function () {
  document.querySelectorAll(".agenda li").forEach(function (li) {
    var t = li.querySelector("time");
    var v = t && t.getAttribute("datetime");
    if (!v || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return;
    if (Date.parse(v + "T23:59:59+01:00") < Date.now()) li.hidden = true;
  });
})();
