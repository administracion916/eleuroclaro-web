"""Guarda en datos/ipc-grupos.json la variación anual del IPC por grupos (último mes publicado por el INE).

Lo ejecuta cada mañana .github/workflows/ine.yml. Usa la API pública del INE (servicios.ine.es/wstempus):
busca entre las tablas de la operación IPC la de «índices nacionales: general y de grupos» y se queda con
las series de variación anual del total nacional. Lo usa la calculadora /inflacion/.
Si algo no cuadra (menos de 12 grupos, sin índice general o cifras fuera de rango), no escribe nada y
termina con error, para que la web siga con el último dato bueno.
Uso: python3 scripts/ine_ipc.py datos/ipc-grupos.json
"""
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

API = "https://servicios.ine.es/wstempus/js/ES/"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


REGISTRO = []


def log(texto):
    """Escribe en el registro de la tarea y lo guarda para el resumen (anotación de GitHub)."""
    print(texto)
    REGISTRO.append(str(texto))


def resumen():
    if REGISTRO:
        print("::notice title=INE IPC::" + "%0A".join(x.replace("%", "%25").replace("\n", " ") for x in REGISTRO[-60:]))


def leer(ruta):
    for intento in range(3):
        try:
            req = urllib.request.Request(API + ruta, headers={"User-Agent": "eleuroclaro.es (datos del IPC)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            log(f"Aviso: {ruta}: {e}")
            time.sleep(5 * (intento + 1))
    raise SystemExit(f"No se pudo leer {ruta}")


def candidatas():
    tablas = leer("TABLAS_OPERACION/IPC")
    out = []
    for t in tablas:
        n = (t.get("Nombre") or "").lower()
        if "grupos" in n and "nacional" in n and "subgrupos" not in n and "especial" not in n and "ponderac" not in n:
            out.append(t)
    log(f"Tablas del IPC: {len(tablas)}; candidatas:")
    for t in out:
        log(f"  {t.get('Id')}: {t.get('Nombre')}")
    if not out:
        for t in tablas[:40]:
            log(f"  (todas) {t.get('Id')}: {t.get('Nombre')}")
    # Las más nuevas primero: con el cambio de base, la tabla vigente es la de Id más alto.
    return sorted(out, key=lambda t: int(t.get("Id") or 0), reverse=True)


def extraer(tabla_id):
    """Devuelve (general, periodo, grupos) del último mes en que el INE da el general y al menos 12 grupos.

    Los nombres de las series son del tipo «Nacional. Alimentos y bebidas no alcohólicas. Variación anual.»
    (sin código de grupo): el código se pone por el orden en que los da el INE, que es el de la ECOICOP.
    """
    series = leer(f"DATOS_TABLA/{tabla_id}?nult=3")
    log(f"Tabla {tabla_id}: {len(series)} series; ejemplos: " + " | ".join((s.get("Nombre") or "")[:70] for s in series[:4]))
    general, grupos = {}, []
    for s in series:
        partes = [x.strip() for x in (s.get("Nombre") or "").split(".") if x.strip()]
        if len(partes) != 3 or partes[0] not in ("Nacional", "Total Nacional") or partes[2] != "Variación anual":
            continue
        valores = {}
        for d in s.get("Data") or []:
            if d.get("Valor") is None or not 1 <= int(d.get("FK_Periodo") or 0) <= 12:
                continue
            valores[(int(d["Anyo"]), int(d["FK_Periodo"]))] = round(float(d["Valor"]), 1)
        if partes[1].lower() == "índice general":
            general = valores
        else:
            grupos.append((partes[1], valores))
    periodos = sorted({p for _, v in grupos for p in v} & set(general), reverse=True)
    for p in periodos:
        lista = [{"codigo": f"{i + 1:02d}", "nombre": n, "tasa": v[p]} for i, (n, v) in enumerate(grupos) if p in v]
        if len(lista) >= 12 and len(lista) == len(grupos):
            return general[p], p, lista
    return (general[max(general)] if general else None), None, []


def main():
    salida = sys.argv[1]
    for t in candidatas():
        try:
            general, periodo, grupos = extraer(t["Id"])
        except SystemExit as e:
            log(f"Tabla {t['Id']}: {e}")
            continue
        log(f"Tabla {t['Id']}: general={general} periodo={periodo} grupos={len(grupos)}")
        if general is None or len(grupos) < 12:
            continue
        lista = grupos
        if len(lista) < 12 or not all(-30 < g["tasa"] < 60 for g in lista) or not -10 < general < 30:
            log("  Descartada: grupos de otro mes o cifras fuera de rango")
            continue
        anyo, mes = periodo
        datos = {
            "actualizado": datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d"),
            "periodo": f"{MESES[mes - 1]} de {anyo}",
            "anyo": anyo,
            "mes": mes,
            "general": general,
            "grupos": lista,
            "fuente": f"INE, Índice de Precios de Consumo, variación anual por grupos (tabla {t['Id']})",
            "tabla": t["Id"],
        }
        for g in datos["grupos"]:
            log(f"  {g['codigo']} {g['nombre']}: {g['tasa']} %")
        with open(salida, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
            f.write("\n")
        log(f"Guardado {salida}: {datos['periodo']}, general {general} %")
        return
    raise SystemExit("Ninguna tabla del IPC por grupos ha pasado las comprobaciones")


if __name__ == "__main__":
    try:
        main()
    finally:
        resumen()
