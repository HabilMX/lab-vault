# Vault desde cero (4): contraseñas que se cambian solas

*Usuarios de base de datos que nacen cuando los pides y mueren a los dos minutos, contraseñas que rotan cada minuto sin que nadie edite un archivo, y un programa de Python que se conecta a PostgreSQL sin conocer ninguna contraseña. Y el final del misterio de las 3:17.*

*Vault desde cero · sesión 4 de 4*

## Repaso de la sesión 3

Contesta sin ver. Las respuestas están en las soluciones.

1. ¿Qué significan las tres partes de `vault:v2:SmfKDK1u...`?
2. Rotaste la llave. ¿Qué pasa con los datos que ya estaban cifrados, y qué operación los sube a la versión nueva sin que nadie vea el dato?
3. ¿Por qué un token que solo puede cifrar es útil para un formulario de alta?

> **El laboratorio de esta sesión** está en el repositorio público [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Ármalo tú primero; el repositorio es para comparar cuando algo no te salga igual. No trae ninguna contraseña: el laboratorio las genera al arrancar.

## Objetivos de esta sesión

| # | Al terminar puedes… | Lo demuestra |
|---|---|---|
| 1 | **Configurar** el motor Database de Vault con un usuario dedicado, sin usar el superusuario | Pasos 2 y 3 |
| 2 | **Pedir** credenciales dinámicas, **entrar** con `psql` y **comprobar** que dejan de servir al caducar o al revocarlas | Ejercicios 16, 17 y 19 |
| 3 | **Poner** un usuario existente bajo rotación automática y **demostrar** que la contraseña vieja ya no entra | Ejercicio 18 |
| 4 | **Crear** una credencial dinámica de solo lectura en MariaDB con el cliente `mariadb`, comprobar que no puede modificar datos y revocarla | Paso 10 |
| 5 | **Ejecutar y modificar** un script de Python que pide sus credenciales a Vault, consulta PostgreSQL y no guarda ninguna contraseña de base de datos | Paso 12 y ejercicio 20 |

---

## Escenario (ficción) — Capítulo 9: Martes, 9:00 a.m.

Iván marca un número que no ha marcado en ocho meses.

—¿Toño? Habla Iván, de Canasta Morada. Oye, una pregunta rara. ¿Te suena un servidor que se llama TR-REPORTES?

Silencio. Luego, una carcajada.

—¡No manches! ¿Sigue prendido?

Toño lo cuenta sin pena. Hace dos años y medio, contabilidad pidió un reporte semanal de los clientes que pagan con vales, con su CURP, para cuadrar con la empresa de vales. La base de datos estaba muy cargada en el día, así que Toño rentó un servidor barato en la nube, con la tarjeta de la empresa, y le puso un programa:

- Cada sábado a las 3:17 se conectaba a la base de datos con la contraseña de `app_tienda`.
- Descargaba el respaldo de la noche y `llave.txt`, para descifrar las CURP.
- Armaba un Excel y lo mandaba al correo `reportes@`.

—Y cuando me fui, se me olvidó decirles. Perdón.

Rocío revisa: el buzón `reportes@` tiene ciento diecisiete correos sin abrir. Nadie lo revisaba desde que el jefe de contabilidad anterior se fue.

No había ningún ladrón.

Había algo peor: una puerta abierta que nadie sabía que existía. Ciento diecisiete copias de ocho mil CURP, con la llave al lado, en un servidor que nadie controlaba, en otro país, pagado cada mes con la tarjeta de la empresa.

Y sin bitácora por identidad ni credenciales que caducan, era imposible distinguirlo de un ataque.

---

## Capítulo 10: Sábado, 3:17 a.m. Un mes después

El servidor TR-REPORTES ya no existe; Iván lo borró con Toño en videollamada, mirando juntos cada carpeta.

El reporte de vales lo hace ahora un programa nuevo, dentro de los servidores de Canasta Morada. A las 3:17 le pide a Vault una credencial para la base de datos. Vault crea un usuario que no existía un segundo antes, con permiso solo de lectura y con fecha de caducidad. El programa trabaja cuatro minutos. A las 3:21 el usuario ya no existe.

La contraseña de la base de datos que usa Vault para crear esos usuarios no la sabe nadie: ni Iván, ni doña Clara. Vault la cambió el primer día.

El celular de Iván no vibra.

Valeria escribe el informe del incidente. En la última línea pone: *«Nunca vamos a saber si alguien vio el repositorio público en esas horas. Por eso cambiamos la contraseña. La próxima vez que alguien suba un `.env` por error, no va a estar ahí la contraseña de la aplicación ni la de Vault. Aun así, lo que ese archivo contenga —como las contraseñas de administración— hay que cambiarlo de inmediato.»*

*(Fin del escenario.)*

---

## Por qué importa

En las sesiones 2 y 3 los secretos ya no vivían en archivos, pero seguían siendo **los mismos durante meses**. Si alguien leía la contraseña de `app_tienda` en Vault, le servía hasta que alguien la cambiara a mano.

Hoy das el último paso: **contraseñas que no existen hasta que las pides y que se mueren solas**. Es la diferencia entre la llave de tu casa y el gafete de visitante de un edificio de oficinas. La llave sirve años. El gafete te lo dan en recepción con tu nombre, abre solo el piso al que vas y a las 6 de la tarde deja de funcionar. Si lo pierdes en el elevador, a nadie le importa.

## Las ideas de hoy

**Credencial dinámica.** Un usuario de base de datos que Vault crea en el momento en que lo pides, con una contraseña al azar, y que borra cuando caduca. Cada programa, y cada vez que lo pide, recibe uno distinto. Si se filtra, sirve minutos.

**Arrendamiento (*lease*) y TTL.** Cada credencial dinámica viene con un arrendamiento: un contrato con fecha de vencimiento. El **TTL** (*time to live*, tiempo de vida) es cuánto dura. Como el estacionamiento de la plaza: tu boleto marca la hora de entrada y vence; si quieres más tiempo, pagas otra vez (renuevas), hasta un máximo.

**Revocar.** Cancelar un arrendamiento antes de tiempo. Vault borra el usuario de la base de datos en ese momento.

**Rol estático con rotación.** Hay usuarios que no puedes cambiar por uno nuevo cada vez, porque otros sistemas los conocen por nombre. Para esos, Vault conserva el usuario y le **cambia la contraseña** cada cierto tiempo, con `rotation_period`. Quien la necesita se la pide a Vault y siempre recibe la vigente ([Database secrets engine](https://developer.hashicorp.com/vault/docs/secrets/databases)).

**La credencial de Vault en la base de datos.** Para crear y borrar usuarios, Vault necesita su propio usuario en la base de datos. La documentación advierte que, si le pides a Vault que rote esa contraseña con `rotate-root`, después **nadie** la va a conocer, y recomienda crear un usuario dedicado para Vault en lugar de usar el superusuario ([API del motor Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). Es lo que hacemos: un usuario `vault_admin` con permisos justos, no el `postgres` que lo puede todo.

---

## Paso 1 — Prepara la terminal

Laboratorio arriba, sello abierto, token exportado y variables de PostgreSQL cargadas desde `.env`:

```
docker compose start
set -a; source .env; set +a
export VAULT_ADDR=http://127.0.0.1:$PUERTO_VAULT
until curl -fsS -o /dev/null "$VAULT_ADDR/v1/sys/seal-status"; do echo "Espero a que Vault inicie..."; sleep 1; done
until docker compose exec -T postgres pg_isready -h 127.0.0.1 -U postgres -q; do echo "Espero a que PostgreSQL inicie..."; sleep 1; done
for i in 0 1 2; do
  LLAVE=$(jq -r ".keys[$i]" secretos-locales/init.json)
  curl -s -X PUT $VAULT_ADDR/v1/sys/unseal -d "{\"key\": \"$LLAVE\"}" | jq -c '{sealed, progress}'
done
export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)
export PGHOST=127.0.0.1 PGPORT=$PUERTO_POSTGRES PGDATABASE=tienda
```

Fíjate en que esta vez **no** exportamos `PGUSER` ni `PGPASSWORD`: hoy vas a entrar a PostgreSQL con varios usuarios distintos, y cada comando dirá cuál.

Las salidas de esta lección son reales, pero vienen de corridas independientes; por eso sus horas, nombres de usuario y números de versión (como `vault:v3:`, que depende de cuántas veces rotaste la llave en la sesión 3) no forman una sola secuencia. Las tuyas serán distintas.

## Paso 2 — Un usuario para Vault, y uno viejo para rotar

Crea en PostgreSQL dos usuarios, con una contraseña inicial generada al azar que se guarda en `secretos-locales/` (git la ignora):

- `vault_admin`: el que usará Vault. Puede crear usuarios (`CREATEROLE`) y dar permiso de lectura sobre las tablas (`WITH GRANT OPTION`). No es superusuario.
- `reportes`: un usuario «de toda la vida», como el que usan los reportes. Lo vas a poner bajo rotación automática.

Cada uno recibe su **propia** contraseña inicial: si compartieran la misma, quien consiguiera la de `reportes` entraría como `vault_admin`, que puede crear usuarios.

**Punto de control antes de repetir.** Este paso espera un laboratorio nuevo. Si lo repites, escribirías contraseñas nuevas en los archivos de `secretos-locales/` que ya no coinciden con las que tiene PostgreSQL. Si ves `role already exists` o que el motor `database/` ya existe, no vuelvas a generar los archivos iniciales: comprueba el estado y haz solo los pasos que falten.

| Si ves | Significa | Qué hacer |
|---|---|---|
| `CREATE ROLE` o `HTTP 204` | Avanzaste bien | Sigue |
| `role "vault_admin" already exists` | El paso 2 ya corrió, total o parcialmente | No regeneres los archivos iniciales |
| `path is already in use` | El motor Database ya está montado | Salta a leer o configurar la conexión (paso 3) |

`psql -v nombre=...` define una variable que adentro se usa como `:'nombre'`. Así la contraseña no queda literal en el comando ni en tu historial. `psql` la sustituye antes de enviar el SQL a PostgreSQL, así que la contraseña sí viaja dentro de la sentencia; por eso, fuera del laboratorio, se usa TLS y se evita registrar las sentencias que contienen contraseñas:

```
$ VAULT_ADMIN_PASS=$(openssl rand -hex 16); echo "$VAULT_ADMIN_PASS" > secretos-locales/vault_admin_inicial.txt
$ REPORTES_PASS=$(openssl rand -hex 16); echo "$REPORTES_PASS" > secretos-locales/reportes_inicial.txt
$ PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -v vault_pass="$VAULT_ADMIN_PASS" -v reportes_pass="$REPORTES_PASS" <<SQL
CREATE ROLE vault_admin WITH LOGIN CREATEROLE PASSWORD :'vault_pass';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO vault_admin WITH GRANT OPTION;
CREATE ROLE reportes WITH LOGIN PASSWORD :'reportes_pass';
GRANT SELECT ON clientes TO reportes;
GRANT reportes TO vault_admin WITH ADMIN OPTION;
SQL
CREATE ROLE
GRANT
CREATE ROLE
GRANT
GRANT ROLE
```

La última línea le da a `vault_admin` permiso de administrar a `reportes`, que es lo que necesita para cambiarle la contraseña. Desde PostgreSQL 16, un usuario con `CREATEROLE` solo puede modificar a los usuarios que creó o que le asignaron así.

## Paso 3 — Conectar Vault con PostgreSQL

Prende el motor Database:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/database -d '{"type": "database"}'
HTTP 204
```

Ahora la conexión. La contraseña de `vault_admin` la lee `jq` del archivo con `--arg`: no la escribes tú, no aparece en tu historial. En `connection_url`, `{{username}}` y `{{password}}` los llena Vault, y el servidor se llama `postgres` porque Vault lo busca por su nombre dentro de la red de Docker Compose, no por `127.0.0.1`. `allowed_roles` dice qué roles pueden usar esta conexión:

```
$ jq -n --arg p "$(cat secretos-locales/vault_admin_inicial.txt)" '{
    plugin_name: "postgresql-database-plugin",
    connection_url: "postgresql://{{username}}:{{password}}@postgres:5432/tienda?sslmode=disable",
    username: "vault_admin",
    password: $p,
    allowed_roles: ["lector", "reportes"]
  }' | curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/config/postgres -d @-
HTTP 204
```

Vault probó la conexión antes de guardarla (`verify_connection` viene prendido); si la contraseña estuviera mal, aquí te diría que no. Lee la configuración:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/config/postgres | jq .data
{
  "allowed_roles": [
    "lector",
    "reportes"
  ],
  "connection_details": {
    "connection_url": "postgresql://{{username}}:{{password}}@postgres:5432/tienda?sslmode=disable",
    "username": "vault_admin"
  },
  ...
  "plugin_name": "postgresql-database-plugin",
  ...
  "verify_connection": true
}
```

La contraseña no aparece. Una vez que Vault la tiene, no la devuelve ni al token root.

## Paso 4 — Un rol para credenciales dinámicas

Un **rol** es la receta para crear un usuario. Guárdala en `roles/lector-postgres.json`. Ese archivo, `politicas/app-python.hcl` y `python/clientes.py` ya vienen en la carpeta del laboratorio; si prefieres escribirlos tú, crea las carpetas con `mkdir -p roles politicas python`, abre el archivo en tu editor, pega el bloque completo sin modificarlo y guárdalo antes de ejecutar el siguiente comando:

```json
{
  "db_name": "postgres",
  "creation_statements": [
    "CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';",
    "GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";"
  ],
  "revocation_statements": [
    "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM \"{{name}}\";",
    "DROP ROLE IF EXISTS \"{{name}}\";"
  ],
  "default_ttl": "2m",
  "max_ttl": "10m"
}
```

- `creation_statements`: el SQL que corre Vault al crear el usuario. `VALID UNTIL '{{expiration}}'` hace que el propio PostgreSQL rechace la contraseña al vencer, aunque Vault tarde en borrarlo. Es el ejemplo de la documentación ([PostgreSQL](https://developer.hashicorp.com/vault/docs/secrets/databases/postgresql)).
- `revocation_statements`: el SQL para borrarlo. Por qué lo escribimos a mano lo vas a ver en el paso 6, con un error real.
- `default_ttl` de 2 minutos para que veas la caducidad sin esperar; en la vida real suelen ser minutos u horas. `max_ttl`: aunque renueves, nunca más de 10.

Súbelo. `-d @archivo` le dice a `curl` que mande el contenido del archivo:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/roles/lector -d @roles/lector-postgres.json
HTTP 204
```

## Paso 5 — Pide una credencial y entra

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector > secretos-locales/creds-lector.json
$ jq "{lease_id, lease_duration, renewable, username: .data.username, password: (.data.password[0:6] + \"...\")}" secretos-locales/creds-lector.json
{
  "lease_id": "database/creds/lector/rOpuliUuxFqc2UbdHMofQV8S",
  "lease_duration": 120,
  "renewable": true,
  "username": "v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049",
  "password": "INYcGz..."
}
```

Un usuario que no existía hace un segundo. El nombre lleva quién lo pidió (`root`), el rol (`lector`), un pedazo al azar y la hora en formato Unix. En este laboratorio, `root` no es una persona: es solo el token de administración. En producción no se le entrega a personas ni a aplicaciones; cada persona o programa entra con su propia identidad (por ejemplo OIDC, AppRole o Kubernetes), para que el nombre del usuario temporal sí diga quién lo pidió. Entra con él:

```
$ export PGUSER=$(jq -r .data.username secretos-locales/creds-lector.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-lector.json)
$ psql -c "SELECT current_user, nombre, left(curp, 9) FROM clientes;"
                 current_user                  | nombre |   left
-----------------------------------------------+--------+-----------
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | Pepe   | vault:v3:
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | María  | vault:v3:
(2 rows)
```

Funciona, y fíjate: hasta con usuario propio, las CURP siguen cifradas. Este lector puede ver la tabla, pero no las CURP; para eso necesitaría además permiso de Transit. Intenta borrar:

```
$ psql -c "DELETE FROM clientes;"
ERROR:  permission denied for table clientes
```

Solo lectura, como dice el rol. Y desde el superusuario puedes ver al nuevo usuario con su fecha de caducidad:

```
$ PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -c "SELECT rolname, rolvaliduntil FROM pg_roles WHERE rolname LIKE 'v-%';"
                    rolname                    |     rolvaliduntil
-----------------------------------------------+------------------------
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | 2026-10-18 14:52:54+00
(1 row)
```

## Paso 6 — Revocar… y un error de verdad

**Nota de lectura.** El primer bloque reproduce un error de una prueba anterior. No ejecutes los comandos que usan `secretos-locales/creds-lector-2.json`: ese archivo no se crea en el recorrido actual. En tu laboratorio, el rol del paso 4 ya trae `revocation_statements`; la revocación correcta la practicas tú en el ejercicio 17, con `creds-16.json`.

La primera vez que probamos esta lección, el rol **no** tenía `revocation_statements`. Pedimos una segunda credencial y la revocamos antes de tiempo con `sys/leases/revoke`:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-lector-2.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
{"errors":["failed to revoke entry: resp: (*logical.Response)(nil) err: could not perform all revocation statements: ERROR: permission denied for sequence clientes_id_seq (SQLSTATE 42501)"]}
```

Código 400. Sin `revocation_statements`, Vault usa el SQL de borrado por defecto del plugin de PostgreSQL, que intenta quitarle al usuario permisos sobre **todo** lo del esquema `public`, incluidas las secuencias (los contadores que generan los `id`). Nuestro `vault_admin`, con permisos justos, no tiene autoridad sobre la secuencia `clientes_id_seq`, y PostgreSQL dijo que no. El usuario temporal quedó a medias: sin permisos sobre la tabla, pero sin borrar.

Es un buen error: aparece **porque** no le dimos a Vault el superusuario. La solución correcta no es darle más poder, sino decirle exactamente qué hacer. Por eso el rol del paso 4 trae sus `revocation_statements`: quitar lo que se dio y borrar el usuario. Con el rol corregido y subido otra vez, la misma revocación funciona:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-lector-2.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
HTTP 204
$ PGUSER=$(jq -r .data.username secretos-locales/creds-lector-2.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-lector-2.json) psql -At -c "SELECT count(*) FROM clientes;"
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-QyRyJ1vdjmrPY6U0KXl2-1792335063"
```

El usuario ya no existe. Si tú copiaste el rol del paso 4 completo, tu primera revocación ya sale bien.

El `"sync": true` es importante: por defecto Vault solo **pone en cola** la revocación y contesta `204` enseguida, sin esperar a que la base de datos borre el usuario. Con `sync` espera a que termine, y así tu prueba de entrar justo después no depende del azar ([sys/leases](https://developer.hashicorp.com/vault/api-docs/system/leases)).

## Paso 7 — Esperar a que caduque

Ahora la primera credencial, la del paso 5. No hagas nada: espera a que pasen sus 2 minutos. Vault la revoca solo, y lo anota en su registro (`docker compose logs vault`):

```
2026-10-18T14:52:49.642Z [INFO]  expiration: revoked lease: lease_id=database/creds/lector/rOpuliUuxFqc2UbdHMofQV8S
```

Intenta entrar:

```
$ date -u +%T; psql -At -c "SELECT count(*) FROM clientes;"
14:53:32
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049"
```

Nadie la revocó a mano. Nadie editó un archivo. Se murió sola. Esto es lo que habría salvado a Canasta Morada: la contraseña del script de Toño habría dejado de servir a los dos minutos del primer sábado.

## Paso 8 — Rotación automática de un usuario existente

`reportes` existe desde antes y otros sistemas lo conocen por nombre. Comprueba que hoy entra con la contraseña inicial:

```
$ PGUSER=reportes PGPASSWORD=$(cat secretos-locales/reportes_inicial.txt) psql -At -c "SELECT current_user;"
reportes
```

Ponlo bajo un **rol estático** que rota cada minuto (el mínimo que acepta la API son 5 segundos; un minuto es para que lo veas sin dormirte):

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-roles/reportes \
    -d '{"db_name": "postgres", "username": "reportes", "rotation_period": "1m"}'
HTTP 204
```

La documentación explica que Vault **rota la contraseña al crear el rol estático**, porque necesita conocerla ([API del motor Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). Así que la inicial ya murió:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes \
    | jq ".data | {username, password: (.password[0:6] + \"...\"), last_vault_rotation, ttl, rotation_period}"
{
  "username": "reportes",
  "password": "ZTU46F...",
  "last_vault_rotation": "2026-10-18T14:51:57.637277774Z",
  "ttl": 60,
  "rotation_period": 60
}
$ PGUSER=reportes PGPASSWORD=$(cat secretos-locales/reportes_inicial.txt) psql -At -c "SELECT current_user;"
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "reportes"
```

Quien necesita entrar como `reportes` le pide la contraseña vigente a Vault en el momento:

```
$ PGUSER=reportes PGPASSWORD=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password) \
    psql -At -c "SELECT current_user, count(*) FROM clientes GROUP BY 1;"
reportes|2
```

Espera un par de minutos y vuelve a preguntar. `last_vault_rotation` avanzó solo, y el registro de Vault lo confirma:

```
2026-10-18T14:52:59.517Z [INFO]  secrets.database.database_4731c3d7: successfully rotated static role: name=reportes ttl=60
```

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -c ".data | {password: (.password[0:6] + \"...\"), last_vault_rotation, ttl}"
{"password":"OH0KOU...","last_vault_rotation":"2026-10-18T14:53:59.530969477Z","ttl":11}
```

Y si no quieres esperar, la rotas tú con `rotate-role`. Otra contraseña nueva; la de hace un momento ya no entra (lo compruebas en el ejercicio 18).

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-role/reportes
HTTP 204
```

Si en lugar de «cada minuto» necesitas «cada domingo a las 4 a.m.», existe `rotation_schedule`, con formato tipo cron de cinco campos; no se puede usar junto con `rotation_period`. Vault lo interpreta en **UTC**, no en la hora de tu ciudad: para las 4:00 a.m. del domingo en la Ciudad de México (UTC-6) se escribe `0 10 * * SUN`; ajusta la cuenta a tu zona ([API del motor Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). En esta lección no lo probamos.

## Paso 9 — Que nadie sepa la contraseña de Vault: `rotate-root`

La contraseña inicial de `vault_admin` está en `secretos-locales/vault_admin_inicial.txt`. Hoy funciona:

```
$ PGUSER=vault_admin PGPASSWORD=$(cat secretos-locales/vault_admin_inicial.txt) psql -At -c "SELECT current_user;"
vault_admin
```

Pídele a Vault que la cambie por una que solo él conozca:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-root/postgres
HTTP 204
$ PGUSER=vault_admin PGPASSWORD=$(cat secretos-locales/vault_admin_inicial.txt) psql -At -c "SELECT current_user;"
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "vault_admin"
```

El archivo ya es basura. Y Vault sigue trabajando, porque él sí sabe la nueva:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector | jq -c "{username: .data.username, lease_duration}"
{"username":"v-root-lector-R3rwerQPR0yvfCxuAxYI-1792335221","lease_duration":120}
```

Ahora ninguna persona conoce la contraseña con la que se crean los usuarios de la base de datos. Si alguien sube por error un archivo de configuración, ahí ya no está la de `vault_admin`. Ojo con lo que sí queda: `.env` sigue guardando las contraseñas de administración de PostgreSQL y MariaDB del laboratorio, y `rotate-root` no las cambia. En la vida real, esas tampoco deberían vivir en un archivo.

## Paso 10 — Lo mismo con MariaDB

MariaDB también corre desde la sesión 2. Su contraseña de `root` está en `.env`. El cliente `mariadb` lee la contraseña de la variable `MYSQL_PWD`, así que tampoco la escribes en el comando. Crea una tabla de productos y el usuario `vault_admin` de MariaDB:

```
$ MARIA_ADMIN_PASS=$(openssl rand -hex 16); echo "$MARIA_ADMIN_PASS" > secretos-locales/vault_admin_maria_inicial.txt
$ MYSQL_PWD=$MARIADB_ROOT_PASSWORD mariadb -h 127.0.0.1 -P $PUERTO_MARIADB -u root tienda <<SQL
CREATE TABLE productos (id INT AUTO_INCREMENT PRIMARY KEY, nombre VARCHAR(50), precio DECIMAL(8,2));
INSERT INTO productos (nombre, precio) VALUES ('Cuaderno', 45.00), ('Pluma', 12.50);
CREATE USER 'vault_admin'@'%' IDENTIFIED BY '$MARIA_ADMIN_PASS';
GRANT CREATE USER ON *.* TO 'vault_admin'@'%';
GRANT SELECT ON tienda.* TO 'vault_admin'@'%' WITH GRANT OPTION;
SQL
WARNING: option --ssl-verify-server-cert is disabled, because of an insecure passwordless login.
```

Esa advertencia la da el cliente nuevo de MariaDB al conectarse sin validar la identidad del servidor (TLS); en el laboratorio no importa. Si te estorba, agrega `--skip-ssl-verify-server-cert`.

Para MariaDB se usa el plugin `mysql-database-plugin`; la documentación de Vault cubre MySQL y MariaDB en la misma página ([MySQL/MariaDB](https://developer.hashicorp.com/vault/docs/secrets/databases/mysql-maria)). Fíjate en que la dirección tiene otra forma:

```
$ jq -n --arg p "$(cat secretos-locales/vault_admin_maria_inicial.txt)" '{
    plugin_name: "mysql-database-plugin",
    connection_url: "{{username}}:{{password}}@tcp(mariadb:3306)/",
    username: "vault_admin",
    password: $p,
    allowed_roles: ["lector-maria"]
  }' | curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/config/mariadb -d @-
HTTP 204
```

El rol, en `roles/lector-mariadb.json`:

```json
{
  "db_name": "mariadb",
  "creation_statements": [
    "CREATE USER '{{name}}'@'%' IDENTIFIED BY '{{password}}';",
    "GRANT SELECT ON tienda.* TO '{{name}}'@'%';"
  ],
  "default_ttl": "2m",
  "max_ttl": "10m"
}
```

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/roles/lector-maria -d @roles/lector-mariadb.json
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector-maria > secretos-locales/creds-maria.json
$ jq "{lease_id, lease_duration, username: .data.username, password: (.data.password[0:6] + \"...\")}" secretos-locales/creds-maria.json
{
  "lease_id": "database/creds/lector-maria/SFcP2O5rDfL6qu6Bbt3RS0p6",
  "lease_duration": 120,
  "username": "v-root-lector-mar-24LwvJevZDrYbE",
  "password": "VVeNO-..."
}
```

Aquí no hizo falta escribir `revocation_statements`: el borrado por defecto del plugin de MySQL funcionó con estos permisos. Entra, lee y trata de cambiar precios:

```
$ MYSQL_PWD=$(jq -r .data.password secretos-locales/creds-maria.json) mariadb -h 127.0.0.1 -P $PUERTO_MARIADB \
    -u $(jq -r .data.username secretos-locales/creds-maria.json) tienda -e "SELECT CURRENT_USER(), nombre, precio FROM productos;"
CURRENT_USER()	nombre	precio
v-root-lector-mar-24LwvJevZDrYbE@%	Cuaderno	45.00
v-root-lector-mar-24LwvJevZDrYbE@%	Pluma	12.50
$ MYSQL_PWD=$(jq -r .data.password secretos-locales/creds-maria.json) mariadb -h 127.0.0.1 -P $PUERTO_MARIADB \
    -u $(jq -r .data.username secretos-locales/creds-maria.json) tienda -e "UPDATE productos SET precio = 0;"
ERROR 1142 (42000) at line 1: UPDATE command denied to user 'v-root-lector-mar-24LwvJevZDrYbE'@'172.21.0.1' for table `tienda`.`productos`
```

Revoca y prueba otra vez:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-maria.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
HTTP 204
$ MYSQL_PWD=$(jq -r .data.password secretos-locales/creds-maria.json) mariadb -h 127.0.0.1 -P $PUERTO_MARIADB \
    -u $(jq -r .data.username secretos-locales/creds-maria.json) tienda -e "SELECT 1;"
ERROR 1045 (28000): Access denied for user 'v-root-lector-mar-24LwvJevZDrYbE'@'172.21.0.1' (using password: YES)
```

(La dirección `172.21.0.1` es la de tu máquina vista desde la red de Docker; la tuya puede ser otra.) Y la raíz:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-root/mariadb
HTTP 204
$ MYSQL_PWD=$(cat secretos-locales/vault_admin_maria_inicial.txt) mariadb --skip-ssl-verify-server-cert -h 127.0.0.1 -P $PUERTO_MARIADB -u vault_admin -e "SELECT CURRENT_USER();"
ERROR 1045 (28000): Access denied for user 'vault_admin'@'172.21.0.1' (using password: YES)
```

## Paso 11 — El botón de pánico

¿Recuerdas el requisito R6 de la sesión 1, revocar de golpe? Si sospechas que todas las credenciales de un rol se filtraron, las cancelas juntas por prefijo. Con el comando `vault`:

```
$ docker compose exec -e VAULT_TOKEN vault vault list sys/leases/lookup/database/creds/lector
Keys
----
HlDBUcqNtR5Ethbo2QU7T8P5
eKeykMcukrSwqRcDhqojSxlM
f9gqAm1x15HqsBwBTtYHHmm4
qDu1j4uI4WP6HP2LpIoyjBt5
$ docker compose exec -e VAULT_TOKEN vault vault lease revoke -prefix database/creds/lector
All revocation operations queued successfully!
$ docker compose exec -e VAULT_TOKEN vault vault list sys/leases/lookup/database/creds/lector
No value found at sys/leases/lookup/database/creds/lector
```

Ojo con lo que demostró esa salida: «queued» quiere decir que Vault aceptó la orden y la puso en cola, y la lista vacía solo dice que ya no hay arrendamientos. Lo que de verdad importa es el efecto en PostgreSQL. Cuenta los usuarios temporales antes de revocar y unos segundos después:

```
PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -At -c "SELECT count(*) FROM pg_roles WHERE rolname LIKE 'v-root-lector-%';"
```

Antes de revocar debe dar más de `0` (uno por cada credencial que siga viva); después, `0`. Si todavía no es `0`, espera un poco y repite: la cola trabaja en segundo plano. Ese conteo es lo que confirma que los usuarios ya no existen.

Cuatro arrendamientos cancelados con una orden. Revocar por prefijo pide permiso especial (`sudo`) en la ruta ([sys/leases](https://developer.hashicorp.com/vault/api-docs/system/leases)); por eso aquí lo hicimos con el token root.

## Paso 12 — El único programa: Python sin contraseñas

Hasta aquí, todo con la terminal. Ahora, lo que hace cualquier aplicación real: pedir su credencial a Vault y conectarse. Primero, una política para el programa, `politicas/app-python.hcl`:

```hcl
# La app de Python puede pedir usuarios temporales de solo lectura
# y descifrar CURPs. No puede cifrar, rotar ni leer otros secretos.
path "database/creds/lector" {
  capabilities = ["read"]
}
path "transit/decrypt/curp" {
  capabilities = ["update"]
}
```

Súbela y crea un token de 30 minutos para el programa:

```
$ jq -n --rawfile p politicas/app-python.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/app-python -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/create \
    -d '{"policies": ["app-python"], "ttl": "30m", "display_name": "app-python"}' \
    | jq -r .auth.client_token > secretos-locales/token-python.txt
```

Instala el conector de PostgreSQL para Python en un entorno virtual:

```
python3 -m venv .venv
.venv/bin/pip install "psycopg[binary]"
```

**Hoy no necesitas dominar Python completo.** Trata este archivo como un programa resuelto y fíjate solo en cuatro zonas: `TOKEN` lee un secreto del entorno; `vault(...)` habla con Vault; `cred = ...` pide el usuario temporal; y el bloque `with psycopg.connect(...)` usa ese usuario en PostgreSQL. En el ejercicio 20 solo cambias cómo termina el programa.

Y el programa, `python/clientes.py`. Usa `urllib`, que viene con Python, para hablar con Vault, y `psycopg` para PostgreSQL. Son 24 líneas:

```python
# Pide a Vault un usuario temporal de PostgreSQL, lee los clientes
# y descifra cada CURP con Transit. La app no guarda ninguna contraseña.
import base64, json, os, urllib.request
import psycopg

VAULT = os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")
TOKEN = os.environ["VAULT_TOKEN"]  # te lo da quien opera Vault; nunca va en el código

def vault(ruta, datos=None):
    cuerpo = json.dumps(datos).encode() if datos else None
    req = urllib.request.Request(f"{VAULT}/v1/{ruta}", data=cuerpo,
                                 headers={"X-Vault-Token": TOKEN})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["data"]

cred = vault("database/creds/lector")
print("Vault me prestó el usuario", cred["username"])

with psycopg.connect(host="127.0.0.1", port=os.environ.get("PGPORT", "5432"),
                     dbname="tienda", user=cred["username"],
                     password=cred["password"]) as conexion:
    for nombre, curp in conexion.execute("SELECT nombre, curp FROM clientes"):
        claro = vault("transit/decrypt/curp", {"ciphertext": curp})["plaintext"]
        print(f"{nombre:6} {curp[:12]}...  ->  {base64.b64decode(claro).decode()}")
```

Lo que hace, en orden: la función `vault` manda una petición a Vault con el token en el encabezado (si le pasas `datos`, es un `POST`; si no, un `GET`) y devuelve la parte `data` de la respuesta. Pide una credencial dinámica, se conecta con ella, lee los clientes y descifra cada CURP con Transit.

Córrelo con el token del programa:

```
$ export VAULT_TOKEN=$(cat secretos-locales/token-python.txt)
$ .venv/bin/python python/clientes.py
Vault me prestó el usuario v-token-ap-lector-9FQ5IlE2i1HAUlZvuxZG-1792335175
Pepe   vault:v3:VEk...  ->  PEPE000101HDFXXX01
María  vault:v3:hKW...  ->  MARA990909MDFXXX02
```

Busca en el archivo una contraseña de PostgreSQL o de Transit: no hay. El programa sí recibe un token de Vault desde el entorno; ese token también es secreto, pero no queda escrito en el código, tiene permisos limitados y dura solo 30 minutos. El nombre del usuario ahora empieza con `v-token-ap`: Vault anota que lo pidió un token `app-python`, no root. Córrelo otra vez y te presta **otro** usuario. Y si el programa intenta salirse de su política:

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Sin token, ni arranca:

```
$ unset VAULT_TOKEN; .venv/bin/python python/clientes.py
...
KeyError: 'VAULT_TOKEN'
```

Cuando termines, regresa al token root: `export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)`.

> **¿Y desde Java, .NET o Go?**
>
> Lo que hiciste con `curl` y Python se hace desde cualquier lenguaje, porque Vault habla HTTP. Casi nadie lo programa a mano: cada lenguaje tiene bibliotecas. HashiCorp mantiene una lista que distingue las oficiales de las de la comunidad ([Client libraries](https://developer.hashicorp.com/vault/api-docs/libraries)):
>
> - **Go:** `github.com/hashicorp/vault/api`, el cliente que HashiCorp mantiene oficialmente.
> - **Java con Spring:** [Spring Cloud Vault](https://spring.io/projects/spring-cloud-vault) carga los secretos de Vault en la configuración de la aplicación y puede pedir credenciales de base de datos al momento. HashiCorp lo lista entre las bibliotecas de la comunidad.
> - **Java con Quarkus:** la extensión [Quarkus Vault](https://docs.quarkiverse.io/quarkus-vault/dev/index.html), del proyecto Quarkiverse, cubre KV, Transit y credenciales dinámicas para la conexión a la base de datos. También es de la comunidad.
> - **.NET:** [VaultSharp](https://github.com/rajanadar/VaultSharp) es la opción más conocida. **No es oficial**: es un proyecto de la comunidad. La lista de HashiCorp menciona además un cliente de .NET experimental que, según la misma página, no está listo para producción.
>
> Y hay una forma de no tocar el código: **Vault Agent**, un programa que corre junto a tu aplicación, se identifica con Vault, renueva su token y escribe los secretos en un archivo a partir de una plantilla; tu aplicación solo lee ese archivo ([Vault Agent](https://developer.hashicorp.com/vault/docs/agent-and-proxy/agent)). En Kubernetes, el **inyector de Vault Agent** lo agrega solo a los pods que lo piden con anotaciones, y deja los secretos en un volumen en memoria compartido con la aplicación ([Agent Injector](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/injector)).

> **¿Y cómo se ve esto en un sistema de verdad?**
>
> Imagina una plataforma que atiende a muchas empresas a la vez y guarda, de cada una, contraseñas de sus proveedores: el acceso a su banco, a su facturador, a su paquetería. Si una empresa ve los secretos de otra, se acabó el negocio.
>
> Un buen diseño no amarra el programa a Vault. Define primero una **pieza con un contrato corto**: «sella este secreto para esta empresa» y «ábrelo». Por dentro, cada empresa tiene **su propia llave, con versiones**, igual que la llave de Transit que rotaste en la sesión 3: si una llave se rota, lo sellado antes se sigue abriendo, y con `min_decryption_version` se le pone fecha de caducidad a lo viejo.
>
> Detrás de ese contrato se conecta el proveedor:
>
> - para las **pruebas**, una versión que guarda todo en memoria y se borra al terminar;
> - para **producción**, un adaptador que llama a Transit con una llave por empresa (`transit/encrypt/empresa-a`, `transit/encrypt/empresa-b`), o a un servicio de llaves de una nube.
>
> Ese proveedor puede ser HashiCorp Vault u OpenBao, su versión libre, que tiene un motor Transit compatible ([Transit en OpenBao](https://openbao.org/docs/secrets/transit/)); en Hábil elegimos OpenBao.
>
> El resto del sistema nunca sabe cuál de los dos está conectado. Así se puede probar todo sin levantar Vault, y cambiar de proveedor sin reescribir el programa. Fíjate en lo que **no** hace: el programa nunca toca la llave. Pide «sella» y «abre», y la llave se queda en Vault, como viste con `curl` en la sesión 3.

---

👉 **Si eres de Administración:** las credenciales dinámicas son el **gafete de visitante** llevado a los sistemas: se emite a nombre de quien lo pide, abre solo lo necesario y vence solo. La rotación automática es el **cambio periódico de combinación** de la caja fuerte, pero sin que nadie tenga que anotar la nueva. Y el botón de pánico responde la pregunta que hace cualquier auditor después de un incidente: «¿cuánto tardaron en cancelar los accesos?». Con esto, la respuesta es «un comando». En el caso de Canasta Morada, la pregunta que de verdad importaba era otra: «¿quién paga ese servidor de 9.99 dólares?». Revisar los cargos recurrentes de la tarjeta de la empresa también es control de accesos.

---

## Ejercicios de la sesión 4

**Ejercicio 16 — Tu gafete.** Pide una credencial del rol `lector`, entra con `psql` y cuenta los clientes. Después intenta `INSERT INTO clientes (nombre, curp) VALUES ('Intruso', 'x');`.

```
# Pista: guarda la credencial para usarla en el ejercicio 17.
# Archivo sugerido: secretos-locales/creds-16.json
# Ruta que debes consultar: database/creds/lector
```

**Cómo compruebas:** el conteo da `2` (o los que tengas); el `INSERT` da `ERROR:  permission denied for table clientes`.

**Ejercicio 17 — Revócala tú.** Revoca la credencial del ejercicio 16 con `sys/leases/revoke` y vuelve a intentar entrar. Hazlo dentro de los 2 minutos: si Vault ya la revocó y la ruta contesta que el arrendamiento no existe, no es un error de permisos. Pide otra credencial, reemplaza `creds-16.json` y revócala enseguida.

**Cómo compruebas:** la revocación contesta `HTTP 204` y `psql` contesta `password authentication failed`. Desde el superusuario, `SELECT count(*) FROM pg_roles WHERE rolname = '<el usuario>';` da `0`.

**Ejercicio 18 — La contraseña de hace un minuto.** Guarda la contraseña vigente de `reportes` en una variable, rota con `rotate-role/reportes` y trata de entrar con la que guardaste.

**Cómo compruebas:** con la guardada, `password authentication failed for user "reportes"`. Con la que Vault te da después de rotar, entra.

**Ejercicio 19 — Gafete de 30 segundos.** Cambia el `default_ttl` del rol `lector` a 30 segundos, sin editar el archivo, con `jq`:

```
jq '.default_ttl = "30s"' roles/lector-postgres.json \
  | curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/roles/lector -d @-
```

Pide una credencial, entra de inmediato, espera 40 segundos y vuelve a intentar. Guarda la credencial en `secretos-locales/creds-19.json` y pon `PGUSER=... PGPASSWORD=... psql` delante de cada intento, leyendo los valores del archivo con `jq` como en el paso 5: lo que exportaste en los ejercicios 16 y 17 pertenece a un usuario ya revocado y te daría un fallo que no es el del TTL.

**Cómo compruebas:** `lease_duration` dice `30`; el primer intento entra; el segundo da `password authentication failed`. Al terminar, regresa el rol a como estaba subiendo otra vez `roles/lector-postgres.json`.

**Ejercicio 20 — Que el programa recoja su basura.** Cada vez que corre `clientes.py`, deja un usuario temporal vivo hasta que caduca. Haz que **revoque su propio token** con `auth/token/revoke-self`, y que lo haga **siempre**, aunque algo falle a la mitad (usa `try` y `finally`). Cuando un token se revoca, Vault revoca también las credenciales que pidió con él. Parte de este esqueleto, que ya acomoda la estructura:

```python
try:
    cred = vault("database/creds/lector")
    # pega aquí el bloque with psycopg.connect(...) que ya existe
finally:
    # aquí va la petición POST a auth/token/revoke-self
    pass
```

**Cómo compruebas:** antes de correrlo, cuenta desde el superusuario los usuarios que empiezan con `v-token-ap`; después de correrlo, el conteo debe quedar igual que antes (el usuario se creó y se borró). Si lo corres otra vez con el mismo token, debe fallar con `HTTP Error 403`, porque el token ya no existe. Para repetir la prueba después de ese 403, crea un token nuevo con el mismo comando del paso 12, guárdalo otra vez en `secretos-locales/token-python.txt` y vuelve a exportar `VAULT_TOKEN`. El 403 es lo esperado solo para el token ya revocado.

---

## Errores comunes (y cómo darte cuenta)

| Error | Cómo se ve | Cómo darte cuenta | Qué hacer |
|---|---|---|---|
| Usar `127.0.0.1` en `connection_url` | Al guardar la configuración: `error verifying connection: ... dial tcp 127.0.0.1:5432: connect: connection refused`, código 400 | El servidor de la URL no es el nombre del servicio; dentro del contenedor de Vault, `127.0.0.1` es el propio Vault | Dentro de Docker Compose, Vault llega a la base de datos por su nombre: `postgres`, `mariadb` |
| Rol que no está en `allowed_roles` | `"escritor" is not an allowed role`, código 500 | El nombre del rol no aparece en `database/config/<conexión>` | Agrégalo a `allowed_roles` de la conexión |
| Revocación que falla con permisos justos | `permission denied for sequence ...` al revocar | El rol no tiene `revocation_statements` | Escribe tus `revocation_statements`; no le des superusuario a Vault para que el error desaparezca |
| Guardar la contraseña de `vault_admin` y luego rotar la raíz | El archivo ya no sirve | `rotate-root` contestó 204 | Es lo que queremos: ninguna persona la conoce. Si necesitas entrar, usa el superusuario de la base de datos, no el de Vault |
| Esperar que la credencial dure más que `max_ttl` | Renuevas y aun así vence | `lease_duration` deja de crecer | `max_ttl` es el tope. Pide una credencial nueva |
| Pegar el token del programa en el código | El token queda escrito en un archivo que git rastrea | `git status` muestra el archivo como modificado, y `grep -rn hvs. python/` encuentra el token | El token entra por variable de ambiente o, mejor, con Vault Agent. Si se subió, revócalo |
| `psql` entra sin pedir contraseña | Crees que la credencial sigue viva | Te conectaste por el socket local dentro del contenedor | Conéctate como en la lección, por red (`-h 127.0.0.1` desde tu máquina), donde PostgreSQL sí revisa la contraseña |

---

## Autoevaluación de la serie

Contesta sin ver. Si fallas más de dos, regresa a la sesión que indica.

1. ¿Cuál es la diferencia entre `DELETE` sobre `secret/data/...` y `destroy`? *(Sesión 2)*
2. Escribe de memoria una política que deje leer `secret/data/app/*` y nada más. *(Sesión 2)*
3. ¿Por qué un 403 es una buena noticia cuando pruebas una política? *(Sesión 2)*
4. ¿Qué necesitas para descifrar un `vault:v1:...` si la llave tiene `min_decryption_version: 2`? *(Sesión 3)*
5. ¿Qué gana un sistema con llaves derivadas y `context`? *(Sesión 3)*
6. ¿Qué diferencia hay entre una credencial dinámica y un rol estático? *(Sesión 4)*
7. ¿Por qué la conexión de Vault a la base de datos usa `vault_admin` y no el superusuario? *(Sesión 4)*
8. Un practicante se va de la empresa. Con lo que construiste, ¿qué contraseñas tendrías que cambiar a mano? *(Todas)*

## Repaso de la serie

| Sesión | El problema | Lo que lo resuelve | El comando que no debes olvidar |
|---|---|---|---|
| 1 | Secretos en archivos, en chats, compartidos y eternos | Requisitos R1 a R7 | `git log -p -S <texto>` |
| 2 | Nadie sabe quién tiene acceso ni quién lo usó | Sello de Shamir, tokens, políticas, bitácora | `curl -H "X-Vault-Token: ..." $VAULT_ADDR/v1/secret/data/...` |
| 3 | La llave de cifrado vive junto a los datos | Transit: cifrar sin tener la llave, rotar, reenvolver | `POST transit/encrypt/<llave>` con `plaintext` en base64 |
| 4 | La misma contraseña de base de datos para todos y para siempre | Credenciales dinámicas, rotación, `rotate-root`, revocación | `GET database/creds/<rol>` |

**Para apagar todo al terminar la serie:** `docker compose down`. Tus datos quedan en las carpetas `vault/`, `postgres/` y `mariadb/`. Si quieres empezar de cero, borra esas carpetas, `secretos-locales/` y `.env`, y vuelve a correr `./iniciar.sh`.

---

## Soluciones (no las veas antes de intentarlo)

**Repaso de la sesión 3.**

1. `vault`: lo cifró Vault; `v2`: con la versión 2 de la llave; lo demás: el dato cifrado, en base64.
2. Siguen cifrados con su versión vieja y se pueden descifrar mientras esa versión no quede por debajo de `min_decryption_version`. `rewrap` los sube a la versión nueva sin revelar el dato.
3. Porque si alguien se roba ese token, puede meter datos cifrados pero no puede leer ninguno. El daño de una filtración es mucho menor.

**Ejercicio 16.**

```
curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector > secretos-locales/creds-16.json
export PGUSER=$(jq -r .data.username secretos-locales/creds-16.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-16.json)
psql -At -c "SELECT count(*) FROM clientes;"
psql -c "INSERT INTO clientes (nombre, curp) VALUES ('Intruso', 'x');"
```

**Ejercicio 17.** El comando del paso 6, con el `lease_id` de `creds-16.json`. Hazlo antes de que pasen los 2 minutos; si Vault se te adelanta, pide otra credencial y revócala enseguida.

**Ejercicio 18.**

```
VIEJA=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password)
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-role/reportes
PGUSER=reportes PGPASSWORD=$VIEJA psql -At -c "SELECT 1;"
NUEVA=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password)
PGUSER=reportes PGPASSWORD=$NUEVA psql -At -c "SELECT 1;"
```

En la prueba de esta lección, la orden que usa `$VIEJA` (la tercera) dio `FATAL:  password authentication failed for user "reportes"`. Ojo: como el rol rota cada minuto, la «vieja» puede morir por la rotación automática antes que por la tuya. El resultado es el mismo. La última orden, con `$NUEVA`, imprime `1`; si esa también falla, vuelve a pedir la contraseña vigente a Vault y ejecútala de nuevo, porque la rotación de un minuto pudo ocurrir entre una orden y otra.

**Ejercicio 19.**

```
curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector > secretos-locales/creds-19.json

PGUSER=$(jq -r .data.username secretos-locales/creds-19.json) \
PGPASSWORD=$(jq -r .data.password secretos-locales/creds-19.json) \
psql -At -c "SELECT count(*) FROM clientes;"

sleep 40

PGUSER=$(jq -r .data.username secretos-locales/creds-19.json) \
PGPASSWORD=$(jq -r .data.password secretos-locales/creds-19.json) \
psql -At -c "SELECT count(*) FROM clientes;"
```

En la prueba:

```
{"lease_duration":30,"username":"v-root-lector-wlrG6BL0dqUomIbQDDrV-1792336140"}
```

El primer intento devolvió `2`. Cuarenta segundos después:

```
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-wlrG6BL0dqUomIbQDDrV-1792336140"
```

**Ejercicio 20.** Mete dentro del `try` la petición de la credencial y todo lo que usa la base de datos, y la revocación en el `finally`, que se ejecuta pase lo que pase (incluso si falla la propia petición de la credencial):

```python
try:
    cred = vault("database/creds/lector")
    print("Vault me prestó el usuario", cred["username"])

    with psycopg.connect(host="127.0.0.1", port=os.environ.get("PGPORT", "5432"),
                         dbname="tienda", user=cred["username"],
                         password=cred["password"]) as conexion:
        for nombre, curp in conexion.execute("SELECT nombre, curp FROM clientes"):
            claro = vault("transit/decrypt/curp", {"ciphertext": curp})["plaintext"]
            print(f"{nombre:6} {curp[:12]}...  ->  {base64.b64decode(claro).decode()}")
finally:
    vault_revoca = urllib.request.Request(f"{VAULT}/v1/auth/token/revoke-self", data=b"{}",
                                          headers={"X-Vault-Token": TOKEN})
    with urllib.request.urlopen(vault_revoca):
        pass
    print("Token revocado; el usuario temporal se va con él")
```

Así, si la petición, la conexión o una consulta fallan, el token se revoca igual. `data=b"{}"` convierte la petición en un `POST`, que es lo que pide esa ruta. En la prueba de esta lección:

```
$ PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -At -c "SELECT count(*) FROM pg_roles WHERE rolname LIKE 'v-token-ap%';"
0
$ .venv/bin/python python/clientes.py
Vault me prestó el usuario v-token-ap-lector-xQMNqaIKMmkt9R54b5Du-1792336196
Pepe   vault:v3:VEk...  ->  PEPE000101HDFXXX01
María  vault:v3:hKW...  ->  MARA990909MDFXXX02
Token revocado; el usuario temporal se va con él
$ PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -At -c "SELECT count(*) FROM pg_roles WHERE rolname LIKE 'v-token-ap%';"
0
$ .venv/bin/python python/clientes.py
...
urllib.error.HTTPError: HTTP Error 403: Forbidden
```

El usuario `v-token-ap-lector-xQMN...` nació y murió dentro de la misma corrida. El programa ya no deja nada atrás.

**Autoevaluación.**

1. `DELETE` borra la última versión de forma reversible (`undelete` la regresa); `destroy` la borra para siempre.
2. `path "secret/data/app/*" { capabilities = ["read"] }`
3. Porque demuestra que la política niega lo que debe negar. Una política que nunca da 403 probablemente da de más.
4. Nada lo descifra mientras el mínimo sea 2. Lo correcto era reenvolverlo antes de subir el mínimo; si no, hay que bajar `min_decryption_version`, reenvolver y volver a subirlo.
5. Que un dato cifrado para un dueño no se pueda descifrar como si fuera de otro, aunque se use la misma llave.
6. La dinámica crea un usuario nuevo cada vez y lo borra al caducar; el estático conserva un usuario que ya existe y le cambia la contraseña cada cierto tiempo.
7. Porque `rotate-root` deja la contraseña en manos de Vault, y la documentación recomienda un usuario dedicado. Además, con permisos justos, un error o una filtración en Vault no da control total de la base de datos.
8. Ninguna se cambia a mano. Revocas su token de Vault y, con él, sus credenciales dinámicas (o todos los que creó, por prefijo). Una excepción: si conocía la contraseña del rol estático `reportes`, rótala de inmediato con `POST /v1/database/rotate-role/reportes`; revocar su token no cambia esa contraseña, que seguiría sirviendo hasta la siguiente rotación. Esa es la diferencia con Canasta Morada al principio de la serie.

---

## Lo que sigue

Esta serie usó Vault con un solo servidor, sin TLS y con las llaves en un archivo, porque es un laboratorio. Si quieres seguir, los siguientes temas son: TLS en el listener, métodos de autenticación para máquinas (AppRole, Kubernetes) en lugar de tokens creados a mano, almacenamiento con varios servidores para alta disponibilidad, y respaldos del propio Vault.

---

*Escribo desde lo que vemos todos los días en Hábil, donde construimos sistemas para banca, seguros y empresas en México. Si en tu trabajo o en el negocio de tu familia se topan con un problema así, platiquemos: [habil.mx](https://habil.mx)*

*Si en tu empresa las contraseñas de las bases de datos todavía viven en un archivo, en Hábil montamos esto como parte del aprovisionamiento de infraestructura: [identidad, llaves y secretos](https://habil.mx).*
