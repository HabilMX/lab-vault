# Vault from Scratch (3): Encrypting Without the Key

*Vault's Transit engine encrypts and decrypts for you, and the key never reaches your program. You store encrypted CURPs in PostgreSQL, rotate the key without losing anything, and learn how to delete data by destroying a key.*

*Vault from Scratch · Session 3 of 4*

## Review from Session 2

Answer without looking. The answers are in the solutions.

1. Why does Vault start sealed, and how many keys do you need by default to unseal it?
2. A token receives a 403. What are two possible causes, and what Vault path tells you what that token is allowed to do?
3. If someone steals the audit log, do they take the passwords with them? Why?

> **This session's lab** is in the public repository [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Build it yourself first; the repository is for comparing whenever something does not match. It contains no passwords: the lab generates them upon startup.

## Objectives for this session

| # | By the end you will be able to… | Demonstrated by |
|---|---|---|
| 1 | **Encrypt and decrypt** data with Transit using `curl`, and **explain** what base64 is and why it is not encryption | Exercise 11 |
| 2 | **Rotate** a key and **rewrap** old data to the new version without decrypting it yourself | Exercises 12 and 14 |
| 3 | **Write** a policy that allows encryption but not decryption, and **verify** the 403 | Exercise 13 |
| 4 | **Store** encrypted data in PostgreSQL with `psql` and **demonstrate** that anyone reading the table cannot see the data | Step 8 (guided) and Exercise 14 |
| 5 | **Bind** encrypted data to its owner with `context`, and **destroy** a key to render whatever it encrypted unreadable | Exercise 15 and Step 10 |

---

## Scenario (fiction) — Chapter 7: Monday, 10:12 a.m.

Iván didn't sleep well over the weekend. The 3:17 clock won't leave him alone.

On Monday, he requests the complete download log of the backups folder from the hosting provider. Not for just one week: for the entire lifespan of the server. He receives a text file with thousands of lines. He filters it by the address `185.xx.xx.xx`.

The first download from that address wasn't last Saturday.

It was two years and three months ago.

And ever since, **every Saturday at 3:21**, someone downloaded the overnight backup. And the folder with `llave.txt`. One hundred and seventeen Saturdays in a row.

Valeria, who finally confessed about the public repository, feels the tightness in her chest loosen. Her mistake happened ten days ago. This has been going on for two years.

“So it wasn't because of what I pushed,” she says.

“No,” answers Iván. “What you pushed was serious too, and that's why we changed everything. But this is something else.”

Doña Clara asks the uncomfortable question:

“And how many times did they take the CURPs?”

“One hundred and seventeen.”

---

## Chapter 8: Monday, 4:50 p.m.

While Iván redoes the encryption for the CURPs, Rocío, the accountant, walks into the office holding a statement from the company credit card. She is doing the monthly reconciliation, and there is a charge she has never understood:

```
SERV VIRTUAL CLOUD  TR-REPORTES     USD 9.99
```

“It's been like this for about two years,” she says. “I always thought it was something of yours.”

Iván looks up the IP address of the server billed under that charge in the provider's dashboard.

`185.xx.xx.xx`.

TR.

*(To be continued in Session 4.)*

---

## Why it matters

Problem number 6 from Session 1 was the key stored right next to the data. Canasta Morada did encrypt the CURPs, but whoever took the backup also took `llave.txt`, and the encryption was of no use.

The solution is not to hide the file better. It is to ensure that **the key is not in any file your program can read**. Your program tells Vault “encrypt this for me” and receives the ciphertext. It tells it “decrypt this for me” and, if authorized, receives the original plaintext. The key stays in Vault, protected by the seal you opened last week with three keys.

