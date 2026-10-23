# Vault de zéro (3) : chiffrer sans avoir la clé

*Le moteur Transit de Vault chiffre et déchiffre à ta place, et la clé n'arrive jamais jusqu'à ton programme. Tu stockes des CURP chiffrées dans PostgreSQL, tu fais la rotation de la clé sans rien perdre et tu apprends à supprimer des données en détruisant une clé.*

*Vault de zéro · session 3 sur 4*

## Révision de la session 2

Réponds sans regarder. Les réponses se trouvent dans les solutions.

1. Pourquoi Vault démarre-t-il scellé, et de combien de clés as-tu besoin par défaut pour l'ouvrir ?
2. Un token reçoit un 403. Quelles sont deux causes possibles, et quelle route de Vault te dit ce que ce token peut faire ?
3. Si quelqu'un vole le journal d'audit, emporte-t-il les mots de passe ? Pourquoi ?

> **Le laboratoire de cette session** se trouve dans le dépôt public [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Monte-le d'abord toi-même ; le dépôt sert de point de comparaison quand quelque chose ne donne pas le même résultat. Il ne contient aucun mot de passe : le laboratoire les génère au démarrage.

## Objectifs de cette session

| # | À la fin, tu peux… | L'exercice qui le démontre |
|---|---|---|
| 1 | **Chiffrer et déchiffrer** une donnée avec Transit en utilisant `curl`, et **expliquer** ce qu'est le base64 et pourquoi ce n'est pas du chiffrement | Exercice 11 |
| 2 | **Faire la rotation** d'une clé et **ré-envelopper** (rewrap) d'anciennes données vers la nouvelle version sans les déchiffrer toi-même | Exercices 12 et 14 |
| 3 | **Écrire** une politique qui permet de chiffrer mais pas de déchiffrer, et **vérifier** le 403 | Exercice 13 |
| 4 | **Stocker** des données chiffrées dans PostgreSQL avec `psql` et **démontrer** que celui qui lit la table ne voit pas la donnée | Étape 8 (guidée) et exercice 14 |
| 5 | **Lier** une donnée chiffrée à son propriétaire avec `context`, et **détruire** une clé pour rendre illisible ce qu'elle a chiffré | Exercice 15 et étape 10 |

---

## Scénario (fiction) — Chapitre 7 : lundi, 10 h 12

Iván n'a pas bien dormi pendant le week-end. L'horloge de 3 h 17 ne le laisse pas en paix.

Le lundi, il demande à l'hébergeur du serveur le journal complet des téléchargements du dossier des sauvegardes. Pas celui d'une semaine : celui de toute la vie du serveur. Il reçoit un fichier texte de plusieurs milliers de lignes. Il le filtre sur l'adresse `185.xx.xx.xx`.

Le premier téléchargement depuis cette adresse n'a pas eu lieu samedi dernier.

Il remonte à deux ans et trois mois.

Et depuis, **chaque samedi à 3 h 21**, quelqu'un a téléchargé la sauvegarde de la nuit. Et le dossier contenant `llave.txt`. Cent dix-sept samedis de suite.

Valeria, qui a enfin avoué l'histoire du dépôt public, sent sa poitrine se relâcher. Son erreur date d'il y a dix jours. Ceci dure depuis deux ans.

« Donc ce n'est pas à cause de ce que j'ai envoyé, dit-elle.

— Non, répond Iván. Ce que tu as envoyé était grave aussi, et c'est pour cela que nous avons tout changé. Mais ceci est autre chose. »

Doña Clara pose la question gênante :

« Et combien de fois ont-ils emporté les CURP ?

— Cent dix-sept. »

---

## Chapitre 8 : lundi, 16 h 50

Pendant qu'Iván refait le chiffrement des CURP, Rocío, la comptable, entre dans le bureau avec un relevé de la carte de l'entreprise. Elle fait le rapprochement du mois et il y a un débit qu'elle n'a jamais compris :

```
SERV VIRTUAL CLOUD  TR-REPORTES     USD 9.99
```

« Ça dure comme ça depuis deux ans, dit-elle. J'ai toujours pensé que c'était quelque chose de chez vous. »

Iván cherche dans le panneau de l'hébergeur l'adresse du serveur qui paie ce débit.

`185.xx.xx.xx`.

TR.

*(À suivre à la session 4.)*

---

## Pourquoi c'est important

Le problème numéro 6 de la session 1 était la clé à côté des données. Canasta Morada chiffrait bien les CURP, mais celui qui a emporté la sauvegarde a aussi emporté `llave.txt`, et le chiffrement n'a servi à rien.

La solution n'est pas de mieux cacher le fichier. C'est que **la clé ne se trouve dans aucun fichier que ton programme peut lire**. Ton programme dit à Vault « chiffre-moi ceci » et reçoit la donnée chiffrée. Il lui dit « déchiffre-moi ceci » et, s'il en a la permission, reçoit la donnée d'origine. La clé reste dans Vault, protégée par le scellement que tu as ouvert la semaine dernière avec trois clés.

C'est cela, le moteur **Transit**. La documentation le décrit comme de la « cryptographie en tant que service » ou du « chiffrement en tant que service », et précise que Vault **ne stocke pas** les données que tu lui envoies : tu stockes le résultat où tu veux ([Transit](https://developer.hashicorp.com/vault/docs/secrets/transit)).

Ainsi, si demain quelqu'un emporte la sauvegarde de la base de données, il emporte des textes comme `vault:v2:SmfKDK1u...`. Sans accès à Vault, ils ne lui servent à rien.

## Trois mots avant de commencer

**Chiffrer.** Mélanger une donnée avec une **clé** pour que seul celui qui a la clé puisse la relire. Quand, enfant, tu écrivais des messages codés en remplaçant chaque lettre par la suivante dans l'alphabet, la clé était « une lettre en avant ». Par défaut, Transit utilise AES-256 en mode GCM, ce qui est beaucoup plus solide et détecte en plus si quelqu'un a altéré la donnée chiffrée ([API de Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)).

**Base64.** Une façon d'écrire n'importe quelle donnée, même binaire, en n'utilisant que des lettres, des chiffres, `+`, `/` et `=`. Transit demande les données en base64 parce que, de cette façon, une donnée quelconque (un texte, une petite image) peut voyager à l'intérieur d'un JSON. Attention à la taille : par défaut, l'API de Vault limite chaque requête à 32 Mo, et le base64 rend les données un tiers plus grosses. Pour les gros fichiers, on chiffre avec une autre technique, sans les envoyer entiers à Transit. **Le base64 n'est pas du chiffrement.** C'est comme le javanais : « bavonjavour » a l'air secret, mais quiconque connaît la règle le lit. Essaie :

```
$ echo -n "PEPE000101HDFXXX01" | base64
UEVQRTAwMDEwMUhERlhYWDAx
$ echo "UEVQRTAwMDEwMUhERlhYWDAx" | base64 -d; echo
PEPE000101HDFXXX01
```

Le `-n` de `echo` évite qu'un saut de ligne se glisse à la fin ; sans lui, tu chiffrerais « CURP + Entrée ». Les CURP de cette leçon sont inventées et ne correspondent à aucune personne ; elles portent `XXX` pour que cela se voie. N'utilise pas de données de personnes réelles dans tes exercices.

**Version de clé.** Une clé Transit peut avoir plusieurs versions. Quand tu en fais la **rotation**, une nouvelle version naît et sert à chiffrer ce qui vient ; les anciennes restent pour pouvoir déchiffrer ce qui précède. C'est comme changer chaque année la combinaison du cadenas de la réserve, en gardant les combinaisons précédentes dans une enveloppe au cas où une vieille caisse réapparaîtrait.

---

## Étape 1 — Démarre le laboratoire et active Transit

**Deux éléments de terminal que tu vas utiliser tout le temps.** `NOM=$(commande)` exécute `commande` et enregistre son résultat dans `NOM`. `$NOM` insère ensuite ce résultat. Essaie : `SALUDO=$(echo hola); echo "$SALUDO"` doit afficher `hola`. Dans le bloc suivant, `LLAVE=$(...)` enregistre temporairement une clé de déverrouillage ; si quelque chose échoue, vérifie que `LLAVE` n'est pas restée vide avec `echo "${#LLAVE}"` (le résultat doit être un nombre supérieur à 0).

Si tu as arrêté le laboratoire, redémarre-le, ouvre le scellement et exporte le token, comme à la session 2 :

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

Active le moteur Transit sur le chemin `transit/` :

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/transit -d '{"type": "transit"}'
HTTP 204
```

**Contrôle d'état.** `docker compose stop` conserve Transit, les clés et la table. Si, en montant Transit, tu reçois `HTTP 400` avec `path is already in use`, il était déjà monté : passe à l'étape 2. Si la clé `curp` ou la table `clientes` existent déjà, ne répète pas les insertions de l'étape 8. Regarde d'abord ce qu'il y a avec `psql -c "SELECT id, nombre, left(curp, 9) FROM clientes;"` et continue seulement si tu reconnais ces lignes comme un travail antérieur.

## Étape 2 — Crée une clé

Une clé appelée `curp`. Tu n'envoies rien : Vault la génère à l'intérieur.

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp
HTTP 200
```

Regarde-la :

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

Remarque ce qui n'apparaît **pas** : la clé. Dans `keys`, il n'y a qu'un nombre par version, qui est la date de sa création. `exportable: false` dit qu'on ne peut pas la sortir. Vérifie :

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/export/encryption-key/curp
{"errors":["private key material is not exportable"]}
 HTTP 400
```

Même le token root ne peut pas la sortir. Si, à la création, tu avais demandé `exportable: true`, ce serait possible, et cette décision est irréversible ; c'est pourquoi l'option est désactivée par défaut.

## Étape 3 — Chiffrer

Tu envoies le texte en base64 dans `plaintext`. Le `$(...)` fait la conversion à la volée :

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq .data
{
  "ciphertext": "vault:v1:A2se3zo5aKjY51c/tlquYpJrN/L8DDNh2BPzqvcrXfYwkW8yVVimMMzir5DRpw==",
  "key_version": 1
}
```

Ce `ciphertext` est ce que tu vas stocker. Il comporte trois parties séparées par deux-points :

- `vault` : chiffré par Vault.
- `v1` : avec la **version 1** de la clé.
- Le reste : la donnée chiffrée.

Chiffre **la même CURP une nouvelle fois** :

```
vault:v1:qy8hRw2+KeTOHWr/RJ7D4tPbSlRDiTk96lZGn9+Jijp+lJRyUlfZph3upajdFw==
```

C'est différent. Chaque chiffrement comporte un ingrédient aléatoire (un *nonce*), et c'est pourquoi deux chiffrements de la même donnée ne se ressemblent jamais. Ainsi, personne ne peut regarder la table et dire « ces deux clients ont la même CURP ». (Transit a un mode appelé *convergent* qui fait le contraire, exprès, pour permettre la recherche ; nous ne l'utilisons pas ici.)

## Étape 4 — Déchiffrer

Tu envoies le `ciphertext` et tu reçois du base64 :

```
$ C=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext)
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$C\"}" | jq .data
{
  "plaintext": "UEVQRTAwMDEwMUhERlhYWDAx"
}
```

Et tu le ramènes en texte avec `base64 -d` :

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$C\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

Si quelqu'un te remet des déchets qui ressemblent à du chiffrement, Vault ne devine pas :

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"vault:v1:estonoescifrado\"}"
{"errors":["invalid ciphertext: could not decode base64"]}
 HTTP 400
```

## Étape 5 — Faire la rotation de la clé sans rien perdre

Enregistre dans un fichier un chiffrement fait avec la version 1, pour t'en servir plus tard :

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext | tee v1.txt
vault:v1:0uoMoZKeXU+18t3TiH3yOlTX7vL9wlNUWlMf1W4XapYdoVq2Z1OWVAg7hIgWlA==
```

`tee` affiche le résultat à l'écran et l'enregistre en plus dans le fichier. Maintenant, fais la **rotation** :

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp/rotate
HTTP 200
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp | jq -c ".data | {latest_version, min_decryption_version, versiones: (.keys | keys)}"
{"latest_version":2,"min_decryption_version":1,"versiones":["1","2"]}
```

Le nouveau sort avec `v2` :

```
vault:v2:uzo5CXHaWgjXF3iUCzzefTFzOecaAcho3WjVJqnjVJ0IQIR3mk1DioElROdsxA==
```

Et l'ancien **se déchiffre toujours**, car la version 1 est toujours conservée :

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

La rotation ne casse rien. C'est pourquoi on peut la faire souvent ; il existe même `auto_rotate_period` pour que Vault fasse tourner une clé tout seul à intervalle régulier.

## Étape 6 — Ré-envelopper (rewrap) : faire monter l'ancien vers la nouvelle version

La rotation ne change pas ce qui est déjà stocké : ta base de données reste pleine de `v1`. Pour les faire monter en `v2`, il y a **rewrap** (ré-envelopper) : tu lui donnes l'ancien chiffrement et il te renvoie un nouveau avec la dernière version. La documentation précise que, dans ce processus, **la donnée d'origine n'est pas révélée** ([Transit](https://developer.hashicorp.com/vault/docs/secrets/transit)) : ni toi ni ton programme ne voyez la CURP.

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/rewrap/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}" | jq -c .data | tee rewrap.json
{"ciphertext":"vault:v2:qR2K9Q5TmpKsG4umLEMX2bguVD1/R4nC+iNhKxAT5jrKGAc1clF5977n49Q85w==","key_version":2}
```

C'est comme apporter tes vieux papiers chez le notaire pour qu'il y appose le nouveau sceau, sans que personne ne les lise.

Quand tu as tout ré-enveloppé, tu dis à Vault de **ne pas accepter** les chiffrements plus anciens que la version 2 :

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/curp/config -d '{"min_decryption_version": 2}'
HTTP 200
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}"
{"errors":["ciphertext or signature version is disallowed by policy (too old)"]}
 HTTP 400
```

Le `v1` ne sert plus. Celui qui a été ré-enveloppé, si :

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(jq -r .ciphertext rewrap.json)\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

C'est ce dont Canasta Morada avait besoin : si une vieille copie de la base de données traîne quelque part, avec des chiffrements `v1`, avec cette configuration, cette copie ne peut plus être déchiffrée. Attention : **ce n'est pas un effacement cryptographique**. Vault conserve toujours la version 1 de la clé, et un opérateur autorisé pourrait abaisser de nouveau le minimum pour permettre de la déchiffrer (la documentation le décrit comme un réglage faisant partie d'une politique de rotation). Détruire réellement une clé, c'est l'étape 10.

## Étape 7 — Une politique qui chiffre mais ne déchiffre pas

Le formulaire d'inscription des clients a besoin de **chiffrer** des CURP. Il n'a jamais besoin de les lire. Crée `politicas/solo-cifrar-curp.hcl` :

```hcl
# El formulario de alta puede CIFRAR curps, pero nunca descifrarlas.
path "transit/encrypt/curp" {
  capabilities = ["update"]
}
```

Dans Transit, chiffrer et déchiffrer sont des opérations d'écriture (`POST`), et dans les politiques cela s'appelle `update`. Pour cette clé, qui existe déjà, `update` est la capacité minimale correcte. Attention : la route `transit/encrypt/<clé>` accepte `create` ou `update`, et avec `create`, Vault peut créer une clé qui n'existait pas, avec des valeurs par défaut, à moins que cette création automatique n'ait été désactivée ([Transit : Encrypt data](https://developer.hashicorp.com/vault/api-docs/secret/transit#encrypt-data)). Ne déduis pas la capacité de la politique du seul verbe HTTP.

Envoie-la et crée un token pour le formulaire. Il dure 3 heures, soit la durée de la session avec ses exercices ; s'il expirait avant, un 403 ressemblerait au 403 que tu cherches à l'exercice 13 :

```
$ jq -n --rawfile p politicas/solo-cifrar-curp.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/solo-cifrar-curp -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/create \
    -d '{"policies": ["solo-cifrar-curp"], "ttl": "3h", "display_name": "formulario-alta"}' \
    | jq -r .auth.client_token > secretos-locales/token-formulario.txt
```

Le formulaire chiffre la CURP d'une nouvelle cliente :

```
$ F=$(cat secretos-locales/token-formulario.txt)
$ curl -s -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n MARA990909MDFXXX02 | base64)\"}" | jq -r .data.ciphertext | tee maria.txt
vault:v2:4LM7LCPcgym6rQAPOMQGWR4DIk1qi4NdtoaBM/yecdQfWsG9iCypdv7IST71dQ==
```

Mais s'il essaie de la lire, ou de faire la rotation de la clé :

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat maria.txt)\"}"
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/keys/curp/rotate
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Si quelqu'un vole le token du formulaire, il peut déposer des CURP chiffrées, mais il ne peut pas en lire une seule. C'est une boîte aux lettres : n'importe qui y glisse des lettres, seul le facteur l'ouvre.

## Étape 8 — Le stocker dans PostgreSQL

PostgreSQL tourne déjà depuis la session 2. Son mot de passe se trouve dans `.env`, que le script a généré. Charge-le dans ton terminal sans le recopier à la main : `set -a` fait que tout ce que tu lis est exporté, et `source .env` lit le fichier.

```
set -a; source .env; set +a
export PGHOST=127.0.0.1 PGPORT=$PUERTO_POSTGRES PGUSER=postgres PGDATABASE=tienda PGPASSWORD=$POSTGRES_PASSWORD
```

`psql` lit tout seul ces variables `PG...` ; ainsi, tu n'écris pas le mot de passe dans la commande, où il resterait dans ton historique. C'est acceptable dans un laboratoire local, mais `PGPASSWORD` laisse le mot de passe dans l'environnement du processus, et la documentation de PostgreSQL le déconseille parce que, sur certains systèmes, d'autres processus peuvent le voir. En production, on utilise un fichier de mots de passe avec des permissions strictes ou, mieux, Vault.

Crée la table des clients :

```
$ psql -c "CREATE TABLE clientes (id serial PRIMARY KEY, nombre text NOT NULL, curp text NOT NULL);"
CREATE TABLE
```

Insère Pepe avec sa CURP chiffrée. D'abord tu chiffres, ensuite tu stockes le résultat :

```
$ CIF=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext)
$ psql -c "INSERT INTO clientes (nombre, curp) VALUES ('Pepe', '$CIF');"
INSERT 0 1
```

Et María, chiffrée par le token du formulaire, qui ne peut pas lire :

```
$ F=$(cat secretos-locales/token-formulario.txt)
$ CIF=$(curl -s -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n MARA990909MDFXXX02 | base64)\"}" | jq -r .data.ciphertext)
$ psql -c "INSERT INTO clientes (nombre, curp) VALUES ('María', '$CIF');"
INSERT 0 1
```

Maintenant, regarde la table comme la verrait quelqu'un qui a la permission de lecture (`SELECT`) sur `clientes`, son propriétaire, un superutilisateur ou celui qui détient la sauvegarde. Se connecter à la base de données ne suffit pas : dans PostgreSQL, il faut cette permission ([Privilèges](https://www.postgresql.org/docs/17/ddl-priv.html)). Ici, cela fonctionne parce que nous sommes entrés en tant que `postgres` :

```
$ psql -c "SELECT * FROM clientes;"
 id | nombre |                                   curp
