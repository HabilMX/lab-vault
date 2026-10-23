# Vault de zéro (4) : des mots de passe qui changent tout seuls

*Des utilisateurs de base de données qui naissent quand tu les demandes et meurent au bout de deux minutes, des mots de passe qui tournent chaque minute sans que personne ne modifie un fichier, et un programme Python qui se connecte à PostgreSQL sans connaître aucun mot de passe. Et la fin du mystère de 3 h 17.*

*Vault de zéro · session 4 sur 4*

## Révision de la session 3

Réponds sans regarder. Les réponses se trouvent dans les solutions.

1. Que signifient les trois parties de `vault:v2:SmfKDK1u...` ?
2. Tu as fait la rotation de la clé. Qu'arrive-t-il aux données déjà chiffrées, et quelle opération les fait monter vers la nouvelle version sans que personne ne voie la donnée ?
3. Pourquoi un token qui ne peut que chiffrer est-il utile pour un formulaire d'inscription ?

> **Le laboratoire de cette session** se trouve dans le dépôt public [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Monte-le d'abord toi-même ; le dépôt sert de point de comparaison quand quelque chose ne donne pas le même résultat. Il ne contient aucun mot de passe : le laboratoire les génère au démarrage.

## Objectifs de cette session

| # | À la fin, tu peux… | L'exercice qui le démontre |
|---|---|---|
| 1 | **Configurer** le moteur Database de Vault avec un utilisateur dédié, sans utiliser le superutilisateur | Étapes 2 et 3 |
| 2 | **Demander** des identifiants dynamiques, **te connecter** avec `psql` et **vérifier** qu'ils cessent de fonctionner à l'expiration ou à la révocation | Exercices 16, 17 et 19 |
| 3 | **Placer** un utilisateur existant sous rotation automatique et **démontrer** que l'ancien mot de passe ne passe plus | Exercice 18 |
| 4 | **Créer** un identifiant dynamique en lecture seule dans MariaDB avec le client `mariadb`, vérifier qu'il ne peut pas modifier les données et le révoquer | Étape 10 |
| 5 | **Exécuter et modifier** un script Python qui demande ses identifiants à Vault, interroge PostgreSQL et ne stocke aucun mot de passe de base de données | Étape 12 et exercice 20 |

---

## Scénario (fiction) — Chapitre 9 : mardi, 9 h 00

Iván compose un numéro qu'il n'a pas composé depuis huit mois.

« Toño ? C'est Iván, de Canasta Morada. Dis, une question bizarre. Ça te dit quelque chose, un serveur qui s'appelle TR-REPORTES ? »

Silence. Puis un éclat de rire.

« Sans blague ! Il est toujours allumé ? »

Toño raconte sans gêne. Il y a deux ans et demi, la comptabilité avait demandé un rapport hebdomadaire des clients qui paient avec des bons d'achat, avec leur CURP, pour rapprocher les chiffres avec l'entreprise émettrice des bons. La base de données était très chargée en journée, alors Toño avait loué un serveur bon marché dans le cloud, avec la carte de l'entreprise, et y avait mis un programme :

- Chaque samedi à 3 h 17, il se connectait à la base de données avec le mot de passe de `app_tienda`.
- Il téléchargeait la sauvegarde de la nuit et `llave.txt`, pour déchiffrer les CURP.
- Il montait un Excel et l'envoyait à l'adresse `reportes@`.

« Et quand je suis parti, j'ai oublié de vous le dire. Désolé. »

Rocío vérifie : la boîte `reportes@` contient cent dix-sept courriels non ouverts. Personne ne la consultait depuis le départ de l'ancien chef de la comptabilité.

Il n'y avait aucun voleur.

Il y avait pire : une porte ouverte dont personne ne connaissait l'existence. Cent dix-sept copies de huit mille CURP, avec la clé à côté, sur un serveur que personne ne contrôlait, dans un autre pays, payé chaque mois avec la carte de l'entreprise.

Et sans journal par identité ni identifiants qui expirent, il était impossible de le distinguer d'une attaque.

---

## Chapitre 10 : samedi, 3 h 17. Un mois plus tard

Le serveur TR-REPORTES n'existe plus ; Iván l'a supprimé avec Toño en visioconférence, en regardant ensemble chaque dossier.

Le rapport des bons d'achat est désormais produit par un nouveau programme, à l'intérieur des serveurs de Canasta Morada. À 3 h 17, il demande à Vault un identifiant pour la base de données. Vault crée un utilisateur qui n'existait pas une seconde plus tôt, avec une permission de lecture seule et une date d'expiration. Le programme travaille quatre minutes. À 3 h 21, l'utilisateur n'existe plus.

Le mot de passe de la base de données que Vault utilise pour créer ces utilisateurs, personne ne le connaît : ni Iván, ni doña Clara. Vault l'a changé le premier jour.

Le téléphone d'Iván ne vibre pas.

Valeria rédige le rapport d'incident. Dans la dernière ligne, elle écrit : *« Nous ne saurons jamais si quelqu'un a vu le dépôt public pendant ces heures. C'est pourquoi nous avons changé le mot de passe. La prochaine fois que quelqu'un enverra un `.env` par erreur, le mot de passe de l'application ne s'y trouvera pas, ni celui de Vault. Malgré tout, ce que ce fichier contient — comme les mots de passe d'administration — doit être changé immédiatement. »*

*(Fin du scénario.)*

---

## Pourquoi c'est important

Aux sessions 2 et 3, les secrets ne vivaient plus dans des fichiers, mais ils restaient **les mêmes pendant des mois**. Si quelqu'un lisait le mot de passe de `app_tienda` dans Vault, il lui servait jusqu'à ce que quelqu'un le change manuellement.

Aujourd'hui, tu fais le dernier pas : **des mots de passe qui n'existent pas tant que tu ne les demandes pas et qui meurent tout seuls**. C'est la différence entre la clé de ta maison et le badge visiteur d'un immeuble de bureaux. La clé sert pendant des années. Le badge, on te le remet à l'accueil à ton nom, il n'ouvre que l'étage où tu vas et à 18 heures il cesse de fonctionner. Si tu le perds dans l'ascenseur, ça n'intéresse personne.

## Les idées du jour

**Identifiant dynamique.** Un utilisateur de base de données que Vault crée au moment où tu le demandes, avec un mot de passe aléatoire, et qu'il supprime à l'expiration. Chaque programme, et chaque fois qu'il en fait la demande, en reçoit un différent. S'il fuite, il sert quelques minutes.

**Bail (*lease*) et TTL.** Chaque identifiant dynamique vient avec un bail : un contrat avec une date d'expiration. Le **TTL** (*time to live*, durée de vie) est sa durée. Comme le parking du centre commercial : ton ticket indique l'heure d'entrée et expire ; si tu veux plus de temps, tu paies à nouveau (tu renouvelles), jusqu'à un maximum.

**Révoquer.** Annuler un bail avant l'échéance. Vault supprime l'utilisateur de la base de données à ce moment-là.

**Rôle statique avec rotation.** Il y a des utilisateurs que tu ne peux pas remplacer par un nouveau à chaque fois, parce que d'autres systèmes les connaissent par leur nom. Pour ceux-là, Vault conserve l'utilisateur et lui **change le mot de passe** à intervalle régulier, avec `rotation_period`. Celui qui en a besoin le demande à Vault et reçoit toujours le mot de passe en vigueur ([Database secrets engine](https://developer.hashicorp.com/vault/docs/secrets/databases)).

**L'identifiant de Vault dans la base de données.** Pour créer et supprimer des utilisateurs, Vault a besoin de son propre utilisateur dans la base de données. La documentation prévient que, si tu demandes à Vault de faire la rotation de ce mot de passe avec `rotate-root`, **personne** ne le connaîtra ensuite, et recommande de créer un utilisateur dédié pour Vault plutôt que d'utiliser le superutilisateur ([API du moteur Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). C'est ce que nous faisons : un utilisateur `vault_admin` avec les permissions strictement nécessaires, et non le `postgres` qui peut tout.

---

## Étape 1 — Prépare le terminal

Laboratoire démarré, scellement ouvert, token exporté et variables de PostgreSQL chargées depuis `.env` :

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

Remarque que, cette fois, nous n'exportons **ni** `PGUSER` **ni** `PGPASSWORD` : aujourd'hui, tu vas te connecter à PostgreSQL avec plusieurs utilisateurs différents, et chaque commande dira lequel.

Les sorties de cette leçon sont réelles, mais elles proviennent d'exécutions indépendantes ; c'est pourquoi leurs heures, leurs noms d'utilisateur et leurs numéros de version (comme `vault:v3:`, qui dépend du nombre de rotations de la clé que tu as faites à la session 3) ne forment pas une seule séquence. Les tiennes seront différentes.

## Étape 2 — Un utilisateur pour Vault, et un ancien à faire tourner

Crée dans PostgreSQL deux utilisateurs, avec un mot de passe initial généré au hasard et enregistré dans `secretos-locales/` (git l'ignore) :

- `vault_admin` : celui que Vault utilisera. Il peut créer des utilisateurs (`CREATEROLE`) et accorder la permission de lecture sur les tables (`WITH GRANT OPTION`). Ce n'est pas un superutilisateur.
- `reportes` : un utilisateur « de toujours », comme celui qu'utilisent les rapports. Tu vas le placer sous rotation automatique.

Chacun reçoit son **propre** mot de passe initial : s'ils partageaient le même, celui qui obtiendrait celui de `reportes` entrerait en tant que `vault_admin`, qui peut créer des utilisateurs.

**Point de contrôle avant de répéter.** Cette étape suppose un laboratoire neuf. Si tu la répètes, tu écrirais de nouveaux mots de passe dans les fichiers de `secretos-locales/` qui ne coïncideraient plus avec ceux de PostgreSQL. Si tu vois `role already exists` ou que le moteur `database/` existe déjà, ne régénère pas les fichiers initiaux : vérifie l'état et ne fais que les étapes qui manquent.

| Si tu vois | Cela signifie | Que faire |
|---|---|---|
| `CREATE ROLE` ou `HTTP 204` | Tu as bien avancé | Continue |
| `role "vault_admin" already exists` | L'étape 2 a déjà été exécutée, en totalité ou en partie | Ne régénère pas les fichiers initiaux |
| `path is already in use` | Le moteur Database est déjà monté | Passe à la lecture ou à la configuration de la connexion (étape 3) |

`psql -v nombre=...` définit une variable qui s'utilise à l'intérieur sous la forme `:'nombre'`. Ainsi, le mot de passe ne reste pas en clair dans la commande ni dans ton historique. `psql` la substitue avant d'envoyer le SQL à PostgreSQL, donc le mot de passe voyage bien à l'intérieur de l'instruction ; c'est pourquoi, hors du laboratoire, on utilise TLS et on évite de journaliser les instructions qui contiennent des mots de passe :

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

La dernière ligne donne à `vault_admin` la permission d'administrer `reportes`, ce dont il a besoin pour lui changer le mot de passe. Depuis PostgreSQL 16, un utilisateur avec `CREATEROLE` ne peut modifier que les utilisateurs qu'il a créés ou qui lui ont été attribués ainsi.

## Étape 3 — Connecter Vault à PostgreSQL

Active le moteur Database :

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/database -d '{"type": "database"}'
HTTP 204
```

Maintenant, la connexion. Le mot de passe de `vault_admin` est lu par `jq` dans le fichier avec `--arg` : tu ne le tapes pas, il n'apparaît pas dans ton historique. Dans `connection_url`, `{{username}}` et `{{password}}` sont remplis par Vault, et le serveur s'appelle `postgres` parce que Vault le cherche par son nom à l'intérieur du réseau de Docker Compose, et non par `127.0.0.1`. `allowed_roles` dit quels rôles peuvent utiliser cette connexion :

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

Vault a testé la connexion avant de l'enregistrer (`verify_connection` est activé par défaut) ; si le mot de passe était erroné, il te le dirait ici. Lis la configuration :

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

Le mot de passe n'apparaît pas. Une fois que Vault l'a, il ne le renvoie pas, même au token root.

## Étape 4 — Un rôle pour les identifiants dynamiques

Un **rôle** est la recette pour créer un utilisateur. Enregistre-la dans `roles/lector-postgres.json`. Ce fichier, `politicas/app-python.hcl` et `python/clientes.py` se trouvent déjà dans le dossier du laboratoire ; si tu préfères les écrire toi-même, crée les dossiers avec `mkdir -p roles politicas python`, ouvre le fichier dans ton éditeur, colle le bloc complet sans le modifier et enregistre-le avant d'exécuter la commande suivante :

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

- `creation_statements` : le SQL que Vault exécute pour créer l'utilisateur. `VALID UNTIL '{{expiration}}'` fait que PostgreSQL lui-même rejette le mot de passe à l'expiration, même si Vault tarde à supprimer l'utilisateur. C'est l'exemple de la documentation ([PostgreSQL](https://developer.hashicorp.com/vault/docs/secrets/databases/postgresql)).
- `revocation_statements` : le SQL pour le supprimer. Pourquoi nous l'écrivons à la main, tu le verras à l'étape 6, avec une vraie erreur.
- `default_ttl` de 2 minutes pour que tu voies l'expiration sans attendre ; dans la vie réelle, ce sont généralement des minutes ou des heures. `max_ttl` : même si tu renouvelles, jamais plus de 10.

Envoie-le. `-d @archivo` dit à `curl` d'envoyer le contenu du fichier :

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/roles/lector -d @roles/lector-postgres.json
HTTP 204
```

## Étape 5 — Demande un identifiant et connecte-toi

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

Un utilisateur qui n'existait pas il y a une seconde. Le nom porte qui l'a demandé (`root`), le rôle (`lector`), un morceau aléatoire et l'heure au format Unix. Dans ce laboratoire, `root` n'est pas une personne : c'est simplement le token d'administration. En production, on ne le remet ni à des personnes ni à des applications ; chaque personne ou programme entre avec sa propre identité (par exemple OIDC, AppRole ou Kubernetes), pour que le nom de l'utilisateur temporaire dise bien qui l'a demandé. Connecte-toi avec lui :

```
$ export PGUSER=$(jq -r .data.username secretos-locales/creds-lector.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-lector.json)
$ psql -c "SELECT current_user, nombre, left(curp, 9) FROM clientes;"
                 current_user                  | nombre |   left
-----------------------------------------------+--------+-----------
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | Pepe   | vault:v3:
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | María  | vault:v3:
(2 rows)
```

Ça fonctionne, et remarque : même avec un utilisateur à soi, les CURP restent chiffrées. Ce lecteur peut voir la table, mais pas les CURP ; pour cela, il lui faudrait en plus une permission Transit. Essaie de supprimer :

```
$ psql -c "DELETE FROM clientes;"
ERROR:  permission denied for table clientes
```

Lecture seule, comme le dit le rôle. Et depuis le superutilisateur, tu peux voir le nouvel utilisateur avec sa date d'expiration :

```
$ PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -c "SELECT rolname, rolvaliduntil FROM pg_roles WHERE rolname LIKE 'v-%';"
                    rolname                    |     rolvaliduntil
-----------------------------------------------+------------------------
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | 2026-10-18 14:52:54+00
(1 row)
```

## Étape 6 — Révoquer… et une vraie erreur

**Note de lecture.** Le premier bloc reproduit une erreur d'un test antérieur. N'exécute pas les commandes qui utilisent `secretos-locales/creds-lector-2.json` : ce fichier n'est pas créé dans le parcours actuel. Dans ton laboratoire, le rôle de l'étape 4 contient déjà les `revocation_statements` ; la révocation correcte, tu la pratiques à l'exercice 17, avec `creds-16.json`.

La première fois que nous avons testé cette leçon, le rôle **n'avait pas** de `revocation_statements`. Nous avons demandé un deuxième identifiant et nous l'avons révoqué avant l'échéance avec `sys/leases/revoke` :

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-lector-2.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
{"errors":["failed to revoke entry: resp: (*logical.Response)(nil) err: could not perform all revocation statements: ERROR: permission denied for sequence clientes_id_seq (SQLSTATE 42501)"]}
```

Code 400. Sans `revocation_statements`, Vault utilise le SQL de suppression par défaut du plugin PostgreSQL, qui tente de retirer à l'utilisateur les permissions sur **tout** ce qui se trouve dans le schéma `public`, y compris les séquences (les compteurs qui génèrent les `id`). Notre `vault_admin`, avec ses permissions strictes, n'a pas autorité sur la séquence `clientes_id_seq`, et PostgreSQL a dit non. L'utilisateur temporaire est resté à moitié supprimé : sans permissions sur la table, mais pas effacé.

C'est une bonne erreur : elle apparaît **parce que** nous n'avons pas donné le superutilisateur à Vault. La bonne solution n'est pas de lui donner plus de pouvoir, mais de lui dire exactement quoi faire. C'est pourquoi le rôle de l'étape 4 contient ses `revocation_statements` : retirer ce qui a été accordé et supprimer l'utilisateur. Avec le rôle corrigé et renvoyé, la même révocation fonctionne :

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-lector-2.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
HTTP 204
$ PGUSER=$(jq -r .data.username secretos-locales/creds-lector-2.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-lector-2.json) psql -At -c "SELECT count(*) FROM clientes;"
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-QyRyJ1vdjmrPY6U0KXl2-1792335063"
```

L'utilisateur n'existe plus. Si tu as copié le rôle de l'étape 4 en entier, ta première révocation se passe déjà bien.

Le `"sync": true` est important : par défaut, Vault ne fait que **mettre en file d'attente** la révocation et répond `204` aussitôt, sans attendre que la base de données supprime l'utilisateur. Avec `sync`, il attend la fin, et ainsi ton test de connexion juste après ne dépend pas du hasard ([sys/leases](https://developer.hashicorp.com/vault/api-docs/system/leases)).

## Étape 7 — Attendre l'expiration

Maintenant, le premier identifiant, celui de l'étape 5. Ne fais rien : attends que ses 2 minutes s'écoulent. Vault le révoque tout seul et le consigne dans son journal (`docker compose logs vault`) :

```
2026-10-18T14:52:49.642Z [INFO]  expiration: revoked lease: lease_id=database/creds/lector/rOpuliUuxFqc2UbdHMofQV8S
```

Essaie de te connecter :

```
$ date -u +%T; psql -At -c "SELECT count(*) FROM clientes;"
14:53:32
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049"
```

Personne ne l'a révoqué manuellement. Personne n'a modifié un fichier. Il est mort tout seul. C'est ce qui aurait sauvé Canasta Morada : le mot de passe du script de Toño aurait cessé de fonctionner au bout de deux minutes, dès le premier samedi.

## Étape 8 — Rotation automatique d'un utilisateur existant

`reportes` existe depuis avant et d'autres systèmes le connaissent par son nom. Vérifie qu'aujourd'hui il se connecte avec le mot de passe initial :

```
$ PGUSER=reportes PGPASSWORD=$(cat secretos-locales/reportes_inicial.txt) psql -At -c "SELECT current_user;"
reportes
```

Place-le sous un **rôle statique** qui fait la rotation chaque minute (le minimum accepté par l'API est de 5 secondes ; une minute, c'est pour que tu le voies sans t'endormir) :

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-roles/reportes \
    -d '{"db_name": "postgres", "username": "reportes", "rotation_period": "1m"}'
HTTP 204
```

La documentation explique que Vault **fait la rotation du mot de passe à la création du rôle statique**, parce qu'il a besoin de le connaître ([API du moteur Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). Donc l'initial est déjà mort :

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

Celui qui a besoin de se connecter en tant que `reportes` demande à Vault le mot de passe en vigueur au moment voulu :

```
$ PGUSER=reportes PGPASSWORD=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password) \
    psql -At -c "SELECT current_user, count(*) FROM clientes GROUP BY 1;"
reportes|2
```

Attends deux minutes environ et redemande. `last_vault_rotation` a avancé tout seul, et le journal de Vault le confirme :

```
2026-10-18T14:52:59.517Z [INFO]  secrets.database.database_4731c3d7: successfully rotated static role: name=reportes ttl=60
```

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -c ".data | {password: (.password[0:6] + \"...\"), last_vault_rotation, ttl}"
{"password":"OH0KOU...","last_vault_rotation":"2026-10-18T14:53:59.530969477Z","ttl":11}
```

Et si tu ne veux pas attendre, tu fais la rotation toi-même avec `rotate-role`. Un autre nouveau mot de passe ; celui d'il y a un instant ne passe plus (tu le vérifies à l'exercice 18).

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-role/reportes
HTTP 204
```

Si, au lieu de « chaque minute », il te faut « chaque dimanche à 4 h du matin », il existe `rotation_schedule`, au format de type cron à cinq champs ; on ne peut pas l'utiliser avec `rotation_period`. Vault l'interprète en **UTC**, et non à l'heure de ta ville : pour 4 h 00 du matin le dimanche à Mexico (UTC-6), on écrit `0 10 * * SUN` ; adapte le calcul à ton fuseau ([API du moteur Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). Nous ne l'avons pas testé dans cette leçon.

## Étape 9 — Que personne ne connaisse le mot de passe de Vault : `rotate-root`

Le mot de passe initial de `vault_admin` se trouve dans `secretos-locales/vault_admin_inicial.txt`. Aujourd'hui, il fonctionne :

```
$ PGUSER=vault_admin PGPASSWORD=$(cat secretos-locales/vault_admin_inicial.txt) psql -At -c "SELECT current_user;"
vault_admin
```

Demande à Vault de le remplacer par un mot de passe que lui seul connaît :

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-root/postgres
HTTP 204
$ PGUSER=vault_admin PGPASSWORD=$(cat secretos-locales/vault_admin_inicial.txt) psql -At -c "SELECT current_user;"
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "vault_admin"
```

Le fichier est désormais inutile. Et Vault continue de travailler, car lui connaît le nouveau :

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector | jq -c "{username: .data.username, lease_duration}"
{"username":"v-root-lector-R3rwerQPR0yvfCxuAxYI-1792335221","lease_duration":120}
```

Maintenant, aucune personne ne connaît le mot de passe avec lequel les utilisateurs de la base de données sont créés. Si quelqu'un envoie par erreur un fichier de configuration, celui de `vault_admin` n'y est plus. Attention à ce qui reste : `.env` conserve toujours les mots de passe d'administration de PostgreSQL et de MariaDB du laboratoire, et `rotate-root` ne les change pas. Dans la vie réelle, ceux-là non plus ne devraient pas vivre dans un fichier.

## Étape 10 — La même chose avec MariaDB

MariaDB tourne aussi depuis la session 2. Son mot de passe `root` est dans `.env`. Le client `mariadb` lit le mot de passe dans la variable `MYSQL_PWD`, donc tu ne l'écris pas non plus dans la commande. Crée une table de produits et l'utilisateur `vault_admin` de MariaDB :

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

Cet avertissement vient du nouveau client MariaDB lorsqu'il se connecte sans valider l'identité du serveur (TLS) ; dans le laboratoire, cela n'a pas d'importance. S'il te gêne, ajoute `--skip-ssl-verify-server-cert`.

Pour MariaDB, on utilise le plugin `mysql-database-plugin` ; la documentation de Vault couvre MySQL et MariaDB sur la même page ([MySQL/MariaDB](https://developer.hashicorp.com/vault/docs/secrets/databases/mysql-maria)). Remarque que l'adresse a une autre forme :

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

Le rôle, dans `roles/lector-mariadb.json` :

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

Ici, il n'a pas été nécessaire d'écrire `revocation_statements` : la suppression par défaut du plugin MySQL a fonctionné avec ces permissions. Connecte-toi, lis et essaie de changer des prix :

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

Révoque et teste à nouveau :

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-maria.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
HTTP 204
$ MYSQL_PWD=$(jq -r .data.password secretos-locales/creds-maria.json) mariadb -h 127.0.0.1 -P $PUERTO_MARIADB \
    -u $(jq -r .data.username secretos-locales/creds-maria.json) tienda -e "SELECT 1;"
ERROR 1045 (28000): Access denied for user 'v-root-lector-mar-24LwvJevZDrYbE'@'172.21.0.1' (using password: YES)
```

(L'adresse `172.21.0.1` est celle de ta machine vue depuis le réseau de Docker ; la tienne peut être différente.) Et la racine :

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-root/mariadb
HTTP 204
$ MYSQL_PWD=$(cat secretos-locales/vault_admin_maria_inicial.txt) mariadb --skip-ssl-verify-server-cert -h 127.0.0.1 -P $PUERTO_MARIADB -u vault_admin -e "SELECT CURRENT_USER();"
ERROR 1045 (28000): Access denied for user 'vault_admin'@'172.21.0.1' (using password: YES)
```

## Étape 11 — Le bouton d'urgence

Tu te souviens de l'exigence R6 de la session 1, révoquer d'un coup ? Si tu soupçonnes que tous les identifiants d'un rôle ont fuité, tu les annules ensemble par préfixe. Avec la commande `vault` :

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

Attention à ce que cette sortie a démontré : « queued » veut dire que Vault a accepté l'ordre et l'a mis en file d'attente, et la liste vide dit seulement qu'il n'y a plus de baux. Ce qui compte vraiment, c'est l'effet dans PostgreSQL. Compte les utilisateurs temporaires avant de révoquer et quelques secondes après :

```
PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -At -c "SELECT count(*) FROM pg_roles WHERE rolname LIKE 'v-root-lector-%';"
```

Avant de révoquer, le résultat doit être supérieur à `0` (un par identifiant encore vivant) ; après, `0`. S'il n'est pas encore `0`, attends un peu et répète : la file d'attente travaille en arrière-plan. Ce décompte est ce qui confirme que les utilisateurs n'existent plus.

Quatre baux annulés avec une seule commande. Révoquer par préfixe demande une permission spéciale (`sudo`) sur la route ([sys/leases](https://developer.hashicorp.com/vault/api-docs/system/leases)) ; c'est pourquoi nous l'avons fait ici avec le token root.

## Étape 12 — Le seul programme : Python sans mots de passe

Jusqu'ici, tout s'est fait dans le terminal. Maintenant, ce que fait toute vraie application : demander son identifiant à Vault et se connecter. D'abord, une politique pour le programme, `politicas/app-python.hcl` :

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

Envoie-la et crée un token de 30 minutes pour le programme :

```
$ jq -n --rawfile p politicas/app-python.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/app-python -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/create \
    -d '{"policies": ["app-python"], "ttl": "30m", "display_name": "app-python"}' \
    | jq -r .auth.client_token > secretos-locales/token-python.txt
```

Installe le connecteur PostgreSQL pour Python dans un environnement virtuel :

```
python3 -m venv .venv
.venv/bin/pip install "psycopg[binary]"
```

**Aujourd'hui, tu n'as pas besoin de maîtriser tout Python.** Traite ce fichier comme un programme déjà résolu et ne regarde que quatre zones : `TOKEN` lit un secret dans l'environnement ; `vault(...)` parle à Vault ; `cred = ...` demande l'utilisateur temporaire ; et le bloc `with psycopg.connect(...)` utilise cet utilisateur dans PostgreSQL. À l'exercice 20, tu ne changes que la façon dont le programme se termine.

Et le programme, `python/clientes.py`. Il utilise `urllib`, fourni avec Python, pour parler à Vault, et `psycopg` pour PostgreSQL. Il fait 24 lignes :

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

Ce qu'il fait, dans l'ordre : la fonction `vault` envoie une requête à Vault avec le token dans l'en-tête (si tu lui passes `datos`, c'est un `POST` ; sinon, un `GET`) et renvoie la partie `data` de la réponse. Il demande un identifiant dynamique, se connecte avec, lit les clients et déchiffre chaque CURP avec Transit.

Lance-le avec le token du programme :

```
$ export VAULT_TOKEN=$(cat secretos-locales/token-python.txt)
$ .venv/bin/python python/clientes.py
Vault me prestó el usuario v-token-ap-lector-9FQ5IlE2i1HAUlZvuxZG-1792335175
Pepe   vault:v3:VEk...  ->  PEPE000101HDFXXX01
María  vault:v3:hKW...  ->  MARA990909MDFXXX02
```

Cherche dans le fichier un mot de passe PostgreSQL ou Transit : il n'y en a pas. Le programme reçoit bien un token Vault depuis l'environnement ; ce token est lui aussi secret, mais il n'est pas écrit dans le code, il a des permissions limitées et ne dure que 30 minutes. Le nom de l'utilisateur commence maintenant par `v-token-ap` : Vault note qu'il a été demandé par un token `app-python`, et non root. Relance-le et il te prête **un autre** utilisateur. Et si le programme tente de sortir de sa politique :

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Sans token, il ne démarre même pas :

```
$ unset VAULT_TOKEN; .venv/bin/python python/clientes.py
...
KeyError: 'VAULT_TOKEN'
```

Quand tu as terminé, reviens au token root : `export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)`.

> **Et depuis Java, .NET ou Go ?**
>
> Ce que tu as fait avec `curl` et Python se fait depuis n'importe quel langage, car Vault parle HTTP. Presque personne ne le programme à la main : chaque langage a des bibliothèques. HashiCorp tient une liste qui distingue les officielles de celles de la communauté ([Client libraries](https://developer.hashicorp.com/vault/api-docs/libraries)) :
>
> - **Go :** `github.com/hashicorp/vault/api`, le client que HashiCorp maintient officiellement.
> - **Java avec Spring :** [Spring Cloud Vault](https://spring.io/projects/spring-cloud-vault) charge les secrets de Vault dans la configuration de l'application et peut demander des identifiants de base de données à la volée. HashiCorp le range parmi les bibliothèques de la communauté.
> - **Java avec Quarkus :** l'extension [Quarkus Vault](https://docs.quarkiverse.io/quarkus-vault/dev/index.html), du projet Quarkiverse, couvre KV, Transit et les identifiants dynamiques pour la connexion à la base de données. Elle est elle aussi issue de la communauté.
> - **.NET :** [VaultSharp](https://github.com/rajanadar/VaultSharp) est l'option la plus connue. **Elle n'est pas officielle** : c'est un projet de la communauté. La liste de HashiCorp mentionne en outre un client .NET expérimental qui, selon la même page, n'est pas prêt pour la production.
>
> Et il y a une façon de ne pas toucher au code : **Vault Agent**, un programme qui tourne à côté de ton application, s'identifie auprès de Vault, renouvelle son token et écrit les secrets dans un fichier à partir d'un modèle ; ton application se contente de lire ce fichier ([Vault Agent](https://developer.hashicorp.com/vault/docs/agent-and-proxy/agent)). Dans Kubernetes, l'**injecteur de Vault Agent** l'ajoute tout seul aux pods qui le demandent avec des annotations, et dépose les secrets dans un volume en mémoire partagé avec l'application ([Agent Injector](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/injector)).

> **Et à quoi cela ressemble-t-il dans un vrai système ?**
>
> Imagine une plateforme qui sert beaucoup d'entreprises à la fois et conserve, pour chacune, les mots de passe de ses fournisseurs : l'accès à sa banque, à son outil de facturation, à son transporteur. Si une entreprise voit les secrets d'une autre, c'est la fin de l'activité.
>
> Une bonne conception n'attache pas le programme à Vault. Elle définit d'abord un **composant avec un contrat court** : « scelle ce secret pour cette entreprise » et « ouvre-le ». À l'intérieur, chaque entreprise a **sa propre clé, avec des versions**, comme la clé Transit dont tu as fait la rotation à la session 3 : si une clé tourne, ce qui a été scellé avant s'ouvre toujours, et avec `min_decryption_version`, on donne une date d'expiration à l'ancien.
>
> Derrière ce contrat se branche le fournisseur :
>
> - pour les **tests**, une version qui garde tout en mémoire et s'efface à la fin ;
> - pour la **production**, un adaptateur qui appelle Transit avec une clé par entreprise (`transit/encrypt/empresa-a`, `transit/encrypt/empresa-b`), ou un service de clés d'un cloud.
>
> Ce fournisseur peut être HashiCorp Vault ou OpenBao, sa version libre, qui a un moteur Transit compatible ([Transit dans OpenBao](https://openbao.org/docs/secrets/transit/)) ; chez Hábil, nous avons choisi OpenBao.
>
> Le reste du système ne sait jamais lequel des deux est branché. Ainsi, on peut tout tester sans démarrer Vault, et changer de fournisseur sans réécrire le programme. Remarque ce qu'il **ne** fait **pas** : le programme ne touche jamais la clé. Il demande « scelle » et « ouvre », et la clé reste dans Vault, comme tu l'as vu avec `curl` à la session 3.

---

👉 **Si tu viens de la gestion :** les identifiants dynamiques sont le **badge visiteur** transposé aux systèmes : il est émis au nom de celui qui le demande, n'ouvre que le nécessaire et expire tout seul. La rotation automatique est le **changement périodique de combinaison** du coffre-fort, mais sans que personne n'ait à noter la nouvelle. Et le bouton d'urgence répond à la question que pose n'importe quel auditeur après un incident : « combien de temps a-t-il fallu pour annuler les accès ? ». Avec cela, la réponse est « une commande ». Dans le cas de Canasta Morada, la question qui importait vraiment était autre : « qui paie ce serveur à 9,99 dollars ? ». Passer en revue les débits récurrents de la carte de l'entreprise relève aussi du contrôle des accès.

---

## Exercices de la session 4

**Exercice 16 — Ton badge.** Demande un identifiant du rôle `lector`, connecte-toi avec `psql` et compte les clients. Ensuite, essaie `INSERT INTO clientes (nombre, curp) VALUES ('Intruso', 'x');`.

```
# Pista: guarda la credencial para usarla en el ejercicio 17.
# Archivo sugerido: secretos-locales/creds-16.json
# Ruta que debes consultar: database/creds/lector
```

**Comment vérifier :** le décompte donne `2` (ou autant que tu en as) ; le `INSERT` donne `ERROR:  permission denied for table clientes`.

**Exercice 17 — Révoque-le toi-même.** Révoque l'identifiant de l'exercice 16 avec `sys/leases/revoke` et essaie de te reconnecter. Fais-le dans les 2 minutes : si Vault l'a déjà révoqué et que la route répond que le bail n'existe pas, ce n'est pas une erreur de permissions. Demande un autre identifiant, remplace `creds-16.json` et révoque-le aussitôt.

**Comment vérifier :** la révocation répond `HTTP 204` et `psql` répond `password authentication failed`. Depuis le superutilisateur, `SELECT count(*) FROM pg_roles WHERE rolname = '<utilisateur>';` donne `0`.

**Exercice 18 — Le mot de passe d'il y a une minute.** Enregistre le mot de passe en vigueur de `reportes` dans une variable, fais la rotation avec `rotate-role/reportes` et essaie de te connecter avec celui que tu as gardé.

**Comment vérifier :** avec celui que tu as gardé, `password authentication failed for user "reportes"`. Avec celui que Vault te donne après la rotation, ça passe.

**Exercice 19 — Badge de 30 secondes.** Change le `default_ttl` du rôle `lector` à 30 secondes, sans modifier le fichier, avec `jq` :

```
jq '.default_ttl = "30s"' roles/lector-postgres.json \
  | curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/roles/lector -d @-
```

Demande un identifiant, connecte-toi immédiatement, attends 40 secondes et essaie à nouveau. Enregistre l'identifiant dans `secretos-locales/creds-19.json` et place `PGUSER=... PGPASSWORD=... psql` devant chaque tentative, en lisant les valeurs du fichier avec `jq` comme à l'étape 5 : ce que tu as exporté aux exercices 16 et 17 appartient à un utilisateur déjà révoqué et te donnerait un échec qui n'est pas celui du TTL.

**Comment vérifier :** `lease_duration` dit `30` ; la première tentative passe ; la seconde donne `password authentication failed`. À la fin, remets le rôle comme il était en renvoyant `roles/lector-postgres.json`.

**Exercice 20 — Que le programme ramasse ses déchets.** Chaque fois que `clientes.py` s'exécute, il laisse un utilisateur temporaire vivant jusqu'à son expiration. Fais en sorte qu'il **révoque son propre token** avec `auth/token/revoke-self`, et qu'il le fasse **toujours**, même si quelque chose échoue à mi-chemin (utilise `try` et `finally`). Quand un token est révoqué, Vault révoque aussi les identifiants demandés avec lui. Pars de ce squelette, qui met déjà en place la structure :

```python
try:
    cred = vault("database/creds/lector")
    # pega aquí el bloque with psycopg.connect(...) que ya existe
finally:
    # aquí va la petición POST a auth/token/revoke-self
    pass
```

**Comment vérifier :** avant de le lancer, compte depuis le superutilisateur les utilisateurs qui commencent par `v-token-ap` ; après l'avoir lancé, le décompte doit rester le même qu'avant (l'utilisateur a été créé puis supprimé). Si tu le relances avec le même token, il doit échouer avec `HTTP Error 403`, parce que le token n'existe plus. Pour répéter le test après ce 403, crée un nouveau token avec la même commande que celle de l'étape 12, enregistre-le de nouveau dans `secretos-locales/token-python.txt` et réexporte `VAULT_TOKEN`. Le 403 n'est attendu que pour le token déjà révoqué.

---

## Erreurs courantes (et comment les repérer)

| Erreur | À quoi cela ressemble | Comment la repérer | Que faire |
|---|---|---|---|
| Utiliser `127.0.0.1` dans `connection_url` | À l'enregistrement de la configuration : `error verifying connection: ... dial tcp 127.0.0.1:5432: connect: connection refused`, code 400 | Le serveur de l'URL n'est pas le nom du service ; dans le conteneur de Vault, `127.0.0.1` est Vault lui-même | Dans Docker Compose, Vault atteint la base de données par son nom : `postgres`, `mariadb` |
| Rôle absent de `allowed_roles` | `"escritor" is not an allowed role`, code 500 | Le nom du rôle n'apparaît pas dans `database/config/<connexion>` | Ajoute-le à `allowed_roles` de la connexion |
| Révocation qui échoue avec des permissions strictes | `permission denied for sequence ...` à la révocation | Le rôle n'a pas de `revocation_statements` | Écris tes `revocation_statements` ; ne donne pas le superutilisateur à Vault pour faire disparaître l'erreur |
| Garder le mot de passe de `vault_admin` puis faire la rotation de la racine | Le fichier ne sert plus | `rotate-root` a répondu 204 | C'est ce que nous voulons : aucune personne ne le connaît. Si tu as besoin de te connecter, utilise le superutilisateur de la base de données, pas celui de Vault |
| Attendre qu'un identifiant dure plus que `max_ttl` | Tu renouvelles et il expire quand même | `lease_duration` cesse de croître | `max_ttl` est le plafond. Demande un nouvel identifiant |
| Coller le token du programme dans le code | Le token est écrit dans un fichier que git suit | `git status` montre le fichier comme modifié, et `grep -rn hvs. python/` trouve le token | Le token entre par une variable d'environnement ou, mieux, avec Vault Agent. S'il a été envoyé, révoque-le |
| `psql` entre sans demander de mot de passe | Tu crois que l'identifiant est toujours vivant | Tu t'es connecté par le socket local à l'intérieur du conteneur | Connecte-toi comme dans la leçon, par le réseau (`-h 127.0.0.1` depuis ta machine), là où PostgreSQL vérifie bien le mot de passe |

---

## Autoévaluation de la série

Réponds sans regarder. Si tu te trompes plus de deux fois, retourne à la session indiquée.

1. Quelle est la différence entre `DELETE` sur `secret/data/...` et `destroy` ? *(Session 2)*
2. Écris de mémoire une politique qui permet de lire `secret/data/app/*` et rien d'autre. *(Session 2)*
3. Pourquoi un 403 est-il une bonne nouvelle quand tu testes une politique ? *(Session 2)*
4. De quoi as-tu besoin pour déchiffrer un `vault:v1:...` si la clé a `min_decryption_version: 2` ? *(Session 3)*
5. Qu'est-ce qu'un système gagne avec les clés dérivées et `context` ? *(Session 3)*
6. Quelle différence y a-t-il entre un identifiant dynamique et un rôle statique ? *(Session 4)*
7. Pourquoi la connexion de Vault à la base de données utilise-t-elle `vault_admin` et non le superutilisateur ? *(Session 4)*
8. Un stagiaire quitte l'entreprise. Avec ce que tu as construit, quels mots de passe devrais-tu changer à la main ? *(Toutes)*

## Révision de la série

| Session | Le problème | Ce qui le résout | La commande à ne pas oublier |
|---|---|---|---|
| 1 | Des secrets dans des fichiers, dans des chats, partagés et éternels | Exigences R1 à R7 | `git log -p -S <texte>` |
| 2 | Personne ne sait qui a accès ni qui l'a utilisé | Scellement de Shamir, tokens, politiques, journal d'audit | `curl -H "X-Vault-Token: ..." $VAULT_ADDR/v1/secret/data/...` |
| 3 | La clé de chiffrement vit à côté des données | Transit : chiffrer sans avoir la clé, rotation, rewrap | `POST transit/encrypt/<clé>` avec `plaintext` en base64 |
| 4 | Le même mot de passe de base de données pour tout le monde et pour toujours | Identifiants dynamiques, rotation, `rotate-root`, révocation | `GET database/creds/<rôle>` |

**Pour tout arrêter à la fin de la série :** `docker compose down`. Tes données restent dans les dossiers `vault/`, `postgres/` et `mariadb/`. Si tu veux repartir de zéro, supprime ces dossiers, `secretos-locales/` et `.env`, et relance `./iniciar.sh`.

---

## Solutions (ne les regarde pas avant d'avoir essayé)

**Révision de la session 3.**

1. `vault` : chiffré par Vault ; `v2` : avec la version 2 de la clé ; le reste : la donnée chiffrée, en base64.
2. Elles restent chiffrées avec leur ancienne version et peuvent être déchiffrées tant que cette version ne passe pas sous `min_decryption_version`. `rewrap` les fait monter vers la nouvelle version sans révéler la donnée.
3. Parce que, si quelqu'un vole ce token, il peut déposer des données chiffrées mais n'en peut lire aucune. Les dégâts d'une fuite sont beaucoup plus faibles.

**Exercice 16.**

```
curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector > secretos-locales/creds-16.json
export PGUSER=$(jq -r .data.username secretos-locales/creds-16.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-16.json)
psql -At -c "SELECT count(*) FROM clientes;"
psql -c "INSERT INTO clientes (nombre, curp) VALUES ('Intruso', 'x');"
```

**Exercice 17.** La commande de l'étape 6, avec le `lease_id` de `creds-16.json`. Fais-le avant que les 2 minutes soient écoulées ; si Vault te devance, demande un autre identifiant et révoque-le aussitôt.

**Exercice 18.**

```
VIEJA=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password)
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-role/reportes
PGUSER=reportes PGPASSWORD=$VIEJA psql -At -c "SELECT 1;"
NUEVA=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password)
PGUSER=reportes PGPASSWORD=$NUEVA psql -At -c "SELECT 1;"
```

Dans le test de cette leçon, la commande qui utilise `$VIEJA` (la troisième) a donné `FATAL:  password authentication failed for user "reportes"`. Attention : comme le rôle fait la rotation chaque minute, la « vieille » peut mourir par la rotation automatique avant la tienne. Le résultat est le même. La dernière commande, avec `$NUEVA`, affiche `1` ; si celle-là échoue aussi, redemande à Vault le mot de passe en vigueur et exécute-la de nouveau, car la rotation d'une minute a pu avoir lieu entre une commande et l'autre.

**Exercice 19.**

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

Dans le test :

```
{"lease_duration":30,"username":"v-root-lector-wlrG6BL0dqUomIbQDDrV-1792336140"}
```

La première tentative a renvoyé `2`. Quarante secondes plus tard :

```
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-wlrG6BL0dqUomIbQDDrV-1792336140"
```

**Exercice 20.** Place dans le `try` la demande d'identifiant et tout ce qui utilise la base de données, et la révocation dans le `finally`, qui s'exécute quoi qu'il arrive (même si la demande d'identifiant elle-même échoue) :

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

Ainsi, si la requête, la connexion ou une interrogation échoue, le token est révoqué quand même. `data=b"{}"` transforme la requête en `POST`, ce que demande cette route. Dans le test de cette leçon :

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

L'utilisateur `v-token-ap-lector-xQMN...` est né et mort au cours de la même exécution. Le programme ne laisse plus rien derrière lui.

**Autoévaluation.**

1. `DELETE` supprime la dernière version de façon réversible (`undelete` la remet) ; `destroy` la supprime pour toujours.
2. `path "secret/data/app/*" { capabilities = ["read"] }`
3. Parce qu'il démontre que la politique refuse ce qu'elle doit refuser. Une politique qui ne donne jamais de 403 donne probablement trop.
4. Rien ne le déchiffre tant que le minimum est 2. La bonne démarche était de le ré-envelopper avant d'augmenter le minimum ; sinon, il faut abaisser `min_decryption_version`, ré-envelopper et l'augmenter à nouveau.
5. Qu'une donnée chiffrée pour un propriétaire ne puisse pas être déchiffrée comme si elle appartenait à un autre, même avec la même clé.
6. La dynamique crée un nouvel utilisateur à chaque fois et le supprime à l'expiration ; la statique conserve un utilisateur qui existe déjà et lui change le mot de passe à intervalle régulier.
7. Parce que `rotate-root` laisse le mot de passe entre les mains de Vault, et que la documentation recommande un utilisateur dédié. De plus, avec des permissions strictes, une erreur ou une fuite dans Vault ne donne pas le contrôle total de la base de données.
8. Aucun ne se change à la main. Tu révoques son token Vault et, avec lui, ses identifiants dynamiques (ou tous ceux qu'il a créés, par préfixe). Une exception : s'il connaissait le mot de passe du rôle statique `reportes`, fais-en la rotation immédiatement avec `POST /v1/database/rotate-role/reportes` ; révoquer son token ne change pas ce mot de passe, qui continuerait de fonctionner jusqu'à la prochaine rotation. C'est la différence avec Canasta Morada au début de la série.

---

## La suite

Cette série a utilisé Vault avec un seul serveur, sans TLS et avec les clés dans un fichier, parce que c'est un laboratoire. Si tu veux continuer, les sujets suivants sont : TLS sur le listener, méthodes d'authentification pour les machines (AppRole, Kubernetes) au lieu de tokens créés à la main, stockage avec plusieurs serveurs pour la haute disponibilité, et sauvegardes de Vault lui-même.

---

*J'écris à partir de ce que nous voyons tous les jours chez Hábil, où nous construisons des systèmes pour la banque, l'assurance et les entreprises au Mexique. Si, dans ton travail ou dans l'entreprise de ta famille, vous rencontrez un problème de ce genre, parlons-en : [habil.mx](https://www.habil.mx/fr/)*

*Si, dans ton entreprise, les mots de passe des bases de données vivent encore dans un fichier, chez Hábil nous mettons cela en place dans le cadre du provisionnement d'infrastructure : [identité, clés et secrets](https://www.habil.mx/fr/).*