That is the **Transit** engine. The documentation describes it as “cryptography as a service” or “encryption as a service,” and makes clear that Vault **does not store** the data you send it: you store the result wherever you want ([Transit](https://developer.hashicorp.com/vault/docs/secrets/transit)).

That way, if someone takes a backup of the database tomorrow, all they get is text like `vault:v2:SmfKDK1u...`. Without access to Vault, it is of no use to them.

## Three words before getting started

**Encrypt.** Scramble data using a **key** so that only someone holding the key can read it again. When you were a child writing secret messages by swapping each letter for the next one in the alphabet, the key was “one letter forward.” Transit defaults to AES-256 in GCM mode, which is immensely stronger and also detects if anyone tampered with the ciphertext ([Transit API](https://developer.hashicorp.com/vault/api-docs/secret/transit)).

**Base64.** A way to represent any data, even binary, using only letters, numbers, `+`, `/`, and `=`. Transit requires data in base64 so arbitrary data (plain text, a small image) can safely travel inside a JSON payload. Mind the size: Vault's API defaults to a 32 MB limit per request, and base64 makes data roughly one-third larger. Large files are encrypted using a different technique, rather than sending them whole to Transit. **Base64 is not encryption.** It is like the F-language (“hofolafa”): it looks secret, but anyone who knows the rule can read it. Try it out:

```
$ echo -n "PEPE000101HDFXXX01" | base64
UEVQRTAwMDEwMUhERlhYWDAx
$ echo "UEVQRTAwMDEwMUhERlhYWDAx" | base64 -d; echo
PEPE000101HDFXXX01
```

The `-n` flag in `echo` prevents a trailing newline from sneaking in; without it, you would encrypt “CURP + Enter”. The CURPs in this lesson are fictional and do not belong to any real person; they include `XXX` so this is obvious. Do not use real people's data in your lab exercises.

**Key version.** A Transit key can have multiple versions. When you **rotate** it, a new version is created and used to encrypt future data; the older versions remain so you can still decrypt past data. It is like changing the padlock combination on a storage room every year while keeping older combinations in an envelope in case an old box turns up.

---

## Step 1 — Start the lab and enable Transit

**Two terminal mechanics you will use constantly.** `NAME=$(command)` executes `command` and stores its output in `NAME`. `$NAME` subsequently inserts that output. Try it: `SALUDO=$(echo hola); echo "$SALUDO"` should output `hola`. In the following block, `LLAVE=$(...)` temporarily stores an unseal key; if anything goes wrong, verify that `LLAVE` did not end up empty using `echo "${#LLAVE}"` (it must return a number greater than 0).

If you shut down the lab, start it up, unseal Vault, and export the token, just like in Session 2:

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

Enable the Transit secrets engine at the `transit/` path:

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/transit -d '{"type": "transit"}'
HTTP 204
```

**State management.** `docker compose stop` preserves Transit, your keys, and the table. If you receive `HTTP 400` with `path is already in use` when mounting Transit, it was already mounted: continue to Step 2. If the `curp` key or the `clientes` table already exists, do not repeat the inserts from Step 8. Check what is there first with `psql -c "SELECT id, nombre, left(curp, 9) FROM clientes;"` and continue only if you recognize those rows as previous work.

## Step 2 — Create a key

A key named `curp`. You do not pass any key material: Vault generates it internally.

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp
HTTP 200
```

Inspect it:

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

Notice what does **not** appear: the key itself. Inside `keys`, there is only a number per version, representing the timestamp when it was created. `exportable: false` states that it cannot be exported. Verify this:

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/export/encryption-key/curp
{"errors":["private key material is not exportable"]}
 HTTP 400
```

Not even the root token can export it. If you had specified `exportable: true` at creation time, it would be possible, and that decision is irreversible; that is why it is disabled by default.

## Step 3 — Encrypt

You send the base64-encoded text inside `plaintext`. The `$(...)` performs the conversion on the fly:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq .data
{
  "ciphertext": "vault:v1:A2se3zo5aKjY51c/tlquYpJrN/L8DDNh2BPzqvcrXfYwkW8yVVimMMzir5DRpw==",
  "key_version": 1
}
```

That `ciphertext` is what you will store. It consists of three parts separated by colons:

- `vault`: encrypted by Vault.
- `v1`: using **version 1** of the key.
- The rest: the encrypted data.

Encrypt **the exact same CURP again**:

```
vault:v1:qy8hRw2+KeTOHWr/RJ7D4tPbSlRDiTk96lZGn9+Jijp+lJRyUlfZph3upajdFw==
```

It is different. Every encryption operation includes a random component (a *nonce*), which is why two ciphertexts of the same input never look alike. This prevents anyone from inspecting the table and concluding “these two customers have the identical CURP.” (Transit offers a mode called *convergent encryption* that deliberately does the opposite so data can be searched; we do not use it here.)

## Step 4 — Decrypt

You send the `ciphertext` and receive base64:

```
$ C=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext)
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$C\"}" | jq .data
{
  "plaintext": "UEVQRTAwMDEwMUhERlhYWDAx"
}
```

And convert it back to plain text with `base64 -d`:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$C\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

If someone passes garbage shaped like a ciphertext, Vault does not guess:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"vault:v1:estonoescifrado\"}"
{"errors":["invalid ciphertext: could not decode base64"]}
 HTTP 400
```

## Step 5 — Rotate the key without losing anything

Save a ciphertext created with version 1 to a file for later use:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext | tee v1.txt
vault:v1:0uoMoZKeXU+18t3TiH3yOlTX7vL9wlNUWlMf1W4XapYdoVq2Z1OWVAg7hIgWlA==
```

`tee` displays the output on the screen while saving it to the file. Now **rotate**:

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp/rotate
HTTP 200
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp | jq -c ".data | {latest_version, min_decryption_version, versiones: (.keys | keys)}"
{"latest_version":2,"min_decryption_version":1,"versiones":["1","2"]}
```

New encryptions now come out with `v2`:

```
vault:v2:uzo5CXHaWgjXF3iUCzzefTFzOecaAcho3WjVJqnjVJ0IQIR3mk1DioElROdsxA==
```

And older data **can still be decrypted**, because version 1 is still retained:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

Rotating does not break anything. That is why it can be done frequently; there is even an `auto_rotate_period` setting so Vault automatically rotates a key on a schedule.

## Step 6 — Rewrap: upgrading old data to the new version

Rotating does not alter what is already stored: your database remains full of `v1` values. To upgrade them to `v2`, use **rewrap**: you provide the old ciphertext and it returns a new one encrypted with the latest version. The documentation clarifies that **the plaintext is never revealed** during this process ([Transit](https://developer.hashicorp.com/vault/docs/secrets/transit)): neither you nor your program ever see the CURP.

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/rewrap/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}" | jq -c .data | tee rewrap.json
{"ciphertext":"vault:v2:qR2K9Q5TmpKsG4umLEMX2bguVD1/R4nC+iNhKxAT5jrKGAc1clF5977n49Q85w==","key_version":2}
```

It is like taking old documents to a notary to get a new official stamp, without anyone reading them.

Once you have rewrapped everything, tell Vault to **reject** ciphertexts older than version 2:

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/curp/config -d '{"min_decryption_version": 2}'
HTTP 200
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}"
{"errors":["ciphertext or signature version is disallowed by policy (too old)"]}
 HTTP 400
```

The `v1` ciphertext no longer works. The rewrapped one does:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(jq -r .ciphertext rewrap.json)\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

This is what Canasta Morada needed: if an old copy of the database is floating around with `v1` ciphertexts, this setting ensures that copy can no longer be decrypted. Note: **this is not cryptographic erasure**. Vault still retains version 1 of the key, and an authorized operator could lower the minimum version again to allow decrypting it (the documentation describes this as a tuning knob that forms part of a rotation policy). Actually destroying a key is covered in Step 10.

## Step 7 — A policy that encrypts but does not decrypt

The customer registration form needs to **encrypt** CURPs. It never needs to read them. Create `politicas/solo-cifrar-curp.hcl`:

```hcl
# El formulario de alta puede CIFRAR curps, pero nunca descifrarlas.
path "transit/encrypt/curp" {
  capabilities = ["update"]
}
```

In Transit, encrypting and decrypting are write operations (`POST`), which in policies are mapped to `update`. For this key, which already exists, `update` is the correct minimum capability. Note: the `transit/encrypt/<key>` path accepts `create` or `update`, and with `create`, Vault can create a key that did not previously exist with default values, unless automatic key creation has been disabled ([Transit: Encrypt data](https://developer.hashicorp.com/vault/api-docs/secret/transit#encrypt-data)). Do not deduce policy capabilities solely from the HTTP verb.

Upload it and create a token for the form. It has a 3-hour TTL, enough for the session and its exercises; if it expires earlier, a 403 would look just like the 403 you are looking for in Exercise 13:

```
$ jq -n --rawfile p politicas/solo-cifrar-curp.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/solo-cifrar-curp -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/create \
    -d '{"policies": ["solo-cifrar-curp"], "ttl": "3h", "display_name": "formulario-alta"}' \
    | jq -r .auth.client_token > secretos-locales/token-formulario.txt
```

The registration form encrypts the CURP of a new customer:

```
$ F=$(cat secretos-locales/token-formulario.txt)
$ curl -s -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n MARA990909MDFXXX02 | base64)\"}" | jq -r .data.ciphertext | tee maria.txt
vault:v2:4LM7LCPcgym6rQAPOMQGWR4DIk1qi4NdtoaBM/yecdQfWsG9iCypdv7IST71dQ==
```

But if it tries to read it, or rotate the key:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat maria.txt)\"}"
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/keys/curp/rotate
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

If someone steals the form's token, they can insert encrypted CURPs, but they cannot read a single one. It is a drop box: anyone can drop a letter in, but only the mail carrier can open it.

## Step 8 — Storing it in PostgreSQL

PostgreSQL has been running since Session 2. Its password is in `.env`, generated by the script. Load it into your terminal without copying it by hand: `set -a` causes all defined variables to be exported, and `source .env` reads the file.

```
set -a; source .env; set +a
export PGHOST=127.0.0.1 PGPORT=$PUERTO_POSTGRES PGUSER=postgres PGDATABASE=tienda PGPASSWORD=$POSTGRES_PASSWORD
```

`psql` reads those `PG...` environment variables automatically; this avoids typing the password in the command line, where it would linger in your shell history. While acceptable in a local lab, `PGPASSWORD` exposes the password in the process environment, and the PostgreSQL documentation discourages it because on some operating systems other processes can view it. In production, use a password file with strict permissions or, better yet, Vault.

Create the customers table:

```
$ psql -c "CREATE TABLE clientes (id serial PRIMARY KEY, nombre text NOT NULL, curp text NOT NULL);"
CREATE TABLE
```

Insert Pepe with his encrypted CURP. First you encrypt, then you store the result:

```
$ CIF=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext)
$ psql -c "INSERT INTO clientes (nombre, curp) VALUES ('Pepe', '$CIF');"
INSERT 0 1
```

And María, encrypted using the registration form's token, which cannot read:

```
$ F=$(cat secretos-locales/token-formulario.txt)
$ CIF=$(curl -s -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n MARA990909MDFXXX02 | base64)\"}" | jq -r .data.ciphertext)
$ psql -c "INSERT INTO clientes (nombre, curp) VALUES ('María', '$CIF');"
INSERT 0 1
```

Now view the table as seen by someone with read permission (`SELECT`) on `clientes`, its owner, a superuser, or whoever possesses a backup. Connecting to the database is not enough: in PostgreSQL, that specific privilege is required ([Privileges](https://www.postgresql.org/docs/17/ddl-priv.html)). Here it works because we connect as `postgres`:

```
$ psql -c "SELECT * FROM clientes;"
 id | nombre |                                   curp