----+--------+---------------------------------------------------------------------------
  1 | Pepe   | vault:v2:GCD4q2/Fp+YtLKT185oGtoSBJ4M9wE5oKrOaDy93Hlmf84Nzh/4ZxWW+E62chg==
  2 | María  | vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
(2 rows)
```

Elles disent `v2` parce que tu as fait la rotation à l'étape 5. Et la sauvegarde, c'est-à-dire ce que Canasta Morada se faisait emporter chaque samedi :

```
$ docker compose exec postgres pg_dump -U postgres -t clientes tienda | grep -A3 "^COPY"
COPY public.clientes (id, nombre, curp) FROM stdin;
1	Pepe	vault:v2:GCD4q2/Fp+YtLKT185oGtoSBJ4M9wE5oKrOaDy93Hlmf84Nzh/4ZxWW+E62chg==
2	María	vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
\.
```

Pas une seule CURP lisible. Et il n'y a plus de `llave.txt` à emporter.

Celui qui a la permission de déchiffrer lit dans la table et demande à Vault :

```
$ CIF=$(psql -At -c "SELECT curp FROM clientes WHERE nombre = 'María';"); echo "$CIF"
vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$CIF\"}" | jq -r .data.plaintext | base64 -d; echo
MARA990909MDFXXX02
```

`-At` demande à `psql` uniquement la valeur, sans en-têtes ni bordures.

## Étape 9 — Lier le chiffrement à son propriétaire : `context`

Imagine que Canasta Morada commence à stocker les dossiers de deux entreprises qui lui achètent en gros, Empresa Norte et Empresa Sur, dans la même table. Une erreur de programmation, ou quelqu'un de malveillant, pourrait prendre un dossier chiffré de Norte, le coller dans la ligne de Sur et demander qu'on le déchiffre « comme celui de Sur ».

Transit a une défense pour cela : les **clés dérivées**. En créant la clé avec `derived: true`, chaque opération doit apporter un `context` : une donnée supplémentaire, en base64, dont Vault dérive une clé différente. Avec un autre `context`, une autre clé ([API de Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)). C'est comme une enveloppe qui ne s'ouvre qu'avec le sceau de l'entreprise à laquelle elle est adressée.

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/expedientes -d '{"derived": true}'
HTTP 200
```

