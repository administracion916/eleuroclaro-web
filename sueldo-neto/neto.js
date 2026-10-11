// Calculadora de sueldo neto 2026 (territorio común): Seguridad Social del trabajador + retención de IRPF
// con el algoritmo oficial de la AEAT (versión del 10-9-2026). Fuentes:
// - AEAT, «Algoritmo de cálculo del tipo de retención 2026»: reducción por rendimientos del trabajo, 2.000 € de gastos,
//   mínimos personal y por descendientes, escala de retención, límites de exclusión (tabla 1) y límite del 43 %.
// - Orden PJC/297/2026 (BOE 31-3-2026): base máxima 5.101,20 €/mes. Tipos del trabajador: contingencias comunes 4,70 %,
//   desempleo 1,55 % (indefinido) o 1,60 % (temporal), formación profesional 0,10 %, MEI 0,15 %.
// No incluye la cotización de solidaridad (solo por encima de la base máxima) ni casos especiales (discapacidad,
// movilidad, pensiones compensatorias, mayores de 64). País Vasco y Navarra tienen su propio IRPF.
(function () {
  "use strict";
  var BASE_MAX_ANUAL = 5101.20 * 12;
  var ESCALA = [[12450, .19], [20200, .24], [35200, .30], [60000, .37], [300000, .45], [Infinity, .47]];
  // Límites excluyentes de retención: [situación][n.º de hijos 0, 1, 2 o más]
  var LIMITES = { 1: [null, 17644, 18694], 2: [17197, 18130, 19262], 3: [15876, 16342, 16867] };
  var MIN_HIJO = [2400, 2700, 4000, 4500];

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
  function r2(n) { return Math.round(n * 100) / 100; }
  function euros(n) { return Math.round(n).toLocaleString("es-ES", { useGrouping: "always" }) + " €"; }
  function pct(n) { return n.toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " %"; }
  function escala(base) {
    var cuota = 0, desde = 0;
    for (var i = 0; i < ESCALA.length && base > desde; i++) {
      cuota += (Math.min(base, ESCALA[i][0]) - desde) * ESCALA[i][1];
      desde = ESCALA[i][0];
    }
    return cuota;
  }

  function calcular(bruto, temporal, situacion, hijos, menores3, entero) {
    var ss = r2(Math.min(bruto, BASE_MAX_ANUAL) * (.047 + (temporal ? .016 : .0155) + .001 + .0015));
    var rnt = Math.max(0, bruto - ss);
    var red = rnt <= 14852 ? 7302 : rnt <= 17673.52 ? 7302 - 1.75 * (rnt - 14852) : rnt < 19747.5 ? 2364.34 - 1.14 * (rnt - 17673.52) : 0;
    red = r2(Math.max(0, red));
    var gastos = Math.min(2000, rnt);
    var base = Math.max(0, rnt - red - gastos);
    var factor = entero ? 1 : .5;
    var minimo = 5550;
    for (var i = 0; i < hijos; i++) minimo += MIN_HIJO[Math.min(i, 3)] * factor;
    minimo += 2800 * Math.min(menores3, hijos) * factor;
    var cuota = Math.max(0, escala(base) - escala(minimo));
    var lim = LIMITES[situacion][Math.min(hijos, 2)];
    var tipo = 0;
    if (!(lim !== null && bruto <= lim)) {
      if (lim !== null && bruto <= 35200) cuota = Math.min(cuota, (bruto - lim) * .43);
      tipo = r2(cuota / bruto * 100);
      if (temporal && tipo < 2) tipo = 2;
    }
    var irpf = r2(bruto * tipo / 100);
    return { ss: ss, tipo: tipo, irpf: irpf, neto: bruto - ss - irpf };
  }
  window.calcularNeto = calcular; // para comprobaciones

  if (!form) return;
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var bruto = num(form.bruto.value);
    if (bruto < 1000) { msg.textContent = "Pon tu sueldo bruto al año, por ejemplo 25.000."; form.bruto.focus(); return; }
    msg.textContent = "";
    var pagas = Number(form.pagas.value) || 14;
    var hijos = Number(form.hijos.value) || 0;
    var r = calcular(bruto, form.contrato.value === "temporal", form.conyuge.checked ? 2 : (hijos && form.solo.checked ? 1 : 3),
      hijos, Number(form.menores.value) || 0, form.solo.checked);
    document.getElementById("r-mes").textContent = euros(r.neto / pagas);
    document.getElementById("r-pagas").textContent = "netos al mes, en " + pagas + " pagas";
    document.getElementById("r-anual").textContent = euros(r.neto);
    document.getElementById("r-ss").textContent = euros(r.ss);
    document.getElementById("r-irpf").textContent = euros(r.irpf) + " (" + pct(r.tipo) + ")";
    document.getElementById("r-ejemplo").textContent = "De cada 100 € de sueldo te quedan " + Math.round(r.neto / bruto * 100) + " €.";
    res.hidden = false;
    res.focus();
    res.scrollIntoView({ behavior: "smooth", block: "start" });
  });
  var hijosSel = form.hijos;
  function verHijos() { document.getElementById("datos-hijos").hidden = hijosSel.value === "0"; }
  hijosSel.addEventListener("change", verHijos);
  verHijos();
})();
