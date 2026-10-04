"""Guarda en prensa.json los últimos titulares de prensa económica (titular, medio, enlace y hora).

Lo ejecuta cada hora .github/workflows/prensa.yml. Solo se guarda el titular y el enlace a la web
del medio, nunca el texto de la noticia. Se quitan las noticias de criptomonedas, las que parecen
recomendaciones de inversión (El Euro Claro no recomienda invertir), los directos y los artículos
de opinión o ideológicos. Solo se aceptan enlaces a los dominios de MEDIOS.
Cada titular lleva un tema («c») para la ilustración propia que lo acompaña en la portada (ver TEMAS).
Uso: python3 scripts/prensa.py prensa.json
"""
import email.utils
import html
import html.entities
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

FUENTES = [
    ("Expansión", "https://e00-expansion.uecdn.es/rss/economia.xml"),
    ("Cinco Días", "https://feeds.elpais.com/mrss-s/pages/ep/site/cincodias.elpais.com/portada"),
    ("Europa Press", "https://www.europapress.es/rss/rss.aspx?ch=00136"),
    ("El País", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada"),
    ("El Mundo", "https://e00-elmundo.uecdn.es/elmundo/rss/economia.xml"),
    ("La Vanguardia", "https://www.lavanguardia.com/rss/economia.xml"),
    ("20minutos", "https://www.20minutos.es/rss/economia/"),
]
# Fuera (4-10-2026): elEconomista responde 403 a la tarea y el RSS de economía de RTVE lleva sin noticias nuevas desde junio.
# El medio se saca del enlace (algunos RSS mezclan noticias de otras cabeceras del grupo).
# Es también la lista de dominios permitidos: un enlace a cualquier otro sitio se descarta.
MEDIOS = {
    "cincodias.elpais.com": "Cinco Días",
    "elpais.com": "El País",
    "expansion.com": "Expansión",
    "europapress.es": "Europa Press",
    "elmundo.es": "El Mundo",
    "lavanguardia.com": "La Vanguardia",
    "20minutos.es": "20minutos",
}
# Secciones de cada web que entran (ruta del enlace). Así no se cuelan gadgets, famosos o política internacional
# que algunos RSS de «economía» mezclan. Un medio que no está aquí entra entero.
SECCIONES = {
    "Cinco Días": re.compile(r"^/(economia|companias|mercados-financieros)/"),
    "El País": re.compile(r"^/economia/"),
    "Expansión": re.compile(r"^/(economia|empresas)/(?!politica/)"),
    "Europa Press": re.compile(r"^/economia/"),
    "El Mundo": re.compile(r"^/economia/"),
    "La Vanguardia": re.compile(r"^/economia/"),
}
POR_MEDIO = 3
TOTAL = 8
HORAS = 36
MADRID = ZoneInfo("Europe/Madrid")

# Temas que no salen en la portada: criptomonedas, consejos de inversión, juego e ideología.
FUERA = re.compile(
    r"cripto|bitc[oó]in|\bbtc\b|ethereum|\bether\b|blockchain|\bnfts?\b|binance|coinbase|stablecoin|memecoin|dogecoin|"
    r"\btether\b|\busdt\b|\bxrp\b|ripple|\btokens?\b|"
    r"(d[oó]nde|c[oó]mo|en qu[eé]) invertir|invertir en (bolsa|oro|acciones|fondos|cripto)|qu[eé] comprar|"
    r"(mejores|\d+) (acciones|valores|fondos|dep[oó]sitos|cuentas)|acciones (del ibex )?para (comprar|invertir)|"
    r"recomienda\w*\s+(comprar|vender)|recomendaci[oó]n de (compra|venta)|potencial alcista|con (m[aá]s )?potencial|"
    r"cartera modelo|precio objetivo|sobrepondera|fondos? (indexados?|de inversi[oó]n)|"
    r"cu[aá]nto rent|momento (de|para) (comprar|invertir)|comprar oro|dividendo|\btrading\b|forex|br[oó]ker|"
    r"hor[oó]scopo|sorteo|loter[ií]a|apuestas|neoliberal|izquierda|derecha",
    re.I,
)
# Directos y piezas de opinión: por palabras del titular, por la categoría del RSS o por la ruta del enlace.
DIRECTO = re.compile(r"\b(en )?directo\b|en vivo|[uú]ltima hora|minuto a minuto", re.I)
OPINION = re.compile(r"opini[oó]n|editorial|tribuna|an[aá]lisis|columna|\bblogs?\b|cartas? al director", re.I)
RUTA_OPINION = re.compile(r"/(opinion|tribuna|blogs?|analisis|editorial|columnas?)/", re.I)
# Titulares que son una cita entera («“…”» o «Nombre: “…”») o una columna tipo «Sánchez: elecciones, clases medias, Trump»:
# suelen ser entrevistas u opinión, y la portada solo enseña noticias (decisión 3-10-2026).
CITA = re.compile(r"^[“«\"']|^[^:“«\"]{2,40}:\s*[“«\"]")
COLUMNA = re.compile(r"^[^:]{2,30}:\s*[^,]{2,30}(,\s*[^,]{2,30})+$")
ETIQUETA = re.compile(r"^(mapa|v[ií]deo|video|gr[aá]fico|fotos?|podcast|infograf[ií]a|exclusiva|entrevista)$", re.I)
# Tema de cada titular, para la ilustración que lo acompaña en la portada (img/prensa/<tema>.svg; son dibujos
# propios, nunca fotos de los medios). Gana el primero que encaja; el orden importa (p. ej. «huelga por la vivienda»
# es vivienda y «coche eléctrico» es transporte). Se compara sin tildes y en minúsculas. Sin tema: «general».
TEMAS = [
    ("pensiones", r"pension|jubilac|jubilad"),
    ("tipos", r"euribor|\bbce\b|banco central|tipos? de interes|(subida|bajada|recorte|alza|rebaja)s? de (los )?tipos|lagarde|reserva federal|\bfed\b|hipotec"),
    ("vivienda", r"vivienda|alquil|inquilin|\bpisos?\b|inmobiliari|promotora|okupa|desahucio|\bsuelo\b"),
    ("transporte", r"turis|hotel|\bviaj|vuelo|aerolinea|aeropuert|\bavion|\baena\b|renfe|\btren(es)?\b|ferrocarril|autobus|\bcoches?\b|automovil|automocion|vehiculo|matriculac|carretera"),
    ("energia", r"\bluz\b|electricidad|electric|\bgas\b|gasolina|diesel|gasoleo|carburante|combustible|petroleo|\bbrent\b|\bopep\b|energ|renovable|fotovoltaic|eolic|nuclear|apagon"),
    ("precios", r"\bipc\b|inflacion|precio|cesta de la compra|supermercad|alimento|aceite|\bleche\b|huevos|consumidor|encarec|abarat"),
    ("empleo", r"empleo|\bparo\b|parados|desemple|\bepa\b|afiliad|afiliacion|seguridad social|salari|sueldo|\bsmi\b|nomina|trabajador|contratacion|despid|\beres?\b|\bertes?\b|huelga|sindicat|ccoo|comisiones obreras|\bugt\b|jornada|autonomos|teletrabajo|convenio"),
    ("impuestos", r"hacienda|impuesto|tribut|\birpf\b|\biva\b|fiscal|\baeat\b|declaracion de la renta|presupuestos|deficit|deuda publica|recaudac"),
    ("economia", r"\bpib\b|crecimiento|recesion|prevision|\bfmi\b|\bocde\b|airef|banco de espana|economia espanola|eurozona|zona euro|productividad|desaceleracion"),
    ("bancos", r"\bbanc(o|os|a|aria|ario|arias|arios)\b|santander|bbva|caixabank|sabadell|bankinter|unicaja|ibercaja|kutxabank|abanca|cajamar|entidades financieras|credito|prestamo|morosidad"),
    ("tecnologia", r"inteligencia artificial|\bia\b|tecnolog|digital|\bchips?\b|semiconductor|software|telecomunicac|startup|ciberataque|nvidia|openai"),
    ("comercio", r"arancel|exportac|importac|comercio (exterior|mundial|internacional)|china|estados unidos|\beeuu\b|\bee\. ?uu\.?|trump|rusia|ucrania|oriente proximo|israel|\biran\b|guerra|geopolitic|bruselas|comision europea|\bue\b|union europea|mercosur|latinoameric|iberoameric|contenedor|\bpuertos?\b|naviera|\bg7\b|\bg20\b|sanciones"),
    ("empresas", r"empresa|compania|resultados|beneficio|factura|\bventas\b|\bibex\b|\bbolsa\b|cotiza|accionista|\bopa\b|fusion|adquisicion|multinacional|consejero delegado|plantilla"),
]
TEMAS = [(k, re.compile(r)) for k, r in TEMAS]
# Secciones de empresas: si el titular no dice nada más, la ilustración es la de empresas.
RUTA_EMPRESAS = re.compile(r"^/(companias|empresas|empresas-finanzas)/")
UA = "Mozilla/5.0 (compatible; ElEuroClaro/1.0; +https://eleuroclaro.es)"
ETIQUETA_HTML = re.compile(r"</?[A-Za-z][^>]*>")


def hijos(el, nombre):
    return [h for h in el if h.tag.split("}")[-1] == nombre]


def texto(el, *nombres):
    for n in nombres:
        for h in hijos(el, n):
            if (h.text or "").strip():
                return h.text.strip()
    return ""


def enlace_de(e):
    """RSS: <link>texto</link>. Atom: <link href> con rel alternate (o sin rel). Último recurso: <guid> permanente."""
    t = texto(e, "link")
    if t:
        return t
    links = [h for h in hijos(e, "link") if h.get("href")]
    for h in links:
        if h.get("rel") in (None, "alternate"):
            return h.get("href")
    for h in hijos(e, "guid"):
        if h.get("isPermaLink") != "false" and (h.text or "").strip().startswith("https://"):
            return h.text.strip()
    return ""


def fecha(s):
    if not s:
        return None
    s = s.strip().replace(" CEST", " +0200").replace(" CET", " +0100")
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=MADRID)
    return d.astimezone(timezone.utc)