Sans `context`, il refuse :

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
    -d "{\"plaintext\": \"$(echo -n diagnostico-confidencial | base64)\"}"
{"errors":["missing 'context' for key derivation; the key was created using a derived key, which means additional, per-request information must be included in order to perform operations with the key"]}
 HTTP 400
```

Chiffre pour Empresa Norte :

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
    -d "{\"plaintext\": \"$(echo -n diagnostico-confidencial | base64)\", \"context\": \"$(echo -n empresa-norte | base64)\"}" \
    | jq -r .data.ciphertext | tee ctx.txt
vault:v1:8lKFunrcJVIzLnq9q4ZNszSLDOotf4gqtenuKek8QTuCIh4yq1ldoqtjMbsojged+/0aPQ==
```

Avec le bon `context`, on lit :

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
    -d "{\"ciphertext\": \"$(cat ctx.txt)\", \"context\": \"$(echo -n empresa-norte | base64)\"}" | jq -r .data.plaintext | base64 -d; echo
diagnostico-confidencial
```

En se faisant passer pour Empresa Sur :

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
    -d "{\"ciphertext\": \"$(cat ctx.txt)\", \"context\": \"$(echo -n empresa-sur | base64)\"}"
{"errors":["cipher: message authentication failed"]}
 HTTP 400
```

