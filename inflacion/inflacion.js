// Calculadora de inflación personal. Todo se calcula en el navegador: no se envía ningún dato.
// La subida de cada grupo sale de /datos/ipc-grupos.json, que guarda cada mañana la tarea «Datos del INE».
(function () {
  "use strict";

  var NEWSLETTER_URL = "https://eleuroclaro.substack.com/subscribe?utm_source=web&utm_medium=calculadora&utm_campaign=inflacion";
  var WEB = "eleuroclaro.es/inflacion";

  // Nombre corto y ejemplos de cada grupo ECOICOP v2 (los 7 primeros se ven siempre; el resto, en «Añadir más gastos»).
  var GRUPOS = {
    "01": { n: "Comida y bebida", d: "La compra del súper, sin alcohol", ph: "400", ver: true },
    "04": { n: "Casa: alquiler, luz, gas y agua", d: "El alquiler sí; la hipoteca, no", ph: "750", ver: true },
    "07": { n: "Transporte", d: "Gasolina, bus, metro, taller", ph: "200", ver: true },
    "11": { n: "Bares, restaurantes y hoteles", d: "Comer fuera, cafés, escapadas", ph: "150", ver: true },
    "08": { n: "Móvil, internet y tele", d: "Tarifas, plataformas, aparatos", ph: "60", ver: true },
    "09": { n: "Ocio, deporte y cultura", d: "Gimnasio, cine, viajes organizados", ph: "80", ver: true },
    "03": { n: "Ropa y calzado", d: "", ph: "60", ver: true },
    "06": { n: "Salud", d: "Farmacia, dentista, óptica", ph: "40" },
    "12": { n: "Seguros y banco", d: "Seguro del coche y del hogar, comisiones", ph: "50" },
    "05": { n: "Muebles y cosas de casa", d: "Electrodomésticos, limpieza", ph: "40" },
    "13": { n: "Cuidado personal y otros", d: "Peluquería, guardería, residencia", ph: "40" },
    "10": { n: "Educación", d: "Colegio, academia, universidad", ph: "0" },
    "02": { n: "Tabaco y alcohol", d: "", ph: "0" }
  };
  var ORDEN = ["01", "04", "07", "11", "08", "09", "03", "06", "12", "05", "13", "10", "02"];

  var form = document.getElementById("calc");
  var filas = document.getElementById("calc-filas");
  var filasMas = document.getElementById("calc-filas-mas");
  var suma = document.getElementById("calc-suma");
  var msg = document.getElementById("calc-msg");
  var datos = null;

  var eur = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0 });
  var pct = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  function euros(x) { return eur.format(Math.round(x)) + " €"; }
  function signo(x) { return (x > 0 ? "+" : x < 0 ? "−" : "") + pct.format(Math.abs(x)) + " %"; }
  function num(v) { v = String(v || "").replace(/\./g, "").replace(",", ".").replace(/[^\d.]/g, ""); var n = parseFloat(v); return isFinite(n) && n > 0 ? n : 0; }

  function pintar() {
    var conocidos = datos.grupos.filter(function (g) { return GRUPOS[g.codigo]; }).length === datos.grupos.length && datos.grupos.length === 13;
    var lista = conocidos ? ORDEN.map(function (c) { return datos.grupos.filter(function (g) { return g.codigo === c; })[0]; }) : datos.grupos;
    lista.forEach(function (g) {
      var info = conocidos ? GRUPOS[g.codigo] : { n: g.nombre, d: "", ph: "0", ver: true };
      var id = "g" + g.codigo;
      var fila = document.createElement("div");
      fila.className = "calc-fila";
      fila.innerHTML =
        '<label for="' + id + '"><span class="cf-n"></span><span class="cf-d"></span></label>' +
        '<span class="cf-tasa" title="Subida oficial de este grupo en 12 meses"></span>' +
        '<span class="cf-in"><input id="' + id + '" name="' + id + '" type="text" inputmode="decimal" autocomplete="off" placeholder=""><span aria-hidden="true">€/mes</span></span>';
      fila.querySelector(".cf-n").textContent = info.n;
      fila.querySelector(".cf-d").textContent = info.d || g.nombre;
      var t = fila.querySelector(".cf-tasa");
      t.textContent = signo(g.tasa);
      t.className = "cf-tasa " + (g.tasa >= datos.general ? "cf-alta" : g.tasa < 0 ? "cf-baja" : "");
      var input = fila.querySelector("input");
      input.placeholder = "p. ej. " + info.ph;
      input.dataset.tasa = g.tasa;
      input.dataset.nombre = info.n;
      input.setAttribute("aria-describedby", "calc-dato");
      (info.ver ? filas : filasMas).appendChild(fila);
    });
    if (!filasMas.children.length) document.getElementById("calc-mas").hidden = true;
    document.getElementById("calc-dato").textContent = "Subida de cada grupo en los últimos 12 meses, según el INE (" + datos.periodo + "). La media, el IPC: " + signo(datos.general) + ".";
    form.addEventListener("input", total);
  }

  function entradas() { return Array.prototype.slice.call(form.querySelectorAll("input[data-tasa]")); }
  function total() { suma.textContent = euros(entradas().reduce(function (a, i) { return a + num(i.value); }, 0)); }

  function calcular(e) {
    e.preventDefault();
    if (!datos) { msg.textContent = "Cargando los datos del INE… prueba en un segundo."; return; }
    var gasto = 0, antes = 0, partes = [];
    entradas().forEach(function (i) {
      var g = num(i.value);
      if (!g) return;
      var r = parseFloat(i.dataset.tasa);
      var hace = g / (1 + r / 100);
      gasto += g; antes += hace;
      partes.push({ n: i.dataset.nombre, extra: (g - hace) * 12, r: r });
    });
    if (!gasto) { msg.textContent = "Pon al menos un gasto, por ejemplo lo que gastas en la compra."; return; }
    msg.textContent = "";
    var extra = (gasto - antes) * 12;
    var tasa = (gasto / antes - 1) * 100;
    partes.sort(function (a, b) { return b.extra - a.extra; });

    document.getElementById("res-tit").textContent = extra >= 0 ? "Lo mismo que hace un año te cuesta ahora" : "Con lo que tú compras, lo mismo que hace un año te cuesta";
    document.getElementById("res-euros").textContent = euros(Math.abs(extra));
    document.querySelector(".res-al").textContent = extra >= 0 ? "más al año" : "menos al año";
    var comp = tasa > datos.general + 0.2 ? "más que la media" : tasa < datos.general - 0.2 ? "menos que la media" : "lo mismo que la media";
    document.getElementById("res-tasa").innerHTML = "Tu subida de precios: <strong>" + signo(tasa) + "</strong>. La media oficial (IPC de " + datos.periodo + "): " + signo(datos.general) + ". A ti te sube " + comp + ".";
    var top = document.getElementById("res-top");
    top.innerHTML = "";
    partes.filter(function (p) { return p.extra > 0.5; }).slice(0, 3).forEach(function (p) {
      var li = document.createElement("li");
      li.textContent = p.n + ": " + euros(p.extra) + " más al año (" + signo(p.r) + ")";
      top.appendChild(li);
    });
    document.getElementById("res-fuente").textContent = "Estimación con la subida oficial de cada grupo del IPC (INE, " + datos.periodo + "). Dentro de cada grupo, unos productos suben más que otros.";

    var res = document.getElementById("resultado");
    res.hidden = false;
    res.focus({ preventScroll: true });
    res.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    compartir(extra, tasa);
  }

  // Imagen para compartir (1080×1350, la medida de Instagram y WhatsApp) dibujada en el navegador.
  function compartir(extra, tasa) {
    var texto = (extra >= 0 ? "A mí la subida de precios me cuesta " + euros(extra) + " más al año." : "A mí la subida de precios no me afecta: pago " + euros(-extra) + " menos al año.") +
      " ¿Y a ti? Calcúlalo en 1 minuto con los datos del INE: https://" + WEB + "/";
    document.getElementById("b-whatsapp").href = "https://wa.me/?text=" + encodeURIComponent(texto);
    (document.fonts ? document.fonts.ready : Promise.resolve()).then(function () {
      var c = document.createElement("canvas");
      c.width = 1080; c.height = 1350;
      var x = c.getContext("2d");
      x.fillStyle = "#0e2a47"; x.fillRect(0, 0, 1080, 1350);
      var grad = x.createRadialGradient(1080, 0, 50, 1080, 0, 900);
      grad.addColorStop(0, "rgba(245,197,26,.28)"); grad.addColorStop(1, "rgba(245,197,26,0)");
      x.fillStyle = grad; x.fillRect(0, 0, 1080, 1350);
      // moneda y marca
      x.fillStyle = "#f5c518"; x.beginPath(); x.arc(130, 140, 48, 0, Math.PI * 2); x.fill();
      x.fillStyle = "#0e2a47"; x.font = "700 52px Fraunces, Georgia, serif"; x.textAlign = "center"; x.fillText("€", 130, 158);
      x.textAlign = "left"; x.fillStyle = "#f5c518"; x.font = "700 56px Fraunces, Georgia, serif"; x.fillText("El Euro Claro", 200, 160);
      x.fillStyle = "#ffffff"; x.font = "600 66px Fraunces, Georgia, serif";
      lineas(x, extra >= 0 ? "A mí la subida de precios me cuesta" : "Con lo que yo compro, los precios me han bajado", 90, 420, 900, 80);
      x.fillStyle = "#f5c518"; x.font = "700 170px Fraunces, Georgia, serif";
      x.fillText(euros(Math.abs(extra)), 90, extra >= 0 ? 700 : 700);
      x.fillStyle = "#ffffff"; x.font = "600 64px Fraunces, Georgia, serif"; x.fillText(extra >= 0 ? "más al año" : "al año", 90, 800);
      x.fillStyle = "#c9d5e6"; x.font = "400 40px 'Public Sans', Arial, sans-serif";
      x.fillText("Mi subida: " + signo(tasa) + "  ·  La media (IPC): " + signo(datos.general), 90, 900);
      x.fillStyle = "#f5c518"; roundRect(x, 90, 1010, 900, 150, 28); x.fill();
      x.fillStyle = "#0e2a47"; x.font = "700 50px 'Public Sans', Arial, sans-serif"; x.fillText("¿Y a ti? Calcúlalo en", 140, 1078);
      x.font = "700 54px 'Public Sans', Arial, sans-serif"; x.fillText(WEB, 140, 1140);
      x.fillStyle = "#93a6c2"; x.font = "400 30px 'Public Sans', Arial, sans-serif";
      x.fillText("Datos: INE, IPC por grupos (" + datos.periodo + "). Estimación.", 90, 1270);
      c.toBlob(function (blob) {
        if (!blob) return;
        var url = URL.createObjectURL(blob);
        var img = document.getElementById("res-img");
        img.src = url; img.hidden = false;
        document.getElementById("b-descargar").href = url;
        var file = new File([blob], "mi-inflacion-eleuroclaro.png", { type: "image/png" });
        document.getElementById("b-compartir").onclick = function () {
          if (navigator.canShare && navigator.canShare({ files: [file] })) {
            navigator.share({ files: [file], text: texto }).catch(function () {});
          } else if (navigator.share) {
            navigator.share({ text: texto, url: "https://" + WEB + "/" }).catch(function () {});
          } else {
            window.open(document.getElementById("b-whatsapp").href, "_blank", "noopener");
          }
        };
      }, "image/png");
    });
  }
  function lineas(x, t, px, py, ancho, alto) {
    var palabras = t.split(" "), l = "";
    palabras.forEach(function (w) {
      var prueba = l ? l + " " + w : w;
      if (x.measureText(prueba).width > ancho && l) { x.fillText(l, px, py); py += alto; l = w; } else { l = prueba; }
    });
    x.fillText(l, px, py);
  }
  function roundRect(x, a, b, w, h, r) {
    x.beginPath(); x.moveTo(a + r, b); x.arcTo(a + w, b, a + w, b + h, r); x.arcTo(a + w, b + h, a, b + h, r);
    x.arcTo(a, b + h, a, b, r); x.arcTo(a, b, a + w, b, r); x.closePath();
  }

  form.addEventListener("submit", calcular);
  fetch("/datos/ipc-grupos.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) { datos = d; pintar(); })
    .catch(function () { msg.textContent = "No hemos podido cargar los datos del INE. Recarga la página en un momento."; });

  // Alta en la newsletter: lleva a la página de Substack con el correo ya puesto.
  var su = document.getElementById("signup");
  var sm = document.getElementById("signup-msg");
  su.addEventListener("submit", function (e) {
    e.preventDefault();
    var email = su.email.value.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { sm.textContent = "Revisa el correo: falta algo (por ejemplo, la @)."; return; }
    if (!su.consent.checked) { sm.textContent = "Marca la casilla de privacidad para apuntarte."; return; }
    window.location.href = NEWSLETTER_URL + "&email=" + encodeURIComponent(email);
  });
})();
