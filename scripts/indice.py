"""Índice del Bolsillo: cuánto suben los precios en un año según la edad de quien más aporta al hogar.

Cálculo propio de El Euro Claro, solo con datos del INE:
- IPC por grupos ECOICOP v2 (tabla 79181: índices y tasas) y sus ponderaciones oficiales (tabla 79185).
- Encuesta de Presupuestos Familiares (EPF): reparto del gasto por grupos según la edad del sustentador
  principal (tabla 73801) y peso de los alquileres imputados, que el IPC no incluye (tabla 73815).

Método: a cada grupo del IPC se le da el peso oficial multiplicado por lo que ese tramo de edad gasta en el
grupo comparado con el conjunto de hogares (EPF, sin alquileres imputados). Con esos pesos se encadena el
índice como el IPC (desde diciembre del año anterior con los pesos de este año y, para el tramo del año
anterior, con la EPF de un año antes) y se aplica la diferencia con la cesta oficial a la tasa anual oficial.
Para todos los hogares sale exactamente el IPC general.
Prueba antes de escribir nada: con las ponderaciones oficiales, el encadenamiento de los grupos tiene que dar
la tasa anual del IPC general de cada mes del año con 0,1 puntos de diferencia como mucho. Si no la da,
termina con error y la web sigue con el último dato bueno.

Lo ejecuta .github/workflows/ine.yml cada mañana (y se puede lanzar a mano).
Uso: python3 scripts/indice.py datos/indice-bolsillo.json indice-del-bolsillo/index.html [carpeta con JSON del INE]
Sin carpeta, lee la API del INE (servicios.ine.es/wstempus).
"""
import html
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

API = "https://servicios.ine.es/wstempus/js/ES/"
TABLAS = {"ipc": (79181, 30), "pesos": (79185, 1), "epf": (73801, 3), "epf_sub": (73815, 3)}
MAX_ERROR = 0.1
PUBLICO = False  # Hasta el estreno en la newsletter nº 3 (25-10-2026): sin indexar ni enlazar.

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]
TODAS = "Todas las edades"
EDADES = [("De 16 a 29 años", "De 16 a 29 años"), ("De 30 a 44 años", "De 30 a 44 años"),
          ("De 45 a 64 años", "De 45 a 64 años"), ("65 y más años", "65 años o más")]
TITULAR = "De 30 a 44 años"
# (nombre corto para la web, nombres en las tablas del INE: IPC, ponderaciones y EPF)
GRUPOS = [
    ("Comida y bebida", ["Alimentos y bebidas no alcohólicas"]),
    ("Alcohol y tabaco", ["Bebidas alcohólicas y tabaco", "Bebidas alcohólicas, tabaco y estupefacientes"]),
    ("Ropa y calzado", ["Vestido y calzado"]),
    ("Casa: alquiler, luz, gas y agua", ["Vivienda, agua, electricidad, gas y otros combustibles"]),
    ("Muebles y hogar", ["Muebles, artículos del hogar y artículos para el mantenimiento corriente del hogar"]),
    ("Salud", ["Sanidad"]),
    ("Transporte", ["Transporte"]),
    ("Móvil, internet y ordenadores", ["Información y comunicaciones"]),
    ("Ocio, deporte y cultura", ["Actividades recreativas, deporte y cultura"]),
    ("Educación", ["Enseñanza", "Servicios de educación"]),
    ("Restaurantes y hoteles", ["Restaurantes y servicios de alojamiento"]),
    ("Seguros y banca", ["Seguros y servicios financieros"]),
    ("Cuidado personal y otros", ["Cuidado personal, protección social, y bienes y servicios diversos"]),
]


def log(texto):
    print(texto)