`message authentication failed` : la vérification d'AES-GCM a détecté que cela ne concorde pas. Le dossier de Norte ne s'ouvre que comme celui de Norte. Dans la vie réelle, le `context` est généralement l'identifiant du client ou de l'entreprise propriétaire de la donnée.

Une précision importante : le `context` **n'est ni un mot de passe ni une autorisation**. C'est une valeur que fournit l'appelant ; si quelqu'un a la permission de déchiffrer cette clé et connaît la valeur `empresa-norte`, il peut demander le déchiffrement avec elle. C'est pourquoi l'application doit tirer le `context` d'une donnée fiable qui ne peut pas être altérée (par exemple, le propriétaire enregistré du dossier), et les politiques doivent limiter qui peut déchiffrer chaque clé.

## Étape 10 — Supprimer en détruisant la clé

Dernier schéma, et le plus drastique. Un client s'en va et te demande de supprimer ses données. Elles sont dans la base de données, dans les sauvegardes d'hier soir, dans celles d'il y a un mois. Aller supprimer dans chaque copie est presque impossible.

Si chaque client a **sa propre clé**, il y a une autre issue : **détruire la clé**. Tout ce qui a été chiffré avec elle devient illisible, où que cela se trouve. On appelle cela l'effacement cryptographique.

Crée une clé pour un client et chiffre quelque chose lui appartenant :

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 200
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/cliente-que-se-va \
    -d "{\"plaintext\": \"$(echo -n datos-de-don-chema | base64)\"}" | jq -r .data.ciphertext | tee borrar.txt