----+--------+---------------------------------------------------------------------------
  1 | Pepe   | vault:v2:GCD4q2/Fp+YtLKT185oGtoSBJ4M9wE5oKrOaDy93Hlmf84Nzh/4ZxWW+E62chg==
  2 | María  | vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
(2 rows)
```

They show `v2` because you rotated the key in Step 5. And the backup, which is what was being stolen every Saturday from Canasta Morada:

```
$ docker compose exec postgres pg_dump -U postgres -t clientes tienda | grep -A3 "^COPY"
COPY public.clientes (id, nombre, curp) FROM stdin;
1	Pepe	vault:v2:GCD4q2/Fp+YtLKT185oGtoSBJ4M9wE5oKrOaDy93Hlmf84Nzh/4ZxWW+E62chg==
2	María	vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
\.
```

Not a single readable CURP. And there is no longer any `llave.txt` to carry away.

Someone who does have decryption permissions reads from the table and requests it from Vault:

```
$ CIF=$(psql -At -c "SELECT curp FROM clientes WHERE nombre = 'María';"); echo "$CIF"
vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$CIF\"}" | jq -r .data.plaintext | base64 -d; echo
MARA990909MDFXXX02
```

`-At` tells `psql` to print only the raw value, with no headers or formatting borders.

## Step 9 — Binding encryption to its owner: `context`

Imagine Canasta Morada begins storing client files from two wholesale corporate customers, Empresa Norte and Empresa Sur, in the same table. A bug in application code, or someone with malicious intent, could take an encrypted record belonging to Norte, paste it into the row for Sur, and request to decrypt it “as belonging to Sur.”

Transit has a defense against this: **derived keys**. When you create a key with `derived: true`, every operation must supply a `context`: an additional piece of data, in base64, from which Vault derives a distinct key. A different `context` produces a different key ([Transit API](https://developer.hashicorp.com/vault/api-docs/secret/transit)). It is like an envelope that can only be opened with the wax seal of the company it was addressed to.

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/expedientes -d '{"derived": true}'
HTTP 200
```

