# Vault from Scratch (2): Spinning Up Vault and Storing Secrets

*A safe that nobody can open alone, a teller window that says no to whoever asks for what isn't theirs, and an audit log that records everything. With Docker Compose and `curl`.*

*Vault from Scratch · Session 2 of 4*

## Review from Session 1

Answer without looking. The answers are in the solutions at the end.

1. Name four of the six ways secrets leak.
2. Why is changing the password after a leak mandatory, even if you already deleted it from git?
3. How is Vault's Transit engine similar to and different from an HSM?

> **The course lab** is in the public repository [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Build it yourself first; the repository is for comparing when something does not come out the same for you. It contains no passwords: the lab generates them upon startup.

## Objectives for this session

| # | By the end you will be able to… | Demonstrated by |
|---|---|---|
| 1 | **Spin up** Vault in server mode with Docker Compose, without writing any passwords in the lab files | Exercise 6 |
| 2 | **Initialize** and **unseal** Vault with 3 of 5 keys, and **explain** why it seals itself upon restarting | Exercise 7 |
| 3 | **Store, read, version, delete, and recover** secrets with `curl` against the API | Exercise 8 |
| 4 | **Write** a policy and **verify** that a restricted token receives a 403 where it shouldn't have access | Exercise 9 |
| 5 | **Read** the audit log with `jq` to know who requested what | Exercise 10 |

---

## Scenario (fiction) — Chapter 5: Saturday, 1:40 p.m.

Iván changed the password for `app_tienda` at noon. It took him an hour and a half to get the four programs back up and running. The accounting macro never turned up; Rocío, the accountant, is going to pull the monthly report by hand.

Doña Clara listens to everything without interrupting. At the end, she says just one thing:

“I don't want to depend ever again on someone remembering where they wrote down a password.”

Iván proposes a safe for secrets. Doña Clara asks who is going to hold the key.

“You,” says Iván.

“No. If something happens to me, nobody can open it. And if someone takes it from me, they can open it all by themselves.”

Iván smiles. That objection has an answer from 1979.

---

## Chapter 6: The following Saturday, 3:17 a.m.

The safe now exists. Five people hold a share of its key. The apps request their secrets using their own identity.

Iván's phone buzzes again. Same time. Same server. But now the database log shows something different:

```
03:17:02  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
03:17:32  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
03:18:02  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
```

Someone is still trying with the old password. Every thirty seconds. Like clockwork.

Iván stares at the screen. Thieves don't keep fixed schedules.

Who does?

*(Continued in Session 3.)*

---

## Why it matters

Until today, at Canasta Morada "having access" meant "knowing the password." Today you are going to build the opposite: a place where nobody knows anything, and everyone **requests** what they need and **proves** who they are. It is the difference between a house where everyone has a copy of the key and a building with a front desk: there they log you in, ask where you are going, and only unlock that specific floor for you.

In this session you will see three ideas used in any serious system, with or without Vault:

- **The seal.** Data is encrypted on disk. Without the master key, not even Vault itself can read it.
- **Denied by default.** If a policy does not say you can, you cannot. As the documentation puts it: "policies are deny by default" ([Policies](https://developer.hashicorp.com/vault/docs/concepts/policies)).
- **Everything is logged.** Every request, whether permitted or denied, leaves a trail in the audit log.

## The answer from 1979: Shamir's keys

In 1979, cryptographer Adi Shamir published a way to split a secret into **N shares** such that any group of **K** shares can reconstruct it, while with fewer than K you know nothing. Not even a little.

Think of a community festival lockbox. There are five stewards. To open it, at least three must come together, each with their key. If one falls ill, the other four are enough. If someone's key is stolen, the thief cannot open anything alone. And nobody, not even the head steward, can open it in secret.

Vault works like this:

- Upon **initializing** it, Vault creates a **master key** that protects everything it stores. By default it splits it into **5 shares** and requires **3** to reconstruct it ([vault operator init](https://developer.hashicorp.com/vault/docs/commands/operator/init)).
- Vault starts up **sealed**: it holds the data, but encrypted, and cannot make sense of it. It is the locked box.
- **Unsealing** (*unseal*) means three stewards enter their key shares. From that point on, Vault operates normally.
- If Vault restarts, **it seals itself again**. You must bring together three keys once more.

The official documentation explains the seal and Shamir's algorithm in [Seal/Unseal](https://developer.hashicorp.com/vault/docs/concepts/seal).

---

## Step 0 — What you need

Docker with Compose, `curl`, `jq` (version 1.6 or newer), `openssl`, and `git`. Verify them:

```
docker compose version
curl --version
jq --version
openssl version
```

If any returns "command not found", install it before continuing. This session uses Vault 2.2.0, PostgreSQL 17.11, and MariaDB 11.8.8, pinned in `compose.yaml`: do not change them to `latest`, because the lesson's commands and responses match those versions.

## Step 1 — The lab folder

Create a folder named `lab-vault` with this structure. The contents of each file are provided below.

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

First comes `.gitignore`. It is the list of what git must never push. It goes **before** anything else because the lab will generate passwords, and we want git to avoid adding them inadvertently from the very first second. Note: `.gitignore` only prevents git from adding files it does not track yet. It does not protect a file that was already committed previously, nor does it stop someone from forcing an add with `git add -f`; that is why it is wise to review `git status` before each `git commit`.

```
# Lo que el laboratorio genera al arrancar. NADA de esto se sube a git.
.env
secretos-locales/
vault/data/
vault/logs/
postgres/
mariadb/
```

Next, `.env.ejemplo`. It is a reference copy **without real values**, so anyone who clones the repository knows what variables exist:

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

The Vault configuration, `vault/config/vault.hcl`:

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

Three things worth understanding:

- **`storage "file"`**: Vault stores its data, already encrypted, in a folder. There are other options for production with multiple servers; this is the simplest ([Filesystem storage](https://developer.hashicorp.com/vault/docs/configuration/storage/filesystem)).
- **`tls_disable = true`**: no encryption on the connection. On your laptop this is fine. On a real server, **never**: passwords would travel in plain text across the network.
- **Not "dev" mode.** Vault has a development mode that starts unsealed, wide open, storing everything in memory. It is convenient, but it hides precisely what we want to learn today.

The `compose.yaml`. Notice two details: **there is not a single hardcoded password**, only variables like `${POSTGRES_PASSWORD}`, and data is stored in **bind-mounted directories** (`./vault/data`), not in Docker volumes, so that you can see the files and they won't get lost if someone prunes Docker:

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

You will use PostgreSQL and MariaDB in Sessions 3 and 4; we spin them up today so we don't have to touch this file later. The `:?falta .env…` means: "if this variable is unset, do not start and display this message."

Three details about this file:

- **`127.0.0.1:` in front of each port** makes Docker bind the service exclusively to your own machine. Without that, Vault (which does not use TLS here) and both databases would be exposed to anyone on your local network.
- **`user:`** makes Vault run with your own user ID. The official image starts as an unprivileged user (`vault`), and on Linux it wouldn't be able to write to directories created by you. The startup script records your user ID in `.env`.
- **If any port is already in use** (8200, 5432, or 3306), change it via `PUERTO_VAULT`, `PUERTO_POSTGRES`, or `PUERTO_MARIADB`, as explained below.

> **On Linux: two folders of yours that aren't yours.**
>
> After spinning up the lab on Linux, run `ls -ln` in the directory. You will see something like this (columns that don't matter have been trimmed; measured on Linux Mint 22.3, with user 1000):
>
> ```
> drwx------  999 1000  postgres
> drwxrwxr-x  999  999  mariadb
> drwx------ 1000 1000  secretos-locales
> drwxr-xr-x 1000 1000  vault
> ```
>
> The `postgres` and `mariadb` directories no longer belong to your user: they belong to UID 999. And if you run `ls -l` without the `n`, instead of the number the name of a system service might appear (on Mint it displayed `dnsmasq`). It is not malware or a bug in the lab. It happens because the official PostgreSQL and MariaDB images start as root inside the container and then hand off their files to their own internal user, UID 999. A **bind-mounted directory** is the same folder seen from two sides: whatever the container does to its files, your disk sees verbatim, user ID included. Your Linux system doesn't know who UID 999 inside the container is; it only sees the number, and if that number has an owner assigned in your system, it displays that name.
>
> This does not happen to Vault because the `user:` directive in compose forces it to run under your user ID. Why isn't the same done for the databases? Because they need to start as root to initialize themselves the first time, and forcing a different user breaks that initial bootstrap.
>
> What this means for you:
> - `ls postgres` will report "Permission denied". To peek inside, use `sudo ls postgres`, or better yet, ask the container itself: `docker compose exec postgres ls /var/lib/postgresql/data`.
> - If you ever want to reset the lab from scratch, first run `docker compose down` and then delete those two directories with `sudo`, because your user cannot remove them.
> - On macOS and Windows you won't see this: Docker runs inside a virtual machine that presents the files to you as owned by your user.

## Step 2 — A startup script that fails closed

`iniciar.sh` prepares everything. The critical part is in step 1: **before generating any password, it checks that `.gitignore` protects it.** If not, it refuses to continue. This is known as **failing closed**: when in doubt, the gate stays shut, like a subway turnstile that won't turn unless your card cleared.

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

`grep -qx` searches for a line that is **exactly** that text (`-x`) and prints nothing (`-q`); it simply returns yes or no. `openssl rand -hex 16` generates 16 random bytes written as 32 hexadecimal characters. `umask 077` ensures `.env` is created readable only by you. `id -u` and `id -g` are your user and group IDs. And `unset` removes any variable with those names from your shell: Compose gives precedence to shell environment variables over `.env`, and we don't want an old password or port silently overriding your configuration.

Give it execute permission with `chmod +x iniciar.sh`. Before running it for real, verify that it truly fails closed. In a copy of the lab where `.gitignore` is missing the line `secretos-locales/`, this is what happens:

```
$ ./iniciar.sh
ALTO: .gitignore no tiene la regla 'secretos-locales/'.
Sin ella, las contraseñas que voy a generar podrían terminar en git. No sigo.
código de salida: 1
```

It did not create any directory or any `.env`. Now, with the complete `.gitignore`:

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

If your machine already uses port 5432 (because you have another PostgreSQL running), start it like this the first time: `PUERTO_POSTGRES=15432 ./iniciar.sh`. The script records it in `.env`.

And here is the proof that git cannot see the secrets. If you run `git init` in the folder and check what it would stage:

```
$ git status --short
?? .env.ejemplo
?? .gitignore
?? compose.yaml
?? iniciar.sh
?? vault/config/vault.hcl
```

Neither `.env`, nor `secretos-locales/`, nor the data directories. Exactly what you wanted.

## Step 3 — Is it alive?

Vault speaks HTTP. Store its address in a variable to avoid retyping it every time:

```
export VAULT_ADDR="http://127.0.0.1:$(grep '^PUERTO_VAULT=' .env | cut -d= -f2)"
```

Run that line inside the `lab-vault` directory. The port is read directly from your `.env`, so it works even if you changed it. Just because Docker says "Started" does not mean Vault is already listening. Wait until it answers:

```
until curl -fsS -o /dev/null "$VAULT_ADDR/v1/sys/seal-status"; do
  echo "Espero a que Vault inicie..."
  sleep 1
done
```

Check its seal status. This endpoint requires no authentication:

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

`initialized: false`: it has never been initialized. `sealed: true`: it is sealed. `t` and `n` are the threshold and total number of keys; there are none yet.

Another quick way to determine the status is the HTTP code from the health endpoint. `-o /dev/null` discards the body and `-w` prints only the status code:

```
$ curl -s -o /dev/null -w "%{http_code}\n" $VAULT_ADDR/v1/sys/health
501
```

501 means "not initialized." You will watch this change.

## Step 4 — Initialize: the five keys are born

This request creates the master key, splits it into 5 shares with a threshold of 3, and returns the shares along with a **root token**. You save it directly into a file in `secretos-locales/`, which git ignores:

```
curl -s -X PUT $VAULT_ADDR/v1/sys/init \
  -d '{"secret_shares": 5, "secret_threshold": 3}' > secretos-locales/init.json
chmod 600 secretos-locales/init.json
```

`chmod 600` makes the file readable only by you. Inspect it without revealing full secrets:

```
$ jq "{llaves: (.keys | length), token_root: (.root_token[0:9] + \"...\")}" secretos-locales/init.json
{
  "llaves": 5,
  "token_root": "hvs.RGQs7..."
}
```

Your values will be different. Each initialization generates brand new keys. Throughout this lesson you will always see tokens truncated like this: `hvs.RGQs7...`.

The **root token** is the owner's key: it can do absolutely everything. You will use it to configure the lab.

> **Not like this, and why**
>
> Storing the five keys and the root token in a file next to `compose.yaml` is a **concession for the lab**, so you can practice on your own machine. **In the real world, it is never done this way.**
>
> - Key shares are distributed among **different individuals**, one to each, precisely so that no single person can open the vault alone. Keeping them together in one file is like consolidating all five stewards into one person.
> - The **root token is revoked** as soon as initial configuration is complete. The documentation recommends exactly this: use it only for what is strictly necessary at the beginning and revoke it as soon as it is no longer needed ([Tokens](https://developer.hashicorp.com/vault/docs/concepts/tokens)). If another is ever needed down the road, it can be generated by bringing the keys together again.
> - A real server uses TLS, not `tls_disable`.
>
> If you ever copy this lab setup to a server, these three things are the very first you change.

Check the seal status again:

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

Initialized, but sealed. Waiting on the stewards.

## Step 5 — Unseal with 3 of 5 keys

Each call to `sys/unseal` submits **one** key share. `jq -r '.keys[0]'` extracts the first one from the file, without quotes:

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

`progress: 1`: it has one out of three. Repeat with `.keys[1]`:

```
{
  "sealed": true,
  "t": 3,
  "n": 5,
  "progress": 2
}
```

And with `.keys[2]`:

```
{
  "sealed": false,
  "t": 3,
  "n": 5,
  "progress": 0
}
```

`sealed: false`. Unsealed. Health check now returns 200:

```
$ curl -s -o /dev/null -w "%{http_code}\n" $VAULT_ADDR/v1/sys/health
200
```

Verify that it seals itself automatically when restarted:

```
$ docker compose restart vault
$ curl -s $VAULT_ADDR/v1/sys/seal-status | jq "{sealed, progress}"
{
  "sealed": true,
  "progress": 0
}
```

This is how it will be every time you power on your computer or restart the container. To avoid retyping the same command three times, unseal it with a loop:

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

What if someone enters a bogus key?

```
$ curl -s -X PUT $VAULT_ADDR/v1/sys/unseal -d '{"key": "esta-no-es-una-llave"}'
{"errors":["'key' must be a valid hex or base64 string"]}
```

## Step 6 — Authenticate: the token

Without a token, the teller window will not serve you:

```
$ curl -s -w " HTTP %{http_code}\n" $VAULT_ADDR/v1/sys/mounts
{"errors":["permission denied"]}
 HTTP 403
```

Export the root token into a variable in your shell. **Never paste it into a file committed to source control**; read it straight from where it lives:

```
export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)
```

The token travels in the `X-Vault-Token` header. Ask who you are:

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

`ttl: 0` means it never expires. Another reason to revoke it in real-world environments.

A clarification: in the lab, the app's "identity" is a token you create by hand. That lets you examine the mechanism up close. In a real system, applications obtain their token automatically by proving who they are through methods such as AppRole, Kubernetes, or OIDC (Vault's documentation calls them *auth methods*); that is outside the scope of this series.

## Step 7 — Enable the audit log before anything else

The audit log goes first, so everything you do from here on out is recorded. A file-based **audit device** writes one JSON line for every request and another for every response ([File audit device](https://developer.hashicorp.com/vault/docs/audit/file)):

```
$ curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/audit/archivo \
    -d '{"type": "file", "options": {"file_path": "/vault/logs/audit.log"}}'
HTTP 204
```

204 means "done, and I have nothing further to report." The audit log resides at `./vault/logs/audit.log` on your machine, thanks to the bind-mounted directory.

## Step 8 — Store secrets: the KV version 2 engine

Enable the **KV v2** engine at the `secret/` path. It is a key-value secrets storage engine that preserves versions ([KV v2](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2)):

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/secret -d '{"type": "kv", "options": {"version": "2"}}'
HTTP 204
```

List the mounted engines:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/mounts | jq -r ".data | keys[]"
agent-registry/
cubbyhole/
identity/
secret/
sys/
```

Yours is `secret/`. The others come preconfigured out of the box.

**Write.** Store the username and password for the store app. These are toy values; in real life, you generate the password with `openssl rand`, just like the script did:

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

Notice the path: `secret/`**`data/`**`tienda/postgres`. In KV v2, secret data lives under `data/`, while information about versions lives under `metadata/`. This is trap number one with KV v2; it is highlighted in the errors table.

**Read:**

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

**A new version.** Change the password:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/secret/data/tienda/postgres \
    -d '{"data": {"usuario": "app_tienda", "password": "Mango-2026"}}' | jq -c ".data | {version, created_time}"
{"version":2,"created_time":"2026-10-18T14:47:29.522529264Z"}
```

Version 1 is still there. Request it with `?version=1`:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/postgres?version=1" | jq -c .data.data
{"password":"Pepino-2026","usuario":"app_tienda"}
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c ".data.data, .data.metadata.version"
{"password":"Mango-2026","usuario":"app_tienda"}
2
```

It is like document version history in the cloud: you can roll back to yesterday's if today's went wrong.

**Delete (with a safety net).** A `DELETE` on `data/` deletes the latest version, but reversibly:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X DELETE $VAULT_ADDR/v1/secret/data/tienda/postgres
HTTP 204
```

Reading it now yields no data, the response includes the deletion timestamp, and the HTTP code is 404:

```
null
"2026-10-18T14:47:29.564180533Z"
HTTP 404
```

**Recover.** `undelete` restores it:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X POST \
    $VAULT_ADDR/v1/secret/undelete/tienda/postgres -d '{"versions": [2]}'
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c .data.data
{"password":"Mango-2026","usuario":"app_tienda"}
```

**Destroy (permanently).** `destroy` permanently erases whichever versions you specify. Destroy version 1, the old password:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X PUT \
    $VAULT_ADDR/v1/secret/destroy/tienda/postgres -d '{"versions": [1]}'
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/postgres?version=1" | jq -c ".data.metadata | {version, destroyed}"
{"version":1,"destroyed":true}
```

**Metadata** tells the whole history of the secret, including who created each version:

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

In that `jq` expression, `map_values(...)` iterates over each version, extracting only two data points: whether it was destroyed and who created it.

And to see what secrets exist inside a directory, use the `LIST` HTTP verb:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X LIST $VAULT_ADDR/v1/secret/metadata/tienda | jq -c .data
{"keys":["postgres"]}
```

### The alternative: the `vault` CLI inside the container

Everything above can also be done using the `vault` command-line tool packaged inside the container. `-e VAULT_TOKEN` passes your environment variable:

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

Store a second secret with it—the payroll bank secret—which you will use to test permissions:

```
$ docker compose exec -e VAULT_TOKEN vault vault kv put secret/nomina/banco cuenta=0123456789 clave=Aguacate-99
====== Secret Path ======
secret/data/nomina/banco
...
version            1
```

Notice that the CLI command appends `data/` automatically. That is why `curl` is more instructive: you see the real endpoint.

## Step 9 — Policies: to each their own key

A **policy** dictates which paths a token can access and what operations it can perform on them. Create the directory `politicas/` and within it the file `politicas/lectura-tienda.hcl`:

```hcl
# La app de la tienda puede LEER sus secretos. Nada más.
path "secret/data/tienda/*" {
  capabilities = ["read"]
}
```

`*` means "anything under `tienda/`." The most common capabilities are `read`, `create`, `update`, `delete`, and `list`. Anything not explicitly granted is denied.

Upload it. The API expects the policy definition inside a JSON object; `jq --rawfile p file` reads the file into variable `p`; `-n` tells `jq` not to wait for standard input, and the `\$p` is escaped so your shell doesn't mistake it for a shell variable. That way `jq` wraps the policy into the JSON payload without requiring manual escaping:

```
$ jq -n --rawfile p politicas/lectura-tienda.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/lectura-tienda -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X LIST $VAULT_ADDR/v1/sys/policies/acl | jq -c .data.keys
["default","default-ceiling","lectura-tienda","root"]
```

`-d @-` tells `curl` that "the payload comes from stdin," meaning whatever `jq` passed down the pipe.

Now create a **token for the app**, attached to that policy, with a 1-hour time-to-live. The full token is written to `secretos-locales/`, never to stdout:

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

The `default` policy is included on all tokens; it allows basic operations, such as inspecting your own token. `lease_duration: 3600` is 3,600 seconds: one hour.

Test all three scenarios. **Reading its own data:**

```
$ curl -s -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c .data.data
{"password":"Mango-2026","usuario":"app_tienda"}
```

Status code 200. **Reading payroll data:**

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/nomina/banco
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

**Writing to its own path:**

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" -X POST \
    $VAULT_ADDR/v1/secret/data/tienda/postgres -d '{"data": {"password": "me-la-robe"}}'
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Two 403s. The teller window said no. You can also query Vault about what capabilities you have on any path, without attempting the action:

```
$ curl -s -H "X-Vault-Token: $APP_TOKEN" -X POST $VAULT_ADDR/v1/sys/capabilities-self \
    -d '{"paths": ["secret/data/tienda/postgres", "secret/data/nomina/banco"]}' \
    | jq -c "{tienda: .[\"secret/data/tienda/postgres\"], nomina: .[\"secret/data/nomina/banco\"]}"
{"tienda":["read"],"nomina":["deny"]}
```

## Step 10 — The audit log: who asked for what

Every line in `vault/logs/audit.log` is a JSON record. How many are there already:

```
$ wc -l vault/logs/audit.log
      62 vault/logs/audit.log
```

The most recent responses, summarized: timestamp, caller, operation, path, and error (if any):

```
$ tail -n 6 vault/logs/audit.log | jq -c "select(.type == \"response\") | {hora: .time, quien: .auth.display_name, operacion: .request.operation, ruta: .request.path, error: .error}"
{"hora":"2026-10-18T14:47:54.325141694Z","quien":"token-app-tienda","operacion":"update","ruta":"secret/data/tienda/postgres","error":"1 error occurred:\n\t* permission denied\n\n"}
{"hora":"2026-10-18T14:47:54.338083991Z","quien":"token-app-tienda","operacion":"update","ruta":"sys/capabilities-self","error":null}
{"hora":"2026-10-18T14:47:54.351637479Z","quien":"token-app-tienda","operacion":"read","ruta":"auth/token/lookup-self","error":null}
```

There is the write attempt from the app, identified by name (`token-app-tienda`: Vault prepends `token-` to the `display_name`) along with its `permission denied`. This is what Iván was missing on Saturday: **the exact identity behind every attempt**.

Who read the store secret?

```
$ jq -c "select(.type == \"response\" and .request.path == \"secret/data/tienda/postgres\" and .request.operation == \"read\") | {quien: .auth.display_name, error}" vault/logs/audit.log
{"quien":"root","error":null}
...
{"quien":"token-app-tienda","error":null}
```

Several reads by `root` (you, configuring things) and one by the app.

Now for the interesting part. Did the audit log record the plaintext password?

```
$ jq -c "select(.type == \"response\" and .request.path == \"secret/data/tienda/postgres\" and .auth.display_name == \"token-app-tienda\") | .response.data" vault/logs/audit.log | head -1
{"data":{"password":"hmac-sha256:bbda6f946e50152cf8b72cd5a9716a077096420551a4c5a7cb395e4f7eddd734","usuario":"hmac-sha256:becdf07b09b37a0b8d310c8f5e99dac229b4cc1b80e092e4b9107ee0f7483212"},"metadata":{...}}
$ grep -c "Mango-2026" vault/logs/audit.log
0
```

No. By default, Vault records an HMAC-SHA256 **hash** of sensitive string values in the audit log, not the raw value ([Audit devices](https://developer.hashicorp.com/vault/docs/audit)). Numbers and boolean values are not hashed; that is why it is best practice to store secrets in Vault as strings, as done in this lab. A hash is like a person's fingerprint: it lets you check whether two things are the same, but it does not let you reconstruct the person. Consequently, whoever inspects the audit log does not walk away with the passwords.

And if you ever need to determine whether a password leaked in a chat room matches what the app read, you can ask Vault for the HMAC hash of that text and compare:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/sys/audit-hash/archivo \
    -d '{"input": "Mango-2026"}' | jq -r .data.hash
hmac-sha256:bbda6f946e50152cf8b72cd5a9716a077096420551a4c5a7cb395e4f7eddd734
```

It is the identical hash. It matches.

To finish up, the application can **revoke its own token** when done. After that, it is rendered useless:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/revoke-self
HTTP 204
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres
{"errors":["2 errors occurred:\n\t* permission denied\n\t* invalid token\n\n"]}
 HTTP 403
```

---

👉 **If you are in Management:** Shamir's keys are the technical equivalent of **joint bank account signatures**: to transfer funds, two out of three authorized signatories must sign, and none can act alone. The policy returning a 403 is **separation of duties**: whoever inputs data does not authorize it; whoever collects payment does not reconcile accounts. And the HMAC-hashed audit log is an audit trail that logs who accessed which record without photocopying the record itself. If you ever have to audit a system's controls, ask about these three things using those exact terms; they will almost always understand you.

---

## Exercises for Session 2

The solutions are at the end.

**Exercise 6 — The turnstile.** Create a new directory, `lab-prueba`, and copy only three files into it: `.gitignore`, `compose.yaml`, and `iniciar.sh`. Do it this way, with a fresh copy, rather than copying your already-used directory: that one already contains a `.env` and the exercise would prove nothing. Inside `lab-prueba`, delete the `.env` line from `.gitignore` and run `./iniciar.sh`.

**How to verify:** before running the script, `ls -a` must not show any `.env`. Afterwards, it must print `ALTO: .gitignore no tiene la regla '.env'.`, exit with code 1 (verify it with `echo $?` immediately after), and **not** create the `.env` file (verify it with `ls -a`).

**Exercise 7 — The stewards.** Restart Vault with `docker compose restart vault`. Unseal it using keys 4 and 5 (`.keys[3]` and `.keys[4]`), followed by key 1.

a) Does it matter which three keys you use?
b) What do you see in `progress` after the second key?

**How to verify:** at the end, `sys/health` must respond with `200`.

**Exercise 8 — Your own versioned secret.** Store under `secret/data/tienda/correo` a user `avisos` and a password generated with `openssl rand -hex 12`. Then update it to another password generated the same way. Finally:

a) Read version 1 and version 2.
b) Delete version 2 with `DELETE`, verify the 404, and recover it.
c) Show using `metadata/` how many versions exist.

**How to verify:** `current_version` must be `2` and the final read must return the second password.

**Exercise 9 — A policy for accounting.** Write `politicas/contabilidad.hcl`: it can **read** `secret/data/nomina/*` and **list** `secret/metadata/nomina/*`, nothing else. Upload it, create a token with it (store it in `secretos-locales/`), and test:

a) Reading `secret/data/nomina/banco`.
b) Reading `secret/data/tienda/postgres`.
c) Writing to `secret/data/nomina/banco`.

**How to verify:** a) 200; b) 403; c) 403. And `sys/capabilities-self` for the payroll path must return `["read"]`.

**Exercise 10 — The detective.** Using `jq` on `vault/logs/audit.log`, generate a list of **all responses with errors**, showing who made them and which path was targeted.

**How to verify:** at least the two 403s from `token-app-tienda` in Step 9 and the two 403s from Exercise 9 (b and c) must appear. If your list comes out empty, check that you filter by `.type == "response"` and check for `.error != null`.

---

## Common errors (and how to spot them)

| Error | What it looks like | How to spot it | What to do |
|---|---|---|---|
| Forgetting `data/` in the KV v2 path | `curl .../v1/secret/tienda/postgres` returns 404 with the message `Invalid path for a versioned K/V secrets engine` | The path lacks `data/` | Data goes in `secret/data/...`; versions in `secret/metadata/...` |
| Policy written without `data/` | You wrote `path "secret/tienda/*"` and the token gets 403 on its own path | `sys/capabilities-self` reports `deny` | The policy uses the API path: `secret/data/tienda/*` |
| Vault sealed after restarting | Everything responds with `{"errors":["Vault is sealed"]}` with HTTP status 503 | `sys/seal-status` reports `sealed: true` | Unseal it with 3 keys. This is expected behavior, not a failure |
| The `VAULT_TOKEN` variable is empty | 403 even though you are using the root token | `echo ${#VAULT_TOKEN}` prints `0` | Each new terminal session starts without variables: export it again |
| Single quotes around a variable | `-d '{"key": "$LLAVE"}'` sends the literal text `$LLAVE` | Vault says the key is invalid | Inside single quotes, the shell does not expand variables. Use double quotes and escape the inner quotes: `"{\"key\": \"$LLAVE\"}"` |
| Pasting the token into a file in the repo | The token appears in `git status` or in a commit | `git log -p -S hvs.` finds it | Tokens live in `secretos-locales/` and in terminal variables. If committed: revoke it |
| Port already in use on startup | `bind: address already in use` | `lsof -nP -iTCP:5432 -sTCP:LISTEN` shows another process (replace 5432 with 8200 or 3306 for another service) | Change the port in `.env` (`PUERTO_POSTGRES=15432`, `PUERTO_VAULT`, or `PUERTO_MARIADB`) and re-run `docker compose up -d`; if you changed `PUERTO_VAULT`, re-export `VAULT_ADDR` |

---

## Review for the next session

Session 3 begins with these three questions. Answer them without looking:

1. Why does Vault start up sealed, and how many keys do you need by default to unseal it?
2. A token receives a 403. What are two possible causes, and which Vault endpoint tells you what that token is allowed to do?
3. If someone steals the audit log, do they get the passwords? Why or why not?

🔁 **Next week:** the stolen backup contained eight thousand CURPs, and the key to decrypt them was stored right beside it. You learn how to encrypt with Vault without your program ever holding the key, store encrypted data in PostgreSQL, and discover how many times that backup was taken.

**Before you go:** shut down the lab with `docker compose stop`. Your data remains in the directories. Next time, run `docker compose start` and unseal it using the loop from Step 5.

---

## Solutions (do not peek before trying)

**Review from Session 1.**

1. Any four of: the password in code or in a committed file; the `.env` shared via chat; the same password for everyone forever; nobody knows who used it; former employees still know it; the encryption key stored next to the data.
2. Because git preserves history: the password remains in previous commits, and anyone who cloned the repository has a copy. Deleting it does not erase those copies; rotating it does make them useless.
3. They are similar in that you send data and receive encrypted data without the key leaving. They differ in that an HSM is a physical hardware appliance with tamper-resistance protections (whose strength depends on the model), while Vault is software running on a server; Transit is a Vault engine that exposes encryption operations via an API.

**Exercise 6.** The output is:

```
ALTO: .gitignore no tiene la regla '.env'.
Sin ella, las contraseñas que voy a generar podrían terminar en git. No sigo.
```

`echo $?` yields `1` and `ls -a` does not show `.env`.

**Exercise 7.** a) It does not matter: any combination of 3 out of the 5 works. b) `progress: 2` and `sealed: true`. With the third key, `sealed: false`.

