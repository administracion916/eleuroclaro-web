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
