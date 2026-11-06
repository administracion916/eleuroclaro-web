// «Tu año en euros»: el resumen de 2026 de tu sueldo, tipo Wrapped. Todo se calcula en el navegador: no se envía nada.
//
// Fuentes y método (cálculo aproximado, se explica también en la página):
// - IRPF y Seguridad Social del trabajador: window.calcularNeto de /sueldo-neto/neto.js (algoritmo de retenciones
//   de la AEAT 2026 y Orden PJC/297/2026). Contrato indefinido, soltero/a o pareja con ingresos, hijos a medias.
// - Seguridad Social que paga la empresa (Orden PJC/297/2026): contingencias comunes 23,60 %, desempleo 5,50 %,
//   FOGASA 0,20 %, formación profesional 0,60 % y MEI 0,75 %, con la misma base máxima. Sin accidentes de trabajo
//   (depende del sector) ni cotización de solidaridad.
// - IVA: lo que gastas (sueldo neto − vivienda − ahorro) por el peso del IVA en el precio. El tipo de cada grupo
//   de gasto es una estimación con los tipos de la Ley 37/1992 (4, 10 y 21 %; seguros, enseñanza y sanidad
//   pública, exentos) y se pondera con el peso de cada grupo en el IPC de 2026 (INE, tabla 79185).
// - Subida de precios del año: media de las tasas anuales del IPC general de 2026 publicadas (INE), de
//   /datos/ipc-grupos.json (general_historia), que renueva cada mañana la tarea «Datos del INE».
(function () {
  "use strict";
  var ANO = 2026;
  var DIAS = 365;
  var WEB = "eleuroclaro.es/tu-ano";
  var BASE_MAX_ANUAL = 5101.20 * 12;
  var SS_EMPRESA = 0.2360 + 0.0550 + 0.0020 + 0.0060 + 0.0075;
  // [peso en el IPC 2026 (por mil), tipo de IVA medio estimado del grupo]
  var IVA_GRUPOS = [
    [174.1, 0.07], // comida y bebida: 4 % pan, leche, fruta, verdura, huevos, aceite de oliva; 10 % el resto
    [35.1, 0.21],  // alcohol y tabaco
    [35.8, 0.21],  // ropa y calzado
    [122.6, 0.19], // casa sin el alquiler o la hipoteca: luz y gas 21 %, agua 10 %
    [47.4, 0.20],  // muebles y hogar (el servicio doméstico, exento)
    [52.3, 0.05],  // salud: medicamentos 4 %, gafas 10 %, consultas exentas
    [154.7, 0.19], // transporte: gasolina, coche y taller 21 %, transporte público 10 %
    [37.5, 0.21],  // móvil, internet y aparatos
    [74.8, 0.16],  // ocio y cultura: 21 % la mayoría, 10 % cine y espectáculos, 4 % libros
    [16.1, 0],     // educación: exenta
    [170.3, 0.10], // bares, restaurantes y hoteles
    [22.7, 0],     // seguros y banca: exentos
    [56.7, 0.15]   // cuidado personal y otros: peluquería 21 %, residencias y guarderías 4-10 % o exentas
  ];
  var IVA_EN_PRECIO = (function () {
    var w = 0, s = 0;
    IVA_GRUPOS.forEach(function (g) { w += g[0]; s += g[0] * g[1] / (1 + g[1]); });
    return s / w; // ≈ 0,118: de cada 100 € que gastas, unos 12 son IVA
  })();
  window.IVA_EN_PRECIO = IVA_EN_PRECIO;

  var MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  var MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

  var form = document.getElementById("ano");
  var msg = document.getElementById("ano-msg");
  var ipc = null; // { media, desde, hasta, meses }

  function num(v) {
    v = String(v || "").replace(/[€%\s]/g, "");
    if (/^-?\d+\.\d{1,2}$/.test(v)) { /* «1452.37»: el punto es el decimal */ }
    else if (/,\d{1,2}$/.test(v)) v = v.replace(/\./g, "").replace(",", ".");
    else v = v.replace(/[.,]/g, "");
    var n = parseFloat(v);
    return isFinite(n) ? n : 0;
  }
  var fmt0 = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0, useGrouping: "always" });
  var fmt1 = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  function euros(n) { return fmt0.format(Math.round(n)) + " €"; }
  function pct(n) { return fmt1.format(n) + " %"; }
  function fecha(dia) { // dia 1 = 1 de enero
    var d = new Date(Date.UTC(ANO, 0, dia));
    return d.getUTCDate() + " de " + MESES[d.getUTCMonth()];
  }

  function calcular(d) {
    var r = window.calcularNeto(d.bruto, false, 3, d.hijos, 0, false, false);
    var neto = r.neto;
    var viviendaAno = d.vivienda * 12;
    var ahorroAno = d.ahorro * 12;
    var gasto = Math.max(0, neto - viviendaAno - ahorroAno);
    var iva = gasto * IVA_EN_PRECIO;
    var empresa = Math.min(d.bruto, BASE_MAX_ANUAL) * SS_EMPRESA;
    var p = ipc ? ipc.media / 100 : 0;
    // Lo que te ha costado de más este año lo mismo que comprabas el año pasado. La hipoteca no entra en el IPC.
    var gastoIpc = gasto + (d.tipo === "alquiler" ? viviendaAno : 0);
    var inflacion = gastoIpc * p / (1 + p);
    var poder = null;
    if (d.subida !== null) {
      var antes = d.bruto / (1 + d.subida / 100);
      poder = d.bruto - antes * (1 + p); // >0: ganas poder de compra
    }
    var fisco = r.irpf + r.ss + iva;
    var dH = Math.round(DIAS * fisco / d.bruto);
    var dV = Math.round(DIAS * (fisco + viviendaAno) / d.bruto) - dH;
    var dT = DIAS - dH - dV;
    return {
      bruto: d.bruto, neto: neto, irpf: r.irpf, tipo: r.tipo, ss: r.ss, iva: iva, empresa: empresa,
      coste: d.bruto + empresa, viviendaAno: viviendaAno, tipoVivienda: d.tipo, gasto: gasto,
      inflacion: inflacion, poder: poder, subida: d.subida, fisco: fisco,
      dH: dH, dV: dV, dT: dT, resto: d.bruto - fisco - viviendaAno
    };
  }
  window.calcularAno = function (d) { return calcular(d); }; // para comprobaciones

  function leer() {
    var bruto = num(form.bruto.value);
    if (bruto < 1000) return { error: "Pon tu sueldo bruto al año, por ejemplo 25.000.", campo: form.bruto };
    if (bruto > 2000000) return { error: "Revisa la cifra: pon tu sueldo bruto al año, por ejemplo 25.000.", campo: form.bruto };
    var tipo = form.tipo.value;
    var vivienda = tipo === "nada" ? 0 : Math.max(0, num(form.vivienda.value));
    if (tipo !== "nada" && !vivienda) return { error: "Pon cuánto pagas al mes de " + (tipo === "alquiler" ? "alquiler" : "hipoteca") + " (tu parte), o elige «Ninguna de las dos».", campo: form.vivienda };
    var ahorro = Math.max(0, num(form.ahorro.value));
    var s = String(form.subida.value || "").trim();
    var subida = s === "" ? null : num(s);
    if (subida !== null && (subida < -50 || subida > 100)) return { error: "La subida de sueldo va en %, por ejemplo 3.", campo: form.subida };
    return { bruto: bruto, tipo: tipo, vivienda: vivienda, ahorro: ahorro, subida: subida, hijos: Number(form.hijos.value) || 0 };
  }

  // ---------- Historias (diapositivas) ----------
  var historia = document.getElementById("historia");
  var pistas = document.getElementById("h-pistas");
  var lamina = document.getElementById("h-lamina");
  var slides = [], actual = 0, temporizador = null, pausa = false;
  var reducir = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var DURACION = 5200;

  function el(tag, cls, texto) { var e = document.createElement(tag); if (cls) e.className = cls; if (texto != null) e.textContent = texto; return e; }

  function construir(r) {
    var casa = r.tipoVivienda === "alquiler" ? "tu casero" : "la hipoteca";
    var s = [];
    s.push({ tema: "t-intro", eti: "Tu " + ANO + " en euros", big: euros(r.bruto), sub: "brutos ganaste en " + ANO + ".",
      txt: "Te llegaron al banco " + euros(r.neto) + ". Vamos a ver a dónde fue cada euro." });
    s.push({ tema: "t-fisco", eti: "Hacienda y Seguridad Social", big: r.dH + " días", sub: "trabajaste para Hacienda y la Seguridad Social.",
      txt: "Del 1 de enero al " + fecha(r.dH) + ". " + euros(r.irpf) + " de IRPF, " + euros(r.ss) + " de Seguridad Social y unos " + euros(r.iva) + " de IVA en lo que compras." });
    s.push({ tema: "t-empresa", eti: "Lo que no sale en tu nómina", big: euros(r.empresa), sub: "pagó además tu empresa a la Seguridad Social por ti.",
      txt: "Le costaste " + euros(r.coste) + ". De cada 100 € que cuestas, a ti te llegan " + Math.round(r.neto / r.coste * 100) + " €." });
    if (r.dV > 0) s.push({ tema: "t-casa", eti: r.tipoVivienda === "alquiler" ? "Tu alquiler" : "Tu hipoteca", big: r.dV + " días", sub: "trabajaste para " + casa + ".",
      txt: "Del " + fecha(r.dH + 1) + " al " + fecha(r.dH + r.dV) + ": " + euros(r.viviendaAno) + " en el año." +
        (r.tipoVivienda === "hipoteca" ? " Ojo: la parte de capital que devuelves sigue siendo tuya, es tu casa." : "") });
    if (ipc) {
      var t = "Lo mismo que comprabas en " + (ANO - 1) + " te costó eso de más: los precios han subido de media un " + pct(ipc.media) + " (INE, " + ipc.texto + ").";
      if (r.poder !== null) t += r.poder >= 0
        ? " Tu sueldo subió un " + pct(r.subida) + ": ganaste " + euros(r.poder) + " de poder de compra."
        : " Tu sueldo subió un " + pct(r.subida) + ": aun así, perdiste " + euros(-r.poder) + " de poder de compra.";
      s.push({ tema: "t-ipc", eti: "La subida de precios", big: euros(r.inflacion), sub: "te quitó la inflación en " + ANO + ".", txt: t });
    }
    s.push({ tema: "t-ti", eti: "Y por fin, para ti", big: r.dT + " días", sub: "quedaron para ti.",
      txt: "Desde el " + fecha(r.dH + r.dV + 1) + ": " + euros(r.resto) + " para comer, moverte, vivir y ahorrar." });
    s.push({ tema: "t-final", final: true });
    return s;
  }

  function barraAno(r, cont) {
    cont.innerHTML = "";
    [["b-fisco", r.dH, "Hacienda"], ["b-casa", r.dV, r.tipoVivienda === "alquiler" ? "Casero" : "Hipoteca"], ["b-ti", r.dT, "Para ti"]].forEach(function (b) {
      if (b[1] <= 0) return;
      var seg = el("span", "seg " + b[0]);
      seg.style.flexGrow = b[1];
      seg.title = b[2] + ": " + b[1] + " días";
      cont.appendChild(seg);
    });
  }

  function pintarSlide(i) {
    actual = i;
    var s = slides[i];
    lamina.className = "h-lamina " + s.tema;
    lamina.innerHTML = "";
    if (s.final) {
      lamina.appendChild(el("p", "h-eti", "Tu " + ANO + ", en un vistazo"));
      var bar = el("div", "h-barra"); barraAno(ultimo, bar); lamina.appendChild(bar);
      var meses = el("div", "h-meses"); MESES_CORTOS.forEach(function (m) { meses.appendChild(el("span", "", m)); }); lamina.appendChild(meses);
      var ul = el("ul", "h-leyenda");
      [["b-fisco", ultimo.dH + " días para Hacienda y la Seguridad Social"],
        ["b-casa", ultimo.dV > 0 ? ultimo.dV + " días para " + (ultimo.tipoVivienda === "alquiler" ? "tu casero" : "la hipoteca") : ""],
        ["b-ti", ultimo.dT + " días para ti"]].forEach(function (x) {
        if (!x[1]) return;
        var li = el("li"); li.appendChild(el("span", "punto " + x[0])); li.appendChild(document.createTextNode(x[1])); ul.appendChild(li);
      });
      lamina.appendChild(ul);
      lamina.appendChild(el("p", "h-pregunta", "¿Y tú, cuántos días trabajas para Hacienda?"));
      var b = el("button", "btn btn-sol h-share", "Compartir mi año");
      b.type = "button";
      b.addEventListener("click", function (e) { e.stopPropagation(); compartir(); });
      lamina.appendChild(b);
    } else {
      lamina.appendChild(el("p", "h-eti", s.eti));
      lamina.appendChild(el("p", "h-big", s.big));
      lamina.appendChild(el("p", "h-sub", s.sub));
      lamina.appendChild(el("p", "h-txt", s.txt));
    }
    lamina.appendChild(el("p", "h-marca", WEB));
    Array.prototype.forEach.call(pistas.children, function (p, j) {
      p.className = "pista" + (j < i ? " llena" : j === i ? " activa" : "");
      p.firstChild.style.animationDuration = DURACION + "ms";
    });
    document.getElementById("h-pos").textContent = "Pantalla " + (i + 1) + " de " + slides.length;
    programar();
  }
  function programar() {
    clearTimeout(temporizador);
    if (reducir || pausa || actual >= slides.length - 1) return;
    temporizador = setTimeout(function () { pintarSlide(actual + 1); }, DURACION);
  }
  function ir(delta) {
    var n = actual + delta;
    if (n < 0) n = 0;
    if (n > slides.length - 1) n = slides.length - 1;
    pintarSlide(n);
  }
  historia.addEventListener("click", function (e) {
    if (e.target.closest("button")) return;
    var rect = historia.getBoundingClientRect();
    ir(e.clientX - rect.left < rect.width / 3 ? -1 : 1);
  });
  historia.addEventListener("keydown", function (e) {
    if (e.key === "ArrowRight") { ir(1); e.preventDefault(); }
    if (e.key === "ArrowLeft") { ir(-1); e.preventDefault(); }
  });
  function setPausa(v) { pausa = v; historia.classList.toggle("pausa", v); if (!v) programar(); else clearTimeout(temporizador); }
  historia.addEventListener("pointerdown", function () { setPausa(true); });
  ["pointerup", "pointercancel", "pointerleave"].forEach(function (ev) { historia.addEventListener(ev, function () { if (pausa) setPausa(false); }); });
  document.getElementById("h-prev").addEventListener("click", function (e) { e.stopPropagation(); ir(-1); });
  document.getElementById("h-next").addEventListener("click", function (e) { e.stopPropagation(); ir(1); });

  // ---------- Resumen en texto (también para lectores de pantalla) ----------
  function resumen(r) {
    var ul = document.getElementById("r-lista");
    ul.innerHTML = "";
    var filas = [
      ["Sueldo bruto", euros(r.bruto)],
      ["IRPF (retención, " + fmt1.format(r.tipo) + " %)", euros(r.irpf)],
      ["Seguridad Social que pagas tú", euros(r.ss)],
      ["IVA en lo que compras (estimación)", euros(r.iva)],
      ["Te llegó al banco", euros(r.neto)],
      [r.tipoVivienda === "alquiler" ? "Alquiler" : r.tipoVivienda === "hipoteca" ? "Hipoteca" : "Vivienda", r.viviendaAno ? euros(r.viviendaAno) : "0 €"],
      ["Seguridad Social que paga tu empresa", euros(r.empresa)],
      ["Lo que le cuestas a tu empresa", euros(r.coste)]
    ];
    if (ipc) filas.push(["Te quitó la subida de precios (" + pct(ipc.media) + ")", euros(r.inflacion)]);
    if (r.poder !== null) filas.push([r.poder >= 0 ? "Poder de compra ganado" : "Poder de compra perdido", euros(Math.abs(r.poder))]);
    filas.forEach(function (f) { var li = el("li"); li.appendChild(el("span", "", f[0])); li.appendChild(el("strong", "", f[1])); ul.appendChild(li); });
    document.getElementById("r-dias").textContent = "De los 365 días del año, trabajaste " + r.dH + " para Hacienda y la Seguridad Social (hasta el " + fecha(r.dH) + ")" +
      (r.dV > 0 ? ", " + r.dV + " para " + (r.tipoVivienda === "alquiler" ? "tu casero" : "pagar la hipoteca") : "") + " y " + r.dT + " para ti.";
    barraAno(r, document.getElementById("r-barra"));
  }

  // ---------- Imagen para compartir (1080×1920, formato historia) ----------
  var logo = new Image();
  var logoListo = new Promise(function (ok) { logo.onload = logo.onerror = ok; });
  logo.src = "/img/logo/icono-512.png";
  var archivo = null, textoCompartir = "";
  function textoDe(r) {
    return "En " + ANO + " trabajé " + r.dH + " días para Hacienda y la Seguridad Social" +
      (r.dV > 0 ? ", " + r.dV + " para " + (r.tipoVivienda === "alquiler" ? "mi casero" : "la hipoteca") : "") +
      " y solo " + r.dT + " para mí. ¿Y tú? Calcula tu año en 1 minuto: https://" + WEB + "/";
  }
  function dibujar(r) {
    return Promise.all([document.fonts ? document.fonts.ready : null, logoListo]).then(function () {
      var c = document.createElement("canvas");
      c.width = 1080; c.height = 1920;
      var x = c.getContext("2d");
      x.fillStyle = "#0e2a47"; x.fillRect(0, 0, 1080, 1920);
      var g = x.createRadialGradient(1080, 0, 60, 1080, 0, 1100);
      g.addColorStop(0, "rgba(245,197,26,.30)"); g.addColorStop(1, "rgba(245,197,26,0)");
      x.fillStyle = g; x.fillRect(0, 0, 1080, 1920);
      if (logo.naturalWidth) x.drawImage(logo, 80, 110, 100, 100);
      x.textAlign = "left";
      x.fillStyle = "#f5c518"; x.font = "700 56px Fraunces, Georgia, serif"; x.fillText("El Euro Claro", 200, 180);
      x.fillStyle = "#ffffff"; x.font = "700 104px Fraunces, Georgia, serif"; x.fillText("Mi " + ANO, 80, 400);
      x.fillText("en euros", 80, 510);
      // barra del año
      var bx = 80, by = 590, bw = 920, bh = 70, total = r.dH + r.dV + r.dT, cx = bx;
      [[r.dH, "#f5c518"], [r.dV, "#8fb0ff"], [r.dT, "#3ccf91"]].forEach(function (s) {
        if (s[1] <= 0) return;
        var w = bw * s[0] / total;
        x.fillStyle = s[1]; x.fillRect(cx, by, w, bh); cx += w;
      });
      x.fillStyle = "#93a6c2"; x.font = "400 28px 'Public Sans', Arial, sans-serif";
      x.fillText("1 de enero", bx, by + bh + 42);
      x.textAlign = "right"; x.fillText("31 de diciembre", bx + bw, by + bh + 42); x.textAlign = "left";
      var y = 830;
      function bloque(color, cifra, texto) {
        x.fillStyle = color; x.font = "700 132px Fraunces, Georgia, serif"; x.fillText(cifra, 80, y);
        x.fillStyle = "#ffffff"; x.font = "600 46px 'Public Sans', Arial, sans-serif";
        y = lineas(x, texto, 80, y + 70, 920, 58) + 190;
      }
      bloque("#f5c518", r.dH + " días", "para Hacienda y la Seguridad Social");
      if (r.dV > 0) bloque("#8fb0ff", r.dV + " días", r.tipoVivienda === "alquiler" ? "para mi casero" : "para la hipoteca");
      bloque("#3ccf91", r.dT + " días", "para mí");
      if (ipc && r.inflacion >= 1) {
        x.fillStyle = "#dde5f1"; x.font = "400 42px 'Public Sans', Arial, sans-serif";
        lineas(x, "Y la subida de precios me quitó " + euros(r.inflacion) + ".", 80, y - 90, 920, 54);
      }
      x.fillStyle = "#f5c518"; roundRect(x, 80, 1600, 920, 170, 30); x.fill();
      x.fillStyle = "#0e2a47"; x.font = "700 52px 'Public Sans', Arial, sans-serif"; x.fillText("¿Y tú? Calcula tu año en", 130, 1672);
      x.font = "700 60px 'Public Sans', Arial, sans-serif"; x.fillText(WEB, 130, 1742);
      x.fillStyle = "#93a6c2"; x.font = "400 28px 'Public Sans', Arial, sans-serif";
      x.fillText("Cálculo aproximado con datos de la AEAT, la Seguridad Social y el INE.", 80, 1850);
      return new Promise(function (ok) { c.toBlob(ok, "image/png"); });
    });
  }
  function lineas(x, t, px, py, ancho, alto) {
    var l = "";
    t.split(" ").forEach(function (w) {
      var prueba = l ? l + " " + w : w;
      if (x.measureText(prueba).width > ancho && l) { x.fillText(l, px, py); py += alto; l = w; } else { l = prueba; }
    });
    x.fillText(l, px, py);
    return py;
  }
  function roundRect(x, a, b, w, h, r) {
    x.beginPath(); x.moveTo(a + r, b); x.arcTo(a + w, b, a + w, b + h, r); x.arcTo(a + w, b + h, a, b + h, r);
    x.arcTo(a, b + h, a, b, r); x.arcTo(a, b, a + w, b, r); x.closePath();
  }
  function compartir() {
    if (archivo && navigator.canShare && navigator.canShare({ files: [archivo] })) {
      navigator.share({ files: [archivo], text: textoCompartir }).catch(function () {});
    } else if (navigator.share) {
      navigator.share({ text: textoCompartir, url: "https://" + WEB + "/" }).catch(function () {});
    } else {
      window.open(document.getElementById("b-whatsapp").href, "_blank", "noopener");
    }
  }
  document.getElementById("b-compartir").addEventListener("click", compartir);

  // ---------- Formulario ----------
  var ultimo = null;
  function verVivienda() {
    var t = form.tipo.value;
    document.getElementById("fila-vivienda").hidden = t === "nada";
    document.getElementById("vivienda-n").textContent = t === "alquiler" ? "Alquiler al mes" : "Hipoteca al mes";
  }
  Array.prototype.forEach.call(form.tipo, function (r) { r.addEventListener("change", verVivienda); });
  verVivienda();

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (!window.calcularNeto) { msg.textContent = "Cargando… prueba en un segundo."; return; }
    var d = leer();
    if (d.error) { msg.textContent = d.error; d.campo.focus(); return; }
    var r = calcular(d);
    if (r.viviendaAno + d.ahorro * 12 > r.neto) {
      msg.textContent = "Con esas cifras, la vivienda y el ahorro suman más que tu sueldo neto (" + euros(r.neto) + " al año). Revisa que el sueldo sea bruto al año y la vivienda, tu parte al mes.";
      return;
    }
    msg.textContent = "";
    ultimo = r;
    slides = construir(r);
    pistas.innerHTML = "";
    slides.forEach(function () { var p = el("span", "pista"); p.appendChild(el("span")); pistas.appendChild(p); });
    resumen(r);
    textoCompartir = textoDe(r);
    document.getElementById("b-whatsapp").href = "https://wa.me/?text=" + encodeURIComponent(textoCompartir);
    var res = document.getElementById("resultado");
    res.hidden = false;
    pintarSlide(0);
    historia.focus({ preventScroll: true });
    res.scrollIntoView({ behavior: reducir ? "auto" : "smooth", block: "start" });
    archivo = null;
    dibujar(r).then(function (blob) {
      if (!blob) return;
      archivo = new File([blob], "mi-ano-en-euros-eleuroclaro.png", { type: "image/png" });
      var url = URL.createObjectURL(blob);
      var img = document.getElementById("r-img");
      img.src = url; img.hidden = false;
      document.getElementById("b-descargar").href = url;
    });
  });

  // ---------- IPC del año ----------
  fetch("/datos/ipc-grupos.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) {
      var meses = (d.general_historia || []).filter(function (h) { return h.anyo === ANO && typeof h.tasa === "number"; });
      if (!meses.length) return;
      var media = meses.reduce(function (a, h) { return a + h.tasa; }, 0) / meses.length;
      var ult = meses[meses.length - 1].mes;
      ipc = { media: Math.round(media * 10) / 10, meses: meses.length,
        texto: meses.length === 1 ? MESES[ult - 1] + " de " + ANO : "media de enero a " + MESES[ult - 1] + " de " + ANO };
      document.getElementById("dato-ipc").textContent = "Subida media de los precios en " + ANO + ": " + pct(ipc.media) + " (INE, " + ipc.texto + ").";
    })
    .catch(function () { /* sin IPC: se quita esa pantalla */ });
})();