**Exercise 8.** One approach:

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

The first two produce `1` and `2`; the two reads with `?version=` display the first and second passwords; `DELETE` yields `204`, the subsequent read returns `404`, and `current_version` yields `2`. The last line prints `true` if the final read retrieves the second password. Notice that you never typed the passwords yourself: they came from `openssl` and traveled inside a variable.

**Exercise 9.** The policy:

```hcl
path "secret/data/nomina/*" {
  capabilities = ["read"]
}
path "secret/metadata/nomina/*" {
  capabilities = ["list"]
}
```

It is uploaded and used just like `lectura-tienda`, changing the name. The expected outcomes: 200, 403, 403.

**Exercise 10.**

```
jq -c 'select(.type == "response" and .error != null) | {quien: .auth.display_name, ruta: .request.path, error}' vault/logs/audit.log
```

Notice that here the filter is wrapped in single quotes, which is why the inner double quotes do not require backslashes.

---

## What's next

In Session 3 you will use PostgreSQL from your terminal with `psql`. Verify that you have it with `psql --version`. If not, install the client: `sudo apt install postgresql-client` on Linux, or `brew install libpq` on macOS (and follow the instructions it provides to add it to your `PATH`).

---

*I write from what we encounter every day at Hábil, where we build systems for banking, insurance, and businesses in Mexico. If you run into a problem like this at work or in your family business, let's talk: [habil.mx](https://www.habil.mx/en/)*