Without `context`, it refuses:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
    -d "{\"plaintext\": \"$(echo -n diagnostico-confidencial | base64)\"}"
{"errors":["missing 'context' for key derivation; the key was created using a derived key, which means additional, per-request information must be included in order to perform operations with the key"]}
 HTTP 400
```

Encrypt for Empresa Norte:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
    -d "{\"plaintext\": \"$(echo -n diagnostico-confidencial | base64)\", \"context\": \"$(echo -n empresa-norte | base64)\"}" \
    | jq -r .data.ciphertext | tee ctx.txt
vault:v1:8lKFunrcJVIzLnq9q4ZNszSLDOotf4gqtenuKek8QTuCIh4yq1ldoqtjMbsojged+/0aPQ==
```

With the correct `context`, it is decrypted:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
    -d "{\"ciphertext\": \"$(cat ctx.txt)\", \"context\": \"$(echo -n empresa-norte | base64)\"}" | jq -r .data.plaintext | base64 -d; echo
diagnostico-confidencial
```

Impersonating Empresa Sur:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
    -d "{\"ciphertext\": \"$(cat ctx.txt)\", \"context\": \"$(echo -n empresa-sur | base64)\"}"
{"errors":["cipher: message authentication failed"]}
 HTTP 400
```

`message authentication failed`: AES-GCM verification detected a mismatch. The file belonging to Norte can only be opened as Norte. In real-world applications, `context` is typically the customer ID or tenant identifier owning the data.