vault:v1:tjerbuHJyEbw+3IiLl0rC/hSEa78E61i9Yg9CancZegxpnBsybXKvkGZ2DwtzQ==
```

Essaie de la supprimer :

```
$ curl -s -w " HTTP %{http_code}\n" -X DELETE -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
{"errors":["error deleting policy cliente-que-se-va: deletion is not allowed for this key"]}
 HTTP 400
```

Vault ne te laisse pas faire, par défaut. La documentation l'appelle « une opération potentiellement catastrophique » et exige d'activer d'abord `deletion_allowed` ([API de Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)). C'est le cran de sûreté du pistolet. Retire-le et supprime :

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/cliente-que-se-va/config -d '{"deletion_allowed": true}'
HTTP 200
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X DELETE -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 204
```

Maintenant, essaie de déchiffrer ce qui appartient à don Chema :

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/cliente-que-se-va \
    -d "{\"ciphertext\": \"$(cat borrar.txt)\"}"
{"errors":["encryption key not found"]}
 HTTP 400
```

Et si quelqu'un crée une autre clé avec le même nom ?

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 200
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/cliente-que-se-va \
    -d "{\"ciphertext\": \"$(cat borrar.txt)\"}"
{"errors":["cipher: message authentication failed"]}
 HTTP 400
```