def leer(ruta):
    for intento in range(3):
        try:
            req = urllib.request.Request(API + ruta, headers={"User-Agent": "eleuroclaro.es (Índice del Bolsillo)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            log(f"Aviso: {ruta}: {e}")
            time.sleep(5 * (intento + 1))
    raise SystemExit(f"No se pudo leer {ruta}")


def cargar(carpeta):
    out = {}
    for clave, (tid, nult) in TABLAS.items():
        if carpeta:
            nombre = {"ipc": f"ipc_{tid}.json", "pesos": f"ipc_pond_{tid}.json"}.get(clave, f"epf_{tid}.json")
            out[clave] = json.load(open(os.path.join(carpeta, nombre), encoding="utf-8"))
        else:
            out[clave] = leer(f"DATOS_TABLA/{tid}?nult={nult}")
    return out


def partes(serie):
    return [p.strip() for p in serie["Nombre"].strip().rstrip(".").split(". ")]


def grupo_de(nombre):
    for i, (_, alias) in enumerate(GRUPOS):
        if nombre in alias:
            return i
    return None


def num(x, dec=1):
    q = Decimal(str(round(x, 6))).quantize(Decimal(1).scaleb(-dec), rounding=ROUND_HALF_UP)
    s = f"{q:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "0,0" if s in ("-0,0",) else s


def r1(x):
    return float(Decimal(str(round(x, 6))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def preparar(t):
    # IPC: índices y tasas anuales por grupo y del general
    idx = [dict() for _ in GRUPOS]
    tasa = [dict() for _ in GRUPOS]
    ig, rg = {}, {}
    for s in t["ipc"]:
        p = partes(s)
        if len(p) < 3:
            continue
        datos = {(x["Anyo"], x["FK_Periodo"]): x["Valor"] for x in s["Data"] if x.get("Valor") is not None}
        if p[1] == "Índice general":
            if p[2] == "Índice":
                ig = datos
            elif p[2] == "Variación anual":
                rg = datos
            continue
        g = grupo_de(p[1])
        if g is None:
            continue
        if p[2] == "Índice":
            idx[g] = datos
        elif p[2] == "Variación anual":
            tasa[g] = datos
    if not ig or not rg or any(not d for d in idx):
        raise SystemExit("Faltan series del IPC por grupos")
    # Ponderaciones oficiales del año más reciente
    pesos, anyo_pesos = [None] * len(GRUPOS), None
    for s in t["pesos"]:
        p = partes(s)
        g = grupo_de(p[1]) if len(p) > 1 else None
        if g is None or not s["Data"]:
            continue
        ult = max(s["Data"], key=lambda x: x["Anyo"])
        pesos[g], anyo_pesos = ult["Valor"], ult["Anyo"]
    if None in pesos or abs(sum(pesos) - 1000) > 1:
        raise SystemExit(f"Ponderaciones incompletas: {pesos}")
    # EPF: reparto del gasto (%) por edad y grupo, y alquileres imputados por edad
    epf, imp = {}, {}
    for s in t["epf"]:
        p = partes(s)
        if len(p) < 4 or p[0] != "Total" or p[2] != "Distribución porcentual":
            continue
        g = grupo_de(p[3])
        if g is None:
            continue
        for x in s["Data"]:
            epf[(p[1], x["Anyo"], g)] = x["Valor"]
    for s in t["epf_sub"]:
        p = partes(s)
        if len(p) >= 3 and p[0] == "Total" and p[2] == "Alquileres imputados de la vivienda":
            for x in s["Data"]:
                imp[(p[1], x["Anyo"])] = x["Valor"]
    return idx, tasa, ig, rg, pesos, anyo_pesos, epf, imp


def main():
    salida_json, salida_html = sys.argv[1], sys.argv[2]
    carpeta = sys.argv[3] if len(sys.argv) > 3 else None
    idx, tasa, ig, rg, W, anyo_pesos, epf, imp = preparar(cargar(carpeta))

    # Meses que se pueden calcular: los del año de las ponderaciones con todos los grupos publicados
    Y = anyo_pesos
    meses = [m for m in range(1, 13) if all((Y, m) in d for d in idx) and (Y, m) in rg]
    necesarios = [(Y - 1, 12), (Y - 2, 12)] + [(Y - 1, m) for m in meses]
    if not meses or any(p not in d for d in idx for p in necesarios):
        raise SystemExit(f"Faltan índices para {Y}: meses {meses}")
    anyos_epf = sorted({a for (_, a, _) in epf})
    e1 = max([a for a in anyos_epf if a <= Y - 1] or [None])
    e0 = max([a for a in anyos_epf if a <= Y - 2] or [e1])
    if e1 is None:
        raise SystemExit("No hay EPF para el año anterior")

    def pesos_edad(edad, anyo):
        if edad == TODAS:
            return list(W)
        def reparto(e):
            v = [epf[(e, anyo, g)] for g in range(len(GRUPOS))]
            v[3] -= imp[(e, anyo)]  # el IPC no incluye los alquileres imputados
            tot = sum(v)
            return [x / tot for x in v]
        a, todas = reparto(edad), reparto(TODAS)
        return [w * x / y for w, x, y in zip(W, a, todas)]

    def cesta_anyo(w, m):
        return sum(x * idx[g][(Y, m)] / idx[g][(Y - 1, 12)] for g, x in enumerate(w)) / sum(w)

    def cesta_previa(w, m):
        num_ = sum(x * idx[g][(Y - 1, 12)] / idx[g][(Y - 2, 12)] for g, x in enumerate(w))
        den = sum(x * idx[g][(Y - 1, m)] / idx[g][(Y - 2, 12)] for g, x in enumerate(w))
        return num_ / den

    # Prueba: con las ponderaciones oficiales tiene que salir el IPC general del INE
    errores = {}
    for m in meses:
        calc = (ig[(Y - 1, 12)] / ig[(Y - 1, m)] * cesta_anyo(W, m) - 1) * 100
        errores[m] = calc - rg[(Y, m)]
        log(f"Prueba {MESES[m - 1]} {Y}: calculado {calc:.3f} %, INE {rg[(Y, m)]} %, diferencia {errores[m]:+.3f}")
    peor = max(abs(e) for e in errores.values())
    if peor > MAX_ERROR:
        raise SystemExit(f"No cuadra con el IPC oficial: diferencia de {peor:.3f} puntos (máximo {MAX_ERROR}). No se publica.")

    def bolsillo(edad, m):
        w1, w0 = pesos_edad(edad, e1), pesos_edad(edad, e0)
        f = (cesta_anyo(w1, m) / cesta_anyo(W, m)) * (cesta_previa(w0, m) / cesta_previa(W, m))
        return ((1 + rg[(Y, m)] / 100) * f - 1) * 100

    serie = []
    for m in meses:
        serie.append({"anyo": Y, "mes": m, "ipc": rg[(Y, m)],
                      "edades": {e: r1(bolsillo(e, m)) for e, _ in EDADES},
                      "exacto": {e: round(bolsillo(e, m), 3) for e, _ in EDADES}})
    ult = serie[-1]
    m = ult["mes"]
    wt = pesos_edad(TITULAR, e1)
    tot = sum(wt)
    aportes = sorted(((GRUPOS[g][0], wt[g] / tot * 1000, W[g], tasa[g].get((Y, m))) for g in range(len(GRUPOS))),
                     key=lambda z: -(z[1] * (z[3] or 0)))
    periodo = f"{MESES[m - 1]} de {Y}"
    ahora = datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Madrid"))
    datos = {
        "actualizado": ahora.strftime("%Y-%m-%d %H:%M"),
        "periodo": periodo, "anyo": Y, "mes": m,
        "ipc": ult["ipc"], "edades": ult["edades"],
        "titular": {"edad": TITULAR, "tasa": ult["edades"][TITULAR],
                    "grupos": [a[0] for a in aportes[:2]]},
        "grupos_titular": [{"grupo": a[0], "peso": round(a[1], 1), "peso_ipc": round(a[2], 1), "tasa": a[3]}
                           for a in aportes],
        "serie": serie,
        "prueba": {"max_diferencia": round(peor, 3), "meses": len(meses)},
        "fuentes": {"ipc": "INE, IPC base 2025, tablas 79181 y 79185",
                    "epf": f"INE, Encuesta de Presupuestos Familiares {e1} (y {e0} para el año anterior), tablas 73801 y 73815"},
        "nota": "Cálculo propio de El Euro Claro con datos del INE. No es una estadística oficial.",
    }
    try:
        previo = json.load(open(salida_json, encoding="utf-8"))
        previo["actualizado"] = datos["actualizado"]
        if previo == datos and os.path.exists(salida_html):
            log(f"Índice del Bolsillo {periodo}: sin cambios")
            return
    except (OSError, ValueError):
        pass
    os.makedirs(os.path.dirname(salida_json) or ".", exist_ok=True)
    with open(salida_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(salida_html) or ".", exist_ok=True)
    with open(salida_html, "w", encoding="utf-8") as f:
        f.write(pagina(datos, e1))
    log(f"Índice del Bolsillo {periodo}: {TITULAR} {num(ult['edades'][TITULAR])} % · IPC {num(ult['ipc'])} % · "
        f"prueba {peor:.3f} · " + ", ".join(f"{e} {num(v)}" for e, v in ult["edades"].items()))


def pagina(d, anyo_epf):
    tit = d["titular"]
    ipc = d["ipc"]
    dif = tit["tasa"] - ipc
    if abs(dif) < 0.05:
        frente = "lo mismo que el IPC general"
    else:
        frente = f"{num(abs(dif))} {'punto' if num(abs(dif)) == '1,0' else 'puntos'} {'más' if dif > 0 else 'menos'} que el IPC general"
    maximo = max(list(d["edades"].values()) + [ipc, 0.1])
    filas_edad = []
    for e, corto in EDADES:
        v = d["edades"][e]
        clase = ' class="ib-tit"' if e == TITULAR else ""
        ancho = max(2, round(max(v, 0) / maximo * 100))
        filas_edad.append(
            f'          <tr{clase}><th scope="row">{corto}</th><td class="num"><strong>{num(v)}&nbsp;%</strong></td>'
            f'<td class="ib-barra" aria-hidden="true"><span style="width:{ancho}%"></span></td></tr>')
    filas_edad.append(
        f'          <tr class="ib-ipc"><th scope="row">IPC general (INE)</th><td class="num"><strong>{num(ipc)}&nbsp;%</strong></td>'
        f'<td class="ib-barra" aria-hidden="true"><span style="width:{max(2, round(max(ipc, 0) / maximo * 100))}%"></span></td></tr>')
    filas_grupos = []
    for g in d["grupos_titular"]:
        t = "" if g["tasa"] is None else f"{'+' if g['tasa'] > 0 else ''}{num(g['tasa'])}&nbsp;%"
        filas_grupos.append(f'          <tr><td>{html.escape(g["grupo"])}</td><td class="num">{t}</td>'
                            f'<td class="num">{num(g["peso"] / 10)}&nbsp;%</td><td class="num">{num(g["peso_ipc"] / 10)}&nbsp;%</td></tr>')
    filas_serie = []
    for s in reversed(d["serie"]):
        celdas = "".join(f'<td class="num">{num(s["edades"][e])}&nbsp;%</td>' for e, _ in EDADES)
        filas_serie.append(f'          <tr><td>{MESES[s["mes"] - 1].capitalize()} {s["anyo"]}</td>'
                           f'<td class="num">{num(s["ipc"])}&nbsp;%</td>{celdas}</tr>')
    cab_serie = "".join(f'<th class="num">{c}</th>' for _, c in EDADES)
    g1, g2 = tit["grupos"]
    resumen = (f"En {d['periodo']}, a un hogar en el que quien más aporta tiene de 30 a 44 años los precios le han "
               f"subido un {num(tit['tasa'])} % en un año, {frente} ({num(ipc)} %). Lo que más pesa: "
               f"{g1.lower()} y {g2.lower()}.")
    robots = "" if PUBLICO else '\n<meta name="robots" content="noindex">'
    return PLANTILLA.format(
        periodo=d["periodo"], tasa=num(tit["tasa"]), ipc=num(ipc), frente=frente, resumen=html.escape(resumen),
        filas_edad="\n".join(filas_edad), filas_grupos="\n".join(filas_grupos),
        filas_serie="\n".join(filas_serie), cab_serie=cab_serie, anyo=d["anyo"], anyo_epf=anyo_epf,
        prueba=num(d["prueba"]["max_diferencia"], 2), n_meses=d["prueba"]["meses"],
        g1=html.escape(g1.lower()), g2=html.escape(g2.lower()), robots=robots,
        actualizado=html.escape(d["actualizado"]),
    )


PLANTILLA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Índice del Bolsillo: cuánto te suben los precios según tu edad · El Euro Claro</title>
<meta name="description" content="{resumen}">{robots}
<meta name="theme-color" content="#0e2a47">
<meta property="og:site_name" content="El Euro Claro">
<meta property="og:title" content="Índice del Bolsillo: a los hogares de 30 a 44 años los precios les suben un {tasa} %">
<meta property="og:description" content="{resumen}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://eleuroclaro.es/indice-del-bolsillo/">
<meta property="og:locale" content="es_ES">
<meta property="og:image" content="https://eleuroclaro.es/img/og-inflacion.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="https://eleuroclaro.es/indice-del-bolsillo/">
<!-- Página generada por scripts/indice.py: no editar a mano. -->
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
      <p class="eyebrow">Índice del Bolsillo · {periodo}</p>
      <h1>¿Cuánto te suben los precios <em>a ti</em>?</h1>
      <p class="intro">El IPC es la media de todos los hogares. Pero no gasta igual una pareja de 35 años que paga alquiler que una persona jubilada. Este índice mide la subida de precios según la edad de quien más aporta al hogar.</p>
      <div class="datos-pareja ib-cifras">
        <div class="dato"><p class="que">Hogares de 30 a 44 años</p><p class="cifra">{tasa}&nbsp;%</p><p class="src">en un año, {frente}</p></div>
        <div class="dato dato-gris"><p class="que">IPC general (INE)</p><p class="cifra">{ipc}&nbsp;%</p><p class="src">la media de todos los hogares</p></div>
      </div>
      <p>Lo que más pesa en un hogar de 30 a 44 años: <strong>{g1}</strong> y <strong>{g2}</strong>.</p>
      <div class="actions"><a class="btn btn-sol" href="/inflacion/">Calcula el tuyo con lo que gastas</a></div>
    </div>
  </section>

  <section class="section alt" aria-labelledby="por-edad">
    <div class="wrap prose">
      <h2 id="por-edad">Según la edad, en {periodo}</h2>
      <p>Subida de los precios en un año para cada tipo de hogar, según la edad de quien más ingresos aporta.</p>
      <div class="tablebox">
        <table class="tabla ib-tabla">
          <thead><tr><th>Edad</th><th class="num">Subida</th><th><span class="sr">Gráfico</span></th></tr></thead>
          <tbody>
{filas_edad}
          </tbody>
        </table>
      </div>
      <p class="small">El dato de 16 a 29 años tiene más margen de error: en la encuesta hay pocos hogares de esa edad.</p>
    </div>
  </section>

  <section class="section" aria-labelledby="grupos">
    <div class="wrap prose">
      <h2 id="grupos">En qué se va el dinero de un hogar de 30 a 44 años</h2>
      <p>Cuánto ha subido cada grupo en un año y qué parte del gasto se lleva, frente a la media que usa el IPC. Ordenado por lo que más empuja la subida.</p>
      <div class="tablebox">
        <table class="tabla">
          <thead><tr><th>Grupo</th><th class="num">Subida en un año</th><th class="num">Peso, 30 a 44 años</th><th class="num">Peso en el IPC</th></tr></thead>
          <tbody>
{filas_grupos}
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <section class="section alt" aria-labelledby="serie">
    <div class="wrap prose">
      <h2 id="serie">Mes a mes</h2>
      <div class="tablebox">
        <table class="tabla">
          <thead><tr><th>Mes</th><th class="num">IPC</th>{cab_serie}</tr></thead>
          <tbody>
{filas_serie}
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <section class="section" aria-labelledby="metodo">
    <div class="wrap prose">
      <h2 id="metodo">Cómo se calcula</h2>
      <p>Solo con datos del INE. Partimos de la subida de precios de cada uno de los 13 grupos del IPC y de lo que pesa cada grupo en la cesta oficial. Después, con la Encuesta de Presupuestos Familiares de {anyo_epf}, vemos cuánto gasta en cada grupo un hogar de cada edad frente a la media, y ajustamos los pesos en esa proporción. No contamos el «alquiler imputado» (lo que pagaría de alquiler quien vive en su casa), porque el IPC tampoco lo cuenta.</p>
      <p>Comprobación: con los pesos oficiales, nuestro cálculo da el IPC general del INE en los {n_meses} meses de {anyo} con una diferencia máxima de {prueba} puntos. Si un mes pasara de 0,1 puntos, no lo publicaríamos.</p>
      <p>Fuentes: INE, <a href="https://www.ine.es/dynt3/inebase/es/index.htm?padre=12722" rel="noopener">Índice de Precios de Consumo</a> (base 2025, grupos ECOICOP) y <a href="https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&amp;cid=1254736176806&amp;menu=ultiDatos&amp;idp=1254735976608" rel="noopener">Encuesta de Presupuestos Familiares</a>. Se actualiza solo cada vez que el INE publica el IPC. Última revisión: {actualizado}.</p>
      <p class="small note-legal">Cálculo propio de El Euro Claro con datos del INE. No es una estadística oficial.</p>
    </div>
  </section>

  <section class="section alt" id="newsletter" aria-labelledby="nl-tit">
    <div class="wrap news">
      <div>
        <p class="eyebrow">Newsletter · domingos · gratis</p>
        <h2 id="nl-tit">El Índice del Bolsillo, cada mes en tu correo</h2>
        <p class="intro">Y cada domingo, en 3 minutos, lo que cambia en tu bolsillo, con ejemplos en euros.</p>
        <p class="regalo">De regalo al apuntarte: la guía de una página <strong>«Cómo leer tu nómina en 2 minutos»</strong>.</p>
      </div>
      <form class="signup" data-campana="indice" novalidate>
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
<script src="/suscribir.js?v=20261010c" defer></script>
<!-- Cloudflare Web Analytics --><script defer src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon='{{"token": "e81aecc33a6b40ccab86c1fbc9fa801c"}}'></script><!-- End Cloudflare Web Analytics -->
</body>
</html>
"""


if __name__ == "__main__":
    main()
