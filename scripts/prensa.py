"""Guarda en prensa.json los últimos titulares de prensa económica (titular, medio, enlace y hora).

Lo ejecuta cada hora .github/workflows/prensa.yml. Solo se guarda el titular y el enlace a la web
del medio, nunca el texto de la noticia. Se quitan las noticias de criptomonedas, las que parecen
recomendaciones de inversión (El Euro Claro no recomienda invertir), los directos y los artículos
de opinión o ideológicos. Solo se aceptan enlaces a los dominios de MEDIOS.
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
    ("elEconomista", "https://www.eleconomista.es/rss/rss-economia.php"),
    ("Europa Press", "https://www.europapress.es/rss/rss.aspx?ch=00136"),
    ("El País", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada"),
    ("RTVE", "https://api2.rtve.es/rss/temas_economia.xml"),
]
# El medio se saca del enlace (algunos RSS mezclan noticias de otras cabeceras del grupo).
# Es también la lista de dominios permitidos: un enlace a cualquier otro sitio se descarta.
MEDIOS = {
    "cincodias.elpais.com": "Cinco Días",
    "elpais.com": "El País",
    "expansion.com": "Expansión",
    "eleconomista.es": "elEconomista",
    "europapress.es": "Europa Press",
    "rtve.es": "RTVE",
}
POR_MEDIO = 2
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
ETIQUETA = re.compile(r"^(mapa|v[ií]deo|video|gr[aá]fico|fotos?|podcast|infograf[ií]a|exclusiva|entrevista)$", re.I)
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
    if len(t) < 25:
        return ""
    return t if len(t) <= 160 else t[:157].rsplit(" ", 1)[0] + "…"


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


def leer(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raiz = analizar(r.read(5_000_000), r.headers.get_content_charset())
    out = []
    for e in raiz.iter():
        if e.tag.split("}")[-1] not in ("item", "entry"):
            continue
        enlace = enlace_de(e).strip()
        if enlace.startswith("http://"):
            enlace = "https://" + enlace[len("http://"):]
        if not enlace.startswith("https://") or RUTA_OPINION.search(enlace):
            continue
        medio = medio_de(enlace)
        categorias = " ".join(normal(h.text or h.get("term") or "") for n in ("category", "subject") for h in hijos(e, n))
        if medio is None or OPINION.search(categorias):
            continue
        t = titular(texto(e, "title"))
        d = fecha(texto(e, "pubDate", "published", "updated", "date"))
        if not t or d is None:
            continue
        out.append({"t": t, "m": medio, "u": enlace, "f": d.strftime("%Y-%m-%dT%H:%M:%SZ")})
    return out


def main(destino):
    ahora = datetime.now(timezone.utc)
    limite = ahora - timedelta(hours=HORAS)
    recientes, fallos = [], 0
    for nombre, url in FUENTES:
        try:
            items = leer(url)
        except Exception as e:  # noqa: BLE001 — un medio caído no debe parar a los demás
            fallos += 1
            print(f"::warning::AVISO {nombre}: {type(e).__name__}: {e}")
            continue
        validos = [i for i in items if limite <= fecha(i["f"]) <= ahora + timedelta(minutes=10)]
        print(f"OK {nombre}: {len(items)} titulares, {len(validos)} de las últimas {HORAS} h")
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