Même nom, nouvelle clé. L'ancien reste illisible : dans la base de données, dans la sauvegarde d'hier soir et dans celle d'il y a un an.

**Une mise en garde honnête.** Cela vaut pour les copies de **tes données**. Si tu conserves des sauvegardes **de Vault lui-même** (de son dossier de données), une sauvegarde faite avant la suppression contient encore la clé. Pour que l'effacement cryptographique soit complet, les sauvegardes de Vault doivent elles aussi expirer.

### L'alternative avec la commande `vault`

```
$ docker compose exec -e VAULT_TOKEN vault vault write transit/encrypt/curp plaintext=$(echo -n PEPE000101HDFXXX01 | base64)
Key            Value
---            -----
ciphertext     vault:v3:7yIAAelQRE+2zGnTO+J0EJcPExHspE4elzod4VDFrTrTSkl4bAYZ9ygbQ25C1Q==
key_version    3
```

(Dans ce test, c'est la version 3 qui est sortie parce que les exercices 12 et 14 avaient déjà été faits. Si tu exécutes cette commande maintenant, avant les exercices, il est normal que la tienne commence par `vault:v2:`. Le numéro change à chaque rotation : ne le compare pas à celui de l'exemple, compare-le à `latest_version` de la clé `curp`.)

---

👉 **Si tu viens de la gestion :** le chiffrement en tant que service obéit au même principe que la **garde de valeurs** : la société de transport de fonds garde les espèces, toi tu n'as que le justificatif, et pour retirer, tu as besoin d'une autorisation. La politique « chiffre mais ne déchiffre pas » est le **guichet de dépôt** : n'importe qui dépose, seul le mandataire retire. Et la suppression par destruction de la clé compte pour la protection des données personnelles : quand un client exerce son droit à l'effacement de ses données, le service juridique va demander « et dans les sauvegardes ? ». Cette technique est une réponse technique démontrable, mais elle ne remplace pas l'analyse juridique : l'effacement peut impliquer une période de blocage avant suppression, des délais de conservation et des exceptions que fixe la loi.

---

## Exercices de la session 3

**Exercice 11 — Ta CURP factice.** Invente une CURP factice (avec `XXX` au milieu, comme celles de la leçon). Chiffre-la deux fois avec la clé `curp` et déchiffre-la.

**Indice si tu es bloqué.** Dans la commande de l'étape 3, tu changes seulement le texte qui se trouve dans `echo -n`. Enregistre le résultat avec `C=$(... | jq -r .data.ciphertext)`, comme à l'étape 4, et pour déchiffrer, réutilise cette même commande en remplaçant seulement le `ciphertext` par `$C`.

d) Complète sans regarder : « Le base64 est __________. Ce n'est pas du chiffrement parce que __________. Dans cet exercice, la protection commence quand __________. »

**Comment vérifier :** les deux `ciphertext` doivent être différents l'un de l'autre, tous deux doivent commencer par le même `vault:vN:`, et en déchiffrant avec `base64 -d`, ta CURP exacte doit apparaître, sans saut de ligne supplémentaire. Si tu vois une ligne vide en trop à la fin, tu as oublié le `-n` dans `echo`. Pour le point d), compare avec la solution.

**Exercice 12 — Rotation et rewrap.** Chiffre ta CURP et enregistre-la dans `mio.txt`. Fais la rotation de la clé `curp`. Ré-enveloppe `mio.txt`.

**Comment vérifier :** le numéro après `vault:v` dans le résultat ré-enveloppé doit être égal à `latest_version` de la clé (consulte-le avec `GET transit/keys/curp`). Et le résultat ré-enveloppé doit se déchiffrer en ta CURP.

**Exercice 13 — La boîte aux lettres.** Avec le token du formulaire (`secretos-locales/token-formulario.txt`) :

a) Chiffre une CURP.
b) Essaie de la déchiffrer.
c) Essaie de chiffrer avec une autre clé, `expedientes`.
d) Maintenant, écris la politique toi-même. Complète les blancs sans regarder l'étape 7 :

```hcl
path "transit/____/curp" {
  capabilities = ["____"]
}
```