An important clarification: `context` **is neither a password nor an authorization mechanism**. It is a parameter supplied by the caller; if someone has permission to decrypt with that key and knows the value `empresa-norte`, they can request decryption with it. That is why the application must derive `context` from trusted data that cannot be altered (for example, the registered owner of the record), and policies must limit who can decrypt with each key.

## Step 10 — Deleting by destroying the key

The final and most drastic pattern. A customer leaves and requests that you delete their data. It resides in the database, in last night's backups, and in backups from a month ago. Going to erase it in each copy is nearly impossible.

If each customer has **their own key**, there is an alternative: **destroy the key**. Everything encrypted with it becomes unreadable, wherever it lives. This is known as cryptographic erasure.

Create a key for a customer and encrypt some of their data:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 200
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/cliente-que-se-va \
    -d "{\"plaintext\": \"$(echo -n datos-de-don-chema | base64)\"}" | jq -r .data.ciphertext | tee borrar.txt
vault:v1:tjerbuHJyEbw+3IiLl0rC/hSEa78E61i9Yg9CancZegxpnBsybXKvkGZ2DwtzQ==
```

Attempt to delete it:

```
$ curl -s -w " HTTP %{http_code}\n" -X DELETE -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
{"errors":["error deleting policy cliente-que-se-va: deletion is not allowed for this key"]}
 HTTP 400
