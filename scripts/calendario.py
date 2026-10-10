"""Genera /calendario/index.html y /calendario.ics con los datos oficiales que tocan el bolsillo.

Fechas: calendario de difusión del INE (www.ine.es/dynt3/Calendario/calenHTML.htm, actualizado el 25-9-2026)
y reuniones del BCE. Para añadir fechas, se editan EVENTOS y se ejecuta:
    python3 scripts/calendario.py
El .ics se puede suscribir (webcal://eleuroclaro.es/calendario.ics): quien se suscribe recibe las fechas nuevas.
"""
import html
from datetime import date, datetime, timezone

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]

# (fecha, título, organismo, para ti, enlace de la web)
EVENTOS = [
    (date(2026, 10, 14), "IPC e IRAV de septiembre", "INE",
     "Lo que suben los precios y el índice de los alquileres. Tu calculadora se pone al día sola.", "/inflacion/"),
    (date(2026, 10, 26), "Compraventa de viviendas e hipotecas de agosto", "INE",
     "Cuántas casas se venden y cuánto se pide de hipoteca de media.", "/euribor/"),
    (date(2026, 10, 27), "Paro y empleo del tercer trimestre (EPA)", "INE",
     "Cuánta gente trabaja y cuánta busca trabajo.", None),
    (date(2026, 10, 29), "El BCE decide los tipos de interés", "BCE",
     "Lo que decida mueve el Euríbor y tu hipoteca variable.", "/euribor/"),
    (date(2026, 10, 30), "IPC adelantado de octubre y PIB del tercer trimestre", "INE",
     "Primer dato de precios de octubre: cuenta para la subida de las pensiones de 2027.", "/pension-2027/"),
    (date(2026, 11, 13), "IPC e IRAV de octubre", "INE",
     "Precios y alquileres de octubre, ya definitivos.", "/inflacion/"),
    (date(2026, 11, 17), "Compraventa de viviendas de septiembre", "INE",
     "Cuántas casas se venden.", None),
    (date(2026, 11, 25), "Hipotecas de septiembre", "INE",
     "Cuántas hipotecas se firman, por cuánto y a qué tipo.", "/euribor/"),
    (date(2026, 11, 27), "IPC adelantado de noviembre", "INE",
     "Con este dato ya se sabe casi seguro cuánto suben las pensiones en 2027.", "/pension-2027/"),
    (date(2026, 12, 4), "Precio de la vivienda del tercer trimestre", "INE",
     "Cuánto sube comprar casa, nueva y de segunda mano.", None),
    (date(2026, 12, 15), "IPC e IRAV de noviembre: subida de las pensiones de 2027", "INE",
     "Último mes que cuenta: con este dato queda calculada la subida de las pensiones contributivas.", "/pension-2027/"),
    (date(2026, 12, 17), "Coste laboral y salarios del tercer trimestre", "INE",
     "Cuánto suben los sueldos frente a los precios.", None),
    (date(2026, 12, 17), "El BCE decide los tipos de interés", "BCE",
     "Última reunión del año: mueve el Euríbor y tu hipoteca variable.", "/euribor/"),
    (date(2026, 12, 18), "Hipotecas de octubre", "INE",
     "Cuántas hipotecas se firman, por cuánto y a qué tipo.", "/euribor/"),
    (date(2026, 12, 23), "PIB del tercer trimestre, dato completo", "INE",
     "Confirma o corrige el primer dato de octubre sobre cómo va la economía.", None),
    (date(2026, 12, 30), "IPC adelantado de diciembre", "INE",
     "Cómo cierran los precios el año.", "/inflacion/"),
]


def slug(s):
    return "".join(c for c in s.lower() if c.isascii() and c.isalnum())[:24]


