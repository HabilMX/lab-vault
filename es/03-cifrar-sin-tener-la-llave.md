# Vault desde cero (3): cifrar sin tener la llave

*El motor Transit de Vault cifra y descifra por ti, y la llave nunca llega a tu programa. Guardas CURP cifradas en PostgreSQL, rotas la llave sin perder nada y aprendes a borrar datos destruyendo una llave.*

*Vault desde cero · sesión 3 de 4*

## Repaso de la sesión 2

Contesta sin ver. Las respuestas están en las soluciones.

1. ¿Por qué Vault arranca sellado, y cuántas llaves necesitas por defecto para abrirlo?
2. Un token recibe 403. ¿Cuáles son dos causas posibles, y qué ruta de Vault te dice qué puede hacer ese token?
3. Si alguien roba la bitácora de auditoría, ¿se lleva las contraseñas? ¿Por qué?

> **El laboratorio de esta sesión** está en el repositorio público [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Ármalo tú primero; el repositorio es para comparar cuando algo no te salga igual. No trae ninguna contraseña: el laboratorio las genera al arrancar.

## Objetivos de esta sesión

| # | Al terminar puedes… | Lo demuestra |
|---|---|---|
| 1 | **Cifrar y descifrar** un dato con Transit usando `curl`, y **explicar** qué es base64 y por qué no es cifrado | Ejercicio 11 |
| 2 | **Rotar** una llave y **reenvolver** datos viejos a la versión nueva sin descifrarlos tú | Ejercicios 12 y 14 |
| 3 | **Escribir** una política que deja cifrar pero no descifrar, y **comprobar** el 403 | Ejercicio 13 |
| 4 | **Guardar** datos cifrados en PostgreSQL con `psql` y **demostrar** que quien lee la tabla no ve el dato | Paso 8 (guiado) y ejercicio 14 |
| 5 | **Ligar** un dato cifrado a su dueño con `context`, y **destruir** una llave para volver ilegible lo que cifró | Ejercicio 15 y paso 10 |

---

## Escenario (ficción) — Capítulo 7: Lunes, 10:12 a.m.

Iván no durmió bien el fin de semana. El reloj de las 3:17 no lo deja en paz.

El lunes pide al proveedor del servidor la bitácora completa de descargas de la carpeta de respaldos. No la de una semana: la de toda la vida del servidor. Le llega un archivo de texto con miles de líneas. Lo filtra por la dirección `185.xx.xx.xx`.

La primera descarga desde esa dirección no fue el sábado pasado.

Fue hace dos años y tres meses.

Y desde entonces, **cada sábado a las 3:21**, alguien descargó el respaldo de la noche. Y la carpeta con `llave.txt`. Ciento diecisiete sábados seguidos.

Valeria, que por fin confesó lo del repositorio público, siente que el pecho se le afloja. Su error fue hace diez días. Esto lleva dos años.

—Entonces no fue por lo que subí —dice.

—No —contesta Iván—. Lo que subiste también era grave, y por eso cambiamos todo. Pero esto es otra cosa.

Doña Clara hace la pregunta incómoda:

—¿Y cuántas veces se llevaron las CURP?

—Ciento diecisiete.

---

## Capítulo 8: Lunes, 4:50 p.m.

Mientras Iván rehace el cifrado de las CURP, Rocío, la contadora, entra a la oficina con un estado de cuenta de la tarjeta de la empresa. Está haciendo la conciliación del mes y hay un cargo que nunca ha entendido:

```
SERV VIRTUAL CLOUD  TR-REPORTES     USD 9.99
```

—Lleva así como dos años —dice—. Siempre pensé que era algo de ustedes.

Iván busca en el panel del proveedor la dirección del servidor que paga ese cargo.

`185.xx.xx.xx`.

TR.

*(Continúa en la sesión 4.)*

---

## Por qué importa

El problema número 6 de la sesión 1 era la llave junto a los datos. Canasta Morada sí cifraba las CURP, pero el que se llevó el respaldo se llevó también `llave.txt`, y el cifrado no sirvió de nada.

La solución no es esconder mejor el archivo. Es que **la llave no esté en ningún archivo que tu programa pueda leer**. Tu programa le dice a Vault «cíframe esto» y recibe el dato cifrado. Le dice «descíframe esto» y, si tiene permiso, recibe el dato original. La llave se queda en Vault, protegida por el sello que abriste la semana pasada con tres llaves.

Eso es el motor **Transit**. La documentación lo describe como «criptografía como servicio» o «cifrado como servicio», y aclara que Vault **no guarda** los datos que le mandas: tú guardas el resultado donde quieras ([Transit](https://developer.hashicorp.com/vault/docs/secrets/transit)).

Así, si mañana alguien se lleva el respaldo de la base de datos, se lleva textos como `vault:v2:SmfKDK1u...`. Sin acceso a Vault, no le sirven de nada.

## Tres palabras antes de empezar

**Cifrar.** Revolver un dato con una **llave** para que solo quien tenga la llave lo pueda volver a leer. Cuando de niño escribías mensajes en clave cambiando cada letra por la que sigue en el abecedario, la llave era «una letra adelante». Transit usa por defecto AES-256 en modo GCM, que es muchísimo más fuerte y además detecta si alguien alteró el dato cifrado ([API de Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)).

**Base64.** Una forma de escribir cualquier dato, incluso uno binario, usando solo letras, números, `+`, `/` y `=`. Transit pide los datos en base64 porque así un dato cualquiera (un texto, una imagen pequeña) puede viajar dentro de un JSON. Ojo con el tamaño: la API de Vault limita por defecto cada solicitud a 32 MB, y base64 hace los datos un tercio más grandes. Para archivos grandes se cifra con otra técnica, no mandándolos enteros a Transit. **Base64 no es cifrado.** Es como el idioma de la F: «hofolafa» parece secreto, pero cualquiera que conozca la regla lo lee. Pruébalo:

```
$ echo -n "PEPE000101HDFXXX01" | base64
UEVQRTAwMDEwMUhERlhYWDAx
$ echo "UEVQRTAwMDEwMUhERlhYWDAx" | base64 -d; echo
PEPE000101HDFXXX01
```

El `-n` de `echo` evita que se cuele un salto de línea al final; sin él, cifrarías «CURP + Enter». Las CURP de esta lección son inventadas y no corresponden a ninguna persona; llevan `XXX` para que se note. No uses datos de personas reales en tus prácticas.

**Versión de llave.** Una llave de Transit puede tener varias versiones. Cuando la **rotas**, nace una versión nueva que se usa para cifrar lo que viene; las viejas se quedan para poder descifrar lo de antes. Es como cambiar la combinación del candado de la bodega cada año, guardando las combinaciones anteriores en un sobre por si aparece una caja vieja.

---

## Paso 1 — Levanta el laboratorio y prende Transit

**Dos piezas de terminal que vas a usar todo el tiempo.** `NOMBRE=$(comando)` ejecuta `comando` y guarda su resultado en `NOMBRE`. `$NOMBRE` inserta después ese resultado. Pruébalo: `SALUDO=$(echo hola); echo "$SALUDO"` debe mostrar `hola`. En el siguiente bloque, `LLAVE=$(...)` guarda temporalmente una llave de desbloqueo; si algo falla, revisa que `LLAVE` no haya quedado vacía con `echo "${#LLAVE}"` (debe dar un número mayor que 0).

Si apagaste el laboratorio, préndelo, abre el sello y exporta el token, como en la sesión 2:

```
docker compose start
set -a; source .env; set +a
export VAULT_ADDR=http://127.0.0.1:$PUERTO_VAULT
for i in 0 1 2; do
  LLAVE=$(jq -r ".keys[$i]" secretos-locales/init.json)
  curl -s -X PUT $VAULT_ADDR/v1/sys/unseal -d "{\"key\": \"$LLAVE\"}" | jq -c '{sealed, progress}'
done
export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)
```

Prende el motor Transit en la ruta `transit/`:

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/transit -d '{"type": "transit"}'
HTTP 204
```

**Control de estado.** `docker compose stop` conserva Transit, las llaves y la tabla. Si al montar Transit recibes `HTTP 400` con `path is already in use`, ya estaba montado: sigue en el paso 2. Si la llave `curp` o la tabla `clientes` ya existen, no repitas las inserciones del paso 8. Mira primero qué hay con `psql -c "SELECT id, nombre, left(curp, 9) FROM clientes;"` y continúa solo si reconoces esas filas como trabajo previo.

## Paso 2 — Crea una llave

Una llave llamada `curp`. No mandas nada: Vault la genera adentro.

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp
HTTP 200
```

Mírala:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp \
    | jq ".data | {name, type, latest_version, min_decryption_version, exportable, deletion_allowed, keys: (.keys | map_values(type))}"
{
  "name": "curp",
  "type": "aes256-gcm96",
  "latest_version": 1,
  "min_decryption_version": 1,
  "exportable": false,
  "deletion_allowed": false,
  "keys": {
    "1": "number"
  }
}
```

Fíjate en lo que **no** aparece: la llave. En `keys` solo hay un número por versión, que es la fecha en que se creó. `exportable: false` dice que no se puede sacar. Compruébalo:

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/export/encryption-key/curp
{"errors":["private key material is not exportable"]}
 HTTP 400
```

Ni siquiera el token root puede sacarla. Si al crearla pidieras `exportable: true`, sí se podría, y esa decisión no tiene regreso; por eso viene apagada.

## Paso 3 — Cifrar

Mandas el texto en base64 dentro de `plaintext`. El `$(...)` hace la conversión en el momento:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq .data
{
  "ciphertext": "vault:v1:A2se3zo5aKjY51c/tlquYpJrN/L8DDNh2BPzqvcrXfYwkW8yVVimMMzir5DRpw==",
  "key_version": 1
}
```

Ese `ciphertext` es lo que vas a guardar. Tiene tres partes separadas por dos puntos:

- `vault`: lo cifró Vault.
- `v1`: con la **versión 1** de la llave.
- Lo demás: el dato cifrado.

Cifra **la misma CURP otra vez**:

```
vault:v1:qy8hRw2+KeTOHWr/RJ7D4tPbSlRDiTk96lZGn9+Jijp+lJRyUlfZph3upajdFw==
```

Es distinto. Cada cifrado lleva un ingrediente al azar (un *nonce*), y por eso dos cifrados del mismo dato nunca se parecen. Así nadie puede ver la tabla y decir «estos dos clientes tienen la misma CURP». (Transit tiene un modo llamado *convergente* que hace lo contrario, a propósito, para poder buscar; aquí no lo usamos.)

## Paso 4 — Descifrar

Mandas el `ciphertext` y recibes base64:

```
$ C=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext)
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$C\"}" | jq .data
{
  "plaintext": "UEVQRTAwMDEwMUhERlhYWDAx"
}
```

Y lo regresas a texto con `base64 -d`:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$C\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

Si alguien te pasa basura con forma de cifrado, Vault no adivina:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"vault:v1:estonoescifrado\"}"
{"errors":["invalid ciphertext: could not decode base64"]}
 HTTP 400
```

## Paso 5 — Rotar la llave sin perder nada

Guarda un cifrado hecho con la versión 1 en un archivo, para usarlo después:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext | tee v1.txt
vault:v1:0uoMoZKeXU+18t3TiH3yOlTX7vL9wlNUWlMf1W4XapYdoVq2Z1OWVAg7hIgWlA==
```

`tee` muestra el resultado en pantalla y además lo guarda en el archivo. Ahora **rota**:

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp/rotate
HTTP 200
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp | jq -c ".data | {latest_version, min_decryption_version, versiones: (.keys | keys)}"
{"latest_version":2,"min_decryption_version":1,"versiones":["1","2"]}
```

Lo nuevo sale con `v2`:

```
vault:v2:uzo5CXHaWgjXF3iUCzzefTFzOecaAcho3WjVJqnjVJ0IQIR3mk1DioElROdsxA==
```

Y lo viejo **todavía se descifra**, porque la versión 1 sigue guardada:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

Rotar no rompe nada. Por eso se puede hacer seguido; incluso existe `auto_rotate_period` para que Vault rote sola una llave cada cierto tiempo.

## Paso 6 — Reenvolver: subir lo viejo a la versión nueva

Rotar no cambia lo que ya está guardado: tu base de datos sigue llena de `v1`. Para subirlos a `v2` está **rewrap** (reenvolver): le das el cifrado viejo y te regresa uno nuevo con la última versión. La documentación aclara que en este proceso **no se revela el dato original** ([Transit](https://developer.hashicorp.com/vault/docs/secrets/transit)): ni tú ni tu programa ven la CURP.

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/rewrap/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}" | jq -c .data | tee rewrap.json
{"ciphertext":"vault:v2:qR2K9Q5TmpKsG4umLEMX2bguVD1/R4nC+iNhKxAT5jrKGAc1clF5977n49Q85w==","key_version":2}
```

Es como llevar tus papeles viejos al notario para que les ponga el sello nuevo, sin que nadie los lea.

Cuando ya reenvolviste todo, le dices a Vault que **no acepte** cifrados más viejos que la versión 2:

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/curp/config -d '{"min_decryption_version": 2}'
HTTP 200
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}"
{"errors":["ciphertext or signature version is disallowed by policy (too old)"]}
 HTTP 400
```

El `v1` ya no sirve. El reenvuelto, sí:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(jq -r .ciphertext rewrap.json)\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

Esto es lo que Canasta Morada necesitaba: si una copia vieja de la base de datos anda por ahí, con cifrados `v1`, con esta configuración esa copia ya no se puede descifrar. Ojo: **no es borrado criptográfico**. Vault todavía conserva la versión 1 de la llave, y un operador autorizado podría volver a bajar el mínimo para permitir descifrarla (la documentación lo describe como un ajuste que forma parte de una política de rotación). Destruir una llave de verdad es el paso 10.

## Paso 7 — Una política que cifra pero no descifra

El formulario de alta de clientes necesita **cifrar** CURP. Nunca necesita leerlas. Crea `politicas/solo-cifrar-curp.hcl`:

```hcl
# El formulario de alta puede CIFRAR curps, pero nunca descifrarlas.
path "transit/encrypt/curp" {
  capabilities = ["update"]
}
```

En Transit, cifrar y descifrar son operaciones de escritura (`POST`), y en las políticas eso se llama `update`. Para esta llave, que ya existe, `update` es la capacidad mínima correcta. Ojo: la ruta `transit/encrypt/<llave>` acepta `create` o `update`, y con `create` Vault puede crear una llave que no existía, con valores predeterminados, a menos que se haya desactivado esa creación automática ([Transit: Encrypt data](https://developer.hashicorp.com/vault/api-docs/secret/transit#encrypt-data)). No deduzcas la capacidad de la política solo del verbo HTTP.

Súbela y crea un token para el formulario. Dura 3 horas, lo que dura la sesión con sus ejercicios; si caduca antes, un 403 se parecería al 403 que buscas en el ejercicio 13:

```
$ jq -n --rawfile p politicas/solo-cifrar-curp.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/solo-cifrar-curp -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/create \
    -d '{"policies": ["solo-cifrar-curp"], "ttl": "3h", "display_name": "formulario-alta"}' \
    | jq -r .auth.client_token > secretos-locales/token-formulario.txt
```

El formulario cifra la CURP de una clienta nueva:

```
$ F=$(cat secretos-locales/token-formulario.txt)
$ curl -s -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n MARA990909MDFXXX02 | base64)\"}" | jq -r .data.ciphertext | tee maria.txt
vault:v2:4LM7LCPcgym6rQAPOMQGWR4DIk1qi4NdtoaBM/yecdQfWsG9iCypdv7IST71dQ==
```

Pero si intenta leerla, o rotar la llave:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat maria.txt)\"}"
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/keys/curp/rotate
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Si alguien se roba el token del formulario, puede meter CURP cifradas, pero no puede leer ni una. Es un buzón: cualquiera echa cartas, solo el cartero abre.

## Paso 8 — Guardarlo en PostgreSQL

PostgreSQL ya está corriendo desde la sesión 2. Su contraseña está en `.env`, que generó el guion. Cárgala en tu terminal sin copiarla a mano: `set -a` hace que todo lo que leas se exporte, y `source .env` lee el archivo.

```
set -a; source .env; set +a
export PGHOST=127.0.0.1 PGPORT=$PUERTO_POSTGRES PGUSER=postgres PGDATABASE=tienda PGPASSWORD=$POSTGRES_PASSWORD
```

`psql` lee esas variables `PG...` solito; así no escribes la contraseña en el comando, donde quedaría en tu historial. Eso es aceptable en un laboratorio local, pero `PGPASSWORD` deja la contraseña en el entorno del proceso, y la documentación de PostgreSQL la desaconseja porque en algunos sistemas otros procesos pueden verla. En producción se usa un archivo de contraseñas con permisos estrictos o, mejor, Vault.

Crea la tabla de clientes:

```
$ psql -c "CREATE TABLE clientes (id serial PRIMARY KEY, nombre text NOT NULL, curp text NOT NULL);"
CREATE TABLE
```

Inserta a Pepe con su CURP cifrada. Primero cifras, después guardas el resultado:

```
$ CIF=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext)
$ psql -c "INSERT INTO clientes (nombre, curp) VALUES ('Pepe', '$CIF');"
INSERT 0 1
```

Y a María, cifrada por el token del formulario, que no puede leer:

```
$ F=$(cat secretos-locales/token-formulario.txt)
$ CIF=$(curl -s -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n MARA990909MDFXXX02 | base64)\"}" | jq -r .data.ciphertext)
$ psql -c "INSERT INTO clientes (nombre, curp) VALUES ('María', '$CIF');"
INSERT 0 1
```

Ahora mira la tabla como la vería alguien con permiso de lectura (`SELECT`) sobre `clientes`, su propietario, un superusuario o quien tenga el respaldo. Conectarse a la base de datos no basta: en PostgreSQL hace falta ese permiso ([Privilegios](https://www.postgresql.org/docs/17/ddl-priv.html)). Aquí funciona porque entramos como `postgres`:

```
$ psql -c "SELECT * FROM clientes;"
 id | nombre |                                   curp
----+--------+---------------------------------------------------------------------------
  1 | Pepe   | vault:v2:GCD4q2/Fp+YtLKT185oGtoSBJ4M9wE5oKrOaDy93Hlmf84Nzh/4ZxWW+E62chg==
  2 | María  | vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
(2 rows)
```

Dicen `v2` porque rotaste en el paso 5. Y el respaldo, que es lo que se llevaban cada sábado de Canasta Morada:

```
$ docker compose exec postgres pg_dump -U postgres -t clientes tienda | grep -A3 "^COPY"
COPY public.clientes (id, nombre, curp) FROM stdin;
1	Pepe	vault:v2:GCD4q2/Fp+YtLKT185oGtoSBJ4M9wE5oKrOaDy93Hlmf84Nzh/4ZxWW+E62chg==
2	María	vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
\.
```

Ni una CURP legible. Y ya no hay `llave.txt` que llevarse.

Quien sí tiene permiso de descifrar lee de la tabla y le pide a Vault:

```
$ CIF=$(psql -At -c "SELECT curp FROM clientes WHERE nombre = 'María';"); echo "$CIF"
vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$CIF\"}" | jq -r .data.plaintext | base64 -d; echo
MARA990909MDFXXX02
```

`-At` le pide a `psql` solo el valor, sin encabezados ni bordes.

## Paso 9 — Ligar el cifrado a su dueño: `context`

Imagina que Canasta Morada empieza a guardar expedientes de dos empresas que le compran al mayoreo, Empresa Norte y Empresa Sur, en la misma tabla. Un error de programación, o alguien malintencionado, podría tomar un expediente cifrado de Norte, pegarlo en el renglón de Sur y pedir que lo descifren «como de Sur».

Transit tiene una defensa para eso: las **llaves derivadas**. Al crear la llave con `derived: true`, cada operación tiene que traer un `context`: un dato extra, en base64, del que Vault deriva una llave distinta. Con otro `context`, otra llave ([API de Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)). Es como un sobre que solo se abre con el sello de la empresa a la que va dirigido.

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/expedientes -d '{"derived": true}'
HTTP 200
```

Sin `context`, se niega:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
    -d "{\"plaintext\": \"$(echo -n diagnostico-confidencial | base64)\"}"
{"errors":["missing 'context' for key derivation; the key was created using a derived key, which means additional, per-request information must be included in order to perform operations with the key"]}
 HTTP 400
```

Cifra para Empresa Norte:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
    -d "{\"plaintext\": \"$(echo -n diagnostico-confidencial | base64)\", \"context\": \"$(echo -n empresa-norte | base64)\"}" \
    | jq -r .data.ciphertext | tee ctx.txt
vault:v1:8lKFunrcJVIzLnq9q4ZNszSLDOotf4gqtenuKek8QTuCIh4yq1ldoqtjMbsojged+/0aPQ==
```

Con el `context` correcto, se lee:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
    -d "{\"ciphertext\": \"$(cat ctx.txt)\", \"context\": \"$(echo -n empresa-norte | base64)\"}" | jq -r .data.plaintext | base64 -d; echo
diagnostico-confidencial
```

Haciéndose pasar por Empresa Sur:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
    -d "{\"ciphertext\": \"$(cat ctx.txt)\", \"context\": \"$(echo -n empresa-sur | base64)\"}"
{"errors":["cipher: message authentication failed"]}
 HTTP 400
```

`message authentication failed`: la verificación de AES-GCM detectó que eso no cuadra. El expediente de Norte solo se abre como de Norte. En la vida real, el `context` suele ser el identificador del cliente o de la empresa dueña del dato.

Una aclaración importante: el `context` **no es una contraseña ni una autorización**. Es un valor que manda quien llama; si alguien tiene permiso de descifrar esa llave y conoce el valor `empresa-norte`, puede pedir el descifrado con él. Por eso la aplicación debe sacar el `context` de un dato confiable que no se pueda alterar (por ejemplo, el dueño registrado del expediente), y las políticas deben limitar quién puede descifrar cada llave.

## Paso 10 — Borrar destruyendo la llave

Último patrón, y el más drástico. Un cliente se va y pide que borres sus datos. Están en la base de datos, en los respaldos de anoche, en los de hace un mes. Ir a borrar en cada copia es casi imposible.

Si cada cliente tiene **su propia llave**, hay otra salida: **destruir la llave**. Todo lo que se cifró con ella queda ilegible, esté donde esté. A esto se le conoce como borrado criptográfico.

Crea una llave para un cliente y cifra algo suyo:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 200
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/cliente-que-se-va \
    -d "{\"plaintext\": \"$(echo -n datos-de-don-chema | base64)\"}" | jq -r .data.ciphertext | tee borrar.txt
vault:v1:tjerbuHJyEbw+3IiLl0rC/hSEa78E61i9Yg9CancZegxpnBsybXKvkGZ2DwtzQ==
```

Intenta borrarla:

```
$ curl -s -w " HTTP %{http_code}\n" -X DELETE -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
{"errors":["error deleting policy cliente-que-se-va: deletion is not allowed for this key"]}
 HTTP 400
```

Vault no te deja, por defecto. La documentación lo llama «una operación potencialmente catastrófica» y exige prender antes `deletion_allowed` ([API de Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)). Es el seguro de la pistola. Quítalo y borra:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/cliente-que-se-va/config -d '{"deletion_allowed": true}'
HTTP 200
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X DELETE -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 204
```

Ahora intenta descifrar lo de don Chema:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/cliente-que-se-va \
    -d "{\"ciphertext\": \"$(cat borrar.txt)\"}"
{"errors":["encryption key not found"]}
 HTTP 400
```

¿Y si alguien crea otra llave con el mismo nombre?

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 200
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/cliente-que-se-va \
    -d "{\"ciphertext\": \"$(cat borrar.txt)\"}"
{"errors":["cipher: message authentication failed"]}
 HTTP 400
```

Mismo nombre, llave nueva. Lo viejo sigue ilegible: en la base de datos, en el respaldo de anoche y en el de hace un año.

**Una advertencia honesta.** Esto vale para las copias de **tus datos**. Si guardas respaldos **del propio Vault** (de su carpeta de datos), un respaldo tomado antes del borrado todavía contiene la llave. Para que el borrado criptográfico sea completo, los respaldos de Vault también tienen que caducar.

### La alternativa con el comando `vault`

```
$ docker compose exec -e VAULT_TOKEN vault vault write transit/encrypt/curp plaintext=$(echo -n PEPE000101HDFXXX01 | base64)
Key            Value
---            -----
ciphertext     vault:v3:7yIAAelQRE+2zGnTO+J0EJcPExHspE4elzod4VDFrTrTSkl4bAYZ9ygbQ25C1Q==
key_version    3
```

(En esta prueba salió la versión 3 porque ya se habían hecho los ejercicios 12 y 14. Si ejecutas este comando ahora, antes de los ejercicios, lo normal es que el tuyo empiece con `vault:v2:`. El número cambia con cada rotación: no lo compares con el del ejemplo, compáralo con `latest_version` de la llave `curp`.)

---

👉 **Si eres de Administración:** el cifrado como servicio es el mismo principio que la **custodia de valores**: la empresa de traslado guarda el efectivo, tú solo tienes el comprobante, y para retirar necesitas autorización. La política «cifra pero no descifra» es la **ventanilla de depósitos**: cualquiera deposita, solo el apoderado retira. Y el borrado destruyendo la llave importa para la protección de datos personales: cuando un cliente ejerce su derecho a que se cancelen sus datos, el área legal va a preguntar «¿y en los respaldos?». Esta técnica es una respuesta técnica que se puede demostrar, pero no sustituye el análisis legal: la cancelación puede implicar un periodo de bloqueo antes de suprimir, plazos de conservación y excepciones que fija la ley.

---

## Ejercicios de la sesión 3

**Ejercicio 11 — Tu CURP de mentiras.** Inventa una CURP de mentiras (con `XXX` en medio, como las de la lección). Cífrala dos veces con la llave `curp` y descífrala.

**Pista si te atoras.** Del comando del paso 3 solo cambias el texto que va dentro de `echo -n`. Guarda el resultado con `C=$(... | jq -r .data.ciphertext)`, como en el paso 4, y para descifrar reutiliza ese mismo comando cambiando solo el `ciphertext` por `$C`.

d) Completa sin ver: «Base64 es __________. No es cifrado porque __________. En esta práctica, la protección empieza cuando __________.»

**Cómo compruebas:** los dos `ciphertext` deben ser distintos entre sí, los dos deben empezar con el mismo `vault:vN:`, y al descifrar con `base64 -d` debe salir tu CURP exacta, sin salto de línea extra. Si al final ves un renglón vacío de más, olvidaste el `-n` en `echo`. Para el inciso d), compara con la solución.

**Ejercicio 12 — Rota y reenvuelve.** Cifra tu CURP y guárdala en `mio.txt`. Rota la llave `curp`. Reenvuelve `mio.txt`.

**Cómo compruebas:** el número después de `vault:v` en el reenvuelto debe ser igual a `latest_version` de la llave (consúltalo con `GET transit/keys/curp`). Y el reenvuelto debe descifrar a tu CURP.

**Ejercicio 13 — El buzón.** Con el token del formulario (`secretos-locales/token-formulario.txt`):

a) Cifra una CURP.
b) Intenta descifrarla.
c) Intenta cifrar con otra llave, `expedientes`.
d) Ahora escribe tú la política. Completa los huecos sin mirar el paso 7:

```hcl
path "transit/____/curp" {
  capabilities = ["____"]
}
```

Súbela con el nombre `solo-cifrar-prueba`, crea un token de prueba con ella (los comandos del paso 7 cambiando los nombres) y repite a), b) y c) con ese token.

**Cómo compruebas:** a) recibes un `vault:v...`; b) 403; c) 403, porque la política solo menciona `transit/encrypt/curp`. Si el inciso a) devuelve 403, no lo cuentes como correcto: puede que el token haya caducado. Crea otro con el comando del paso 7, vuelve a cargar `F` y empieza de nuevo; la prueba vale desde que cifrar con `F` sí devuelve `vault:v...`. En d), `encrypt/curp` funciona; `decrypt/curp` y `encrypt/expedientes` dan 403.

**Ejercicio 14 — Reenvolver toda una tabla.** Rota la llave `curp` otra vez. Después recorre la tabla `clientes` y reenvuelve cada CURP.

**Primero, una prueba que no toca nada.** Antes de cualquier `UPDATE`, comprueba que el ciclo lee bien la tabla:

```
psql -At -F " " -c "SELECT id, curp FROM clientes;" | while read ID CIF; do
  echo "ID=$ID | CIF=$CIF"
done
```

`|` le pasa cada renglón al ciclo, `-F " "` le pide a `psql` que separe las columnas con un espacio, y `read` pone la primera columna en `ID` y la segunda en `CIF`. Debes ver un renglón por cliente antes de seguir.

Ahora el esqueleto de verdad; complétalo. El `if` evita que, si Vault falla, se guarde en la tabla un `null` en lugar de la CURP cifrada:

```
psql -At -F " " -c "SELECT id, curp FROM clientes;" | while read ID CIF; do
  NUEVO=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/____/curp \
          -d "{\"ciphertext\": \"$CIF\"}" | jq -r .data.ciphertext)
  if [ -z "$NUEVO" ] || [ "$NUEVO" = "null" ]; then
    echo "No actualicé id=$ID: Vault no devolvió un ciphertext. Revisa que siga abierto y que VAULT_TOKEN sea válido."
    continue
  fi
  psql -q -c "UPDATE clientes SET curp = '$NUEVO' WHERE id = ____;"
done
```

**Cómo compruebas:** `psql -c "SELECT id, nombre, left(curp, 9) AS version FROM clientes;"` debe mostrar la misma versión nueva en todos los renglones, y cada CURP debe seguir descifrando bien.

**Ejercicio 15 — El sobre equivocado.** Con la llave `expedientes`, cifra la palabra `credito-aprobado` con el context `empresa-sur`. Descífrala con `empresa-sur`, luego con `empresa-norte` y luego sin context.

e) Sin ejecutar otro borrado, completa: «Recrear `cliente-que-se-va` no recupera lo cifrado antes porque __________. Antes de permitir el borrado de una llave debo comprobar __________.»

**Cómo compruebas:** la primera da `credito-aprobado`; la segunda, `cipher: message authentication failed`; la tercera, `missing 'context' for key derivation`. El inciso e) se compara con la solución.

---

## Errores comunes (y cómo darte cuenta)

| Error | Cómo se ve | Cómo darte cuenta | Qué hacer |
|---|---|---|---|
| Mandar el texto sin base64 | Suele salir `{"errors":["illegal base64 data at input byte N"]}` con código 400. Pero si el texto casualmente es base64 válido, Vault lo acepta y cifra bytes distintos a los que querías | El valor de `plaintext` se ve igual que tu texto original | Siempre `$(echo -n TEXTO | base64)` |
| Olvidar `-n` en `echo` | Al descifrar aparece un renglón vacío de más | El base64 termina distinto: `...WDAxCg==` en lugar de `...WDAx` | `echo -n` no agrega el salto de línea |
| Creer que base64 es cifrado | «Ya está protegido, se ve raro» | `base64 -d` lo lee cualquiera | Base64 es solo una forma de escribir. El cifrado lo hace Transit |
| Subir `min_decryption_version` antes de reenvolver | Los datos viejos dan `disallowed by policy (too old)` | Hay renglones con `vault:v1:` en la tabla | Reenvuelve todo primero; sube el mínimo al final. Si te pasó y aún tienes cifrados `v1`: repite el comando de configuración del paso 6 con `{"min_decryption_version": 1}`, confirma que `v1.txt` vuelve a descifrar, reenvuelve todo y solo al final sube el mínimo a la versión nueva |
| Política de Transit con `read` | El token recibe 403 al cifrar | `sys/capabilities-self` no dice `update` | Cifrar y descifrar son `update` |
| Llave derivada sin `context` | `missing 'context' for key derivation` | La llave dice `derived: true` | Manda siempre el mismo `context`, en base64, para cifrar y descifrar |
| Borrar una llave «para probar» | Todo lo cifrado con ella se vuelve ilegible para siempre | `encryption key not found` | No hay regreso. Por eso existe `deletion_allowed`: déjalo apagado salvo cuando de verdad quieras destruir |

---

## Repaso para la próxima sesión

La sesión 4 empieza con estas tres preguntas. Contéstalas sin ver:

1. ¿Qué significan las tres partes de `vault:v2:SmfKDK1u...`?
2. Rotaste la llave. ¿Qué pasa con los datos que ya estaban cifrados, y qué operación los sube a la versión nueva sin que nadie vea el dato?
3. ¿Por qué un token que solo puede cifrar es útil para un formulario de alta?

🔁 **La próxima semana:** Canasta Morada descubre de quién es el servidor `185.xx.xx.xx`. Tú haces que las contraseñas de PostgreSQL y MariaDB nazcan, caduquen y cambien solas, y escribes un programa de Python que se conecta a la base de datos sin conocer ninguna contraseña.

**Antes de irte:** `docker compose stop`. La próxima vez, `start`, abre el sello y exporta el token.

---

## Soluciones (no las veas antes de intentarlo)

**Repaso de la sesión 2.**

1. Porque sus datos están cifrados en disco con una llave maestra que no guarda completa: está partida en pedazos (Shamir). Por defecto son 5 pedazos y se necesitan 3.
2. Que la política no incluye esa ruta o esa capacidad (por ejemplo, la ruta sin `data/`), o que el token caducó o fue revocado. `sys/capabilities-self` te dice qué puede hacer el token en cada ruta.
3. No, con la configuración predeterminada. Vault registra una huella (HMAC-SHA256) de la mayoría de los valores de texto sensibles, no el valor; sirve para comparar, no para reconstruir. Verifica siempre la configuración del dispositivo de auditoría antes de asumirlo: con `log_raw=true`, con atributos exentos de huella o con valores que no son texto, el dato puede quedar sin ocultar ([Auditoría](https://developer.hashicorp.com/vault/docs/audit)).

**Ejercicio 11.** Con una CURP de ejemplo, `ABCD020202HDFXXX03`:

```
curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
  -d "{\"plaintext\": \"$(echo -n ABCD020202HDFXXX03 | base64)\"}" | jq -r .data.ciphertext
```

Dos veces dan dos textos distintos con el mismo prefijo. Para descifrar, el comando del paso 4 con tu `ciphertext`.

Inciso d): «Base64 es una forma de escribir datos (una codificación). No es cifrado porque cualquiera puede revertirlo. En esta práctica, la protección empieza cuando Transit cifra el dato con la llave.»

**Ejercicio 12.** Rotas con `POST transit/keys/curp/rotate`, reenvuelves con `POST transit/rewrap/curp` mandando `{"ciphertext": "<lo de mio.txt>"}`. Si antes la última versión era 2, después de rotar es 3 y el reenvuelto empieza con `vault:v3:`.

**Ejercicio 13.** a) Igual que el paso 7. b) y c) `{"errors":["1 error occurred:\n\t* permission denied\n\n"]}` con `HTTP 403`. d) Los huecos son `encrypt` y `update`: la misma política del paso 7 con otro nombre.

**Ejercicio 14.** Los huecos son `rewrap` y `$ID`. Cada rotación crea una versión nueva: si antes hiciste el ejercicio 12, esta rotación lleva la llave a la versión 4 y verás `vault:v4:`; si no, a la 3. En la prueba de esta lección, después de rotar a la versión 3:

```
 id | nombre |  version
----+--------+-----------
  1 | Pepe   | vault:v3:
  2 | María  | vault:v3:
(2 rows)
```

Nadie vio una sola CURP durante el proceso: ni tú, ni la terminal, ni el ciclo. Si el `if` imprime «No actualicé», esa fila quedó como estaba; arregla el problema y vuelve a correr el ciclo.

**Ejercicio 15.**

```
CTX_SUR=$(echo -n empresa-sur | base64)
C=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
  -d "{\"plaintext\": \"$(echo -n credito-aprobado | base64)\", \"context\": \"$CTX_SUR\"}" | jq -r .data.ciphertext)
curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
  -d "{\"ciphertext\": \"$C\", \"context\": \"$CTX_SUR\"}" | jq -r .data.plaintext | base64 -d; echo
```

Para las otras dos, cambia el context por `$(echo -n empresa-norte | base64)` o quita el campo `context`. Los errores son los del paso 9.

Inciso e): «porque la llave nueva es material criptográfico distinto, aunque lleve el mismo nombre»; «que la llave es solo de ese cliente y que alguien con autoridad autorizó destruirla, porque no hay regreso».

---

## Lo que sigue

En la sesión 4 usas también el cliente de MariaDB. Compruébalo con `mariadb --version`. Si no lo tienes: `sudo apt install mariadb-client` en Debian o Ubuntu (en otras distribuciones de Linux, el administrador de paquetes que use la tuya), o `brew install mariadb` en macOS. Y para el script final, Python 3.10 o más nuevo: `python3 --version`.

---

*Escribo desde lo que vemos todos los días en Hábil, donde construimos sistemas para banca, seguros y empresas en México. Si en tu trabajo o en el negocio de tu familia se topan con un problema así, platiquemos: [habil.mx](https://habil.mx)*