```

By default, Vault refuses. The documentation calls it “a potentially catastrophic operation” and requires enabling `deletion_allowed` first ([Transit API](https://developer.hashicorp.com/vault/api-docs/secret/transit)). It is the safety latch on the firearm. Disengage it and delete:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/cliente-que-se-va/config -d '{"deletion_allowed": true}'
HTTP 200
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X DELETE -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 204
```

Now try to decrypt Don Chema's data:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/cliente-que-se-va \
    -d "{\"ciphertext\": \"$(cat borrar.txt)\"}"
{"errors":["encryption key not found"]}
 HTTP 400
```

What if someone creates another key with the exact same name?

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 200
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/cliente-que-se-va \
    -d "{\"ciphertext\": \"$(cat borrar.txt)\"}"
{"errors":["cipher: message authentication failed"]}
 HTTP 400
```

Same name, completely new key. The old data remains unreadable: in the database, in last night's backup, and in the backup from a year ago.

**An honest warning.** This applies to copies of **your data**. If you maintain backups **of Vault itself** (of its data folder), a backup taken prior to the deletion still contains the key. For cryptographic erasure to be complete, Vault's backups must also expire.

### The alternative using the `vault` CLI

```
$ docker compose exec -e VAULT_TOKEN vault vault write transit/encrypt/curp plaintext=$(echo -n PEPE000101HDFXXX01 | base64)
Key            Value
---            -----
ciphertext     vault:v3:7yIAAelQRE+2zGnTO+J0EJcPExHspE4elzod4VDFrTrTSkl4bAYZ9ygbQ25C1Q==
key_version    3
```

(In this run, version 3 was returned because Exercises 12 and 14 had already been completed. If you run this command right now, before the exercises, yours will normally start with `vault:v2:`. The number changes with every rotation: do not compare it with the example, compare it with `latest_version` on the `curp` key.)

---

👉 **If you are in Management:** encryption as a service follows the same principle as **custody of valuables**: the cash-in-transit company holds the cash, you hold only the receipt, and withdrawing requires authorization. The “encrypts but does not decrypt” policy is the **deposit window**: anyone can deposit, only the authorized signatory withdraws. And deleting by destroying the key matters for personal data protection: when a customer exercises their right to have their data cancelled, legal will ask “what about the backups?”. This technique is a technical answer that can be demonstrated, but it does not replace legal analysis: cancellation can involve a blocking period before deletion, retention periods, and exceptions set by law.

---

## Session 3 Exercises

**Exercise 11 — Your dummy CURP.** Make up a dummy CURP (with `XXX` in the middle, just like in the lesson). Encrypt it twice using the `curp` key, and decrypt it.

**Hint if you get stuck.** From the command in Step 3, only change the string inside `echo -n`. Store the output with `C=$(... | jq -r .data.ciphertext)`, as in Step 4, and to decrypt, reuse that same command, replacing only `ciphertext` with `$C`.

d) Fill in the blanks without looking: “Base64 is __________. It is not encryption because __________. In this lab, protection begins when __________.”

**How to verify:** both `ciphertext` values must differ from each other, both must start with the same `vault:vN:`, and decrypting with `base64 -d` must yield your exact dummy CURP without an extra trailing newline. If you see an extra blank line at the end, you forgot `-n` in `echo`. For item d), compare against the solution.

**Exercise 12 — Rotate and rewrap.** Encrypt your dummy CURP and save it to `mio.txt`. Rotate the `curp` key. Rewrap `mio.txt`.

**How to verify:** the number following `vault:v` in the rewrapped ciphertext must match the key's `latest_version` (check it with `GET transit/keys/curp`). And the rewrapped ciphertext must decrypt back to your CURP.

**Exercise 13 — The drop box.** Using the registration form's token (`secretos-locales/token-formulario.txt`):

a) Encrypt a CURP.
b) Attempt to decrypt it.
c) Attempt to encrypt using another key, `expedientes`.
d) Now write the policy yourself. Fill in the blanks without looking back at Step 7:

```hcl
path "transit/____/curp" {
  capabilities = ["____"]
}
```