def medio_de(enlace):
    host = (urllib.parse.urlsplit(enlace).hostname or "").lower()
    for dominio, nombre in MEDIOS.items():
        if host == dominio or host.endswith("." + dominio):
            return nombre
    return None


def normal(t):
    t = ETIQUETA_HTML.sub(" ", t)
    t = html.unescape(t)
    t = ETIQUETA_HTML.sub(" ", t)
    t = unicodedata.normalize("NFKC", t)
    t = "".join(c for c in t if unicodedata.category(c) not in ("Cf", "Cc"))
    return re.sub(r"\s+", " ", t).strip()


def titular(crudo):
    """Devuelve el titular limpio o "" si hay que descartarlo.

    Algunos medios añaden una etiqueta («Mapa | …», «Directo | …») o su nombre («… | Expansión»):
    se quitan y se queda la primera parte con contenido."""
    t = normal(crudo)
    if not t or FUERA.search(t) or DIRECTO.search(t):
        return ""
    nombres = {n.lower() for n in MEDIOS.values()}
    partes = [p.strip() for p in t.split(" | ") if p.strip() and p.strip().lower() not in nombres]
    if not partes or OPINION.match(partes[0]):
        return ""
    if len(partes) > 1 and (ETIQUETA.match(partes[0]) or len(partes[0].split()) <= 3):
        partes = partes[1:]
    t = partes[0]
    if len(t) < 25 or CITA.search(t) or (COLUMNA.match(t) and len(t.split()) <= 9):
        return ""
    return t if len(t) <= 160 else t[:157].rsplit(" ", 1)[0] + "…"


