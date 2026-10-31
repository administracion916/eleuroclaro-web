/* Cuenta atrás del reto de noviembre y marca del paso de cada domingo. */
(function () {
  "use strict";
  // Domingos a las 09:00 en Madrid (hora de invierno, UTC+1).
  var PASOS = ["2026-11-01T08:00:00Z", "2026-11-08T08:00:00Z", "2026-11-15T08:00:00Z", "2026-11-22T08:00:00Z"].map(function (s) { return new Date(s).getTime(); });
  var DIA = 86400000;
  var cuenta = document.getElementById("reto-cuenta");
  var items = document.querySelectorAll(".reto-pasos li");
  var ahora = Date.now();

  var hechos = PASOS.filter(function (t) { return t <= ahora; }).length;
  Array.prototype.forEach.call(items, function (li, i) {
    if (i < hechos) li.classList.add("rp-hecho");
    if (i === hechos) li.classList.add("rp-siguiente");
  });

  if (!cuenta) return;
  if (hechos === 0) {
    // Días de calendario en Madrid (UTC+1), no bloques de 24 horas.
    var dia = function (t) { return Math.floor((t + 3600000) / DIA); };
    var dias = dia(PASOS[0]) - dia(ahora);
    cuenta.textContent = dias <= 0 ? "Empieza hoy a las 9:00: apúntate y te llega el primer paso"
      : dias === 1 ? "Empieza mañana, domingo 1 de noviembre, a las 9:00"
      : "Empieza el domingo 1 de noviembre · faltan " + dias + " días";
  } else if (hechos < PASOS.length) {
    cuenta.textContent = "El reto ya ha empezado: apúntate y te llega el paso " + (hechos + 1) + " el domingo";
  } else {
    cuenta.textContent = "El reto ya ha terminado: apúntate y te avisamos del próximo";
  }
})();
