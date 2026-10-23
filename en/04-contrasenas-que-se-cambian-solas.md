# Vault from Scratch (4): Passwords That Change Themselves

*Database users born the moment you ask for them and dead two minutes later, passwords rotating every minute without anyone editing a file, and a Python program connecting to PostgreSQL without knowing any passwords at all. And the conclusion to the 3:17 mystery.*

*Vault from Scratch · Session 4 of 4*

## Review from Session 3

Answer without looking. The answers are in the solutions at the end.

1. What do the three parts of `vault:v2:SmfKDK1u...` mean?
2. You rotated the key. What happens to the data that was already encrypted, and what operation upgrades it to the new version without anyone seeing the plaintext?
3. Why is an encrypt-only token useful for a registration form?

> **The course lab** is in the public repository [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Build it yourself first; the repository is for comparing when something does not come out the same for you. It contains no passwords: the lab generates them upon startup.

## Objectives for this session

| # | By the end you will be able to… | Demonstrated by |
|---|---|---|
| 1 | **Configure** Vault's Database engine with a dedicated user, without using the superuser | Steps 2 and 3 |
| 2 | **Request** dynamic credentials, **log in** with `psql`, and **verify** that they stop working upon expiring or being revoked | Exercises 16, 17, and 19 |
| 3 | **Place** an existing user under automatic rotation and **demonstrate** that the old password no longer works | Exercise 18 |
| 4 | **Create** a dynamic read-only credential in MariaDB using the `mariadb` client, verify that it cannot modify data, and revoke it | Step 10 |
| 5 | **Run and modify** a Python script that requests its credentials from Vault, queries PostgreSQL, and stores zero database passwords | Step 12 and Exercise 20 |

---

## Scenario (fiction) — Chapter 9: Tuesday, 9:00 a.m.

Iván dials a number he hasn't dialed in eight months.

“Toño? It's Iván, from Canasta Morada. Hey, weird question. Does a server named TR-REPORTES ring a bell?”

Silence. Then, a burst of laughter.

“No way! Is that thing still running?”

Toño explains without embarrassment. Two and a half years ago, accounting asked for a weekly report of customers paying with grocery vouchers, along with their CURP, to reconcile with the voucher company. The database was heavily loaded during the day, so Toño rented a cheap cloud server on the company card and set up a script:

- Every Saturday at 3:17 it connected to the database using the `app_tienda` password.
- It downloaded the nightly backup and `llave.txt` to decrypt the CURPs.
- It generated an Excel sheet and emailed it to `reportes@`.

“And when I left, I forgot to tell you guys. My bad.”

Rocío checks: the `reportes@` inbox has one hundred and seventeen unopened emails. Nobody had checked it since the previous head of accounting left.

There was no thief.

There was something worse: an open door nobody knew existed. One hundred and seventeen copies of eight thousand CURPs, with the key sitting right beside them, on a server nobody controlled, in another country, paid for every month on the company card.

And without identity-based audit logging or expiring credentials, it was impossible to tell apart from an attack.

---

## Chapter 10: Saturday, 3:17 a.m. One month later

The TR-REPORTES server no longer exists; Iván deleted it while on a video call with Toño, reviewing every folder together.

The voucher report is now handled by a new script running inside Canasta Morada's servers. At 3:17 it asks Vault for database credentials. Vault creates a user that didn't exist a second earlier, with read-only permissions and an expiration date. The script runs for four minutes. By 3:21, the user is gone.

The database password Vault uses to create those users is known to no one: not Iván, not doña Clara. Vault rotated it on day one.

Iván's phone does not buzz.

Valeria writes the incident postmortem. On the last line she notes: *“We will never know if someone saw the public repository during those hours. That's why we changed the password. Next time someone accidentally pushes a `.env`, neither the application password nor Vault's will be in it. Even so, whatever that file does contain—such as administrative passwords—must be rotated immediately.”*

*(End of scenario.)*

---

## Why it matters

In Sessions 2 and 3 secrets no longer lived in files, but they were still **the same for months**. If someone read the `app_tienda` password from Vault, it was good until someone changed it by hand.

Today you take the final step: **passwords that do not exist until you request them and die on their own**. It is the difference between your house key and a visitor badge at an office building. The key works for years. The badge is handed to you at reception with your name on it, unlocks only the floor you are visiting, and stops working at 6:00 p.m. If you lose it in the elevator, nobody cares.

## Today's concepts

**Dynamic credential.** A database user that Vault creates at the moment you ask for it, with a random password, and deletes when it expires. Every program, each time it asks, receives a different one. If it leaks, it is only good for minutes.

**Lease and TTL.** Every dynamic credential comes with a lease: a contract with an expiration timestamp. The **TTL** (*time to live*) is how long it lasts. Like a shopping mall parking ticket: your ticket records entry time and expires; if you need more time, you pay again (renew), up to a ceiling.

**Revoke.** Canceling a lease early. Vault drops the user from the database right at that moment.

**Static role with rotation.** There are users you cannot swap for a new one every time, because other systems identify them by name. For those, Vault keeps the user and **rotates the password** periodically, using `rotation_period`. Whoever needs it requests it from Vault and always gets the active one ([Database secrets engine](https://developer.hashicorp.com/vault/docs/secrets/databases)).

**Vault's credential in the database.** To create and drop users, Vault needs its own user inside the database. The documentation warns that if you ask Vault to rotate that password with `rotate-root`, afterwards **nobody** will know it, and recommends creating a dedicated user for Vault instead of using the superuser ([Database secrets engine API](https://developer.hashicorp.com/vault/api-docs/secret/databases)). That is what we do: a `vault_admin` user with least privilege, not `postgres` which can do everything.

---

## Step 1 — Prepare your terminal

Lab running, Vault unsealed, token exported, and PostgreSQL variables loaded from `.env`:

```
docker compose start
set -a; source .env; set +a
export VAULT_ADDR=http://127.0.0.1:$PUERTO_VAULT
for i in 0 1 2; do
  LLAVE=$(jq -r ".keys[$i]" secretos-locales/init.json)
  curl -s -X PUT $VAULT_ADDR/v1/sys/unseal -d "{\"key\": \"$LLAVE\"}" | jq -c '{sealed, progress}'
done
export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)
export PGHOST=127.0.0.1 PGPORT=$PUERTO_POSTGRES PGDATABASE=tienda
```

Notice that this time we do **not** export `PGUSER` or `PGPASSWORD`: today you will log into PostgreSQL with several different users, and each command will specify which one.

The outputs in this lesson are real, but they come from independent runs; that is why their timestamps, usernames, and version numbers (such as `vault:v3:`, which depends on how many times you rotated the key in Session 3) do not form a single sequence. Yours will differ.

## Step 2 — A user for Vault, and an old user to rotate

Create two users in PostgreSQL, each with an initial random password saved in `secretos-locales/` (git ignores it):

- `vault_admin`: the one Vault will use. It can create users (`CREATEROLE`) and grant read permissions on tables (`WITH GRANT OPTION`). It is not a superuser.
- `reportes`: a longstanding user, like the kind reporting jobs use. You will place it under automatic rotation.

Each receives its **own** initial password: if they shared the same one, anyone who obtained `reportes`'s password would log in as `vault_admin`, which can create users.

**Checkpoint before repeating.** This step expects a fresh lab. If you repeat it, you would write new passwords into the files in `secretos-locales/` that no longer match what PostgreSQL has. If you see `role already exists` or that the `database/` engine already exists, do not regenerate the initial files: check the state and only perform the missing steps.

| If you see | It means | What to do |
|---|---|---|
| `CREATE ROLE` or `HTTP 204` | You are on track | Continue |
| `role "vault_admin" already exists` | Step 2 already ran, fully or partially | Do not regenerate the initial files |
| `path is already in use` | The Database engine is already mounted | Skip to reading or configuring the connection (Step 3) |

`psql -v name=...` defines a variable that is used inside as `:'name'`. That way the password is not left verbatim in the command or in your history. `psql` substitutes it before sending the SQL to PostgreSQL, so the password does travel inside the query; for that reason, outside the lab, TLS is used and logging queries containing passwords is avoided:

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

The last line grants `vault_admin` permission to administer `reportes`, which is what it needs to change its password. Starting with PostgreSQL 16, a user with `CREATEROLE` can only alter users it created or that were granted to it like this.

## Step 3 — Connect Vault to PostgreSQL

Enable the Database engine:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/database -d '{"type": "database"}'
HTTP 204
```

Now the connection. The `vault_admin` password is read by `jq` from the file with `--arg`: you don't type it, and it doesn't show up in your history. In `connection_url`, `{{username}}` and `{{password}}` are filled in by Vault, and the host is named `postgres` because Vault looks for it by its name on the Docker Compose network, not `127.0.0.1`. `allowed_roles` specifies which roles can use this connection:

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

Vault verified the connection before saving it (`verify_connection` is enabled by default); if the password were wrong, it would reject it right here. Read the configuration:

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

The password does not appear. Once Vault has it, it does not reveal it even to the root token.

## Step 4 — A role for dynamic credentials

A **role** is the recipe for creating a user. Save it in `roles/lector-postgres.json`. That file, `politicas/app-python.hcl`, and `python/clientes.py` already come in the lab directory; if you prefer to write them yourself, create the directories with `mkdir -p roles politicas python`, open the file in your editor, paste the full block without modifying it, and save it before running the next command:

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

- `creation_statements`: the SQL statements Vault runs when creating the user. `VALID UNTIL '{{expiration}}'` causes PostgreSQL itself to reject the password once expired, even if Vault takes time to drop it. This is the example from the documentation ([PostgreSQL](https://developer.hashicorp.com/vault/docs/secrets/databases/postgresql)).
- `revocation_statements`: the SQL to drop it. Why we wrote it by hand you will see in Step 6, through a real-world error.
- `default_ttl` of 2 minutes so you can witness expiration without waiting; in real life these are usually minutes or hours. `max_ttl`: even if renewed, never beyond 10.

Write it to Vault. `-d @file` tells `curl` to send the file's contents:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/roles/lector -d @roles/lector-postgres.json
HTTP 204
```

## Step 5 — Request a credential and log in

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

A user that didn't exist a second ago. The name includes who requested it (`root`), the role (`lector`), a random string, and the Unix timestamp. In this lab, `root` is not a person: it is simply the administrative token. In production it is not handed to people or applications; each person or program authenticates with their own identity (such as OIDC, AppRole, or Kubernetes), so that the temporary username clearly indicates who requested it. Log in with it:

```
$ export PGUSER=$(jq -r .data.username secretos-locales/creds-lector.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-lector.json)
$ psql -c "SELECT current_user, nombre, left(curp, 9) FROM clientes;"
                 current_user                  | nombre |   left
-----------------------------------------------+--------+-----------
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | Pepe   | vault:v3:
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | María  | vault:v3:
(2 rows)
```

It works, and notice: even with their own user, CURPs remain encrypted. This reader can view the table, but not the CURPs; for that they would also need Transit permissions. Try deleting:

```
$ psql -c "DELETE FROM clientes;"
ERROR:  permission denied for table clientes
```

Read-only, just as defined in the role. And from the superuser account, you can see the new user along with its expiration date:

```
$ PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -c "SELECT rolname, rolvaliduntil FROM pg_roles WHERE rolname LIKE 'v-%';"
                    rolname                    |     rolvaliduntil
-----------------------------------------------+------------------------
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | 2026-10-18 14:52:54+00
(1 row)
```

## Step 6 — Revoking… and a real error

**Reading note.** The first block reproduces an error from an earlier test run. Do not execute commands using `secretos-locales/creds-lector-2.json`: that file is not created in this current walkthrough. In your lab, the role from Step 4 already includes `revocation_statements`; you practice proper revocation in Exercise 17, using `creds-16.json`.

The first time we tested this lesson, the role did **not** have `revocation_statements`. We requested a second credential and revoked it early with `sys/leases/revoke`:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-lector-2.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
{"errors":["failed to revoke entry: resp: (*logical.Response)(nil) err: could not perform all revocation statements: ERROR: permission denied for sequence clientes_id_seq (SQLSTATE 42501)"]}
```

HTTP 400. Without `revocation_statements`, Vault uses the PostgreSQL plugin's default drop SQL, which attempts to revoke the user's permissions on **everything** in the `public` schema, including sequences (the counters generating `id`s). Our `vault_admin`, configured with least privilege, has no authority over the `clientes_id_seq` sequence, and PostgreSQL refused. The temporary user was left in limbo: stripped of table permissions, but not dropped.

It is a great error: it appears **because** we did not grant Vault superuser privileges. The right fix isn't to give it more power, but to tell it exactly what to do. That's why the role in Step 4 carries its own `revocation_statements`: revoke what was granted and drop the user. With the role corrected and uploaded again, the same revocation succeeds:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-lector-2.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
HTTP 204
$ PGUSER=$(jq -r .data.username secretos-locales/creds-lector-2.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-lector-2.json) psql -At -c "SELECT count(*) FROM clientes;"
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-QyRyJ1vdjmrPY6U0KXl2-1792335063"
```

The user no longer exists. If you copied the complete role from Step 4, your first revocation will work right away.

`"sync": true` is important: by default Vault merely **queues** revocation and returns `204` immediately without waiting for the database to delete the user. With `sync`, it waits until completion, so your attempt to log in right after does not depend on luck ([sys/leases](https://developer.hashicorp.com/vault/api-docs/system/leases)).

## Step 7 — Waiting for it to expire

Now for the first credential, the one from Step 5. Do nothing: wait for its 2 minutes to pass. Vault revokes it automatically and logs it (`docker compose logs vault`):

```
2026-10-18T14:52:49.642Z [INFO]  expiration: revoked lease: lease_id=database/creds/lector/rOpuliUuxFqc2UbdHMofQV8S
```

Try logging in:

```
$ date -u +%T; psql -At -c "SELECT count(*) FROM clientes;"
14:53:32
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049"
```

Nobody revoked it manually. Nobody edited a file. It died on its own. This is what would have saved Canasta Morada: the password in Toño's script would have stopped working two minutes into that first Saturday.

## Step 8 — Automatic rotation of an existing user

`reportes` has existed from before and other systems identify it by name. Confirm that today it can log in using its initial password:

```
$ PGUSER=reportes PGPASSWORD=$(cat secretos-locales/reportes_inicial.txt) psql -At -c "SELECT current_user;"
reportes
```

Put it under a **static role** that rotates every minute (the API's minimum is 5 seconds; one minute lets you see it without falling asleep):

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-roles/reportes \
    -d '{"db_name": "postgres", "username": "reportes", "rotation_period": "1m"}'
HTTP 204
```

The documentation explains that Vault **rotates the password upon creating the static role**, because it needs to know it ([Database secrets engine API](https://developer.hashicorp.com/vault/api-docs/secret/databases)). Thus, the initial password is already dead:

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

Whoever needs to log in as `reportes` asks Vault for the currently active password on the spot:

```
$ PGUSER=reportes PGPASSWORD=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password) \
    psql -At -c "SELECT current_user, count(*) FROM clientes GROUP BY 1;"
reportes|2
```

Wait a couple of minutes and ask again. `last_vault_rotation` stepped forward on its own, and Vault's log confirms it:

```
2026-10-18T14:52:59.517Z [INFO]  secrets.database.database_4731c3d7: successfully rotated static role: name=reportes ttl=60
```

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -c ".data | {password: (.password[0:6] + \"...\"), last_vault_rotation, ttl}"
{"password":"OH0KOU...","last_vault_rotation":"2026-10-18T14:53:59.530969477Z","ttl":11}
```

And if you don't want to wait, rotate it yourself using `rotate-role`. Another new password; the one from a moment ago no longer logs in (you verify this in Exercise 18).

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-role/reportes
HTTP 204
```

If instead of “every minute” you need “every Sunday at 4:00 a.m.”, there is `rotation_schedule`, with a five-field cron format; it cannot be used together with `rotation_period`. Vault evaluates it in **UTC**, not your local city time: for 4:00 a.m. on Sunday in Mexico City (UTC-6), write `0 10 * * SUN`; adjust the calculation for your time zone ([Database secrets engine API](https://developer.hashicorp.com/vault/api-docs/secret/databases)). We do not test it in this lesson.

## Step 9 — Ensuring no one knows Vault's password: `rotate-root`

The initial password for `vault_admin` is in `secretos-locales/vault_admin_inicial.txt`. Right now it works:

```
$ PGUSER=vault_admin PGPASSWORD=$(cat secretos-locales/vault_admin_inicial.txt) psql -At -c "SELECT current_user;"
vault_admin
```

Ask Vault to change it to one only it knows:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-root/postgres
HTTP 204
$ PGUSER=vault_admin PGPASSWORD=$(cat secretos-locales/vault_admin_inicial.txt) psql -At -c "SELECT current_user;"
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "vault_admin"
```

The file is now garbage. And Vault keeps working, because it does know the new one:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector | jq -c "{username: .data.username, lease_duration}"
{"username":"v-root-lector-R3rwerQPR0yvfCxuAxYI-1792335221","lease_duration":120}
```

Now no human knows the password used to create database users. If someone mistakenly uploads a configuration file, `vault_admin`'s password is no longer in it. Watch out for what does remain: `.env` still holds the administrative passwords for PostgreSQL and MariaDB in the lab, and `rotate-root` does not touch them. In production, those shouldn't live in a file either.

## Step 10 — The same with MariaDB

MariaDB has also been running since Session 2. Its `root` password is in `.env`. The `mariadb` client reads the password from the `MYSQL_PWD` environment variable, so you don't type it into the command either. Create a products table and MariaDB's `vault_admin` user:

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

That warning is emitted by the newer MariaDB client when connecting without verifying the server's identity (TLS); in the lab it doesn't matter. If it bothers you, add `--skip-ssl-verify-server-cert`.

For MariaDB, the `mysql-database-plugin` is used; Vault's documentation covers MySQL and MariaDB on the same page ([MySQL/MariaDB](https://developer.hashicorp.com/vault/docs/secrets/databases/mysql-maria)). Note that the address format is different:

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

The role, in `roles/lector-mariadb.json`:

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

Here there was no need to write `revocation_statements`: the MySQL plugin's default drop behavior worked with these permissions. Connect, read, and try to change prices:

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

Revoke and test again:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-maria.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
HTTP 204
$ MYSQL_PWD=$(jq -r .data.password secretos-locales/creds-maria.json) mariadb -h 127.0.0.1 -P $PUERTO_MARIADB \
    -u $(jq -r .data.username secretos-locales/creds-maria.json) tienda -e "SELECT 1;"
ERROR 1045 (28000): Access denied for user 'v-root-lector-mar-24LwvJevZDrYbE'@'172.21.0.1' (using password: YES)
```

(The address `172.21.0.1` is your machine as seen from the Docker network; yours might differ.) And the root credential:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-root/mariadb
HTTP 204
$ MYSQL_PWD=$(cat secretos-locales/vault_admin_maria_inicial.txt) mariadb --skip-ssl-verify-server-cert -h 127.0.0.1 -P $PUERTO_MARIADB -u vault_admin -e "SELECT CURRENT_USER();"
ERROR 1045 (28000): Access denied for user 'vault_admin'@'172.21.0.1' (using password: YES)
```

## Step 11 — The panic button

Remember requirement R6 from Session 1: revoking everything in one fell swoop? If you suspect that all credentials for a given role have leaked, you cancel them together by prefix. Using the `vault` CLI:

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

Pay attention to what that output demonstrated: “queued” means Vault accepted the command and queued it, and the empty list only shows that there are no leases left. What truly matters is the effect inside PostgreSQL. Count temporary users before revoking and a few seconds later:

```
PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -At -c "SELECT count(*) FROM pg_roles WHERE rolname LIKE 'v-root-lector-%';"
```

Before revoking it should return more than `0` (one for each credential still active); afterwards, `0`. If it's not `0` yet, wait a moment and run it again: the queue processes in the background. That count is what confirms the users are truly gone.

Four leases canceled with a single command. Revoking by prefix requires special permissions (`sudo`) on the path ([sys/leases](https://developer.hashicorp.com/vault/api-docs/system/leases)); that is why we did it here with the root token.

## Step 12 — The only program: Python without passwords

Up to this point, everything was through the terminal. Now, what any real-world application does: ask Vault for its credential and connect. First, a policy for the program, `politicas/app-python.hcl`:

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

Write it to Vault and create a 30-minute token for the program:

```
$ jq -n --rawfile p politicas/app-python.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/app-python -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/create \
    -d '{"policies": ["app-python"], "ttl": "30m", "display_name": "app-python"}' \
    | jq -r .auth.client_token > secretos-locales/token-python.txt
```

Install the PostgreSQL connector for Python in a virtual environment:

```
python3 -m venv .venv
.venv/bin/pip install "psycopg[binary]"
```

**Today you don't need to master all of Python.** Treat this file as a solved program and focus only on four areas: `TOKEN` reads a secret from the environment; `vault(...)` communicates with Vault; `cred = ...` requests the temporary user; and the `with psycopg.connect(...)` block uses that user in PostgreSQL. In Exercise 20 you only change how the program exits.

And the program, `python/clientes.py`. It uses `urllib`, which comes standard with Python, to speak to Vault, and `psycopg` for PostgreSQL. It is 24 lines:

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

What it does, in order: the `vault` function sends a request to Vault with the token in the header (if you pass `datos`, it is a `POST`; if not, a `GET`) and returns the `data` portion of the response. It requests a dynamic credential, connects with it, reads the customers, and decrypts each CURP with Transit.

Run it using the program's token:

```
$ export VAULT_TOKEN=$(cat secretos-locales/token-python.txt)
$ .venv/bin/python python/clientes.py
Vault me prestó el usuario v-token-ap-lector-9FQ5IlE2i1HAUlZvuxZG-1792335175
Pepe   vault:v3:VEk...  ->  PEPE000101HDFXXX01
María  vault:v3:hKW...  ->  MARA990909MDFXXX02
```

Look through the file for a PostgreSQL or Transit password: there are none. The program does receive a Vault token from the environment; that token is also a secret, but it is not written in the code, it has limited permissions, and it lasts only 30 minutes. The username now starts with `v-token-ap`: Vault records that an `app-python` token requested it, not root. Run it again and it gives you **another** user. And if the program tries to step outside its policy:

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Without a token, it won't even start:

```
$ unset VAULT_TOKEN; .venv/bin/python python/clientes.py
...
KeyError: 'VAULT_TOKEN'
```

When you're done, switch back to the root token: `export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)`.

> **What about Java, .NET, or Go?**
>
> What you did with `curl` and Python can be done from any language, because Vault speaks HTTP. Almost nobody programs it by hand: every language has libraries. HashiCorp maintains a list distinguishing official libraries from community ones ([Client libraries](https://developer.hashicorp.com/vault/api-docs/libraries)):
>
> - **Go:** `github.com/hashicorp/vault/api`, the client officially maintained by HashiCorp.
> - **Java with Spring:** [Spring Cloud Vault](https://spring.io/projects/spring-cloud-vault) loads secrets from Vault into application configuration and can request database credentials on the fly. HashiCorp lists it among community libraries.
> - **Java with Quarkus:** the [Quarkus Vault](https://docs.quarkiverse.io/quarkus-vault/dev/index.html) extension, from the Quarkiverse project, covers KV, Transit, and dynamic credentials for database connectivity. It is also community-maintained.
> - **.NET:** [VaultSharp](https://github.com/rajanadar/VaultSharp) is the most widely known option. **It is not official**: it is a community project. HashiCorp's list also mentions an experimental .NET client which, according to the same page, is not production-ready.
>
> And there is a way to avoid touching code entirely: **Vault Agent**, a process that runs alongside your application, authenticates with Vault, renews its token, and renders secrets into a file using a template; your application simply reads that file ([Vault Agent](https://developer.hashicorp.com/vault/docs/agent-and-proxy/agent)). In Kubernetes, the **Vault Agent Injector** automatically adds it to pods that request it via annotations, placing secrets in a shared in-memory volume with the application ([Agent Injector](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/injector)).

> **And how does this look in a real-world system?**
>
> Imagine a platform serving many companies simultaneously that stores each company's provider passwords: bank access, invoicing provider, shipping carrier. If one company sees another's secrets, game over.
>
> Sound design does not tie the program to Vault. It first defines a **component with a concise contract**: “seal this secret for this company” and “unseal it”. Internally, each company gets **its own key, with versions**, just like the Transit key you rotated in Session 3: if a key is rotated, data sealed previously can still be unsealed, and with `min_decryption_version` an expiration is placed on old versions.
>
> Behind that contract, the provider is plugged in:
>
> - for **tests**, an in-memory implementation that wipes everything when finished;
> - for **production**, an adapter that calls Transit with a key per company (`transit/encrypt/empresa-a`, `transit/encrypt/empresa-b`), or a cloud key management service.
>
> That provider can be HashiCorp Vault or OpenBao, its open-source fork, which features a compatible Transit engine ([Transit in OpenBao](https://openbao.org/docs/secrets/transit/)); at Hábil we chose OpenBao.
>
> The rest of the system never knows which of the two is plugged in. This allows testing everything without spinning up Vault, and switching providers without rewriting the program. Notice what it **does not** do: the program never touches the key. It requests “seal” and “unseal”, and the key remains inside Vault, as you saw with `curl` in Session 3.

---

👉 **If you are in Management:** dynamic credentials are the equivalent of a **visitor badge** applied to systems: issued to whoever requests it, granting access only where necessary, and expiring on its own. Automatic rotation is the **periodic combination change** of the safe, but without anyone having to jot down the new code. And the panic button answers the question every auditor asks after an incident: “How long did it take you to revoke access?”. With this, the answer is “one command”. In Canasta Morada's case, the question that truly mattered was different: “Who is paying for that $9.99 server?”. Reviewing recurring company credit card charges is also access control.

---

## Exercises for Session 4

**Exercise 16 — Your badge.** Request a credential for the `lector` role, log in with `psql`, and count the customers. Then attempt `INSERT INTO clientes (nombre, curp) VALUES ('Intruso', 'x');`.

```
# Pista: guarda la credencial para usarla en el ejercicio 17.
# Archivo sugerido: secretos-locales/creds-16.json
# Ruta que debes consultar: database/creds/lector
```

**How to verify:** the count returns `2` (or however many you have); the `INSERT` returns `ERROR:  permission denied for table clientes`.

**Exercise 17 — Revoke it yourself.** Revoke the credential from Exercise 16 with `sys/leases/revoke` and attempt to log in again. Do this within the 2-minute window: if Vault already revoked it and the endpoint answers that the lease does not exist, that is not a permissions error. Request another credential, overwrite `creds-16.json`, and revoke it immediately.

**How to verify:** the revocation returns `HTTP 204` and `psql` returns `password authentication failed`. From the superuser, `SELECT count(*) FROM pg_roles WHERE rolname = '<the username>';` returns `0`.

**Exercise 18 — The password from a minute ago.** Store `reportes`'s active password in a variable, rotate it using `rotate-role/reportes`, and attempt to log in with the stored password.

**How to verify:** with the saved password, `password authentication failed for user "reportes"`. With the one Vault provides after rotating, you can log in.

**Exercise 19 — 30-second badge.** Change `default_ttl` for the `lector` role to 30 seconds, without editing the file, using `jq`:

```
jq '.default_ttl = "30s"' roles/lector-postgres.json \
  | curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/roles/lector -d @-
```

Request a credential, log in immediately, wait 40 seconds, and try again. Save the credential in `secretos-locales/creds-19.json` and prefix each attempt with `PGUSER=... PGPASSWORD=... psql`, reading values from the file with `jq` as in Step 5: whatever you exported in Exercises 16 and 17 belongs to an already revoked user and would give you a failure unrelated to TTL.

**How to verify:** `lease_duration` indicates `30`; the first attempt succeeds; the second returns `password authentication failed`. When finished, restore the role to its previous state by uploading `roles/lector-postgres.json` again.

**Exercise 20 — Having the program clean up its mess.** Every time `clientes.py` runs, it leaves a temporary user active until it expires. Have it **revoke its own token** using `auth/token/revoke-self`, and do so **always**, even if something fails midway (use `try` and `finally`). When a token is revoked, Vault also revokes the credentials requested with it. Start with this skeleton, which sets up the structure:

```python
try:
    cred = vault("database/creds/lector")
    # pega aquí el bloque with psycopg.connect(...) que ya existe
finally:
    # aquí va la petición POST a auth/token/revoke-self
    pass
```

**How to verify:** before running it, count from the superuser account the users starting with `v-token-ap`; after running it, the count should remain the same as before (the user was created and dropped). If you run it again with the same token, it must fail with `HTTP Error 403`, because the token no longer exists. To repeat the test after that 403, create a new token with the same command from Step 12, save it again in `secretos-locales/token-python.txt`, and export `VAULT_TOKEN` again. The 403 is expected only for the already revoked token.

---

## Common errors (and how to spot them)

| Error | What it looks like | How to spot it | What to do |
|---|---|---|---|
| Using `127.0.0.1` in `connection_url` | When saving the configuration: `error verifying connection: ... dial tcp 127.0.0.1:5432: connect: connection refused`, code 400 | The URL host is not the service name; inside the Vault container, `127.0.0.1` is Vault itself | Inside Docker Compose, Vault reaches the database by its service name: `postgres`, `mariadb` |
| Role not listed in `allowed_roles` | `"escritor" is not an allowed role`, code 500 | The role name does not appear in `database/config/<connection>` | Add it to the connection's `allowed_roles` |
| Revocation failing under least privilege | `permission denied for sequence ...` upon revocation | The role lacks `revocation_statements` | Write your `revocation_statements`; do not grant Vault superuser privileges just to make the error disappear |
| Storing the `vault_admin` password and then rotating root | The file is now useless | `rotate-root` returned 204 | That's what we want: no human knows it. If you need access, use the database superuser, not Vault's user |
| Expecting credentials to outlive `max_ttl` | You renew and it still expires | `lease_duration` stops growing | `max_ttl` is the ceiling. Request a new credential |
| Pasting the program's token into the code | The token is written into a file tracked by git | `git status` shows the file as modified, and `grep -rn hvs. python/` finds the token | The token should enter via environment variable or, better, via Vault Agent. If pushed, revoke it |
| `psql` connects without prompting for a password | You assume the credential is still active | You connected via the local socket inside the container | Connect over the network as done in the lesson (`-h 127.0.0.1` from your host machine), where PostgreSQL does verify passwords |

---

## Series Self-Assessment

Answer without looking. If you miss more than two, revisit the indicated session.

1. What is the difference between `DELETE` on `secret/data/...` and `destroy`? *(Session 2)*
2. Write from memory a policy that allows reading `secret/data/app/*` and nothing else. *(Session 2)*
3. Why is a 403 good news when testing a policy? *(Session 2)*
4. What do you need to decrypt a `vault:v1:...` if the key has `min_decryption_version: 2`? *(Session 3)*
5. What does a system gain from derived keys and `context`? *(Session 3)*
6. What is the difference between a dynamic credential and a static role? *(Session 4)*
7. Why does Vault's database connection use `vault_admin` rather than the superuser? *(Session 4)*
8. An intern leaves the company. With what you built, which passwords would you have to rotate manually? *(All)*

## Series Review

| Session | The problem | What solves it | The command you must not forget |
|---|---|---|---|
| 1 | Secrets in files, in chats, shared, and eternal | Requirements R1 through R7 | `git log -p -S <text>` |
| 2 | Nobody knows who has access or who used it | Shamir's secret sharing, tokens, policies, audit log | `curl -H "X-Vault-Token: ..." $VAULT_ADDR/v1/secret/data/...` |
| 3 | The encryption key lives right next to the data | Transit: encrypting without holding the key, rotating, rewrapping | `POST transit/encrypt/<key>` with base64 `plaintext` |
| 4 | The same database password for everyone and forever | Dynamic credentials, rotation, `rotate-root`, revocation | `GET database/creds/<role>` |

**To tear everything down upon completing the series:** `docker compose down`. Your data stays in the `vault/`, `postgres/`, and `mariadb/` folders. If you want to start from scratch, delete those folders, `secretos-locales/`, and `.env`, and run `./iniciar.sh` again.

---

## Solutions (don't look before trying)

**Review from Session 3.**

1. `vault`: encrypted by Vault; `v2`: using version 2 of the key; the rest: the encrypted ciphertext, base64-encoded.
2. They remain encrypted with their old version and can still be decrypted as long as that version does not fall below `min_decryption_version`. `rewrap` upgrades them to the new version without revealing the plaintext.
3. Because if someone steals that token, they can submit encrypted data but cannot read any of it. The damage from a leak is much smaller.

**Exercise 16.**

```
curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector > secretos-locales/creds-16.json
export PGUSER=$(jq -r .data.username secretos-locales/creds-16.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-16.json)
psql -At -c "SELECT count(*) FROM clientes;"
psql -c "INSERT INTO clientes (nombre, curp) VALUES ('Intruso', 'x');"
```

**Exercise 17.** The command from Step 6, using the `lease_id` from `creds-16.json`. Do it before the 2 minutes elapse; if Vault beats you to it, request another credential and revoke it immediately.

**Exercise 18.**

```
VIEJA=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password)
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-role/reportes
PGUSER=reportes PGPASSWORD=$VIEJA psql -At -c "SELECT 1;"
NUEVA=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password)
PGUSER=reportes PGPASSWORD=$NUEVA psql -At -c "SELECT 1;"
```

In this lesson's test run, the command using `$VIEJA` (the third one) returned `FATAL:  password authentication failed for user "reportes"`. Note: because the role rotates every minute, the “old” password might die from automatic rotation before yours triggers. The outcome is the same. The final command, using `$NUEVA`, prints `1`; if that also fails, request the current password from Vault again and re-run it, as the one-minute rotation could have occurred between commands.

**Exercise 19.**

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

In the test run:

```
{"lease_duration":30,"username":"v-root-lector-wlrG6BL0dqUomIbQDDrV-1792336140"}
```

The first attempt returned `2`. Forty seconds later:

```
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-wlrG6BL0dqUomIbQDDrV-1792336140"
```

**Exercise 20.** Place the credential request and everything using the database inside the `try`, and the revocation in the `finally`, which runs no matter what (even if the credential request itself fails):

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

That way, if the request, connection, or a query fails, the token is revoked regardless. `data=b"{}"` turns the request into a `POST`, which is what that endpoint requires. In this lesson's test run:

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

The user `v-token-ap-lector-xQMN...` was born and died within the same run. The program leaves nothing behind anymore.

**Self-Assessment.**

1. `DELETE` removes the latest version in a soft, reversible way (`undelete` restores it); `destroy` permanently deletes it.
2. `path "secret/data/app/*" { capabilities = ["read"] }`
3. Because it proves the policy denies what it is supposed to deny. A policy that never yields a 403 is likely overly permissive.
4. Nothing can decrypt it as long as the minimum is 2. The proper procedure was to rewrap it before raising the minimum; otherwise, you must lower `min_decryption_version`, rewrap, and raise it again.
5. That data encrypted for one tenant cannot be decrypted as if it belonged to another, even when using the same key.
6. A dynamic credential creates a fresh user each time and drops it upon expiration; a static role retains an existing user and rotates its password on a schedule.
7. Because `rotate-root` places the password in Vault's hands, and the documentation recommends a dedicated user. Furthermore, with least privilege, an error or breach in Vault does not grant complete control of the database.
8. None are rotated manually. You revoke their Vault token and, along with it, their dynamic credentials (or all credentials they created, by prefix). One exception: if they knew the password for the static role `reportes`, rotate it immediately with `POST /v1/database/rotate-role/reportes`; revoking their token does not change that password, which would otherwise remain valid until the next scheduled rotation. That is the contrast with Canasta Morada at the start of the series.

---

## What's next

This series ran Vault as a single server, without TLS and with keys saved to a file, because it is a lab. If you want to take it further, the next topics are: TLS on the listener, machine authentication methods (AppRole, Kubernetes) instead of manually issued tokens, multi-server storage for high availability, and backups of Vault itself.

---

*I write from what we see every day at Hábil, where we build systems for banking, insurance, and businesses in Mexico. If you run into a problem like this at work or in your family business, let's talk: [habil.mx](https://www.habil.mx/en/)*

*If database passwords in your company still live in a file, at Hábil we set this up as part of infrastructure provisioning: [identity, keys, and secrets](https://www.habil.mx/en/).*
