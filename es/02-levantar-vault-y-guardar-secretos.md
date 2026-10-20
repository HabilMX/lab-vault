# Vault desde cero (2): levantar Vault y guardar secretos

*Una caja fuerte que nadie puede abrir solo, una ventanilla que le dice que no a quien pide lo que no le toca, y una bitácora que lo anota todo. Con Docker Compose y `curl`.*

*Vault desde cero · sesión 2 de 4*

## Repaso de la sesión 1

Contesta sin ver. Las respuestas están en las soluciones, al final.

1. Nombra cuatro de las seis formas en que se escapa un secreto.
2. ¿Por qué cambiar la contraseña después de una filtración es obligatorio, aunque ya la hayas borrado de git?
3. ¿En qué se parece y en qué se diferencia el motor Transit de Vault de un HSM?

## Objetivos de esta sesión

| # | Al terminar puedes… | Lo demuestra |
|---|---|---|
| 1 | **Levantar** Vault en modo servidor con Docker Compose, sin escribir ninguna contraseña en los archivos del laboratorio | Ejercicio 6 |
| 2 | **Inicializar** y **abrir** Vault con 3 de 5 llaves, y **explicar** por qué se cierra solo al reiniciar | Ejercicio 7 |
| 3 | **Guardar, leer, versionar, borrar y recuperar** secretos con `curl` contra la API | Ejercicio 8 |
| 4 | **Escribir** una política y **comprobar** que un token limitado recibe 403 donde no debe | Ejercicio 9 |
| 5 | **Leer** la bitácora de auditoría con `jq` para saber quién pidió qué | Ejercicio 10 |

---

## Escenario (ficción) — Capítulo 5: Sábado, 1:40 p.m.

Iván cambió la contraseña de `app_tienda` a mediodía. Tardó hora y media en volver a levantar los cuatro programas. La macro de contabilidad nunca apareció; Rocío, la contadora, va a sacar el reporte del mes a mano.

Doña Clara lo escucha todo sin interrumpir. Al final dice una sola cosa:

—No quiero volver a depender de que alguien se acuerde de dónde escribió una contraseña.

Iván propone una caja fuerte para secretos. Doña Clara pregunta quién va a tener la llave.

—Usted —dice Iván.

—No. Si me pasa algo, nadie abre. Y si alguien me la quita, abre solo.

Iván sonríe. Esa objeción tiene una respuesta de 1979.

---

## Capítulo 6: El sábado siguiente, 3:17 a.m.

La caja fuerte ya existe. Cinco personas tienen un pedazo de su llave. Las apps piden sus secretos con su propia identificación.

El celular de Iván vibra otra vez. Misma hora. Mismo servidor. Pero ahora la bitácora de la base de datos dice otra cosa:

```
03:17:02  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
03:17:32  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
03:18:02  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
```

Alguien sigue intentando con la contraseña vieja. Cada treinta segundos. Como un reloj.

Iván se queda viendo la pantalla. Los ladrones no tienen horario fijo.

¿Quién sí?

*(Continúa en la sesión 3.)*

---

## Por qué importa

Hasta hoy, en Canasta Morada «tener acceso» quería decir «saberse la contraseña». Hoy vas a construir lo contrario: un lugar donde nadie se sabe nada, y cada quien **pide** lo que necesita y **demuestra** quién es. Es la diferencia entre una casa donde todos tienen copia de la llave y un edificio con recepción: ahí te anotan, te preguntan a dónde vas y solo te abren ese piso.

En esta sesión vas a ver tres ideas que se usan en cualquier sistema serio, con o sin Vault:

