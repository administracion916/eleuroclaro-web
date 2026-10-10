// Alta en la newsletter desde cualquier página: lleva a la página de Substack con el correo ya puesto.
// Cada formulario dice de qué página viene (data-campana) para saber en Substack qué páginas traen altas.
(function () {
  "use strict";
  var BASE = "https://eleuroclaro.substack.com/subscribe?utm_source=web&utm_medium=formulario&utm_campaign=";
  Array.prototype.forEach.call(document.querySelectorAll("form.signup[data-campana]"), function (form) {
    var msg = form.querySelector(".msg");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var email = form.email.value.trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { msg.textContent = "Revisa el correo: falta algo (por ejemplo, la @)."; return; }
      if (!form.consent.checked) { msg.textContent = "Marca la casilla de privacidad para apuntarte."; return; }
      window.location.href = BASE + encodeURIComponent(form.getAttribute("data-campana")) + "&email=" + encodeURIComponent(email);
    });
  });
})();
