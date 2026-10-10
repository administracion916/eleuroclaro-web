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

  // Barra de la newsletter abajo: sale al pasar un tercio de la página, se esconde cuando se ve el formulario
  // y, si se cierra, no vuelve en 14 días. No sale en páginas con <body data-sin-barra>.
  var nl = document.getElementById("newsletter");
  if (!nl || document.body.hasAttribute("data-sin-barra") || !("IntersectionObserver" in window)) return;
  var CLAVE = "nl-barra-cerrada", DIAS14 = 14 * 864e5;
  try { if (Date.now() - Number(localStorage.getItem(CLAVE) || 0) < DIAS14) return; } catch (e) { /* sin almacenamiento: se muestra */ }
  var barra = document.createElement("aside");
  barra.className = "nl-barra";
  barra.setAttribute("aria-label", "Newsletter");
  barra.hidden = true;
  barra.innerHTML = '<p><strong>Cada domingo, lo que cambia en tu bolsillo.</strong> <span>Gratis, en 3 minutos.</span></p>' +
    '<a class="btn btn-sol" href="#newsletter">Apuntarme</a>' +
    '<button type="button" class="nl-cerrar" aria-label="Cerrar">×</button>';
  document.body.appendChild(barra);
  var visto = false, pasado = false;
  function pintar() { barra.hidden = !(pasado && !visto); }
  new IntersectionObserver(function (e) { visto = e[0].isIntersecting; pintar(); }, { threshold: .25 })
    .observe(nl.querySelector("form") || nl);
  window.addEventListener("scroll", function () {
    if (!pasado && window.scrollY > (document.documentElement.scrollHeight - window.innerHeight) / 3) { pasado = true; pintar(); }
  }, { passive: true });
  barra.querySelector("a").addEventListener("click", function () {
    var correo = nl.querySelector("input[type=email]");
    if (correo) setTimeout(function () { correo.focus({ preventScroll: true }); }, 400);
  });
  barra.querySelector(".nl-cerrar").addEventListener("click", function () {
    barra.remove();
    try { localStorage.setItem(CLAVE, String(Date.now())); } catch (e) { /* nada */ }
  });
})();