def ics_texto(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def plegar(linea):
    """Líneas de 75 octetos como pide RFC 5545."""
    out, actual = [], b""
    for ch in linea:
        c = ch.encode("utf-8")
        if len(actual) + len(c) > 73:
            out.append(actual.decode("utf-8"))
            actual = b" " + c
        else:
            actual += c
    out.append(actual.decode("utf-8"))
    return "\r\n".join(out)


def ics():
    sello = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lineas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//El Euro Claro//Calendario de datos//ES",
              "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:El Euro Claro: datos que tocan tu bolsillo",
              "X-WR-TIMEZONE:Europe/Madrid", "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D"]
    for d, titulo, org, para, enlace in EVENTOS:
        url = "https://eleuroclaro.es" + (enlace or "/calendario/")
        lineas += [
            "BEGIN:VEVENT",
            f"UID:{d:%Y%m%d}-{slug(titulo)}@eleuroclaro.es",
            f"DTSTAMP:{sello}",
            f"DTSTART;VALUE=DATE:{d:%Y%m%d}",
            f"SUMMARY:{ics_texto(titulo + ' (' + org + ')')}",
            f"DESCRIPTION:{ics_texto(para + chr(10) + 'Lo explicamos en ' + url)}",
            f"URL:{url}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    lineas.append("END:VCALENDAR")
    return "\r\n".join(plegar(x) for x in lineas) + "\r\n"


def pagina():
    filas = []
    mes_actual = None
    for d, titulo, org, para, enlace in EVENTOS:
        if (d.year, d.month) != mes_actual:
            if mes_actual:
                filas.append("        </ol>")
            mes_actual = (d.year, d.month)
            filas.append(f'        <h2 class="cal-mes">{MESES[d.month - 1].capitalize()} de {d.year}</h2>')
            filas.append('        <ol class="cal-lista">')
        mas = f' <a href="{enlace}">Lo explicamos aquí →</a>' if enlace else ""
        filas.append(
            f'          <li class="cal-ev" data-fecha="{d.isoformat()}"><time datetime="{d.isoformat()}">'
            f'<span class="cal-dia">{d.day}</span><span class="cal-sem">{DIAS[d.weekday()]}</span></time>'
            f'<div><p class="cal-tit">{html.escape(titulo)} <span class="cal-org">{org}</span></p>'
            f'<p class="cal-para">{html.escape(para)}{mas}</p></div></li>')
    filas.append("        </ol>")
    return PLANTILLA.replace("{{LISTA}}", "\n".join(filas))


PLANTILLA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Calendario de datos económicos que tocan tu bolsillo · El Euro Claro</title>
<meta name="description" content="Cuándo salen el IPC, el IRAV, el paro, las hipotecas, la subida de las pensiones y las decisiones del BCE. Fechas oficiales del INE y el BCE, para añadir al calendario del móvil.">
<meta name="theme-color" content="#0e2a47">
<meta property="og:site_name" content="El Euro Claro">
<meta property="og:title" content="Calendario de los datos que tocan tu bolsillo">
<meta property="og:description" content="IPC, alquiler, pensiones, hipotecas y BCE: las fechas oficiales, en el calendario de tu móvil.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://eleuroclaro.es/calendario/">
<meta property="og:locale" content="es_ES">
<meta property="og:image" content="https://eleuroclaro.es/img/og-eleuroclaro.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Moneda de euro y el texto: El Euro Claro, la noticia económica del día en euros de tu bolsillo.">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="https://eleuroclaro.es/calendario/">
<!-- Página generada por scripts/calendario.py: no editar a mano. -->
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/fonts.css">
<link rel="stylesheet" href="/style.css?v=20261010i">
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
      <p class="eyebrow">Calendario · fechas oficiales</p>
      <h1>Los datos que tocan tu bolsillo, en tu calendario</h1>
      <p class="intro cal-intro">IPC, alquiler, pensiones, hipotecas y tipos de interés: cuándo sale cada dato. Añádelo al móvil y te aparece solo; si cambia una fecha, se actualiza.</p>
      <div class="actions">
        <a class="btn btn-sol" href="webcal://eleuroclaro.es/calendario.ics">Añadir al iPhone</a>
        <a class="btn btn-primary" href="https://calendar.google.com/calendar/r?cid=webcal%3A%2F%2Feleuroclaro.es%2Fcalendario.ics" rel="noopener">Añadir a Google Calendar</a>
        <a class="btn btn-ghost" href="/calendario.ics" download>Descargar (.ics)</a>
      </div>
      <p class="small cal-nota">El INE publica a las 9:00. Fuentes: calendario de difusión del INE y calendario del Banco Central Europeo.</p>
    </div>
  </section>

  <section class="section alt">
    <div class="wrap cal">
{{LISTA}}
    </div>
  </section>

  <section class="section" id="newsletter" aria-labelledby="nl-tit">
    <div class="wrap news">
      <div>
        <p class="eyebrow">Newsletter · domingos · gratis</p>
        <h2 id="nl-tit">Y el domingo, qué significa para ti</h2>
        <p class="intro">Cada semana, en 3 minutos, los datos que han salido explicados con ejemplos en euros.</p>
        <p class="regalo">De regalo al apuntarte: la guía de una página <strong>«Cómo leer tu nómina en 2 minutos»</strong>.</p>
      </div>
      <form class="signup" data-campana="calendario" novalidate>
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
/* Atenúa las fechas pasadas y marca la siguiente. */
(function () {
  var d = new Date(), dos = function (n) { return (n < 10 ? "0" : "") + n; };
  var hoy = d.getFullYear() + "-" + dos(d.getMonth() + 1) + "-" + dos(d.getDate()), primera = true;
  Array.prototype.forEach.call(document.querySelectorAll(".cal-ev"), function (li) {
    var f = li.getAttribute("data-fecha");
    if (f < hoy) li.classList.add("cal-pasado");
    else if (primera) { li.classList.add("cal-proximo"); primera = false; }
  });
})();
</script>
<script src="/suscribir.js?v=20261010c" defer></script>
<!-- Cloudflare Web Analytics --><script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{"token": "e81aecc33a6b40ccab86c1fbc9fa801c"}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>
"""


if __name__ == "__main__":
    with open("calendario/index.html", "w", encoding="utf-8") as f:
        f.write(pagina())
    with open("calendario.ics", "w", encoding="utf-8", newline="") as f:
        f.write(ics())
    print(f"calendario/index.html y calendario.ics: {len(EVENTOS)} fechas")
