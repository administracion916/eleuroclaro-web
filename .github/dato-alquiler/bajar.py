"""Baja del INE los datos en bruto para el dato propio «Dónde te queda más dinero después de pagar el alquiler».

Lo lanza .github/workflows/dato-alquiler.yml; el resultado va a la rama «dato-alquiler» (no se publica).
Guarda: la lista de operaciones del INE que encajan, las tablas del Atlas de Distribución de Renta de los
Hogares (ADRH, «renta media y mediana» por provincia) y del Índice de Precios de Vivienda en Alquiler (IPVA),
solo con las series de municipio y provincia (sin secciones ni distritos, que pesan mucho).
Uso: python3 .github/dato-alquiler/bajar.py crudo
"""
import gzip
import json
import os
import sys
import time
import urllib.request

API = "https://servicios.ine.es/wstempus/js/ES/"


def leer(ruta, timeout=180):
    for intento in range(3):
        try:
            req = urllib.request.Request(API + ruta, headers={"User-Agent": "eleuroclaro.es (dato propio alquiler)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print(f"Aviso: {ruta}: {e}")
            time.sleep(5 * (intento + 1))
    return None


def guardar(carpeta, nombre, datos):
    with gzip.open(os.path.join(carpeta, nombre + ".gz"), "wt", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    print(f"{nombre}: {len(json.dumps(datos)) // 1024} KB")


def sin_secciones(series):
    if not isinstance(series, list):
        print(f"Aviso: respuesta que no es lista: {str(series)[:300]}")
        return series
    out = []
    for s in series:
        if not isinstance(s, dict):
            continue
        n = (s.get("Nombre") or "").lower()
        if "sección" in n or "seccion" in n or "distrito" in n:
            continue
        out.append(s)
    return out


def tablas_de(cods):
    for cod in cods:
        t = leer(f"TABLAS_OPERACION/{cod}")
        if t:
            return cod, t
    return None, []


def main(carpeta):
    os.makedirs(carpeta, exist_ok=True)
    ops = leer("OPERACIONES_DISPONIBLES") or []
    elegidas = [o for o in ops if any(k in (o.get("Nombre") or "").lower() for k in ("renta de los hogares", "alquiler", "distribución de renta"))]
    guardar(carpeta, "operaciones.json", elegidas)
    print("Operaciones:", [(o.get("Id"), o.get("Codigo"), o.get("Nombre")) for o in elegidas])

    cods_adrh = ["ADRH"] + [str(o.get("Id")) for o in elegidas if "renta" in (o.get("Nombre") or "").lower()]
    cods_ipva = ["IPVA"] + [str(o.get("Id")) for o in elegidas if "alquiler" in (o.get("Nombre") or "").lower()]

    cod, adrh = tablas_de(cods_adrh)
    guardar(carpeta, "adrh_tablas.json", adrh)
    print(f"ADRH ({cod}): {len(adrh)} tablas")
    for t in adrh:
        n = (t.get("Nombre") or "").lower()
        if "media y mediana" in n or ("renta" in n and "media" in n and "fuente" not in n):
            datos = leer(f"DATOS_TABLA/{t['Id']}?nult=4", timeout=300)
            guardar(carpeta, f"adrh_{t['Id']}.json", {"tabla": t, "series": sin_secciones(datos)})

    cod, ipva = tablas_de(cods_ipva)
    guardar(carpeta, "ipva_tablas.json", ipva)
    print(f"IPVA ({cod}): {len(ipva)} tablas")
    for t in ipva:
        datos = leer(f"DATOS_TABLA/{t['Id']}?nult=4", timeout=300)
        guardar(carpeta, f"ipva_{t['Id']}.json", {"tabla": t, "series": sin_secciones(datos)})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "crudo")
