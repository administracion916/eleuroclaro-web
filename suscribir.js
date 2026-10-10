// Alta en la newsletter desde cualquier página: lleva a la página de Substack con el correo ya puesto.
// Origen del alta (para saber en Substack qué trae suscriptores): primero los utm_* con los que llegó la visita
// (por ejemplo, un anuncio con ?utm_source=fb-promo), si no, los del formulario (data-fuente, data-medio, data-campana).
(function () {
  "use strict";
  var BASE = "https://eleuroclaro.substack.com/subscribe";
  var q = new URLSearchParams(location.search);
  function limpio(v) { v = String(v || "").toLowerCase(); return /^[a-z0-9-]{2,30}$/.test(v) ? v : ""; }
  Array.prototype.forEach.call(document.querySelectorAll("form.signup[data-campana]"), function (form) {
    var msg = form.querySelector(".msg");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var email = form.email.value.trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { msg.textContent = "Revisa el correo: falta algo (por ejemplo, la @)."; return; }
      if (!form.consent.checked) { msg.textContent = "Marca la casilla de privacidad para apuntarte."; return; }
      var p = new URLSearchParams();
      p.set("email", email);
      p.set("utm_source", limpio(q.get("utm_source")) || limpio(q.get("src")) || limpio(form.getAttribute("data-fuente")) || "web");
      p.set("utm_medium", limpio(q.get("utm_medium")) || limpio(form.getAttribute("data-medio")) || "formulario");
      p.set("utm_campaign", limpio(q.get("utm_campaign")) || limpio(form.getAttribute("data-campana")) || "web");
      window.location.href = BASE + "?" + p.toString();
    });
  });
})();