Envoie-la sous le nom `solo-cifrar-prueba`, crée avec elle un token de test (les commandes de l'étape 7 en changeant les noms) et répète a), b) et c) avec ce token.

**Comment vérifier :** a) tu reçois un `vault:v...` ; b) 403 ; c) 403, parce que la politique ne mentionne que `transit/encrypt/curp`. Si le point a) renvoie 403, ne le compte pas comme correct : le token a peut-être expiré. Crée-en un autre avec la commande de l'étape 7, recharge `F` et recommence ; le test ne vaut qu'à partir du moment où chiffrer avec `F` renvoie bien `vault:v...`. En d), `encrypt/curp` fonctionne ; `decrypt/curp` et `encrypt/expedientes` donnent 403.

**Exercice 14 — Ré-envelopper toute une table.** Fais de nouveau la rotation de la clé `curp`. Ensuite, parcours la table `clientes` et ré-enveloppe chaque CURP.

**D'abord, un test qui ne touche à rien.** Avant tout `UPDATE`, vérifie que la boucle lit bien la table :

```
psql -At -F " " -c "SELECT id, curp FROM clientes;" | while read ID CIF; do
  echo "ID=$ID | CIF=$CIF"
done
```

`|` passe chaque ligne à la boucle, `-F " "` demande à `psql` de séparer les colonnes par une espace, et `read` place la première colonne dans `ID` et la deuxième dans `CIF`. Tu dois voir une ligne par client avant de continuer.

Maintenant, le vrai squelette ; complète-le. Le `if` évite que, si Vault échoue, on enregistre dans la table un `null` à la place de la CURP chiffrée :

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

**Comment vérifier :** `psql -c "SELECT id, nombre, left(curp, 9) AS version FROM clientes;"` doit afficher la même nouvelle version sur toutes les lignes, et chaque CURP doit toujours se déchiffrer correctement.

**Exercice 15 — La mauvaise enveloppe.** Avec la clé `expedientes`, chiffre le mot `credito-aprobado` avec le context `empresa-sur`. Déchiffre-le avec `empresa-sur`, puis avec `empresa-norte`, puis sans context.

e) Sans exécuter une autre suppression, complète : « Recréer `cliente-que-se-va` ne récupère pas ce qui a été chiffré avant parce que __________. Avant d'autoriser la suppression d'une clé, je dois vérifier __________. »

**Comment vérifier :** la première donne `credito-aprobado` ; la deuxième, `cipher: message authentication failed` ; la troisième, `missing 'context' for key derivation`. Le point e) se compare avec la solution.

---

## Erreurs courantes (et comment les repérer)

| Erreur | À quoi cela ressemble | Comment la repérer | Que faire |
|---|---|---|---|
| Envoyer le texte sans base64 | On obtient en général `{"errors":["illegal base64 data at input byte N"]}` avec le code 400. Mais si le texte est par hasard du base64 valide, Vault l'accepte et chiffre des octets différents de ceux que tu voulais | La valeur de `plaintext` ressemble à ton texte d'origine | Toujours `$(echo -n TEXTE | base64)` |
| Oublier `-n` dans `echo` | Au déchiffrement, une ligne vide en trop apparaît | Le base64 se termine autrement : `...WDAxCg==` au lieu de `...WDAx` | `echo -n` n'ajoute pas le saut de ligne |
| Croire que le base64 est du chiffrement | « C'est déjà protégé, ça a l'air bizarre » | N'importe qui le lit avec `base64 -d` | Le base64 n'est qu'une façon d'écrire. Le chiffrement, c'est Transit qui le fait |
| Augmenter `min_decryption_version` avant de ré-envelopper | Les anciennes données donnent `disallowed by policy (too old)` | Il y a des lignes avec `vault:v1:` dans la table | Ré-enveloppe tout d'abord ; augmente le minimum à la fin. Si c'est arrivé et que tu as encore des chiffrements `v1` : répète la commande de configuration de l'étape 6 avec `{"min_decryption_version": 1}`, confirme que `v1.txt` se déchiffre de nouveau, ré-enveloppe tout et n'augmente le minimum à la nouvelle version qu'à la fin |
| Politique Transit avec `read` | Le token reçoit un 403 en chiffrant | `sys/capabilities-self` ne dit pas `update` | Chiffrer et déchiffrer sont des `update` |
| Clé dérivée sans `context` | `missing 'context' for key derivation` | La clé indique `derived: true` | Envoie toujours le même `context`, en base64, pour chiffrer et déchiffrer |
| Supprimer une clé « pour tester » | Tout ce qui a été chiffré avec elle devient illisible pour toujours | `encryption key not found` | Il n'y a pas de retour. C'est pourquoi `deletion_allowed` existe : laisse-le désactivé sauf quand tu veux vraiment détruire |

---

## Révision pour la prochaine session

La session 4 commence par ces trois questions. Réponds-y sans regarder :

1. Que signifient les trois parties de `vault:v2:SmfKDK1u...` ?
2. Tu as fait la rotation de la clé. Qu'arrive-t-il aux données déjà chiffrées, et quelle opération les fait monter vers la nouvelle version sans que personne ne voie la donnée ?
3. Pourquoi un token qui ne peut que chiffrer est-il utile pour un formulaire d'inscription ?

