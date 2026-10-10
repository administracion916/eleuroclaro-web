"""Baja del INE los datos en bruto para el Índice del Bolsillo y los deja en la carpeta que se le pase.

Lo lanza a mano .github/workflows/indice.yml; el resultado va a la rama «indice» (no se publica).
Guarda: la lista de tablas del IPC y de la EPF, las tablas de ponderaciones del IPC por grupos,
la tabla 79181 (índices y tasas del IPC por grupos) y las tablas de la EPF por edad del sustentador principal.
Uso: python3 .github/indice/bajar.py crudo
"""
import json
import os
import sys
import time
import urllib.request

API = "https://servicios.ine.es/wstempus/js/ES/"


def leer(ruta):
    for intento in range(3):
        try:
            req = urllib.request.Request(API + ruta, headers={"User-Agent": "eleuroclaro.es (Índice del Bolsillo)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print(f"Aviso: {ruta}: {e}")
            time.sleep(5 * (intento + 1))
    return None


def guardar(carpeta, nombre, datos):
    with open(os.path.join(carpeta, nombre), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    print(f"{nombre}: {len(json.dumps(datos)) // 1024} KB")


def main(carpeta):
    os.makedirs(carpeta, exist_ok=True)
    ipc = leer("TABLAS_OPERACION/IPC") or []
    guardar(carpeta, "ipc_tablas.json", ipc)
    for t in ipc:
        n = (t.get("Nombre") or "").lower()
        if "ponderac" in n and "grupo" in n:
            guardar(carpeta, f"ipc_pond_{t['Id']}.json", leer(f"DATOS_TABLA/{t['Id']}?nult=3"))
    guardar(carpeta, "ipc_79181.json", leer("DATOS_TABLA/79181?nult=40"))
    epf = None
    for cod in ("EPF", "30458"):
        epf = leer(f"TABLAS_OPERACION/{cod}")
        if epf:
            break
    guardar(carpeta, "epf_tablas.json", epf or [])
    for t in epf or []:
        n = (t.get("Nombre") or "").lower()
        if "edad" in n or "monetario" in n or t["Id"] in (73779, 73782):
            guardar(carpeta, f"epf_{t['Id']}.json", leer(f"DATOS_TABLA/{t['Id']}?nult=2"))


if __name__ == "__main__":
    main(sys.argv[1])