def tema(titulo, enlace=""):
    t = "".join(c for c in unicodedata.normalize("NFD", titulo.lower()) if unicodedata.category(c) != "Mn")
    for clave, patron in TEMAS:
        if patron.search(t):
            return clave
    if RUTA_EMPRESAS.search(urllib.parse.urlsplit(enlace).path):
        return "empresas"
    return "general"


def analizar(datos, charset):
    try:
        return ET.fromstring(datos)
    except ET.ParseError:
        # RSS sin declaración de codificación o con entidades HTML (&oacute;): se arregla y se reintenta.
        txt = datos.decode(charset or "utf-8", errors="replace")
        txt = re.sub(r"^<\?xml[^>]*\?>", "", txt.lstrip())
        txt = re.sub(
            r"&([A-Za-z][A-Za-z0-9]*);",
            lambda m: m.group(0) if m.group(1) in ("amp", "lt", "gt", "quot", "apos")
            else (f"&#{html.entities.name2codepoint[m.group(1)]};" if m.group(1) in html.entities.name2codepoint else " "),
            txt,
        )
        return ET.fromstring(txt)


def leer(url, stats=None):
    """Titulares válidos de un RSS. En stats (si se pasa) cuenta por qué se descarta cada entrada, para el resumen de la tarea."""
    stats = {} if stats is None else stats
    cuenta = lambda k: stats.__setitem__(k, stats.get(k, 0) + 1)  # noqa: E731
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raiz = analizar(r.read(5_000_000), r.headers.get_content_charset())
    out = []
    for e in raiz.iter():
        if e.tag.split("}")[-1] not in ("item", "entry"):
            continue
        cuenta("entradas")
        d = fecha(texto(e, "pubDate", "published", "updated", "date"))
        if d is not None and (stats.get("mas_reciente") is None or d > stats["mas_reciente"]):
            stats["mas_reciente"] = d
        enlace = enlace_de(e).strip()
        if enlace.startswith("http://"):
            enlace = "https://" + enlace[len("http://"):]
        if not enlace.startswith("https://") or RUTA_OPINION.search(enlace):
            cuenta("enlace/opinión")
            continue
        medio = medio_de(enlace)
        if medio in SECCIONES and not SECCIONES[medio].search(urllib.parse.urlsplit(enlace).path):
            cuenta("sección")
            stats.setdefault("ruta_ejemplo", urllib.parse.urlsplit(enlace).path[:40])
            continue
        categorias = " ".join(normal(h.text or h.get("term") or "") for n in ("category", "subject") for h in hijos(e, n))
        if medio is None or OPINION.search(categorias):
            cuenta("medio/categoría")
            continue
        t = titular(texto(e, "title"))
        if not t or d is None:
            cuenta("titular/fecha")
            continue
        out.append({"t": t, "m": medio, "u": enlace, "f": d.strftime("%Y-%m-%dT%H:%M:%SZ"), "c": tema(t, enlace)})
    return out


