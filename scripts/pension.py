"""Genera /pension-2027/index.html: cuánto suben las pensiones contributivas en 2027 según el IPC.

Regla (art. 58 de la Ley General de la Seguridad Social, redacción de la Ley 21/2021): las pensiones
contributivas se revalorizan cada 1 de enero con la media de las tasas anuales del IPC general de los
12 meses de diciembre del año anterior al anterior a noviembre del año anterior. Para 2027: de diciembre
de 2025 a noviembre de 2026. Si la media sale negativa, las pensiones no bajan.

Lee datos/ipc-grupos.json (general_historia, que guarda scripts/ine_ipc.py) y escribe la página con las
cifras en el HTML, para que se lean sin JavaScript y en buscadores. Un mes que tiene dato general pero aún
no tiene grupos es el indicador adelantado del INE: se marca como adelantado.
Lo ejecuta .github/workflows/ine.yml después de leer el INE.
Uso: python3 scripts/pension.py datos/ipc-grupos.json pension-2027/index.html
"""
import html
import json
import sys

ANYO = 2027
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
VENTANA = [(ANYO - 2, 12)] + [(ANYO - 1, m) for m in range(1, 12)]
PREVIA = [(ANYO - 3, 12)] + [(ANYO - 2, m) for m in range(1, 12)]
IMPORTES = list(range(600, 3301, 100))


def num(x, dec=2):
    """Formato español: 1.234,56."""
    s = f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def eur(x):
    return num(x, 2).replace(",00", "") + "&nbsp;€"


def pct(x):
    return num(x, 1) + "&nbsp;%"


def media(tasas):
    # El INE da las tasas con un decimal; la revalorización se publica con un decimal.
    return round(sum(tasas) / len(tasas) + 1e-9, 1)


