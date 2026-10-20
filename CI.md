# Integración continua

Lo que la integración continua (CI) de este repositorio debe comprobar en cada cambio. Si cualquiera de estas
comprobaciones falla, el cambio no se publica.

## Entorno

- Python 3.12. El verificador solo usa la biblioteca estándar: no hay `requirements.txt` ni nada que instalar con pip.
- `bash` y `openssl` (el verificador corre `iniciar.sh` en una copia temporal).
- Docker con Compose, para la comprobación 4. En GitHub Actions, `ubuntu-latest` ya lo trae. **La CI nunca levanta
  contenedores:** solo corre `docker compose config`, que lee y valida `compose.yaml` sin descargar imágenes.
- La variable de entorno `CI` puesta (GitHub Actions y GitLab CI la ponen solas). Con ella, una comprobación saltada
  cuenta como falla: en la CI no se admite un verde que no midió.

## La lista exacta

| # | Qué se comprueba | Comando | Debe pasar |
|---|---|---|---|
| 1 | Las ocho comprobaciones del laboratorio (ver abajo) | `python verificar.py` | código de salida 0; el resumen dice «Comprobaciones: 8 de 8 pasaron; fallan: 0; saltadas: 0» y «RESULTADO: TODO EN VERDE» |
| 2 | El verificador se pone en rojo cuando debe (mete fallas a propósito en una copia y comprueba que las detecta) | `python verificar.py --autoprueba` | código de salida 0; «Casos: 15; detectados como se esperaba: 15; fallan: 0; saltados: 0» y «AUTOPRUEBA SUPERADA» |
| 3 | Ningún título de un `.md` lleva emoji, ningún archivo de texto trae palabras vetadas y ningún `.md` trae un patrón de `.publicable-prohibido.txt` | `python verificar.py --revisar-md` | código de salida 0 y «todo limpio» |
| 4 | No hay secretos en el repositorio (llaves, tokens, contraseñas asignadas, variables de `.env.ejemplo` con valor) | `python verificar.py --revisar-secretos` | código de salida 0 y «todo limpio» |

Las ocho comprobaciones del paso 1, en el orden en que salen:

1. Los archivos del laboratorio que lista `manifiesto.json` existen, y no hay una política ni un rol fuera del manifiesto.
2. `.gitignore` tiene las seis reglas: `.env`, `secretos-locales/`, `vault/data/`, `vault/logs/`, `postgres/` y `mariadb/`.
3. `iniciar.sh` tiene sintaxis válida y, en una copia temporal con un `docker` de mentira: sin la regla `.env` termina
   con código 1, sin crear `.env` y sin llamar a docker; sin la regla `secretos-locales/`, lo mismo; con el `.gitignore`
   completo termina con código 0, genera `.env` con sus siete variables y llama a `docker compose up -d` (de mentira).
4. `docker compose config` falla sin `.env` (y el mensaje pide correr `./iniciar.sh`) y pasa con un `.env` de prueba.
5. Los roles (`roles/*.json`) son JSON válido con `db_name` y `creation_statements`; las políticas y `vault.hcl` no están
   vacíos, tienen al menos un `path` y sus llaves cuadran.
6. `python/clientes.py` compila.
7. Ningún archivo trae secretos (igual que el paso 4 de la tabla).
8. Títulos sin emoji y sin palabras vetadas (igual que el paso 3 de la tabla).

Notas:

- **Autoprueba.** Un verificador que nunca falla no sirve. La autoprueba trabaja en una copia temporal y no toca el
  repositorio. Sus casos: quitar `.env` y `mariadb/` del `.gitignore`; un `iniciar.sh` que sigue aunque falte la regla,
  y otro que deja de revisar `secretos-locales/`; un `compose.yaml` sin las guardas `:?`; un token falso en una
  política; una contraseña con valor en `.env.ejemplo` y otra escrita en el programa de Python; un JSON roto; una
  política vacía; un programa que no compila; un emoji en un título; una palabra prohibida en un `.md`; un archivo del
  manifiesto que falta. Al final exige que la copia sin tocar dé verde.
- **Secretos.** Los patrones viven en `verificar.py` (`SECRETOS`). Si aparece un falso positivo, se corrige el texto o
  se afina el patrón para todos los archivos; no se agrega una excepción por archivo.
- **Palabras prohibidas.** La lista vive en `.publicable-prohibido.txt` y está hecha para crecer.
- **`es/`** se genera desde las lecciones del curso; no se edita a mano en el repositorio.

## Ejemplo para GitHub Actions

Es el que está en `.github/workflows/verificar.yml`:

```yaml
name: verificar
on: [push, pull_request]
jobs:
  verificar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: docker compose version
      - run: python verificar.py
      - run: python verificar.py --autoprueba
      - run: python verificar.py --revisar-md
      - run: python verificar.py --revisar-secretos
```

## Ejemplo para GitLab CI

La imagen `python:3.12` no trae Docker. `docker compose config` no necesita el servicio de Docker corriendo, solo el
cliente con Compose, así que basta una imagen que lo traiga y agregarle Python. Este ejemplo no se ha corrido; si la
comprobación 4 sale «saltada», con `CI` puesta el trabajo falla, que es lo que debe pasar.

```yaml
verificar:
  image: docker:27-cli
  before_script:
    - apk add --no-cache python3 bash openssl
  script:
    - docker compose version
    - python3 verificar.py
    - python3 verificar.py --autoprueba
    - python3 verificar.py --revisar-md
    - python3 verificar.py --revisar-secretos
```

## Qué no cubre

- No levanta el laboratorio: no comprueba que Vault arranque, se inicialice o abra el sello, ni que PostgreSQL y
  MariaDB acepten las credenciales dinámicas. Eso se probó a mano al escribir las lecciones (Linux Mint 22.3 con la
  imagen oficial `hashicorp/vault:2.2.0`, y macOS).
- No comprueba que las políticas y los roles hagan lo que dice la lección: solo que se pueden leer. Su sintaxis HCL se
  revisa por encima (no vacío, con `path`, llaves que cuadran), no con el analizador de Vault.
- No corre `python/clientes.py`: necesita un Vault y un PostgreSQL vivos. Solo comprueba que compila.
- No comprueba si un archivo generado (`.env`, `secretos-locales/`) quedó rastreado por git: eso lo evita el
  `.gitignore`, que sí se comprueba.