def main(destino):
    ahora = datetime.now(timezone.utc)
    limite = ahora - timedelta(hours=HORAS)
    recientes, fallos = [], 0
    for nombre, url in FUENTES:
        stats = {}
        try:
            items = leer(url, stats)
        except Exception as e:  # noqa: BLE001 — un medio caído no debe parar a los demás
            fallos += 1
            print(f"::warning::AVISO {nombre}: {type(e).__name__}: {e}")
            continue
        validos = [i for i in items if limite <= fecha(i["f"]) <= ahora + timedelta(minutes=10)]
        reciente = stats.pop("mas_reciente", None)
        detalle = ", ".join(f"{k} {v}" for k, v in stats.items())
        # ::notice:: para que el resumen se vea en la página de la tarea sin abrir el registro
        print(f"::notice::{nombre}: {len(items)} titulares, {len(validos)} de las últimas {HORAS} h; "
              f"más reciente del RSS {reciente:%d-%m %H:%M} UTC; {detalle}" if reciente else
              f"::notice::{nombre}: {len(items)} titulares, {len(validos)} de las últimas {HORAS} h; {detalle}")
        recientes += validos
    # Una sola pasada, de más reciente a más antiguo: sin repetidos y como mucho POR_MEDIO por medio.
    recientes.sort(key=lambda i: i["f"], reverse=True)
    todos, vistos, cuenta = [], set(), {}
    for i in recientes:
        clave = re.sub(r"\W+", "", i["t"].lower())[:60]
        if clave in vistos or i["u"] in vistos or cuenta.get(i["m"], 0) >= POR_MEDIO:
            continue
        vistos.update((clave, i["u"]))
        todos.append(i)
        cuenta[i["m"]] = cuenta.get(i["m"], 0) + 1
        if len(todos) == TOTAL:
            break
    if not todos:
        # La portada esconde sola los titulares de más de 36 h, así que no hace falta fallar cada hora.
        print("::warning::Ningún titular nuevo; prensa.json se queda como estaba")
        return 0
    try:
        with open(destino, encoding="utf-8") as f:
            antes = json.load(f).get("items")
    except (OSError, ValueError, AttributeError):
        antes = None
    if antes == todos:
        print("Sin cambios")
        return 0
    with open(destino, "w", encoding="utf-8") as f:
        json.dump({"actualizado": ahora.strftime("%Y-%m-%dT%H:%M:%SZ"), "items": todos}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"Guardados {len(todos)} titulares ({fallos} medios sin respuesta)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "prensa.json"))