def main():
    datos = json.load(open(sys.argv[1], encoding="utf-8"))
    salida = sys.argv[2]
    hist = {(h["anyo"], h["mes"]): h["tasa"] for h in datos["general_historia"]}
    grupos_hasta = (datos["anyo"], datos["mes"])

    meses = [(p, hist.get(p)) for p in VENTANA]
    publicados = [(p, t) for p, t in meses if t is not None]
    if len(publicados) < 3:
        raise SystemExit("Muy pocos meses publicados para estimar")
    ultimo = publicados[-1][0]
    adelantado = ultimo > grupos_hasta
    tasa = media([t for _, t in publicados])
    if tasa < 0:
        tasa = 0.0
    n = len(publicados)
    definitiva = n == 12 and not adelantado
    previa = [hist.get(p) for p in PREVIA]
    tasa_previa = media(previa) if all(t is not None for t in previa) else None

    def nombre_mes(p):
        return f"{MESES[p[1] - 1]} de {p[0]}"

    if definitiva:
        estado = "con los 12 meses del INE"
        etiqueta = "Cifra final con los datos del INE"
        aviso_estado = (f"Ya están los 12 meses: la subida de {ANYO} es del {pct(tasa)}. "
                        "La confirma el Gobierno en el BOE antes del 1 de enero.")
    else:
        faltan = 12 - n
        estado = f"provisional, con {n} de 12 meses"
        etiqueta = "Provisional"
        aviso_estado = (f"Es la media de los {n} meses que el INE ya ha publicado "
                        f"(de diciembre de {ANYO - 2} a {nombre_mes(ultimo)}"
                        + (", que es el dato adelantado" if adelantado else "")
                        + f"). Faltan {faltan} {'mes' if faltan == 1 else 'meses'}: la cifra final sale con el IPC "
                        f"de noviembre de {ANYO - 1} y cambiará si los precios suben más o menos.")

    filas_meses = []
    for p, t in meses:
        if t is None:
            celda = '<td class="num pend">pendiente</td>'
        else:
            nota = " (adelantado)" if p > grupos_hasta else ""
            celda = f'<td class="num">{pct(t)}{nota}</td>'
        filas_meses.append(f"            <tr><td>{nombre_mes(p).capitalize()}</td>{celda}</tr>")

    filas = []
    for imp in IMPORTES:
        nuevo = round(imp * (1 + tasa / 100), 2)
        mas = nuevo - imp
        filas.append(f'            <tr><td>{eur(imp)}</td><td class="num"><strong>{eur(nuevo)}</strong></td>'
                     f'<td class="num">+{eur(mas)}</td><td class="num">+{eur(round(mas * 14, 2))}</td></tr>')

    ej = 1200
    ej_mas = round(ej * tasa / 100, 2)
    resumen = (f"Con la media del IPC publicada hasta {nombre_mes(ultimo)}, las pensiones contributivas "
               f"subirían un {num(tasa, 1)} % en {ANYO}: una pensión de 1.200 € brutos al mes pasaría a "
               f"{num(ej + ej_mas)} € ({num(ej_mas)} € más al mes).")
    if definitiva:
        resumen = (f"Las pensiones contributivas suben un {num(tasa, 1)} % en {ANYO}: una pensión de 1.200 € "
                   f"brutos al mes pasa a {num(ej + ej_mas)} € ({num(ej_mas)} € más al mes).")
    previa_txt = ""
    if tasa_previa is not None:
        previa_txt = (f"<p>Con la misma cuenta, la media de diciembre de {ANYO - 3} a noviembre de {ANYO - 2} "
                      f"fue del {pct(tasa_previa)}: es lo que subieron las pensiones en {ANYO - 1}.</p>")

    faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f"¿Cuánto subirán las pensiones en {ANYO}?",
             "acceptedAnswer": {"@type": "Answer", "text": resumen}},
            {"@type": "Question", "name": "¿Cómo se calcula la subida de las pensiones?",
             "acceptedAnswer": {"@type": "Answer", "text": (
                 "Por ley (artículo 58 de la Ley General de la Seguridad Social), las pensiones contributivas "
                 "suben cada 1 de enero la media de las tasas anuales del IPC de los 12 meses de diciembre a "
                 "noviembre anteriores. Si la media es negativa, no bajan.")}},
            {"@type": "Question", "name": "¿Vale para las pensiones mínimas y no contributivas?",
             "acceptedAnswer": {"@type": "Answer", "text": (
                 "No. Las pensiones no contributivas, las del SOVI y los complementos a mínimos los fija el "
                 "Gobierno cada año con otra regla.")}},
        ],
    }

    pagina = PLANTILLA.format(
        anyo=ANYO, anyo1=ANYO - 1, anyo2=ANYO - 2,
        tasa=pct(tasa), tasa_js=f"{tasa:.1f}", estado=estado, etiqueta=etiqueta,
        aviso_estado=aviso_estado, filas_meses="\n".join(filas_meses), filas="\n".join(filas),
        ejemplo=eur(ej + ej_mas), ejemplo_mas=eur(ej_mas), previa=previa_txt,
        ultimo=nombre_mes(ultimo), actualizado=html.escape(datos.get("actualizado", "")),
        descripcion=html.escape(resumen + " Calcula la tuya."), faq=json.dumps(faq, ensure_ascii=False),
    )
    with open(salida, "w", encoding="utf-8") as f:
        f.write(pagina)
    print(f"{salida}: {num(tasa, 1)} % ({estado})")


PLANTILLA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Subida de las pensiones en {anyo}: cuánto sube la tuya · El Euro Claro</title>
<meta name="description" content="{descripcion}">
<meta name="theme-color" content="#0e2a47">
<meta property="og:site_name" content="El Euro Claro">
<meta property="og:title" content="¿Cuánto subirá tu pensión en {anyo}?">
<meta property="og:description" content="La subida que marca la ley con el IPC publicado hasta ahora ({tasa}). Calcula la tuya en euros.">
<meta property="og:type" content="article">
<meta property="og:url" content="https://eleuroclaro.es/pension-{anyo}/">
<meta property="og:locale" content="es_ES">
<meta property="og:image" content="https://eleuroclaro.es/img/og-pension.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="¿Cuánto subirá tu pensión en {anyo}? Calcúlalo con el IPC en El Euro Claro.">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="https://eleuroclaro.es/pension-{anyo}/">
<!-- Página generada por scripts/pension.py con datos del INE: no editar a mano. -->
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/fonts.css">
<link rel="stylesheet" href="/style.css?v=20261010i">
<script type="application/ld+json">{faq}</script>
</head>
<body>

