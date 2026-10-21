# Vault desde cero: el laboratorio

Laboratorio del curso «Vault desde cero» de Hábil. Con él se aprende a guardar contraseñas, llaves y otros secretos en
HashiCorp Vault, a cifrar datos sin que la llave llegue al programa y a que las contraseñas de las bases de datos se
cambien solas. Todo se hace desde la terminal: `curl`, `psql`, `mariadb` y Docker Compose. El único programa del curso
es un archivo de Python de 24 líneas, en la sesión 4.

Autor: Dorian Chávez, Hábil.

Este repositorio trae el laboratorio listo para arrancar (un Vault en modo servidor, un PostgreSQL y un MariaDB), las
políticas y los roles que se usan en las lecciones, las cuatro lecciones completas en [`es/`](es/) y un verificador que
revisa el laboratorio sin levantarlo.

**El repositorio no trae ninguna contraseña, token ni llave.** Las contraseñas de las bases de datos las genera
`iniciar.sh` al azar la primera vez que corre, y las guarda en `.env`, que `.gitignore` impide subir. Las llaves y el
token de Vault nacen cuando Vault se inicializa, en la sesión 2. Si el `.gitignore` no protege esos archivos,
`iniciar.sh` se niega a generar nada.

## Las cuatro sesiones

| Sesión | Lección | De qué trata |
|---|---|---|
| 1 | [El problema de los secretos](es/01-el-problema-de-los-secretos.md) | las seis formas en que se escapa un secreto, con `grep` y `git`; qué es Vault y qué no es |
| 2 | [Levantar Vault y guardar secretos](es/02-levantar-vault-y-guardar-secretos.md) | el laboratorio con Docker Compose, el sello y sus llaves, secretos con `curl`, políticas y bitácora |
| 3 | [Cifrar sin tener la llave](es/03-cifrar-sin-tener-la-llave.md) | el motor Transit: cifrar, descifrar, rotar la llave y guardar CURP cifradas en PostgreSQL |
| 4 | [Contraseñas que se cambian solas](es/04-contrasenas-que-se-cambian-solas.md) | credenciales que caducan solas en PostgreSQL y MariaDB, rotación automática y un programa de Python sin contraseñas |

La sesión 1 no usa el laboratorio: solo una terminal y `git`. Desde la sesión 2 se usa todo lo de este repositorio.
Las lecciones se publican una por semana en «En construcción», el Substack de Hábil: https://enconstruccionmx.substack.com

## Requisitos

- **Docker con Compose** (`docker compose version` debe responder).
- **curl**.
- **jq 1.6 o más nuevo**: lee las respuestas de Vault, que vienen en formato JSON.
- **openssl**: `iniciar.sh` lo usa para generar las contraseñas al azar.
- **git 2.28 o más nuevo**.
- Para la sesión 3, el cliente `psql`; para la sesión 4, también el cliente `mariadb` y Python 3 con `psycopg`. Cada
  lección dice cómo instalarlos cuando hacen falta.

Las versiones de las imágenes están fijas en `compose.yaml`: Vault 2.2.0 (`hashicorp/vault:2.2.0`), PostgreSQL 17.11 y
MariaDB 11.8.8. No se cambian por `latest`: los comandos y las respuestas de las lecciones son los de esas versiones.

Probado en Linux Mint 22.3 con la imagen oficial `hashicorp/vault:2.2.0`, y en macOS. En Windows no se ha probado.

## Cómo arrancar

```bash
git clone https://github.com/HabilMX/lab-vault.git
cd lab-vault
./iniciar.sh
```

`iniciar.sh` hace cuatro cosas, en este orden:

1. Revisa que `.gitignore` tenga las reglas `.env` y `secretos-locales/`. Si falta alguna, se detiene con código 1 y no
   genera nada.
2. Crea las carpetas que montan los contenedores (`vault/data`, `vault/logs`, `postgres`, `mariadb`) y
   `secretos-locales/`, donde se guardan las llaves de Vault en la sesión 2. Son carpetas normales, no volúmenes de
   Docker: se pueden ver y borrar a mano.
3. Si no existe `.env`, lo genera con contraseñas al azar, los puertos y tu usuario. Si ya existe, lo deja como está.
4. Levanta los tres contenedores con `docker compose up -d`.

Después de la primera vez, el laboratorio se levanta y se apaga con Compose:

```bash
docker compose up -d
docker compose down
```

Sin `.env`, `docker compose` se niega a arrancar y dice «corre primero ./iniciar.sh». Los puertos solo escuchan en
`127.0.0.1` (8200 para Vault, 5432 para PostgreSQL y 3306 para MariaDB); si alguno ya está ocupado en tu computadora,
cámbialo en `.env`. `.env.ejemplo` muestra qué variables lleva `.env`, sin ningún valor real.

Vault corre sin TLS y con un solo servidor **solo porque es un laboratorio** en tu computadora. La sesión 4 dice qué
falta para usarlo en un sistema de verdad.

## Qué hay en el repositorio

- `compose.yaml`: los tres servicios del laboratorio.
- `iniciar.sh`: el guion de arranque que falla cerrado.
- `.env.ejemplo`: las variables de `.env`, sin valores.
- `.gitignore`: lo que el laboratorio genera y nunca se sube (`.env`, `secretos-locales/` y las carpetas de datos).
- `vault/config/vault.hcl`: la configuración de Vault en modo servidor.
- `politicas/`: las tres políticas de las sesiones 2 a 4 (quién puede leer, cifrar o pedir qué).
- `roles/`: los roles de credenciales dinámicas de PostgreSQL y MariaDB de la sesión 4.
- `python/clientes.py`: el programa de la sesión 4.
- `es/`: las cuatro lecciones.
- `verificar.py`: el verificador, con autoprueba.
- `CI.md`: lo que comprueba la integración continua.

## Cómo correr el verificador

`verificar.py` revisa el laboratorio **sin levantar ningún contenedor**: que `iniciar.sh` se detenga cuando falta una
regla del `.gitignore`, que el `.gitignore` tenga sus seis reglas, que `docker compose config` falle sin `.env` y pase
con uno de prueba, que las políticas y los roles se puedan leer, que el programa de Python compile y que no haya
secretos. Al final dice cuántas comprobaciones pasaron de cuántas. Solo necesita Python 3 (sin bibliotecas extra) y,
para la comprobación de Compose, Docker; si Docker no está, esa comprobación sale como «saltada» y el resumen lo dice.

```bash
python3 verificar.py                    # las comprobaciones del laboratorio
python3 verificar.py --autoprueba       # comprueba que el verificador se pone en rojo cuando debe
python3 verificar.py --revisar-md       # títulos sin emojis y sin palabras vetadas
python3 verificar.py --revisar-secretos # tokens, llaves y contraseñas escritas en archivos
```

## Licencia

El material del laboratorio y el código tienen cada uno su licencia; los términos completos están en `LICENSE.md`.
