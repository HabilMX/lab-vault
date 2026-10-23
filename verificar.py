#!/usr/bin/env python3
"""Verificador del laboratorio del curso «Vault desde cero» (Hábil).

Qué hace
--------
Revisa el laboratorio SIN levantar ningún contenedor. Nunca corre `docker compose up`: donde
hace falta correr iniciar.sh, lo corre en una copia temporal con un `docker` de mentira al
frente del PATH, que solo anota con qué argumentos lo llamaron.

Las comprobaciones, en orden:

1. Los archivos del laboratorio que lista manifiesto.json existen, y no hay una política o un
   rol que no esté en el manifiesto.
2. .gitignore tiene las seis reglas: .env, secretos-locales/, vault/data/, vault/logs/,
   postgres/ y mariadb/ (cada una como línea completa).
3. iniciar.sh tiene sintaxis válida de bash, y en una copia temporal:
   a) sin la línea `.env` en .gitignore, termina con código 1, no crea .env y no llama a docker;
   b) sin la línea `secretos-locales/`, lo mismo;
   c) con el .gitignore completo, termina con código 0, crea .env con sus siete variables y
      llama a `docker compose up -d` (control positivo: sin él, a) y b) podrían pasar porque
      el guion falla por cualquier otra razón).
4. `docker compose config` falla sin .env (y su mensaje pide correr ./iniciar.sh) y pasa con un
   .env de prueba con valores al azar. Solo si hay `docker` con Compose: si no, la comprobación
   queda SALTADA y el resumen lo dice. Con la variable de entorno CI puesta (GitHub Actions y
   GitLab CI la ponen), una comprobación saltada cuenta como falla.
5. Los roles (roles/*.json) se leen con json.load y traen db_name y creation_statements; las
   políticas y vault.hcl no están vacíos, tienen al menos un `path` y sus llaves { } cuadran.
6. python/clientes.py compila (python -m py_compile; el caché va a una carpeta temporal).
7. Ningún archivo trae secretos (los patrones de SECRETOS, más: en .env.ejemplo ninguna variable
   de contraseña, token o llave tiene valor).
8. Ningún título de un .md lleva emoji, y ningún archivo de texto trae palabras vetadas. Los
   patrones de .publicable-prohibido.txt NO se revisan aquí: esa lista no se publica
   (export-ignore), así que este guion, que sí viaja y corre en el CI público, no puede depender
   de ella. Esa revisión es previa a publicar y vive en verificar-publicable.sh, que tampoco viaja.

Lo que el laboratorio genera al arrancar (.env, secretos-locales/, vault/data/, vault/logs/,
postgres/, mariadb/) no se revisa: está en .gitignore y nunca se publica. Que siga en .gitignore
es justo lo que vigilan las comprobaciones 2 y 3.

Uso
---
    python verificar.py                    # las ocho comprobaciones
    python verificar.py --autoprueba       # comprueba que el verificador SÍ se pone en rojo
    python verificar.py --revisar-md       # solo la comprobación 8
    python verificar.py --revisar-secretos # solo la comprobación 7

Códigos de salida: 0 sin fallas; 1 con alguna falla (o con una saltada, si CI está puesta).
"""
import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
REGLAS_GITIGNORE = [".env", "secretos-locales/", "vault/data/", "vault/logs/", "postgres/", "mariadb/"]
REGLAS_QUE_EXIGE_INICIAR = [".env", "secretos-locales/"]
VARIABLES_ENV = ["POSTGRES_PASSWORD", "MARIADB_ROOT_PASSWORD", "PUERTO_VAULT", "PUERTO_POSTGRES",
                 "PUERTO_MARIADB", "LOCAL_UID", "LOCAL_GID"]
GENERADOS = {".env", "secretos-locales", "postgres", "mariadb"}           # en la raíz
GENERADOS_VAULT = {"data", "logs"}                                         # dentro de vault/
IGNORAR_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules"}