<header class="top">
  <div class="wrap">
    <a class="brand" href="/" aria-label="El Euro Claro, inicio">
      <svg class="coin" viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="18" fill="#f4c51a"/><circle cx="20" cy="20" r="14.5" fill="none" stroke="#0e2a47" stroke-width="1.2" opacity=".45"/><text x="20" y="26.5" text-anchor="middle" font-family="Georgia, serif" font-size="19" font-weight="700" fill="#10294a">€</text></svg>
      El Euro Claro
    </a>
    <nav class="nav" aria-label="Secciones">
      <a href="/#noticias">Noticias</a>
      <a href="/#videos">Vídeos</a>
      <a href="/inflacion/">Calculadora</a>
      <a href="/#kit">Kit</a>
      <a href="/empresas/">Empresas</a>
      <a href="/#newsletter">Newsletter</a>
      <a href="/libros/">Libros</a>
    </nav>
  </div>
</header>

<main>
  <section class="section page-head">
    <div class="wrap">
      <p class="eyebrow">Pensiones {anyo} · {etiqueta}</p>
      <h1>¿Cuánto subirá tu pensión en {anyo}?</h1>
      <div class="dato">
        <p class="que">Subida de las pensiones contributivas en {anyo} · {estado}</p>
        <p class="cifra">{tasa}</p>
        <p class="src">{aviso_estado} Fuente: INE, IPC general, tasa anual. Regla: artículo 58 de la Ley General de la Seguridad Social.</p>
      </div>
      <p class="pen-aviso"><strong>Ojo:</strong> vale para pensiones contributivas (jubilación, incapacidad, viudedad, orfandad). Si tu pensión lleva complemento a mínimos, es no contributiva o del SOVI, la subida la fija el Gobierno con otra regla.</p>

      <form class="calc pen-calc" id="calc-pension" data-tasa="{tasa_js}" novalidate>
        <label class="pen-label" for="pension">Tu pensión bruta al mes (en 14 pagas)</label>
        <span class="cf-in"><input id="pension" name="pension" type="text" inputmode="decimal" autocomplete="off" placeholder="p. ej. 1.200"><span aria-hidden="true">€/mes</span></span>
        <p class="pen-res" id="pen-res" aria-live="polite">Con una pensión de 1.200&nbsp;€, en {anyo} cobrarías <strong>{ejemplo}</strong> al mes: {ejemplo_mas} más.</p>
      </form>
      <p class="pen-cta"><a class="btn btn-sol" href="#newsletter">Avísame de la cifra final</a><span class="small">Te la mandamos al correo cuando salga. Gratis.</span></p>
    </div>
  </section>

  <section class="section alt" aria-labelledby="tabla">
    <div class="wrap prose">
      <h2 id="tabla">Tu pensión en {anyo}, en euros</h2>
      <p>Con la subida del {tasa} ({estado}). Cifras brutas: lo que te llega depende de tu retención de IRPF.</p>
      <div class="tablebox">
        <table class="tabla">
          <thead><tr><th scope="col">Pensión al mes en {anyo1}</th><th scope="col" class="num">En {anyo}</th><th scope="col" class="num">Más al mes</th><th scope="col" class="num">Más al año (14 pagas)</th></tr></thead>
          <tbody>
{filas}
          </tbody>
        </table>
      </div>
      <p class="small">La pensión máxima tiene su propio límite, que se publica en el BOE a final de año.</p>
    </div>
  </section>

  <section class="section" aria-labelledby="meses">
    <div class="wrap prose">
      <h2 id="meses">Los 12 meses que cuentan</h2>
      <p>La subida de {anyo} es la media de la tasa anual del IPC de estos meses. Cada vez que el INE publica uno, actualizamos esta página.</p>
      <div class="tablebox">
        <table class="tabla">
          <thead><tr><th scope="col">Mes</th><th scope="col" class="num">IPC, tasa anual</th></tr></thead>
          <tbody>
{filas_meses}
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <section class="section alt" aria-labelledby="como">
    <div class="wrap prose">
      <h2 id="como">Cómo se calcula</h2>
      <p>Lo dice la ley (artículo 58 de la Ley General de la Seguridad Social, tras la reforma de 2021): las pensiones contributivas suben cada 1 de enero la media de las tasas anuales del IPC de los 12 meses que van de diciembre a noviembre. Si la media saliera negativa, no bajan.</p>
      {previa}
      <p>El Gobierno confirma la cifra en el BOE antes del 1 de enero y la nueva pensión llega en la nómina de enero.</p>
      <p>¿Y tus gastos? Mira <a href="/inflacion/">cuánto te cuesta a ti la subida de precios</a>.</p>
      <p class="small note-legal">Contenido divulgativo. No es asesoramiento. Para tu caso concreto, consulta a la Seguridad Social.</p>
    </div>
  </section>

  <section class="section" id="newsletter" aria-labelledby="nl-tit">
    <div class="wrap news">
      <div>
        <p class="eyebrow">Newsletter · domingos · gratis</p>
        <h2 id="nl-tit">La cifra final, en tu correo</h2>
        <p class="intro">Cuando el INE publique el IPC de noviembre, te mandamos el domingo la tabla definitiva. Para ti o para tus padres. Y cada semana, en 3 minutos, lo que cambia en tu bolsillo.</p>
        <p class="regalo">De regalo al apuntarte: la guía de una página <strong>«Cómo leer tu nómina en 2 minutos»</strong>.</p>
      </div>
      <form class="signup" data-campana="pension" novalidate>
        <label for="email">Tu correo electrónico</label>
        <input type="email" id="email" name="email" placeholder="nombre@correo.es" autocomplete="email" required>
        <label class="consent" for="consent">
          <input type="checkbox" id="consent" name="consent" required>
          <span>Quiero recibir la newsletter y he leído la <a href="/privacidad.html">política de privacidad</a>.</span>
        </label>
        <button class="btn btn-primary" type="submit">Apuntarme gratis</button>
        <p class="msg" role="status"></p>
        <p class="fine">Odana Ingeniería SL usará tu correo para enviarte la newsletter semanal, que puede incluir publicidad marcada y ofertas de nuestros productos, con tu consentimiento. Lo guarda nuestra plataforma de envíos, Substack (EE. UU.). Puedes darte de baja cuando quieras y ejercer tus derechos en hola@eleuroclaro.es. Más información en la <a href="/privacidad.html">política de privacidad</a>.</p>
      </form>
    </div>
  </section>