Upload it under the name `solo-cifrar-prueba`, create a test token with it (using the commands from Step 7 with updated names), and repeat a), b), and c) with that token.

**How to verify:** a) you receive a `vault:v...`; b) 403; c) 403, because the policy only references `transit/encrypt/curp`. If item a) returns 403, do not count it as correct: the token may have expired. Generate a new one using the command from Step 7, reload `F`, and start over; the test is valid once encrypting with `F` successfully returns `vault:v...`. In d), `encrypt/curp` works; `decrypt/curp` and `encrypt/expedientes` return 403.

**Exercise 14 — Rewrapping an entire table.** Rotate the `curp` key once more. Then iterate over the `clientes` table and rewrap every CURP.

**First, a dry run that touches nothing.** Before running any `UPDATE`, verify that the loop reads the table correctly:

```
psql -At -F " " -c "SELECT id, curp FROM clientes;" | while read ID CIF; do
  echo "ID=$ID | CIF=$CIF"
done
```

`|` pipes each row into the loop, `-F " "` instructs `psql` to separate columns with a space, and `read` assigns the first column to `ID` and the second to `CIF`. You should see one line per customer before proceeding.

Now the actual skeleton; fill in the blanks. The `if` check prevents a `null` from being written to the table instead of the ciphertext if Vault fails:

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

**How to verify:** `psql -c "SELECT id, nombre, left(curp, 9) AS version FROM clientes;"` must show the same new version across all rows, and each CURP must still decrypt properly.

**Exercise 15 — The wrong envelope.** Using the `expedientes` key, encrypt the string `credito-aprobado` with context `empresa-sur`. Decrypt it with `empresa-sur`, then with `empresa-norte`, and then without any context.

e) Without executing another deletion, fill in the blanks: “Recreating `cliente-que-se-va` does not recover previously encrypted data because __________. Before allowing a key to be deleted, I must verify __________.”

**How to verify:** the first yields `credito-aprobado`; the second, `cipher: message authentication failed`; the third, `missing 'context' for key derivation`. Item e) is compared against the solution.

---

## Common mistakes (and how to spot them)

| Mistake | What it looks like | How to spot it | What to do |
|---|---|---|---|
| Sending text without base64 | Typically outputs `{"errors":["illegal base64 data at input byte N"]}` with code 400. However, if the text happens to be valid base64, Vault accepts it and encrypts different bytes than intended | The `plaintext` value looks identical to your original text | Always use `$(echo -n TEXT | base64)` |
| Forgetting `-n` in `echo` | Upon decryption, an extra empty line appears | The base64 ends differently: `...WDAxCg==` instead of `...WDAx` | `echo -n` does not append a trailing newline |
| Believing base64 is encryption | “It's already protected, it looks scrambled” | Anyone can read it with `base64 -d` | Base64 is merely an encoding. The actual encryption is performed by Transit |
| Raising `min_decryption_version` before rewrapping | Older data returns `disallowed by policy (too old)` | There are rows with `vault:v1:` in the table | Rewrap everything first; bump the minimum version last. If this happened to you and you still have `v1` ciphertexts: re-run the configuration command from Step 6 with `{"min_decryption_version": 1}`, confirm that `v1.txt` decrypts again, rewrap everything, and only then raise the minimum to the new version |
| Transit policy using `read` | The token receives a 403 when encrypting | `sys/capabilities-self` does not list `update` | Encrypting and decrypting require `update` |
| Derived key without `context` | `missing 'context' for key derivation` | The key has `derived: true` | Always supply the same `context`, base64-encoded, for both encryption and decryption |
| Deleting a key “just to test” | Everything encrypted with it becomes permanently unreadable | `encryption key not found` | There is no going back. That is why `deletion_allowed` exists: keep it disabled unless you genuinely intend to destroy the key |

---

## Review for the next session

Session 4 starts with these three questions. Answer them without looking:

1. What do the three parts of `vault:v2:SmfKDK1u...` signify?
2. You rotated the key. What happens to the data that was already encrypted, and what operation upgrades it to the new version without anyone seeing the plaintext?
3. Why is a token that can only encrypt useful for a customer registration form?