- **El sello.** Los datos están cifrados en el disco. Sin la llave maestra, ni el propio Vault puede leerlos.
- **Negado por defecto.** Si una política no dice que puedes, no puedes. La documentación lo dice así: «las políticas niegan por defecto» ([Policies](https://developer.hashicorp.com/vault/docs/concepts/policies)).
- **Todo queda anotado.** Cada petición, permitida o negada, deja huella en la bitácora.

## La respuesta de 1979: llaves de Shamir

En 1979, el criptógrafo Adi Shamir publicó una forma de partir un secreto en **N pedazos** de manera que cualquier grupo de **K** pedazos lo reconstruye, y con menos de K no se sabe nada. Ni siquiera un poquito.

Piensa en la alcancía de la fiesta del pueblo. Hay cinco mayordomos. Para abrirla tienen que juntarse al menos tres, cada uno con su llave. Si uno se enferma, los otros cuatro alcanzan. Si a uno le roban la llave, el ladrón no abre nada solo. Y nadie, ni el mayordomo principal, puede abrirla a escondidas.

Vault funciona así:

- Al **inicializarlo**, Vault crea una **llave maestra** que protege todo lo que guarda. Por defecto la parte en **5 pedazos** y pide **3** para reconstruirla ([vault operator init](https://developer.hashicorp.com/vault/docs/commands/operator/init)).
- Vault arranca **sellado** (*sealed*): tiene los datos, pero cifrados, y no los entiende. Es la alcancía cerrada.
- **Abrir el sello** (*unseal*) es que tres mayordomos metan su llave. A partir de ahí Vault trabaja normal.
- Si Vault se reinicia, **vuelve a sellarse**. Hay que juntar otra vez tres llaves.

La documentación oficial explica el sello y el algoritmo de Shamir en [Seal/Unseal](https://developer.hashicorp.com/vault/docs/concepts/seal).

---

## Paso 0 — Lo que necesitas

Docker con Compose, `curl`, `jq` (versión 1.6 o más nueva), `openssl` y `git`. Compruébalo:

```
docker compose version
curl --version
jq --version
openssl version
```

Si alguno marca «command not found», instálalo antes de seguir. Esta sesión usa Vault 2.2.0, PostgreSQL 17.11 y MariaDB 11.8.8, fijados en el `compose.yaml`: no los cambies por `latest`, porque los comandos y las respuestas de la lección son los de esas versiones.

## Paso 1 — La carpeta del laboratorio

Crea una carpeta `lab-vault` con esta forma. El contenido de cada archivo viene abajo.

```
lab-vault/
├── .gitignore
├── .env.ejemplo
├── compose.yaml
├── iniciar.sh
└── vault/
    └── config/
        └── vault.hcl
```

Lo primero es el `.gitignore`. Es la lista de lo que git nunca debe subir. Va **antes** que cualquier otra cosa porque el laboratorio va a generar contraseñas, y queremos que, desde el primer segundo, git no las agregue por descuido. Ojo: `.gitignore` solo evita que git agregue archivos que todavía no conoce. No protege un archivo que ya se confirmó antes, ni a alguien que fuerce la subida con `git add -f`; por eso conviene revisar `git status` antes de cada `git commit`.

```
# Lo que el laboratorio genera al arrancar. NADA de esto se sube a git.
.env
secretos-locales/
vault/data/
vault/logs/
postgres/
mariadb/
```

Después, `.env.ejemplo`. Es una copia de referencia **sin valores reales**, para que quien clone el repositorio sepa qué variables existen:

```
# Referencia SIN valores reales. El archivo .env de verdad lo genera iniciar.sh
# con contraseñas al azar, y .gitignore impide que se suba.
POSTGRES_PASSWORD=
MARIADB_ROOT_PASSWORD=
PUERTO_VAULT=8200
PUERTO_POSTGRES=5432
PUERTO_MARIADB=3306
LOCAL_UID=
LOCAL_GID=
```

La configuración de Vault, `vault/config/vault.hcl`:

```hcl
# Vault en modo servidor (no "dev"): guarda todo cifrado en una carpeta.
storage "file" {
  path = "/vault/file"
}

# Escucha en el puerto 8200. Sin TLS SOLO porque es un laboratorio en tu máquina.
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = true
}

api_addr      = "http://127.0.0.1:8200"
ui            = true
disable_mlock = true
```

Tres cosas que conviene entender:

- **`storage "file"`**: Vault guarda sus datos, ya cifrados, en una carpeta. Hay otras opciones para producción con varios servidores; esta es la más simple ([Filesystem storage](https://developer.hashicorp.com/vault/docs/configuration/storage/filesystem)).
- **`tls_disable = true`**: sin cifrado en la conexión. En tu laptop está bien. En un servidor de verdad, **jamás**: las contraseñas viajarían en texto plano por la red.
- **No es modo «dev».** Vault tiene un modo de desarrollo que arranca abierto, sin sello y guardando todo en memoria. Es cómodo, pero te esconde justo lo que queremos aprender hoy.

El `compose.yaml`. Fíjate en dos detalles: **no hay ninguna contraseña escrita**, solo variables como `${POSTGRES_PASSWORD}`, y los datos se guardan en **carpetas montadas** (`./vault/data`), no en volúmenes de Docker, para que veas los archivos y no se pierdan si alguien limpia Docker:

```yaml
name: lab-vault-educacion

services:
  vault:
    image: hashicorp/vault:2.2.0
    command: server
    environment:
      VAULT_ADDR: http://127.0.0.1:8200   # para usar el comando vault dentro del contenedor
    user: "${LOCAL_UID:?corre primero ./iniciar.sh}:${LOCAL_GID:?corre primero ./iniciar.sh}"   # tu usuario: así Vault puede escribir en las carpetas montadas
    ports:
      - "127.0.0.1:${PUERTO_VAULT:?falta .env, corre ./iniciar.sh}:8200"
    volumes:
      - ./vault/config:/vault/config
      - ./vault/data:/vault/file
      - ./vault/logs:/vault/logs
    networks: [lab]

  postgres:
    image: postgres:17.11
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?falta .env, corre ./iniciar.sh}
      POSTGRES_DB: tienda
    ports:
      - "127.0.0.1:${PUERTO_POSTGRES:?falta .env, corre ./iniciar.sh}:5432"
    volumes:
      - ./postgres:/var/lib/postgresql/data
    networks: [lab]

  mariadb:
    image: mariadb:11.8.8
    environment:
      MARIADB_ROOT_PASSWORD: ${MARIADB_ROOT_PASSWORD:?falta .env, corre ./iniciar.sh}
      MARIADB_DATABASE: tienda
    ports:
      - "127.0.0.1:${PUERTO_MARIADB:?falta .env, corre ./iniciar.sh}:3306"
    volumes:
      - ./mariadb:/var/lib/mysql
    networks: [lab]

networks:
  lab:
```

PostgreSQL y MariaDB los usas en las sesiones 3 y 4; los levantamos desde hoy para no tocar el archivo después. El `:?falta .env…` quiere decir: «si esta variable no existe, no arranques y muestra este mensaje».

Tres detalles de este archivo:

- **`127.0.0.1:` delante de cada puerto** hace que Docker publique el servicio solo para tu propia computadora. Sin eso, Vault (que aquí no usa TLS) y las dos bases quedarían abiertas a cualquiera de tu red.
- **`user:`** hace que Vault corra con tu usuario. La imagen oficial arranca con un usuario sin privilegios (`vault`), y en Linux no podría escribir en carpetas que creaste tú. El guion de arranque anota tu número de usuario en `.env`.
- **Si algún puerto ya está en uso** (el 8200, el 5432 o el 3306), cámbialo con `PUERTO_VAULT`, `PUERTO_POSTGRES` o `PUERTO_MARIADB`, como se explica abajo.

> **En Linux: dos carpetas tuyas que no son tuyas.**
>
> Después de levantar el laboratorio en Linux, corre `ls -ln` en la carpeta. Vas a ver algo así (recortamos las columnas que no importan; lo medimos en Linux Mint 22.3, con el usuario 1000):
>
> ```
> drwx------  999 1000  postgres
> drwxrwxr-x  999  999  mariadb
> drwx------ 1000 1000  secretos-locales
> drwxr-xr-x 1000 1000  vault
> ```
>
> Las carpetas `postgres` y `mariadb` ya no son de tu usuario: son del 999. Y si corres `ls -l` sin la `n`, en lugar del número puede aparecer el nombre de un servicio de tu sistema (en Mint salió `dnsmasq`). No es un virus ni un error del laboratorio. Pasa porque las imágenes oficiales de PostgreSQL y MariaDB arrancan como administrador dentro del contenedor y luego le pasan sus archivos a su propio usuario interno, el número 999. Una **carpeta montada** es la misma carpeta vista desde dos lados: lo que el contenedor le hace a sus archivos, tu disco lo ve tal cual, número de usuario incluido. Tu Linux no sabe quién es el 999 del contenedor; solo ve el número, y si en tu sistema ese número tiene dueño, te muestra su nombre.
>
> A Vault no le pasa porque el `user:` del compose lo obliga a correr con tu número. ¿Por qué no se hace lo mismo con las bases de datos? Porque necesitan arrancar como administrador para prepararse la primera vez, y forzarles otro usuario rompe ese primer arranque.
>
> Qué significa para ti:
> - `ls postgres` te dirá «Permiso denegado». Para mirar adentro usa `sudo ls postgres`, o mejor, pregúntale al propio contenedor: `docker compose exec postgres ls /var/lib/postgresql/data`.
> - Si algún día quieres empezar el laboratorio desde cero, primero `docker compose down` y luego borra esas dos carpetas con `sudo`, porque tu usuario no puede.
> - En macOS y Windows no lo vas a ver: Docker corre dentro de una máquina virtual que te muestra los archivos como tuyos.

## Paso 2 — Un guion de arranque que falla cerrado

`iniciar.sh` prepara todo. Lo importante está en el punto 1: **antes de generar cualquier contraseña, revisa que `.gitignore` la proteja.** Si no, se niega a seguir. A eso se le llama **fallar cerrado**: ante la duda, la puerta se queda cerrada, como el torniquete del metro que no gira si no pasó tu tarjeta.

```bash
#!/usr/bin/env bash
# Prepara el laboratorio de Vault: revisa .gitignore, genera contraseñas al azar
# y levanta los contenedores. No escribe ninguna contraseña fija en ningún lado.
set -euo pipefail
cd "$(dirname "$0")"

# 1. Falla cerrado: si .gitignore no protege los secretos, no se genera nada.
for regla in '.env' 'secretos-locales/'; do
  if ! grep -qx "$regla" .gitignore 2>/dev/null; then
    echo "ALTO: .gitignore no tiene la regla '$regla'." >&2
    echo "Sin ella, las contraseñas que voy a generar podrían terminar en git. No sigo." >&2
    exit 1
  fi
done

# 2. Carpetas montadas (nada de volúmenes de Docker).
mkdir -p vault/data vault/logs postgres mariadb secretos-locales
chmod 700 secretos-locales

# 3. Contraseñas al azar, solo la primera vez.
if [ ! -f .env ]; then
  umask 077
  {
    echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)"
    echo "MARIADB_ROOT_PASSWORD=$(openssl rand -hex 16)"
    echo "PUERTO_VAULT=${PUERTO_VAULT:-8200}"
    echo "PUERTO_POSTGRES=${PUERTO_POSTGRES:-5432}"
    echo "PUERTO_MARIADB=${PUERTO_MARIADB:-3306}"
    echo "LOCAL_UID=$(id -u)"
    echo "LOCAL_GID=$(id -g)"
  } > .env
  echo "Generé .env con contraseñas nuevas (y no se sube a git)."
else
  echo "Ya existe .env; uso las contraseñas que tiene."
fi

# 4. Arriba. Una variable ya exportada en tu terminal mandaría sobre .env; se quitan
#    para que Compose use exactamente lo que dice .env.
unset POSTGRES_PASSWORD MARIADB_ROOT_PASSWORD PUERTO_VAULT PUERTO_POSTGRES PUERTO_MARIADB LOCAL_UID LOCAL_GID
docker compose up -d
```

`grep -qx` busca una línea que sea **exactamente** ese texto (`-x`) y no imprime nada (`-q`); solo dice sí o no. `openssl rand -hex 16` genera 16 bytes al azar escritos como 32 caracteres hexadecimales. `umask 077` hace que el `.env` nazca legible solo por ti. `id -u` e `id -g` son tu número de usuario y de grupo. Y el `unset` quita de tu terminal cualquier variable con esos nombres: Compose da prioridad a las variables de la terminal sobre `.env`, y no queremos que una contraseña o un puerto viejo ganen sin que te enteres.

Dale permiso de ejecución con `chmod +x iniciar.sh`. Antes de correrlo bien, comprueba que de verdad falla cerrado. En una copia del laboratorio donde al `.gitignore` le falta la línea `secretos-locales/`, esto es lo que pasa:

```
$ ./iniciar.sh
ALTO: .gitignore no tiene la regla 'secretos-locales/'.
Sin ella, las contraseñas que voy a generar podrían terminar en git. No sigo.
código de salida: 1
```

No creó ninguna carpeta ni ningún `.env`. Ahora, con el `.gitignore` completo:

```
$ ./iniciar.sh
Generé .env con contraseñas nuevas (y no se sube a git).
 Network lab-vault-educacion_lab Created
 Container lab-vault-educacion-vault-1 Created
 Container lab-vault-educacion-postgres-1 Created
 Container lab-vault-educacion-mariadb-1 Created
 ...
 Container lab-vault-educacion-vault-1 Started
 Container lab-vault-educacion-postgres-1 Started
 Container lab-vault-educacion-mariadb-1 Started
código de salida: 0
```

Si en tu máquina ya usas el puerto 5432 (porque tienes otro PostgreSQL), arráncalo así la primera vez: `PUERTO_POSTGRES=15432 ./iniciar.sh`. El guion lo anota en `.env`.

Y la prueba de que git no ve los secretos. Si haces `git init` en la carpeta y preguntas qué subiría:

```
$ git status --short
?? .env.ejemplo
?? .gitignore
?? compose.yaml
?? iniciar.sh
?? vault/config/vault.hcl
```

Ni `.env`, ni `secretos-locales/`, ni los datos. Es lo que querías.

## Paso 3 — ¿Está vivo?

Vault habla HTTP. Guarda su dirección en una variable para no escribirla cada vez:

```
export VAULT_ADDR="http://127.0.0.1:$(grep '^PUERTO_VAULT=' .env | cut -d= -f2)"
```

Corre esa línea dentro de la carpeta `lab-vault`. El puerto se lee de tu `.env`, así que funciona aunque lo hayas cambiado. Que Docker diga «Started» no quiere decir que Vault ya esté escuchando. Espera a que conteste:

```
until curl -fsS -o /dev/null "$VAULT_ADDR/v1/sys/seal-status"; do
  echo "Espero a que Vault inicie..."
  sleep 1
done
```

Pregúntale cómo está su sello. Esta ruta no pide identificación:

```
$ curl -s $VAULT_ADDR/v1/sys/seal-status | jq .
{
  "type": "shamir",
  "initialized": false,
  "sealed": true,
  "t": 0,
  "n": 0,
  "progress": 0,
  "nonce": "",
  "version": "2.2.0",
  "build_date": "2026-10-14T15:24:08Z",
  "migration": false,
  "recovery_seal": false,
  "storage_type": "file"
}
```

`initialized: false`: nunca lo han inicializado. `sealed: true`: está sellado. `t` y `n` son el umbral y el total de llaves; todavía no hay.

Otra forma rápida de saber el estado es el código HTTP de la ruta de salud. `-o /dev/null` tira la respuesta y `-w` imprime solo el código:

```
$ curl -s -o /dev/null -w "%{http_code}\n" $VAULT_ADDR/v1/sys/health
501
```

501 quiere decir «no inicializado». Vas a ver cómo cambia.

## Paso 4 — Inicializar: nacen las cinco llaves

Esta petición crea la llave maestra, la parte en 5 pedazos con umbral de 3, y te devuelve los pedazos y un **token root**. La guardas directo en un archivo de la carpeta `secretos-locales/`, que git ignora:

```
curl -s -X PUT $VAULT_ADDR/v1/sys/init \
  -d '{"secret_shares": 5, "secret_threshold": 3}' > secretos-locales/init.json
chmod 600 secretos-locales/init.json
```

`chmod 600` deja el archivo legible solo para ti. Míralo sin enseñar los valores completos:

```
$ jq "{llaves: (.keys | length), token_root: (.root_token[0:9] + \"...\")}" secretos-locales/init.json
{
  "llaves": 5,
  "token_root": "hvs.RGQs7..."
}
```

Tus valores van a ser otros. Cada inicialización crea llaves nuevas. En esta lección siempre verás los tokens cortados, así: `hvs.RGQs7...`.

El **token root** es la llave de dueño: puede hacer absolutamente todo. Lo usarás para configurar el laboratorio.

> **Así no, y por qué**
>
> Guardar las cinco llaves y el token root en un archivo junto al `compose.yaml` es una **concesión del laboratorio**, para que puedas practicar solo en tu máquina. **En la vida real nunca se hace así.**
>
> - Las llaves se reparten entre **personas distintas**, una a cada quien, justo para que nadie pueda abrir la caja solo. Juntarlas en un archivo es tener a los cinco mayordomos en una sola persona.
> - El **token root se revoca** en cuanto termina la configuración inicial. La documentación lo recomienda así: usarlo solo para lo indispensable al principio y revocarlo en cuanto deja de necesitarse ([Tokens](https://developer.hashicorp.com/vault/docs/concepts/tokens)). Si un día hace falta otro, se genera juntando otra vez las llaves.
> - Un servidor de verdad usa TLS, no `tls_disable`.
>
> Si algún día copias este laboratorio a un servidor, estas tres cosas son lo primero que cambias.

Comprueba el sello otra vez:

```
$ curl -s $VAULT_ADDR/v1/sys/seal-status | jq "{initialized, sealed, t, n, progress}"
{
  "initialized": true,
  "sealed": true,
  "t": 3,
  "n": 5,
  "progress": 0
}
```

Inicializado, pero sellado. Faltan los mayordomos.

## Paso 5 — Abrir el sello con 3 de 5 llaves

Cada llamada a `sys/unseal` entrega **una** llave. `jq -r '.keys[0]'` saca la primera del archivo, sin comillas:

```
$ LLAVE=$(jq -r '.keys[0]' secretos-locales/init.json)
$ curl -s -X PUT $VAULT_ADDR/v1/sys/unseal -d "{\"key\": \"$LLAVE\"}" | jq '{sealed, t, n, progress}'
{
  "sealed": true,
  "t": 3,
  "n": 5,
  "progress": 1
}
```

`progress: 1`: lleva una de tres. Repite con `.keys[1]`:

```
{
  "sealed": true,
  "t": 3,
  "n": 5,
  "progress": 2
}
```

Y con `.keys[2]`:

```
{
  "sealed": false,
  "t": 3,
  "n": 5,
  "progress": 0
}
```

`sealed: false`. Abierto. La salud ahora contesta 200:

```
$ curl -s -o /dev/null -w "%{http_code}\n" $VAULT_ADDR/v1/sys/health
200
```

Prueba que se sella solo al reiniciar:

```
$ docker compose restart vault
$ curl -s $VAULT_ADDR/v1/sys/seal-status | jq "{sealed, progress}"
{
  "sealed": true,
  "progress": 0
}
```

Así va a estar cada vez que prendas tu computadora o reinicies el contenedor. Para no escribir tres veces lo mismo, ábrelo con un ciclo:

```
for i in 0 1 2; do
  LLAVE=$(jq -r ".keys[$i]" secretos-locales/init.json)
  curl -s -X PUT $VAULT_ADDR/v1/sys/unseal -d "{\"key\": \"$LLAVE\"}" | jq -c '{sealed, progress}'
done
```

```
{"sealed":true,"progress":1}
{"sealed":true,"progress":2}
{"sealed":false,"progress":0}
```

¿Y si alguien mete una llave falsa?

```
$ curl -s -X PUT $VAULT_ADDR/v1/sys/unseal -d '{"key": "esta-no-es-una-llave"}'
{"errors":["'key' must be a valid hex or base64 string"]}
```

## Paso 6 — Identificarte: el token

Sin token, la ventanilla no te atiende:

```
$ curl -s -w " HTTP %{http_code}\n" $VAULT_ADDR/v1/sys/mounts
{"errors":["permission denied"]}
 HTTP 403
```

Exporta el token root a una variable de tu terminal. **Nunca lo pegues en un archivo que se suba**; lo lees de donde está:

```
export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)
```

El token viaja en el encabezado `X-Vault-Token`. Pregunta quién eres:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/auth/token/lookup-self | jq ".data | {display_name, policies, ttl}"
{
  "display_name": "root",
  "policies": [
    "root"
  ],
  "ttl": 0
}
```

`ttl: 0` quiere decir que no caduca nunca. Otra razón para revocarlo en la vida real.

Una aclaración: en el laboratorio, la "identificación" de la app es un token que tú creas a mano. Así se ve el mecanismo de cerca. En un sistema real, las aplicaciones obtienen su token solas, probando quiénes son con métodos como AppRole, Kubernetes u OIDC (la documentación de Vault los llama *métodos de autenticación*); eso queda fuera de esta serie.

## Paso 7 — Prender la bitácora antes que nada

La bitácora va primero, para que todo lo que hagas de aquí en adelante quede registrado. Un **dispositivo de auditoría** de tipo archivo escribe una línea JSON por cada petición y otra por cada respuesta ([File audit device](https://developer.hashicorp.com/vault/docs/audit/file)):

```
$ curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/audit/archivo \
    -d '{"type": "file", "options": {"file_path": "/vault/logs/audit.log"}}'
HTTP 204
```

204 quiere decir «hecho, y no tengo nada que contarte». La bitácora queda en `./vault/logs/audit.log` de tu máquina, gracias a la carpeta montada.

## Paso 8 — Guardar secretos: el motor KV versión 2

Prende el motor **KV v2** en la ruta `secret/`. Es un cajón de secretos llave-valor que guarda versiones ([KV v2](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2)):

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/secret -d '{"type": "kv", "options": {"version": "2"}}'
HTTP 204
```

Lista los motores que hay:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/mounts | jq -r ".data | keys[]"
agent-registry/
cubbyhole/
identity/
secret/
sys/
```

El tuyo es `secret/`. Los demás vienen de fábrica.

**Escribir.** Guarda el usuario y la contraseña de la app de la tienda. Los valores son de juguete; en la vida real la contraseña la generas con `openssl rand`, como hizo el guion:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/secret/data/tienda/postgres \
    -d '{"data": {"usuario": "app_tienda", "password": "Pepino-2026"}}' | jq .data
{
  "created_time": "2026-10-18T14:47:29.493537576Z",
  "custom_metadata": null,
  "deletion_time": "",
  "destroyed": false,
  "version": 1
}
```

Fíjate en la ruta: `secret/`**`data/`**`tienda/postgres`. En KV v2, los datos van bajo `data/` y la información sobre las versiones, bajo `metadata/`. Es la trampa número uno de KV v2; está en la tabla de errores.

**Leer:**

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq .data
{
  "data": {
    "password": "Pepino-2026",
    "usuario": "app_tienda"
  },
  "metadata": {
    "created_time": "2026-10-18T14:47:29.493537576Z",
    "custom_metadata": null,
    "deletion_time": "",
    "destroyed": false,
    "version": 1
  }
}
```

**Una versión nueva.** Cambia la contraseña:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/secret/data/tienda/postgres \
    -d '{"data": {"usuario": "app_tienda", "password": "Mango-2026"}}' | jq -c ".data | {version, created_time}"
{"version":2,"created_time":"2026-10-18T14:47:29.522529264Z"}
```

La versión 1 sigue ahí. Pídela con `?version=1`:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/postgres?version=1" | jq -c .data.data
{"password":"Pepino-2026","usuario":"app_tienda"}
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c ".data.data, .data.metadata.version"
{"password":"Mango-2026","usuario":"app_tienda"}
2
```

Es como el historial de versiones de un documento en la nube: puedes regresar a la de ayer si la de hoy salió mal.

**Borrar (con red de seguridad).** `DELETE` sobre `data/` borra la última versión, pero de forma reversible:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X DELETE $VAULT_ADDR/v1/secret/data/tienda/postgres
HTTP 204
```

Al leer ya no hay datos, la respuesta trae la hora del borrado y el código es 404:

```
null
"2026-10-18T14:47:29.564180533Z"
HTTP 404
```

**Recuperar.** `undelete` la regresa:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X POST \
    $VAULT_ADDR/v1/secret/undelete/tienda/postgres -d '{"versions": [2]}'
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c .data.data
{"password":"Mango-2026","usuario":"app_tienda"}
```

**Destruir (sin regreso).** `destroy` borra para siempre las versiones que le digas. Destruye la 1, la contraseña vieja:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X PUT \
    $VAULT_ADDR/v1/secret/destroy/tienda/postgres -d '{"versions": [1]}'
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/postgres?version=1" | jq -c ".data.metadata | {version, destroyed}"
{"version":1,"destroyed":true}
```

**Los metadatos** te cuentan la historia del secreto, incluido quién creó cada versión:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/metadata/tienda/postgres \
    | jq ".data | {current_version, versions: (.versions | map_values({destroyed, quien: .created_by.actor}))}"
{
  "current_version": 2,
  "versions": {
    "1": {
      "destroyed": true,
      "quien": "root"
    },
    "2": {
      "destroyed": false,
      "quien": "root"
    }
  }
}
```

En esa consulta de `jq`, `map_values(...)` recorre cada versión y deja de ella solo dos datos: si fue destruida y quién la creó.

Y para ver qué secretos hay en una carpeta, el verbo `LIST`:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X LIST $VAULT_ADDR/v1/secret/metadata/tienda | jq -c .data
{"keys":["postgres"]}
```

### La alternativa: el comando `vault` dentro del contenedor

Todo lo anterior también se hace con el comando `vault`, que viene dentro del contenedor. `-e VAULT_TOKEN` le pasa tu variable:

```
$ docker compose exec -e VAULT_TOKEN vault vault kv get secret/tienda/postgres
======= Secret Path =======
secret/data/tienda/postgres

======= Metadata =======
Key                Value
---                -----
created_time       2026-10-18T14:47:29.522529264Z
custom_metadata    <nil>
deletion_time      n/a
destroyed          false
version            2

====== Data ======
Key         Value
---         -----
password    Mango-2026
usuario     app_tienda
```

Guarda con él un segundo secreto, el de la nómina, que vas a usar para probar permisos:

```
$ docker compose exec -e VAULT_TOKEN vault vault kv put secret/nomina/banco cuenta=0123456789 clave=Aguacate-99
====== Secret Path ======
secret/data/nomina/banco
...
version            1
```

Fíjate en que el comando agrega el `data/` solo. Por eso `curl` enseña más: ves la ruta real.

## Paso 9 — Políticas: cada quien su llave

Una **política** dice qué rutas puede tocar un token y qué puede hacer en ellas. Crea la carpeta `politicas/` y dentro el archivo `politicas/lectura-tienda.hcl`:

```hcl
# La app de la tienda puede LEER sus secretos. Nada más.
path "secret/data/tienda/*" {
  capabilities = ["read"]
}
```

`*` quiere decir «cualquier cosa debajo de `tienda/`». Las capacidades más usadas son `read`, `create`, `update`, `delete` y `list`. Lo que no está, está negado.

Súbela. La API espera el texto de la política dentro de un JSON; `jq --rawfile p archivo` lee el archivo y lo guarda en la variable `p`; `-n` le dice a `jq` que no espere datos de entrada, y el `\$p` lleva diagonal para que tu terminal no lo confunda con una variable suya. Así `jq` envuelve la política en el JSON sin que tengas que escaparla a mano:

```
$ jq -n --rawfile p politicas/lectura-tienda.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/lectura-tienda -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X LIST $VAULT_ADDR/v1/sys/policies/acl | jq -c .data.keys
["default","default-ceiling","lectura-tienda","root"]
```

`-d @-` le dice a `curl` «el cuerpo viene de la entrada», o sea, de lo que le pasó `jq` por el tubo.

Ahora crea un **token para la app**, con esa política y una hora de vida. El token completo va a `secretos-locales/`, nunca a la pantalla:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/create \
    -d '{"policies": ["lectura-tienda"], "ttl": "1h", "display_name": "app-tienda"}' \
    > secretos-locales/token-app.json
$ jq ".auth | {client_token: (.client_token[0:9] + \"...\"), policies, lease_duration, renewable}" secretos-locales/token-app.json
{
  "client_token": "hvs.CAESI...",
  "policies": [
    "default",
    "lectura-tienda"
  ],
  "lease_duration": 3600,
  "renewable": true
}
$ export APP_TOKEN=$(jq -r .auth.client_token secretos-locales/token-app.json)
```

La política `default` viene incluida en todos los tokens; deja hacer cosas básicas, como consultar tu propio token. `lease_duration: 3600` son 3,600 segundos: una hora.

Prueba los tres casos. **Leer lo suyo:**

```
$ curl -s -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c .data.data
{"password":"Mango-2026","usuario":"app_tienda"}
```

Código 200. **Leer la nómina:**

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/nomina/banco
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

**Escribir en lo suyo:**

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" -X POST \
    $VAULT_ADDR/v1/secret/data/tienda/postgres -d '{"data": {"password": "me-la-robe"}}'
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Dos 403. La ventanilla dijo que no. Y puedes preguntarle a Vault qué te deja hacer en cada ruta, sin intentarlo:

```
$ curl -s -H "X-Vault-Token: $APP_TOKEN" -X POST $VAULT_ADDR/v1/sys/capabilities-self \
    -d '{"paths": ["secret/data/tienda/postgres", "secret/data/nomina/banco"]}' \
    | jq -c "{tienda: .[\"secret/data/tienda/postgres\"], nomina: .[\"secret/data/nomina/banco\"]}"
{"tienda":["read"],"nomina":["deny"]}
```

## Paso 10 — La bitácora: quién pidió qué

Cada línea de `vault/logs/audit.log` es un JSON. Cuántas hay ya:

```
$ wc -l vault/logs/audit.log
      62 vault/logs/audit.log
```

Las últimas respuestas, resumidas: hora, quién, qué operación, qué ruta y si hubo error:

```
$ tail -n 6 vault/logs/audit.log | jq -c "select(.type == \"response\") | {hora: .time, quien: .auth.display_name, operacion: .request.operation, ruta: .request.path, error: .error}"
{"hora":"2026-10-18T14:47:54.325141694Z","quien":"token-app-tienda","operacion":"update","ruta":"secret/data/tienda/postgres","error":"1 error occurred:\n\t* permission denied\n\n"}
{"hora":"2026-10-18T14:47:54.338083991Z","quien":"token-app-tienda","operacion":"update","ruta":"sys/capabilities-self","error":null}
{"hora":"2026-10-18T14:47:54.351637479Z","quien":"token-app-tienda","operacion":"read","ruta":"auth/token/lookup-self","error":null}
```

Ahí está el intento de escritura de la app, con su nombre (`token-app-tienda`: Vault le pone `token-` adelante al `display_name`) y su `permission denied`. Esto es lo que Iván no tenía el sábado: **nombre y apellido de cada intento**.

¿Quién leyó el secreto de la tienda?

```
$ jq -c "select(.type == \"response\" and .request.path == \"secret/data/tienda/postgres\" and .request.operation == \"read\") | {quien: .auth.display_name, error}" vault/logs/audit.log
{"quien":"root","error":null}
...
{"quien":"token-app-tienda","error":null}
```

Varias lecturas de `root` (tú, configurando) y una de la app.

Ahora lo interesante. ¿La bitácora guardó la contraseña?

```
$ jq -c "select(.type == \"response\" and .request.path == \"secret/data/tienda/postgres\" and .auth.display_name == \"token-app-tienda\") | .response.data" vault/logs/audit.log | head -1
{"data":{"password":"hmac-sha256:bbda6f946e50152cf8b72cd5a9716a077096420551a4c5a7cb395e4f7eddd734","usuario":"hmac-sha256:becdf07b09b37a0b8d310c8f5e99dac229b4cc1b80e092e4b9107ee0f7483212"},"metadata":{...}}
$ grep -c "Mango-2026" vault/logs/audit.log
0
```

No. Por defecto, Vault escribe en la bitácora una **huella** (un HMAC-SHA256) de los valores de texto sensibles, no el valor ([Audit devices](https://developer.hashicorp.com/vault/docs/audit)). Los números y los valores sí/no no los convierte en huella; por eso conviene guardar en Vault secretos de texto, como en este laboratorio. Una huella es como la huella digital de una persona: sirve para comprobar si dos cosas son la misma, pero no te deja reconstruir a la persona. Así, quien lea la bitácora no se lleva las contraseñas.

Y si un día necesitas saber si la contraseña que apareció en un chat es la que la app leyó, le pides a Vault la huella de ese texto y comparas:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/sys/audit-hash/archivo \
    -d '{"input": "Mango-2026"}' | jq -r .data.hash
hmac-sha256:bbda6f946e50152cf8b72cd5a9716a077096420551a4c5a7cb395e4f7eddd734
```

Es la misma huella. Coincide.

Para cerrar, la app puede **revocar su propio token** cuando termina. Después de eso, ya no le sirve:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/revoke-self
HTTP 204
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres
{"errors":["2 errors occurred:\n\t* permission denied\n\t* invalid token\n\n"]}
 HTTP 403
```

---

👉 **Si eres de Administración:** las llaves de Shamir son el equivalente técnico de las **firmas mancomunadas** de una cuenta de banco: para mover dinero firman dos de tres apoderados, y ninguno puede solo. La política con 403 es la **segregación de funciones**: quien captura no autoriza, quien cobra no concilia. Y la bitácora con huellas es una auditoría que registra quién tocó cada expediente sin fotocopiar el expediente. Si te toca revisar los controles de un sistema, pregunta por estas tres cosas con esas palabras; casi siempre te entienden.

---

## Ejercicios de la sesión 2

Las soluciones están al final.

**Ejercicio 6 — El torniquete.** Crea una carpeta nueva, `lab-prueba`, y copia ahí solo tres archivos: `.gitignore`, `compose.yaml` y `iniciar.sh`. Hazlo así, con copia nueva, y no copiando tu carpeta ya usada: esa ya trae un `.env` y el ejercicio no podría demostrar nada. Dentro de `lab-prueba`, borra la línea `.env` del `.gitignore` y corre `./iniciar.sh`.

**Cómo compruebas:** antes de correr el guion, `ls -a` no debe mostrar ningún `.env`. Después, debe decir `ALTO: .gitignore no tiene la regla '.env'.`, salir con código 1 (compruébalo con `echo $?` justo después) y **no** crear el archivo `.env` (compruébalo con `ls -a`).

**Ejercicio 7 — Los mayordomos.** Reinicia Vault con `docker compose restart vault`. Ábrelo usando las llaves 4 y 5 (`.keys[3]` y `.keys[4]`) y después la 1.

a) ¿Importa cuáles tres llaves uses?
b) ¿Qué ves en `progress` después de la segunda llave?

**Cómo compruebas:** al final, `sys/health` debe contestar `200`.

**Ejercicio 8 — Tu propio secreto con versiones.** Guarda en `secret/data/tienda/correo` un usuario `avisos` y una contraseña que generes con `openssl rand -hex 12`. Después cámbiala por otra generada igual. Al final:

a) Lee la versión 1 y la 2.
b) Borra la 2 con `DELETE`, comprueba el 404 y recupérala.
c) Muestra con `metadata/` cuántas versiones hay.

**Cómo compruebas:** `current_version` debe ser `2` y la lectura final debe dar la segunda contraseña.

**Ejercicio 9 — Una política para contabilidad.** Escribe `politicas/contabilidad.hcl`: puede **leer** `secret/data/nomina/*` y **listar** `secret/metadata/nomina/*`, nada más. Súbela, crea un token con ella (guárdalo en `secretos-locales/`) y prueba:

a) Leer `secret/data/nomina/banco`.
b) Leer `secret/data/tienda/postgres`.
c) Escribir en `secret/data/nomina/banco`.

**Cómo compruebas:** a) 200; b) 403; c) 403. Y `sys/capabilities-self` para la ruta de la nómina debe decir `["read"]`.

**Ejercicio 10 — El detective.** Con `jq` sobre `vault/logs/audit.log`, saca una lista de **todas las respuestas con error**, mostrando quién y qué ruta.

**Cómo compruebas:** deben aparecer, por lo menos, los dos 403 de `token-app-tienda` del paso 9 y los dos 403 del ejercicio 9 (b y c). Si tu lista sale vacía, revisa que filtras `.type == "response"` y que preguntas por `.error != null`.

---

## Errores comunes (y cómo darte cuenta)

| Error | Cómo se ve | Cómo darte cuenta | Qué hacer |
|---|---|---|---|
| Olvidar `data/` en la ruta de KV v2 | `curl .../v1/secret/tienda/postgres` da 404 con el aviso `Invalid path for a versioned K/V secrets engine` | La ruta no tiene `data/` | Datos en `secret/data/...`; versiones en `secret/metadata/...` |
| Política escrita sin `data/` | Pusiste `path "secret/tienda/*"` y el token recibe 403 en lo suyo | `sys/capabilities-self` dice `deny` | La política usa la ruta de la API: `secret/data/tienda/*` |
| Vault sellado después de reiniciar | Todo contesta `{"errors":["Vault is sealed"]}` con código 503 | `sys/seal-status` dice `sealed: true` | Ábrelo con 3 llaves. Es lo que debe pasar, no una falla |
| La variable `VAULT_TOKEN` vacía | 403 aunque uses el token root | `echo ${#VAULT_TOKEN}` da `0` | Cada terminal nueva empieza sin variables: vuelve a exportarla |
| Comillas simples alrededor de una variable | `-d '{"key": "$LLAVE"}'` manda el texto `$LLAVE` | Vault dice que la llave no es válida | Dentro de comillas simples, la terminal no sustituye variables. Usa comillas dobles y escapa las internas: `"{\"key\": \"$LLAVE\"}"` |
| Pegar el token en un archivo del repo | El token aparece en `git status` o en un commit | `git log -p -S hvs.` lo encuentra | Los tokens viven en `secretos-locales/` y en variables de la terminal. Si se subió: revócalo |
| Puerto ocupado al arrancar | `bind: address already in use` | `lsof -nP -iTCP:5432 -sTCP:LISTEN` muestra otro proceso (cambia 5432 por 8200 o 3306 si es otro servicio) | Cambia el puerto en `.env` (`PUERTO_POSTGRES=15432`, `PUERTO_VAULT` o `PUERTO_MARIADB`) y vuelve a correr `docker compose up -d`; si cambiaste `PUERTO_VAULT`, vuelve a definir `VAULT_ADDR` |

---

## Repaso para la próxima sesión

La sesión 3 empieza con estas tres preguntas. Contéstalas sin ver:

1. ¿Por qué Vault arranca sellado, y cuántas llaves necesitas por defecto para abrirlo?
2. Un token recibe 403. ¿Cuáles son dos causas posibles, y qué ruta de Vault te dice qué puede hacer ese token?
3. Si alguien roba la bitácora de auditoría, ¿se lleva las contraseñas? ¿Por qué?

🔁 **La próxima semana:** el respaldo robado tenía ocho mil CURP, y la llave para leerlas iba al lado. Aprendes a cifrar con Vault sin que tu programa tenga nunca la llave, guardas los datos cifrados en PostgreSQL y descubres cuántas veces se llevaron ese respaldo.

**Antes de irte:** apaga el laboratorio con `docker compose stop`. Tus datos se quedan en las carpetas. La próxima vez, `docker compose start` y abre el sello con el ciclo del paso 5.

---

## Soluciones (no las veas antes de intentarlo)

**Repaso de la sesión 1.**

1. Cualesquiera cuatro de: la contraseña en el código o en un archivo que se sube; el `.env` que viaja por chat; la misma contraseña para todos y para siempre; nadie sabe quién la usó; el que se fue todavía la sabe; la llave de cifrado junto a los datos.
2. Porque git guarda la historia: la contraseña sigue en los cambios anteriores, y cualquiera que haya clonado el repositorio tiene su copia. Borrar no deshace las copias; cambiarla sí las vuelve inútiles.
3. Se parece en que mandas datos y recibes datos cifrados sin que la llave salga. Se diferencia en que un HSM es un aparato físico con protecciones contra manipulación (que tan fuertes sean depende del modelo), y Vault es software en un servidor; Transit es un motor de Vault que ofrece las operaciones de cifrado por API.

**Ejercicio 6.** La salida es:

```
ALTO: .gitignore no tiene la regla '.env'.
Sin ella, las contraseñas que voy a generar podrían terminar en git. No sigo.
```

`echo $?` da `1` y `ls -a` no muestra `.env`.

**Ejercicio 7.** a) No importa: cualquier combinación de 3 de las 5 sirve. b) `progress: 2` y `sealed: true`. Con la tercera, `sealed: false`.

**Ejercicio 8.** Una forma:

```
P1=$(openssl rand -hex 12)
curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/secret/data/tienda/correo \
  -d "{\"data\": {\"usuario\": \"avisos\", \"password\": \"$P1\"}}" | jq .data.version
P2=$(openssl rand -hex 12)
curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/secret/data/tienda/correo \
  -d "{\"data\": {\"usuario\": \"avisos\", \"password\": \"$P2\"}}" | jq .data.version
curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/correo?version=1" | jq -c .data.data
curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/correo?version=2" | jq -c .data.data
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X DELETE $VAULT_ADDR/v1/secret/data/tienda/correo
curl -s -o /dev/null -w "%{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/correo
curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/secret/undelete/tienda/correo -d '{"versions": [2]}'
curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/metadata/tienda/correo | jq .data.current_version
curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/correo \
  | jq -e --arg p "$P2" '.data.data.password == $p'
```

Las dos primeras dan `1` y `2`; las dos lecturas con `?version=` muestran la primera y la segunda contraseña; el `DELETE` da `204`, la lectura siguiente `404`, y `current_version` da `2`. La última línea imprime `true` si la lectura final trae la segunda contraseña. Fíjate en que las contraseñas nunca las escribiste tú: salieron de `openssl` y viajaron en una variable.

**Ejercicio 9.** La política:

```hcl
path "secret/data/nomina/*" {
  capabilities = ["read"]
}
path "secret/metadata/nomina/*" {
  capabilities = ["list"]
}
```

Se sube y se usa igual que `lectura-tienda`, cambiando el nombre. Los resultados esperados: 200, 403, 403.

**Ejercicio 10.**

```
jq -c 'select(.type == "response" and .error != null) | {quien: .auth.display_name, ruta: .request.path, error}' vault/logs/audit.log
```

Fíjate en que aquí el filtro va entre comillas simples, y por eso las comillas dobles de adentro no llevan diagonal.

---

## Lo que sigue

En la sesión 3 usas PostgreSQL desde tu terminal con `psql`. Comprueba que lo tienes con `psql --version`. Si no, instala el cliente: `sudo apt install postgresql-client` en Linux, o `brew install libpq` en macOS (y sigue la indicación que te da para agregarlo a tu `PATH`).

---

*Escribo desde lo que vemos todos los días en Hábil, donde construimos sistemas para banca, seguros y empresas en México. Si en tu trabajo o en el negocio de tu familia se topan con un problema así, platiquemos: [habil.mx](https://habil.mx)*