</main>

<footer class="foot">
  <div class="wrap">
    <p class="lema">La economía de tu bolsillo, en euros claros.</p>
    <nav aria-label="Legal">
      <a href="/aviso-legal.html">Aviso legal</a>
      <a href="/privacidad.html">Privacidad</a>
      <a href="/cookies.html">Cookies</a>
      <span>Contacto: <span class="mail">hola@eleuroclaro.es</span></span>
    </nav>
    <p class="disclaimer">El Euro Claro es un medio divulgativo. La información es general y no constituye asesoramiento financiero ni una recomendación de comprar o vender ningún producto. Algunos enlaces pueden ser de afiliado y se indica cuando lo son.</p>
    <p>© 2026 El Euro Claro · Odana Ingeniería SL</p>
  </div>
</footer>
<script>
(function () {{
  "use strict";
  var f = document.getElementById("calc-pension"), out = document.getElementById("pen-res");
  var tasa = parseFloat(f.getAttribute("data-tasa"));
  var e = function (x) {{ return x.toLocaleString("es-ES", {{ minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: "always" }}).replace(/,00$/, "") + "\\u00a0€"; }};
  f.addEventListener("submit", function (ev) {{ ev.preventDefault(); }});
  f.pension.addEventListener("input", function () {{
    var v = parseFloat(String(f.pension.value).replace(/\\./g, "").replace(",", "."));
    if (!(v > 0 && v < 100000)) return;
    var nuevo = Math.round(v * (1 + tasa / 100) * 100) / 100, mas = nuevo - v;
    out.innerHTML = "";
    out.append("Con " + e(v) + " al mes, en {anyo} cobrarías ");
    var s = document.createElement("strong"); s.textContent = e(nuevo); out.append(s);
    out.append(" al mes: " + e(mas) + " más al mes y " + e(mas * 14) + " más al año.");
  }});
}})();
</script>
<script src="/suscribir.js?v=20261010c" defer></script>
<!-- Cloudflare Web Analytics --><script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "e81aecc33a6b40ccab86c1fbc9fa801c"}}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>
"""


if __name__ == "__main__":
    main()