🔁 **Next week:** Canasta Morada discovers who owns the `185.xx.xx.xx` server. You make PostgreSQL and MariaDB passwords be born, expire, and change on their own, and you write a Python program that connects to the database without knowing any password.

**Before you leave:** `docker compose stop`. Next time, run `start`, unseal Vault, and export the token.

---

## Solutions (do not look before trying)

**Review from Session 2.**

1. Because its data is encrypted on disk with a master key that is not stored whole: it is split into shards (Shamir's secret sharing). By default, there are 5 shards and 3 are required.
2. Either the policy does not include that path or capability (for instance, referencing the path without `data/`), or the token expired or was revoked. `sys/capabilities-self` tells you what the token can do on each path.
3. No, under the default configuration. Vault logs an HMAC-SHA256 hash of most sensitive text values rather than the plaintext; it serves for comparison, not reconstruction. Always verify the audit device configuration before making assumptions: with `log_raw=true`, attributes exempt from hashing, or non-string values, sensitive data may be logged unmasked ([Audit Devices](https://developer.hashicorp.com/vault/docs/audit)).

**Exercise 11.** Using a dummy CURP, `ABCD020202HDFXXX03`:

```
curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
  -d "{\"plaintext\": \"$(echo -n ABCD020202HDFXXX03 | base64)\"}" | jq -r .data.ciphertext
```

Running it twice yields two different strings with the same prefix. To decrypt, use the command from Step 4 with your `ciphertext`.

Item d): “Base64 is a way of writing data (an encoding). It is not encryption because anyone can reverse it. In this lab, protection begins when Transit encrypts the data using the key.”

**Exercise 12.** You rotate with `POST transit/keys/curp/rotate`, and rewrap with `POST transit/rewrap/curp` passing `{"ciphertext": "<content of mio.txt>"}`. If the latest version was previously 2, after rotation it becomes 3 and the rewrapped output begins with `vault:v3:`.

**Exercise 13.** a) Same as Step 7. b) and c) `{"errors":["1 error occurred:\n\t* permission denied\n\n"]}` with `HTTP 403`. d) The blanks are `encrypt` and `update`: the exact same policy from Step 7 under another name.

**Exercise 14.** The blanks are `rewrap` and `$ID`. Each rotation creates a new version: if you already completed Exercise 12, this rotation bumps the key to version 4 and you will see `vault:v4:`; otherwise, to version 3. In this lesson's test run, after rotating to version 3:

```
 id | nombre |  version
----+--------+-----------
  1 | Pepe   | vault:v3:
  2 | María  | vault:v3:
(2 rows)
```

No one saw a single CURP throughout the entire process: not you, not the terminal, not the loop. If the `if` block prints “No actualicé”, that row was left untouched; fix the issue and run the loop again.

**Exercise 15.**

```
CTX_SUR=$(echo -n empresa-sur | base64)
C=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
  -d "{\"plaintext\": \"$(echo -n credito-aprobado | base64)\", \"context\": \"$CTX_SUR\"}" | jq -r .data.ciphertext)
curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
  -d "{\"ciphertext\": \"$C\", \"context\": \"$CTX_SUR\"}" | jq -r .data.plaintext | base64 -d; echo
```

For the other two cases, change the context to `$(echo -n empresa-norte | base64)` or remove the `context` field altogether. The resulting errors match those shown in Step 9.

Item e): “because the new key is distinct cryptographic material, even if it shares the same name”; “that the key belongs only to that customer and that someone with authority approved destroying it, because there is no going back.”

---

## What's next

In Session 4, you will also use the MariaDB client. Verify it with `mariadb --version`. If you do not have it installed: run `sudo apt install mariadb-client` on Debian or Ubuntu (or your Linux distribution's package manager), or `brew install mariadb` on macOS. And for the final script, you will need Python 3.10 or newer: check with `python3 --version`.

---

*I write from what we encounter every day at Hábil, where we build systems for banking, insurance, and businesses in Mexico. If you run into a problem like this at work or in your family business, let's talk: [habil.mx](https://www.habil.mx/en/)*