OK, FALLA, SALTADA = "ok", "FALLA", "SALTADA"

# Las palabras vetadas y el prefijo del token de GitLab se parten para que este archivo no los
# contenga al pie de la letra y la propia revisión pueda recorrerlo.
VETADAS = [
    ("tont" + "os", re.I), ("dum" + "mies", re.I), ("Cla" + "ude", 0), ("A" + "XO", 0),
    ("En" + "ti", 0), ("Unu" + "hi", 0),
]
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍⌀-⏿]")
SECRETOS = [
    ("llave de AWS", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("llave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("token de Slack", re.compile(r"xox[abprs]-[0-9A-Za-z-]{10,}")),
    ("token de GitHub", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}")),
    ("token de GitLab", re.compile("glp" + r"at-[A-Za-z0-9_-]{15,}")),   # partido para no disparar a los revisores de secretos
    ("llave tipo sk-", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("token de Vault", re.compile(r"\bhv[sbr]\.[A-Za-z0-9_-]{20,}")),     # las lecciones los muestran cortados: hvs.RGQs7...
    # «password = 'x'», «password: 'x'», «password:'x'»; NO «PASSWORD :'nombre'», que en psql es una
    # variable que se sustituye (la sesión 4 la usa justo para no escribir la contraseña).
    ("asignación de secreto", re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b(?:\s*=\s*|\s*:\s+|:)['\"][^'\"\s]{8,}['\"]")),
]
VARIABLE_SECRETA_CON_VALOR = re.compile(r"^\s*[A-Z0-9_]*(PASSWORD|PASSWD|SECRET|TOKEN|KEY)[A-Z0-9_]*\s*=\s*\S")
EXT_TEXTO = {".md", ".py", ".txt", ".json", ".hcl", ".sh", ".yaml", ".yml", ".cfg", ".toml"}
NOMBRES_TEXTO = {".gitignore", ".env.ejemplo"}


# ------------------------------------------------------------------------------ utilidades

def archivos(raiz):
    """Todos los archivos del repositorio, sin lo que el laboratorio genera al arrancar."""
    for p in sorted(raiz.rglob("*")):
        partes = p.relative_to(raiz).parts
        if not p.is_file() or any(x in IGNORAR_DIRS for x in partes):
            continue
        if partes[0] in GENERADOS or (len(partes) > 1 and partes[0] == "vault" and partes[1] in GENERADOS_VAULT):
            continue
        yield p


def archivos_de_texto(raiz, extensiones=EXT_TEXTO, nombres=NOMBRES_TEXTO):
    for p in archivos(raiz):
        if p.suffix in extensiones or p.name in nombres:
            yield p


def leer(p):
    return p.read_text(encoding="utf-8")


def copiar(raiz, destino):
    shutil.copytree(raiz, destino, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "venv",
                                                                   *GENERADOS))
    for d in GENERADOS_VAULT:
        shutil.rmtree(destino / "vault" / d, ignore_errors=True)


def entorno_limpio(**extra):
    """El entorno de esta terminal sin las variables del laboratorio: una exportada mandaría sobre .env."""
    env = {k: v for k, v in os.environ.items() if k not in VARIABLES_ENV and not k.startswith("COMPOSE_")}
    env.update(extra)
    return env


def hay_compose():
    if not shutil.which("docker"):
        return False, "no hay `docker` en el PATH"
    try:
        p = subprocess.run(["docker", "compose", "version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"`docker compose version` no respondió ({e})"
    if p.returncode != 0:
        return False, "`docker compose version` falló: " + p.stdout.decode(errors="replace").strip()[:200]
    return True, p.stdout.decode(errors="replace").strip()


# ---------------------------------------------------------------------------- comprobaciones

def c_manifiesto(raiz):
    try:
        datos = json.loads(leer(raiz / "manifiesto.json"))
        rutas = [a["ruta"] for a in datos["archivos"]]
    except (OSError, ValueError, KeyError, TypeError) as e:
        return FALLA, [f"manifiesto.json no se puede leer: {e}"]
    problemas = [f"falta {r}" for r in rutas if not (raiz / r).is_file()]
    for p in list(raiz.glob("politicas/*")) + list(raiz.glob("roles/*")):
        r = p.relative_to(raiz).as_posix()
        if p.is_file() and r not in rutas:
            problemas.append(f"{r} no está en manifiesto.json")
    return (FALLA, problemas) if problemas else (OK, [f"{len(rutas)} archivos"])


def c_gitignore(raiz):
    try:
        lineas = {l.strip() for l in leer(raiz / ".gitignore").splitlines() if l.strip() and not l.strip().startswith("#")}
    except OSError as e:
        return FALLA, [f".gitignore no se puede leer: {e}"]
    faltan = [r for r in REGLAS_GITIGNORE if r not in lineas]
    if faltan:
        return FALLA, ["faltan las reglas: " + ", ".join(faltan)]
    return OK, [f"las {len(REGLAS_GITIGNORE)} reglas están"]


def correr_iniciar(raiz, tmp, quitar=None):
    """Corre iniciar.sh en una copia, con un docker de mentira. Devuelve (código, salida, .env creado, llamadas a docker)."""
    copia = Path(tempfile.mkdtemp(dir=tmp)) / "lab"
    copiar(raiz, copia)
    if quitar is not None:
        gi = copia / ".gitignore"
        gi.write_text("".join(l for l in leer(gi).splitlines(keepends=True) if l.strip() != quitar), encoding="utf-8")
    falso = copia.parent / "bin"
    falso.mkdir()
    bitacora = copia.parent / "llamadas-a-docker.txt"
    (falso / "docker").write_text('#!/bin/sh\necho "$@" >> "$BITACORA_DOCKER"\nexit 0\n', encoding="utf-8")
    (falso / "docker").chmod(0o755)
    env = entorno_limpio(PATH=str(falso) + os.pathsep + os.environ.get("PATH", ""), BITACORA_DOCKER=str(bitacora))
    p = subprocess.run(["bash", str(copia / "iniciar.sh")], cwd=copia, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    llamadas = leer(bitacora).splitlines() if bitacora.exists() else []
    env_creado = leer(copia / ".env") if (copia / ".env").exists() else None
    return p.returncode, p.stdout.decode(errors="replace"), env_creado, llamadas


def c_iniciar(raiz):
    problemas, notas = [], []
    if not (raiz / "iniciar.sh").is_file():
        return FALLA, ["no existe iniciar.sh"]
    p = subprocess.run(["bash", "-n", str(raiz / "iniciar.sh")], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        return FALLA, ["bash -n: " + p.stdout.decode(errors="replace").strip()]
    with tempfile.TemporaryDirectory(prefix="verificar-iniciar-") as tmp:
        for regla in REGLAS_QUE_EXIGE_INICIAR:
            codigo, salida, env_creado, llamadas = correr_iniciar(raiz, tmp, quitar=regla)
            if codigo != 1:
                problemas.append(f"sin «{regla}» en .gitignore terminó con código {codigo}, no 1")
            if env_creado is not None:
                problemas.append(f"sin «{regla}» en .gitignore creó .env")
            if llamadas:
                problemas.append(f"sin «{regla}» en .gitignore llamó a docker: {llamadas}")
            if codigo == 1 and env_creado is None and not llamadas:
                notas.append(f"sin «{regla}»: código 1, sin .env, sin docker")
        codigo, salida, env_creado, llamadas = correr_iniciar(raiz, tmp)
        if codigo != 0:
            problemas.append(f"con el .gitignore completo terminó con código {codigo}: {salida.strip()[-300:]}")
        else:
            claves = [l.split("=", 1)[0] for l in (env_creado or "").splitlines() if "=" in l]
            if claves != VARIABLES_ENV:
                problemas.append(f"el .env generado trae {claves}, se esperaba {VARIABLES_ENV}")
            vacias = [l for l in (env_creado or "").splitlines() if l.endswith("=")]
            if vacias:
                problemas.append(f"el .env generado trae variables vacías: {vacias}")
            if llamadas != ["compose up -d"]:
                problemas.append(f"con el .gitignore completo, docker se llamó así: {llamadas}")
            if not problemas:
                notas.append("completo: código 0, .env con 7 variables, `docker compose up -d` (de mentira)")
    return (FALLA, problemas) if problemas else (OK, notas)


def c_compose(raiz):
    hay, detalle = hay_compose()
    if not hay:
        return SALTADA, [detalle]
    problemas, notas = [], []
    with tempfile.TemporaryDirectory(prefix="verificar-compose-") as tmp:
        copia = Path(tmp) / "lab"
        copiar(raiz, copia)
        env = entorno_limpio()
        p = subprocess.run(["docker", "compose", "config", "--quiet"], cwd=copia, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        salida = p.stdout.decode(errors="replace")
        if p.returncode == 0:
            problemas.append("sin .env, `docker compose config` pasó (debía fallar)")
        elif "iniciar.sh" not in salida:
            problemas.append("sin .env falló, pero el mensaje no pide correr ./iniciar.sh: " + salida.strip()[:300])
        else:
            notas.append("sin .env: falla y pide ./iniciar.sh")
        valores = {
            "POSTGRES_PASSWORD": secrets.token_hex(16), "MARIADB_ROOT_PASSWORD": secrets.token_hex(16),
            "PUERTO_VAULT": "18200", "PUERTO_POSTGRES": "15432", "PUERTO_MARIADB": "13306",
            "LOCAL_UID": "1000", "LOCAL_GID": "1000",
        }
        (copia / ".env").write_text("".join(f"{k}={v}\n" for k, v in valores.items()), encoding="utf-8")
        p = subprocess.run(["docker", "compose", "config", "--quiet"], cwd=copia, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        if p.returncode != 0:
            problemas.append("con un .env de prueba, `docker compose config` falló: " + p.stdout.decode(errors="replace").strip()[:300])
        else:
            notas.append("con .env de prueba: pasa")
    return (FALLA, problemas) if problemas else (OK, notas)


def llaves_cuadran(texto):
    sin_comentarios = re.sub(r'"(?:\\.|[^"\\])*"', '""', "\n".join(l.split("#", 1)[0] for l in texto.splitlines()))
    nivel = 0
    for ch in sin_comentarios:
        nivel += {"{": 1, "}": -1}.get(ch, 0)
        if nivel < 0:
            return False
    return nivel == 0


def c_politicas_y_roles(raiz):
    problemas, n_json, n_hcl = [], 0, 0
    for p in sorted(raiz.glob("roles/*.json")):
        try:
            datos = json.loads(leer(p))
        except ValueError as e:
            problemas.append(f"{p.relative_to(raiz)}: no es JSON válido ({e})")
            continue
        if not isinstance(datos, dict) or not datos.get("db_name") or not datos.get("creation_statements"):
            problemas.append(f"{p.relative_to(raiz)}: le falta db_name o creation_statements")
            continue
        n_json += 1
    for p in sorted(raiz.glob("politicas/*.hcl")) + [raiz / "vault/config/vault.hcl"]:
        if not p.is_file():
            problemas.append(f"no existe {p.relative_to(raiz)}")
            continue
        texto = leer(p)
        if not texto.strip():
            problemas.append(f"{p.relative_to(raiz)}: está vacío")
        elif not re.search(r"^\s*path\b", texto, re.M) and not re.search(r"^\s*path\s*=", texto, re.M):
            problemas.append(f"{p.relative_to(raiz)}: no tiene ningún `path`")
        elif not llaves_cuadran(texto):
            problemas.append(f"{p.relative_to(raiz)}: las llaves {{ }} no cuadran")
        else:
            n_hcl += 1
    if n_json == 0:
        problemas.append("no hay ningún rol en roles/")
    return (FALLA, problemas) if problemas else (OK, [f"{n_json} JSON y {n_hcl} HCL"])


def c_python(raiz):
    p = raiz / "python/clientes.py"
    if not p.is_file():
        return FALLA, ["no existe python/clientes.py"]
    with tempfile.TemporaryDirectory(prefix="verificar-pyc-") as tmp:
        r = subprocess.run([sys.executable, "-m", "py_compile", str(p)], env=dict(os.environ, PYTHONPYCACHEPREFIX=tmp),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        return FALLA, [r.stdout.decode(errors="replace").strip()[-400:]]
    return OK, ["compila"]


def revisar_secretos(raiz):
    problemas = []
    for p in archivos_de_texto(raiz):
        for n, linea in enumerate(leer(p).split("\n"), 1):
            for nombre, patron in SECRETOS:
                if patron.search(linea):
                    problemas.append(f"{p.relative_to(raiz)}:{n}: posible secreto ({nombre})")
            if p.name.startswith(".env") and VARIABLE_SECRETA_CON_VALOR.search(linea):
                problemas.append(f"{p.relative_to(raiz)}:{n}: variable de secreto con valor")
    return problemas


def revisar_md(raiz):
    problemas = []
    for p in archivos_de_texto(raiz, {".md"}, set()):
        en_codigo = False
        for n, linea in enumerate(leer(p).split("\n"), 1):
            if linea.startswith("```"):
                en_codigo = not en_codigo
            if not en_codigo and re.match(r"#{1,6}\s", linea) and EMOJI.search(linea):
                problemas.append(f"{p.relative_to(raiz)}:{n}: emoji en un título: {linea.strip()}")
    for p in archivos_de_texto(raiz):
        texto = leer(p)
        for palabra, flags in VETADAS:
            patron = re.compile(r"\b" + palabra + r"\b", flags)
            for n, linea in enumerate(texto.split("\n"), 1):
                if patron.search(linea):
                    problemas.append(f"{p.relative_to(raiz)}:{n}: palabra vetada")
    return problemas


def c_secretos(raiz):
    malos = revisar_secretos(raiz)
    return (FALLA, malos) if malos else (OK, [f"{sum(1 for _ in archivos_de_texto(raiz))} archivos de texto revisados"])


def c_md(raiz):
    malos = revisar_md(raiz)
    return (FALLA, malos) if malos else (OK, [f"{sum(1 for _ in archivos_de_texto(raiz, {'.md'}, set()))} archivos .md revisados"])


COMPROBACIONES = [
    ("manifiesto", "1. los archivos del laboratorio están y no sobra ninguno", c_manifiesto),
    ("gitignore", "2. .gitignore tiene las seis reglas", c_gitignore),
    ("iniciar", "3. iniciar.sh se detiene con código 1 si falta .env o secretos-locales/ en .gitignore", c_iniciar),
    ("compose", "4. docker compose config falla sin .env y pasa con uno de prueba", c_compose),
    ("politicas", "5. roles JSON y políticas HCL legibles", c_politicas_y_roles),
    ("python", "6. python/clientes.py compila", c_python),
    ("secretos", "7. ningún archivo trae secretos", c_secretos),
    ("md", "8. títulos sin emoji y sin palabras vetadas", c_md),
]


def correr(raiz, callar=False):
    resultados = []
    for clave, nombre, f in COMPROBACIONES:
        try:
            estado, detalle = f(raiz)
        except Exception as e:  # una comprobación que revienta es una falla, nunca un verde
            estado, detalle = FALLA, [f"la comprobación reventó: {type(e).__name__}: {e}"]
        resultados.append((clave, nombre, estado, detalle))
        if not callar:
            print(f"  [{estado}]".ljust(12) + nombre)
            for d in detalle[:20]:
                print("      " + d)
    return resultados


# ------------------------------------------------------------------------------ autoprueba

def autoprueba():
    """Mete fallas a propósito en una copia del repositorio y exige que cada una se ponga en rojo.
    También exige que la copia sin tocar dé verde (sin eso, «todo en rojo» no probaría nada)."""
    print("Autoprueba del verificador (se trabaja en una copia temporal; el repositorio no se toca)")
    hay, detalle_compose = hay_compose()
    fallas, saltadas, casos = [], [], 0
    with tempfile.TemporaryDirectory(prefix="autoprueba-lab-vault-") as tmp:
        copia = Path(tmp) / "copia"
        copiar(RAIZ, copia)

        def estado_de(clave):
            f = dict((c, fn) for c, _, fn in COMPROBACIONES)[clave]
            try:
                return f(copia)
            except Exception as e:
                return FALLA, [f"reventó: {e}"]

        def caso(nombre, ruta, cambiar, clave, requiere_docker=False):
            nonlocal casos
            casos += 1
            if requiere_docker and not hay:
                print(f"  [SALTADA] {nombre}: {detalle_compose}")
                saltadas.append(nombre)
                return
            p = copia / ruta
            original = p.read_bytes()
            try:
                p.write_text(cambiar(original.decode("utf-8")), encoding="utf-8")
                estado, detalle = estado_de(clave)
            finally:
                p.write_bytes(original)
            bien = estado == FALLA
            print(f"  [{'ok' if bien else 'FALLA'}] {nombre}: "
                  f"{'se puso en rojo' if bien else 'NO se puso en rojo (' + estado + ')'}"
                  + (f" — {detalle[0].strip().splitlines()[-1]}" if bien and detalle else ""))
            if not bien:
                fallas.append(nombre)

        def quitar_linea(regla):
            return lambda t: "".join(l for l in t.splitlines(keepends=True) if l.strip() != regla)

        token_falso = "glp" + "at-" + "Ab3dE6gH9jK2mN5pQ8sT"
        caso("1. quitar `.env` del .gitignore", ".gitignore", quitar_linea(".env"), "gitignore")
        caso("2. quitar `mariadb/` del .gitignore", ".gitignore", quitar_linea("mariadb/"), "gitignore")
        caso("3. iniciar.sh sigue aunque falte la regla (exit 1 -> exit 0)", "iniciar.sh",
             lambda t: t.replace("exit 1", "exit 0"), "iniciar")
        caso("4. iniciar.sh deja de revisar `secretos-locales/`", "iniciar.sh",
             lambda t: t.replace("for regla in '.env' 'secretos-locales/'; do", "for regla in '.env'; do"), "iniciar")
        caso("5. compose.yaml sin las guardas `:?` (arranca sin .env)", "compose.yaml",
             lambda t: re.sub(r":\?[^}]*\}", ":-1}", t), "compose", requiere_docker=True)
        caso("6. un token falso en una política", "politicas/app-python.hcl",
             lambda t: t + f"# token = {token_falso}\n", "secretos")
        caso("7. una contraseña con valor en .env.ejemplo", ".env.ejemplo",
             lambda t: t.replace("POSTGRES_PASSWORD=", "POSTGRES_PASSWORD=x9Kq2LmP7v"), "secretos")
        caso("7b. una contraseña escrita en el programa de Python", "python/clientes.py",
             lambda t: t + "PASS" + 'WORD = "s3cr3tValor99"\n', "secretos")
        caso("8. un JSON roto en roles/", "roles/lector-postgres.json", lambda t: t.rstrip().rstrip("}"), "politicas")
        caso("9. una política vacía", "politicas/lectura-tienda.hcl", lambda t: "", "politicas")
        caso("10. python/clientes.py que no compila", "python/clientes.py", lambda t: t + "\ndef roto(:\n", "python")
        caso("11. un emoji en un título de .md", "es/README.md",
             lambda t: t.replace("## Las cuatro sesiones", "## Las cuatro sesiones \U0001F510", 1), "md")
        caso("12. un archivo del manifiesto que falta", "manifiesto.json",
             lambda t: t.replace('"ruta": "compose.yaml"', '"ruta": "compose-que-no-existe.yaml"'), "manifiesto")

        print("  Copia sin tocar:")
        casos += 1
        resultados = correr(copia, callar=True)
        rojos = [n for _, n, e, _ in resultados if e == FALLA]
        if rojos:
            print(f"  [FALLA] 14. la copia sin tocar da verde: no, fallan {rojos}")
            fallas.append("14")
        else:
            sal = [n for _, n, e, _ in resultados if e == SALTADA]
            print("  [ok] 14. la copia sin tocar da verde" + (f" (con {len(sal)} saltada(s))" if sal else ""))
    print()
    print(f"Casos: {casos}; detectados como se esperaba: {casos - len(fallas) - len(saltadas)}; "
          f"fallan: {len(fallas)}; saltados: {len(saltadas)}")
    if fallas:
        print(f"AUTOPRUEBA FALLIDA: el verificador no se comportó como debía en {len(fallas)} caso(s): {', '.join(fallas)}")
        return 1
    if saltadas and os.environ.get("CI"):
        print(f"AUTOPRUEBA FALLIDA: en CI no se admiten casos saltados ({detalle_compose})")
        return 1
    if saltadas:
        print(f"AUTOPRUEBA SUPERADA CON {len(saltadas)} CASO(S) SALTADO(S): {detalle_compose}")
        return 0
    print("AUTOPRUEBA SUPERADA: el verificador detectó todas las fallas introducidas a propósito.")
    return 0


# ------------------------------------------------------------------------------- principal

def main(argv=None):
    ap = argparse.ArgumentParser(description="Verificador del laboratorio de Vault desde cero")
    ap.add_argument("--autoprueba", action="store_true", help="comprueba que el verificador detecta fallas")
    ap.add_argument("--revisar-md", action="store_true", help="títulos sin emojis y sin palabras vetadas")
    ap.add_argument("--revisar-secretos", action="store_true", help="busca posibles secretos")
    ap.add_argument("--raiz", default=str(RAIZ), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    raiz = Path(a.raiz).resolve()

    if a.autoprueba:
        return autoprueba()
    if a.revisar_md or a.revisar_secretos:
        malos = []
        if a.revisar_md:
            malos += revisar_md(raiz)
        if a.revisar_secretos:
            malos += revisar_secretos(raiz)
        for m in malos:
            print("  [FALLA] " + m)
        n = sum(1 for _ in archivos_de_texto(raiz))
        print(f"Revisión de texto ({n} archivos): " + ("todo limpio" if not malos else f"{len(malos)} problema(s)"))
        return 1 if malos else 0

    en_ci = bool(os.environ.get("CI"))
    print(f"Python {sys.version.split()[0]}" + (" · CI: una comprobación saltada cuenta como falla" if en_ci else ""))
    print("Comprobaciones:")
    resultados = correr(raiz)
    total = len(resultados)
    ok = sum(1 for r in resultados if r[2] == OK)
    fallan = [r for r in resultados if r[2] == FALLA]
    saltadas = [r for r in resultados if r[2] == SALTADA]
    print()
    print(f"Comprobaciones: {ok} de {total} pasaron; fallan: {len(fallan)}; saltadas: {len(saltadas)}")
    for _, nombre, _, detalle in saltadas:
        print(f"  saltada: {nombre} ({detalle[0] if detalle else 'sin detalle'})")
    if fallan or (saltadas and en_ci):
        print("RESULTADO: HAY FALLAS" + ("" if fallan else " (en CI, una comprobación saltada cuenta como falla)"))
        return 1
    if saltadas:
        print(f"RESULTADO: SIN FALLAS, PERO NO TODO EN VERDE: {len(saltadas)} comprobación(es) saltada(s)")
        return 0
    print("RESULTADO: TODO EN VERDE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
