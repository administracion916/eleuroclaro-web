"""Guarda en prensa.json los últimos titulares de prensa económica (titular, medio, enlace y hora).

Lo ejecuta cada hora .github/workflows/prensa.yml. Solo se guarda el titular y el enlace a la web
del medio, nunca el texto de la noticia. Se quitan las noticias de criptomonedas y las que
parecen recomendaciones de inversión, porque El Euro Claro no recomienda invertir.
Uso: python3 scripts/prensa.py prensa.json
"""
import email.utils
import html
import json
import re
import sys
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

FUENTES = [
    ("Expansión", "https://e00-expansion.uecdn.es/rss/economia.xml"),
    ("Cinco Días", "https://feeds.elpais.com/mrss-s/pages/ep/site/cincodias.elpais.com/section/economia/portada"),
    ("elEconomista", "https://www.eleconomista.es/rss/rss-economia.php"),
    ("Europa Press", "https://www.europapress.es/rss/rss.aspx?ch=00136"),
    ("El País", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada"),
    ("RTVE", "https://api2.rtve.es/rss/temas_economia.xml"),
]
POR_MEDIO = 2
TOTAL = 8
HORAS = 36

FUERA = re.compile(
    r"cripto|bitcoin|\bbtc\b|ethereum|\bether\b|blockchain|\bnft|binance|coinbase|stablecoin|memecoin|"
    r"dogecoin|solana|\btokens?\b|qué comprar|dónde invertir|invertir en|valores para|acciones para|"
    r"recomienda comprar|cartera modelo|precio objetivo|dividendo|\btrading\b|forex|bróker|broker|horóscopo|sorteo|lotería|"
    r"neoliberal|izquierda|derecha|en directo",
    re.I,
)
# El medio se saca del enlace: algunos RSS mezclan noticias de otras cabeceras del mismo grupo.
MEDIOS = {
    "cincodias.elpais.com": "Cinco Días",
    "elpais.com": "El País",
    "expansion.com": "Expansión",
    "eleconomista.es": "elEconomista",
    "europapress.es": "Europa Press",
    "rtve.es": "RTVE",
}
UA = "Mozilla/5.0 (compatible; ElEuroClaro/1.0; +https://eleuroclaro.es)"


def texto(el, *nombres):
    for n in nombres:
        x = el.find(n)
        if x is not None and (x.text or "").strip():
            return x.text.strip()
        for hijo in el:
            if hijo.tag.split("}")[-1] == n and (hijo.text or "").strip():
                return hijo.text.strip()
    return ""


def fecha(s):
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def medio_de(enlace, por_defecto):
    host = urllib.parse.urlsplit(enlace).hostname or ""
    for dominio, nombre in MEDIOS.items():
        if host == dominio or host.endswith("." + dominio):
            return nombre
    return por_defecto


def limpio(t):
    t = re.sub(r"<[^>]+>", " ", html.unescape(t))
    t = re.sub(r"\s+", " ", t).strip()
    t = t.split(" | ")[0].strip()
    return t if len(t) <= 160 else t[:157].rsplit(" ", 1)[0] + "…"


def leer(medio, url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raiz = ET.fromstring(r.read())
    items = [e for e in raiz.iter() if e.tag.split("}")[-1] in ("item", "entry")]
    out = []
    for e in items:
        t = limpio(texto(e, "title"))
        enlace = texto(e, "link")
        if not enlace:
            for hijo in e:
                if hijo.tag.split("}")[-1] == "link" and hijo.get("href"):
                    enlace = hijo.get("href")
                    break
        enlace = enlace.strip()
        if enlace.startswith("http://"):
            enlace = "https://" + enlace[len("http://"):]
        d = fecha(texto(e, "pubDate", "published", "updated", "date"))
        if not t or not enlace.startswith("https://") or d is None:
            continue
        if FUERA.search(t) or "/opinion/" in enlace:
            continue
        out.append({"t": t, "m": medio_de(enlace, medio), "u": enlace, "f": d.strftime("%Y-%m-%dT%H:%M:%SZ")})
    return out


def main(destino):
    ahora = datetime.now(timezone.utc)
    limite = ahora - timedelta(hours=HORAS)
    todos, vistos, cuenta, fallos = [], set(), {}, 0
    for medio, url in FUENTES:
        try:
            items = leer(medio, url)
        except Exception as e:  # noqa: BLE001 — un medio caído no debe parar a los demás
            fallos += 1
            print(f"AVISO {medio}: {type(e).__name__}: {e}")
            continue
        recientes = [i for i in items if limite <= fecha(i["f"]) <= ahora + timedelta(minutes=10)]
        recientes.sort(key=lambda i: i["f"], reverse=True)
        print(f"OK {medio}: {len(items)} titulares, {len(recientes)} de las últimas {HORAS} h")
        for i in recientes:
            clave = re.sub(r"\W+", "", i["t"].lower())[:60]
            if clave in vistos or cuenta.get(i["m"], 0) >= POR_MEDIO:
                continue
            vistos.add(clave)
            todos.append(i)
            cuenta[i["m"]] = cuenta.get(i["m"], 0) + 1
    if not todos:
        print("ERROR: ningún titular; se deja prensa.json como estaba")
        return 1
    todos.sort(key=lambda i: i["f"], reverse=True)
    todos = todos[:TOTAL]
    try:
        with open(destino, encoding="utf-8") as f:
            antes = json.load(f).get("items")
    except (OSError, ValueError):
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
