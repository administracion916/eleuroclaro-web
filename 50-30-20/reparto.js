// Calculadora de la regla 50/30/20: reparte el sueldo neto y avisa si la vivienda pasa del 35 % (orientativo).
(function () {
  "use strict";
  var form = document.getElementById("calc");
  var res = document.getElementById("resultado");
  var msg = document.getElementById("calc-msg");
  function num(v) {
    v = String(v || "").replace(/[€\s]/g, "");
    if (/,\d{1,2}$/.test(v)) v = v.replace(/\./g, "").replace(",", ".");
    else v = v.replace(/[.,]/g, "");
    var n = parseFloat(v);
    return isFinite(n) && n > 0 ? n : 0;
  }
  function euros(n) { return Math.round(n).toLocaleString("es-ES", { useGrouping: "always" }) + " €"; }
  function pon(id, t) { document.getElementById(id).textContent = t; }
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var neto = num(form.neto.value), casa = num(form.casa.value);
    if (neto < 100) { msg.textContent = "Pon tu sueldo neto al mes, por ejemplo 1.500."; form.neto.focus(); return; }
    msg.textContent = "";
    pon("r-fijos", euros(neto * .5));
    pon("r-caprichos", euros(neto * .3));
    pon("r-ahorro", euros(neto * .2));
    pon("r-ahorro2", euros(neto * .2));
    pon("r-colchon", euros(neto * .8 * 3) + " a " + euros(neto * .8 * 6));
    pon("r-anio", "En un año, " + euros(neto * .2 * 12) + " ahorrados sin contar intereses.");
    var aviso = document.getElementById("r-casa");
    if (casa) {
      var p = Math.round(casa / neto * 100);
      aviso.textContent = p > 35
        ? "Tu vivienda se lleva el " + p + " % del sueldo. Recorta primero de caprichos y aparta al menos " + euros(neto * .1) + " al mes (un 10 %)."
        : "Tu vivienda se lleva el " + p + " % del sueldo: cabe bien dentro de la mitad para lo necesario.";
      aviso.hidden = false;
    } else aviso.hidden = true;
    res.hidden = false;
    res.focus();
    res.scrollIntoView({ behavior: "smooth", block: "start" });
  });
})();
