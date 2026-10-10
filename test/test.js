/* Test de dinero en 7 preguntas: una pregunta por pantalla, explicación al responder,
   resultado para compartir y reto con ?r=N (la nota de quien lo envía). Nada sale del navegador. */
(function () {
  "use strict";
  var PREGUNTAS = [
    {
      q: "Tienes 1.000 € guardados en casa. Si los precios suben un 4 % en un año, dentro de un año con ese dinero podrás comprar…",
      o: ["Más que hoy", "Lo mismo que hoy", "Menos que hoy"], ok: 2,
      x: "Los billetes siguen siendo 1.000 €, pero cada cosa cuesta un 4 % más: lo que hoy vale 1.000 € costará 1.040 €. Eso es la inflación.",
      dato: "El 65 % de los españoles acierta una pregunta parecida (Banco de España, Encuesta de Competencias Financieras 2021).",
      enlace: ["/inflacion/", "Calcula cuánto te cuesta a ti la subida de precios"]
    },
    {
      q: "Metes 100 € en una cuenta al 2 % al año y no sacas nada, ni los intereses. Sin comisiones ni impuestos, al cabo de 5 años tendrás…",
      o: ["Más de 110 €", "Justo 110 €", "Menos de 110 €"], ok: 0,
      x: "Cada año ganas intereses también sobre los intereses de los años anteriores (interés compuesto): al quinto año tienes unos 110,41 €.",
      dato: "Solo el 41 % de los españoles acierta una pregunta parecida (Banco de España, Encuesta de Competencias Financieras 2021)."
    },
    {
      q: "En tu nómina, ¿qué es el «líquido a percibir»?",
      o: ["Lo que paga tu empresa en total", "Tu sueldo antes de impuestos", "Lo que te llega a la cuenta"], ok: 2,
      x: "Es lo que cobras de verdad: lo que ganas (devengos) menos lo que te quitan (Seguridad Social e IRPF).",
      enlace: ["/nomina/", "Guía gratis: lee tu nómina en 2 minutos"]
    },
    {
      q: "Para comparar el coste de dos préstamos, ¿qué cifra miras?",
      o: ["El TIN", "La TAE", "La cuota del primer mes"], ok: 1,
      x: "El TIN es solo el tipo de interés. La TAE suma además las comisiones y cómo se pagan los intereses, así que es la que permite comparar."
    },
    {
      q: "Tienes una hipoteca variable y el Euríbor sube. En la próxima revisión, tu cuota…",
      o: ["Sube", "Baja", "No cambia"], ok: 0,
      x: "En una hipoteca variable pagas el Euríbor más un diferencial fijo. Si el Euríbor sube, en la revisión sube la cuota.",
      enlace: ["/euribor/", "Mira el Euríbor de este mes y cuánto cambia tu cuota"]
    },
    {
      q: "Alquilas un piso para vivir. ¿Cuánto es la fianza que marca la ley?",
      o: ["Un mes de renta", "Dos meses de renta", "Lo que pida el casero"], ok: 0,
      x: "La Ley de Arrendamientos Urbanos fija una fianza de un mes para la vivienda. Aparte, el casero puede pedir una garantía adicional, de dos meses como mucho en los contratos de hasta 5 años (7 si el casero es una empresa)."
    },
    {
      q: "Tienes 10.000 € en una cuenta que no da intereses y los precios suben un 3 % en un año. ¿Cuánto poder de compra pierdes, más o menos?",
      o: ["Nada: siguen siendo 10.000 €", "Unos 300 €", "Unos 3.000 €"], ok: 1,
      x: "Con un 3 % de inflación, tus 10.000 € compran lo que antes costaba unos 9.709 €: pierdes unos 290 € de poder de compra en un año."
    }
  ];
  var MEDIA = 53; // % de aciertos medio en España en las preguntas básicas del Banco de España (ECF 2021).
  var URL_TEST = "https://eleuroclaro.es/test/";

  var $ = function (id) { return document.getElementById(id); };
  var inicio = $("t-inicio"), caja = $("t-caja"), fin = $("t-fin");
  var i = 0, aciertos = 0;

  var reto = parseInt(new URLSearchParams(location.search).get("r"), 10);
  if (reto >= 0 && reto <= 7) {
    var r = $("t-reto");
    r.textContent = "Quien te lo ha enviado ha acertado " + reto + " de 7. ¿Le ganas?";
    r.hidden = false;
  }

  $("t-empezar").addEventListener("click", function () {
    inicio.hidden = true; caja.hidden = false; pintar();
  });

  function pintar() {
    var p = PREGUNTAS[i];
    $("t-num").textContent = "Pregunta " + (i + 1) + " de " + PREGUNTAS.length;
    $("t-barra").style.width = (i / PREGUNTAS.length * 100) + "%";
    $("t-q").textContent = p.q;
    var ops = $("t-ops"); ops.textContent = "";
    p.o.forEach(function (txt, k) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "t-op"; b.textContent = txt;
      b.addEventListener("click", function () { responder(k); });
      ops.appendChild(b);
    });
    $("t-exp").hidden = true;
    $("t-q").focus();
  }

  function responder(k) {
    var p = PREGUNTAS[i], botones = $("t-ops").querySelectorAll("button");
    Array.prototype.forEach.call(botones, function (b, n) {
      b.disabled = true;
      if (n === p.ok) b.classList.add("t-bien");
      else if (n === k) b.classList.add("t-mal");
    });
    var bien = k === p.ok;
    if (bien) aciertos++;
    $("t-veredicto").textContent = bien ? "¡Correcto!" : "No es esa.";
    $("t-veredicto").className = bien ? "t-v-bien" : "t-v-mal";
    $("t-x").textContent = p.x;
    var dato = $("t-dato"); dato.textContent = p.dato || ""; dato.hidden = !p.dato;
    var en = $("t-enlace");
    if (p.enlace) { en.href = p.enlace[0]; en.textContent = p.enlace[1] + " →"; en.hidden = false; } else en.hidden = true;
    $("t-sig").textContent = i + 1 < PREGUNTAS.length ? "Siguiente pregunta" : "Ver mi resultado";
    $("t-exp").hidden = false;
    $("t-sig").focus();
  }

  $("t-sig").addEventListener("click", function () {
    i++;
    if (i < PREGUNTAS.length) pintar(); else resultado();
  });

  function resultado() {
    caja.hidden = true; fin.hidden = false;
    var pct = Math.round(aciertos / PREGUNTAS.length * 100);
    $("t-nota").textContent = aciertos + " de 7";
    var frase;
    if (aciertos === 7) frase = "Pleno. Sabes de dinero más que la mayoría.";
    else if (pct > MEDIA) frase = "Por encima de la media: has acertado el " + pct + " %.";
    else if (pct === MEDIA) frase = "Justo en la media.";
    else frase = "Has acertado el " + pct + " %: con 3 minutos a la semana se sube rápido.";
    $("t-frase").textContent = frase;
    if (reto >= 0 && reto <= 7) {
      $("t-vs").textContent = aciertos > reto ? "Has ganado a quien te lo envió (" + reto + " de 7)." :
        aciertos === reto ? "Empate con quien te lo envió (" + reto + " de 7)." :
        "Quien te lo envió sacó " + reto + " de 7. Te toca la revancha.";
      $("t-vs").hidden = false;
    }
    var url = URL_TEST + "r/" + aciertos + "/";
    var texto = "He acertado " + aciertos + " de 7 en el test de dinero de El Euro Claro. ¿Me ganas?";
    $("t-wa").href = "https://wa.me/?text=" + encodeURIComponent(texto + " " + url);
    $("t-compartir").onclick = function () {
      if (navigator.share) navigator.share({ title: "Test de dinero", text: texto, url: url }).catch(function () {});
      else window.open($("t-wa").href, "_blank", "noopener");
    };
    fin.focus();
  }
})();