🔁 **La semaine prochaine :** Canasta Morada découvre à qui appartient le serveur `185.xx.xx.xx`. Toi, tu fais en sorte que les mots de passe de PostgreSQL et de MariaDB naissent, expirent et changent tout seuls, et tu écris un programme Python qui se connecte à la base de données sans connaître aucun mot de passe.

**Avant de partir :** `docker compose stop`. La prochaine fois, `start`, ouvre le scellement et exporte le token.

---

## Solutions (ne les regarde pas avant d'avoir essayé)

**Révision de la session 2.**

1. Parce que ses données sont chiffrées sur le disque avec une clé maîtresse qu'il ne conserve pas entière : elle est découpée en morceaux (Shamir). Par défaut, il y a 5 morceaux et il en faut 3.
2. Que la politique n'inclut pas cette route ou cette capacité (par exemple, la route sans `data/`), ou que le token a expiré ou a été révoqué. `sys/capabilities-self` te dit ce que le token peut faire sur chaque route.
3. Non, avec la configuration par défaut. Vault enregistre une empreinte (HMAC-SHA256) de la plupart des valeurs de texte sensibles, et non la valeur ; elle sert à comparer, pas à reconstituer. Vérifie toujours la configuration du périphérique d'audit avant de le supposer : avec `log_raw=true`, avec des attributs exemptés d'empreinte ou avec des valeurs qui ne sont pas du texte, la donnée peut rester non masquée ([Audit](https://developer.hashicorp.com/vault/docs/audit)).

**Exercice 11.** Avec une CURP d'exemple, `ABCD020202HDFXXX03` :

```
curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
  -d "{\"plaintext\": \"$(echo -n ABCD020202HDFXXX03 | base64)\"}" | jq -r .data.ciphertext
```

Deux fois donnent deux textes différents avec le même préfixe. Pour déchiffrer, la commande de l'étape 4 avec ton `ciphertext`.

Point d) : « Le base64 est une façon d'écrire des données (un encodage). Ce n'est pas du chiffrement parce que n'importe qui peut l'inverser. Dans cet exercice, la protection commence quand Transit chiffre la donnée avec la clé. »

**Exercice 12.** Tu fais la rotation avec `POST transit/keys/curp/rotate`, tu ré-enveloppes avec `POST transit/rewrap/curp` en envoyant `{"ciphertext": "<le contenu de mio.txt>"}`. Si la dernière version était 2 auparavant, après la rotation c'est la 3 et le résultat ré-enveloppé commence par `vault:v3:`.

**Exercice 13.** a) Comme à l'étape 7. b) et c) `{"errors":["1 error occurred:\n\t* permission denied\n\n"]}` avec `HTTP 403`. d) Les blancs sont `encrypt` et `update` : la même politique que celle de l'étape 7 sous un autre nom.

**Exercice 14.** Les blancs sont `rewrap` et `$ID`. Chaque rotation crée une nouvelle version : si tu as fait l'exercice 12 avant, cette rotation amène la clé à la version 4 et tu verras `vault:v4:` ; sinon, à la 3. Dans le test de cette leçon, après la rotation vers la version 3 :

```
 id | nombre |  version
----+--------+-----------
  1 | Pepe   | vault:v3:
  2 | María  | vault:v3:
(2 rows)
```

Personne n'a vu une seule CURP pendant le processus : ni toi, ni le terminal, ni la boucle. Si le `if` affiche « No actualicé », cette ligne est restée comme elle était ; corrige le problème et relance la boucle.

**Exercice 15.**

```
CTX_SUR=$(echo -n empresa-sur | base64)
C=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
  -d "{\"plaintext\": \"$(echo -n credito-aprobado | base64)\", \"context\": \"$CTX_SUR\"}" | jq -r .data.ciphertext)
curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
  -d "{\"ciphertext\": \"$C\", \"context\": \"$CTX_SUR\"}" | jq -r .data.plaintext | base64 -d; echo
```

Pour les deux autres, remplace le context par `$(echo -n empresa-norte | base64)` ou retire le champ `context`. Les erreurs sont celles de l'étape 9.

Point e) : « parce que la nouvelle clé est un matériel cryptographique différent, même si elle porte le même nom » ; « que la clé appartient uniquement à ce client et que quelqu'un ayant autorité a autorisé sa destruction, car il n'y a pas de retour ».

---

## La suite

À la session 4, tu utilises aussi le client MariaDB. Vérifie-le avec `mariadb --version`. Si tu ne l'as pas : `sudo apt install mariadb-client` sous Debian ou Ubuntu (sur d'autres distributions Linux, le gestionnaire de paquets qu'utilise la tienne), ou `brew install mariadb` sous macOS. Et pour le script final, Python 3.10 ou plus récent : `python3 --version`.

---

*J'écris à partir de ce que nous voyons tous les jours chez Hábil, où nous construisons des systèmes pour la banque, l'assurance et les entreprises au Mexique. Si, dans ton travail ou dans l'entreprise de ta famille, vous rencontrez un problème de ce genre, parlons-en : [habil.mx](https://www.habil.mx/fr/)*
