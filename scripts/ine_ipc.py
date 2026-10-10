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


def leer(ruta):
    for intento in range(3):
        try:
            req = urllib.request.Request(API + ruta, headers={"User-Agent": "eleuroclaro.es (datos del IPC)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print(f"Aviso: {ruta}: {e}", file=sys.stderr)
            time.sleep(5 * (intento + 1))
    raise SystemExit(f"No se pudo leer {ruta}")


def candidatas():
    tablas = leer("TABLAS_OPERACION/IPC")
    out = []
    for t in tablas:
        n = (t.get("Nombre") or "").lower()
        if "grupos" in n and "nacional" in n and "subgrupos" not in n and "especial" not in n and "ponderac" not in n:
            out.append(t)
    print("Tablas candidatas:")
    for t in out:
        print(f"  {t.get('Id')}: {t.get('Nombre')} (última modificación {t.get('Ultima_Modificacion')})")
    # Las más nuevas primero: con el cambio de base, la tabla vigente es la de Id más alto.
    return sorted(out, key=lambda t: int(t.get("Id") or 0), reverse=True)


def extraer(tabla_id):
    series = leer(f"DATOS_TABLA/{tabla_id}?nult=1")
    general, grupos, periodo = None, {}, None
    for s in series:
        nombre = (s.get("Nombre") or "").strip()
        bajo = nombre.lower()
        if "variación anual" not in bajo or "nacional" not in bajo:
            continue
        datos = [d for d in (s.get("Data") or []) if d.get("Valor") is not None]
        if not datos:
            continue
        d = datos[-1]
        p = (int(d["Anyo"]), int(d["FK_Periodo"]))
        valor = round(float(d["Valor"]), 1)
        if "índice general" in bajo:
            general, periodo = valor, p
            continue
        m = re.search(r"\b(\d{2})\s+([^.]+)", nombre)
        if m:
            grupos[m.group(1)] = {"codigo": m.group(1), "nombre": m.group(2).strip(), "tasa": valor, "periodo": p}
    return general, periodo, grupos


def main():
    salida = sys.argv[1]
    for t in candidatas():
        general, periodo, grupos = extraer(t["Id"])
        print(f"Tabla {t['Id']}: general={general} periodo={periodo} grupos={len(grupos)}")
        if general is None or len(grupos) < 12:
            continue
        lista = [g for g in sorted(grupos.values(), key=lambda g: g["codigo"]) if g["periodo"] == periodo]
        if len(lista) < 12 or not all(-30 < g["tasa"] < 60 for g in lista) or not -10 < general < 30:
            print("  Descartada: grupos de otro mes o cifras fuera de rango")
            continue
        anyo, mes = periodo
        datos = {
            "actualizado": datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d"),
            "periodo": f"{MESES[mes - 1]} de {anyo}",
            "anyo": anyo,
            "mes": mes,
            "general": general,
            "grupos": [{"codigo": g["codigo"], "nombre": g["nombre"], "tasa": g["tasa"]} for g in lista],
            "fuente": f"INE, Índice de Precios de Consumo, variación anual por grupos (tabla {t['Id']})",
            "tabla": t["Id"],
        }
        for g in datos["grupos"]:
            print(f"  {g['codigo']} {g['nombre']}: {g['tasa']} %")
        with open(salida, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print(f"Guardado {salida}: {datos['periodo']}, general {general} %")
        return
    raise SystemExit("Ninguna tabla del IPC por grupos ha pasado las comprobaciones")


if __name__ == "__main__":
    main()
