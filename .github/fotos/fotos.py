"""Fotos reales de uso libre para las noticias de prensa de la portada (una por tema).

Solo fotos con licencia CC0 o de dominio público (Openverse: https://openverse.org), que se pueden usar
sin pedir permiso ni citar al autor. Igualmente se guarda autor, licencia y enlace de cada una en creditos.json.
Nunca fotos de los periódicos.

  python3 fotos.py candidatas salida/        -> baja miniaturas de varias fotos por tema para elegir
  python3 fotos.py elegidas ids.json salida/ -> baja las elegidas ({"tema": "id de Openverse"}) a 960x540
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.openverse.org/v1/images/"
UA = "ElEuroClaro/1.0 (+https://eleuroclaro.es; hola@eleuroclaro.es)"
BUSQUEDAS = {
    "vivienda": ["apartment building facade balconies", "residential buildings street", "house keys"],
    "tipos": ["euro coins", "euro banknotes", "calculator mortgage"],
    "precios": ["supermarket shopping cart", "grocery store shelves", "fruit market prices"],
    "energia": ["electricity pylon", "power lines", "gas station fuel pump"],
    "empleo": ["construction worker", "office desk work", "factory workers"],
    "pensiones": ["elderly couple walking", "senior hands", "retirement savings"],
    "impuestos": ["calculator documents", "tax forms paperwork", "receipts calculator"],
    "bancos": ["bank building columns", "atm cash machine", "credit card payment"],
    "empresas": ["office buildings skyscrapers", "business district", "stock market screen"],
    "comercio": ["container ship port", "shipping containers cranes", "cargo port"],
    "economia": ["financial charts screen", "city skyline", "money growth chart"],
    "transporte": ["airplane airport", "train station platform", "highway traffic"],
    "tecnologia": ["circuit board microchip", "laptop code", "server room"],
    "general": ["newspapers", "newspaper coffee", "news paper stack"],
}


def pedir(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            print(f"  reintento {i + 1} {url[:90]}: {e}")
            time.sleep(4 * (i + 1))
    return None


def buscar(q):
    params = {"q": q, "license": "cc0,pdm", "category": "photograph", "mature": "false", "page_size": "20", "aspect_ratio": "wide,square"}
    datos = pedir(API + "?" + urllib.parse.urlencode(params))
    return json.loads(datos)["results"] if datos else []


def candidatas(salida, por_tema=9):
    meta = {}
    for tema, qs in BUSQUEDAS.items():
        os.makedirs(os.path.join(salida, tema), exist_ok=True)
        vistos, lista = set(), []
        for q in qs:
            for r in buscar(q):
                if r["id"] in vistos or (r.get("width") or 0) < 1000:
                    continue
                vistos.add(r["id"])
                lista.append(r)
            time.sleep(2)
        # Repartir entre búsquedas: las primeras de cada una
        lista = lista[: por_tema * 2]
        n = 0
        for r in lista:
            if n >= por_tema:
                break
            img = pedir(r["thumbnail"])
            if not img or len(img) < 3000:
                continue
            n += 1
            nombre = f"{n:02d}.jpg"
            with open(os.path.join(salida, tema, nombre), "wb") as f:
                f.write(img)
            meta.setdefault(tema, {})[nombre] = {k: r.get(k) for k in ("id", "title", "creator", "license", "license_version", "source", "foreign_landing_url", "url", "width", "height")}
        print(f"{tema}: {n} candidatas")
    with open(os.path.join(salida, "candidatas.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)


def elegidas(ids_json, salida):
    from PIL import Image, ImageOps
    import io
    ids = json.load(open(ids_json, encoding="utf-8"))
    os.makedirs(salida, exist_ok=True)
    creditos = {}
    for tema, ident in ids.items():
        info = json.loads(pedir(API + ident + "/") or b"{}")
        if info.get("license") not in ("cc0", "pdm"):
            print(f"::error::{tema}: {ident} no es CC0 ni dominio público ({info.get('license')})")
            continue
        datos = pedir(info["url"])
        if not datos:
            print(f"::error::{tema}: no se pudo bajar {info['url']}")
            continue
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(datos))).convert("RGB")
        im = ImageOps.fit(im, (960, 540), Image.LANCZOS, centering=(0.5, 0.5))
        im.save(os.path.join(salida, f"{tema}.jpg"), "JPEG", quality=78, optimize=True, progressive=True)
        creditos[tema] = {k: info.get(k) for k in ("id", "title", "creator", "license", "license_version", "source", "foreign_landing_url")}
        print(f"{tema}: OK ({info.get('source')}, {info.get('license')})")
    with open(os.path.join(salida, "creditos.json"), "w", encoding="utf-8") as f:
        json.dump(creditos, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    if sys.argv[1] == "candidatas":
        candidatas(sys.argv[2])
    else:
        elegidas(sys.argv[2], sys.argv[3])
