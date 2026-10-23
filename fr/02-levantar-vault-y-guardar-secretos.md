# Vault de zéro (2) : démarrer Vault et stocker des secrets

*Un coffre-fort que personne ne peut ouvrir seul, un guichet qui dit non à celui qui demande ce qui ne le concerne pas, et un journal qui note tout. Avec Docker Compose et `curl`.*

*Vault de zéro · session 2 sur 4*

## Révision de la session 1

Réponds sans regarder. Les réponses se trouvent dans les solutions, à la fin.

1. Nomme quatre des six manières dont un secret s'échappe.
2. Pourquoi changer le mot de passe après une fuite est-il obligatoire, même si tu l'as déjà supprimé de git ?
3. En quoi le moteur Transit de Vault ressemble-t-il à un HSM, et en quoi en diffère-t-il ?

> **Le laboratoire de cette session** se trouve dans le dépôt public [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Monte-le d'abord toi-même ; le dépôt sert de point de comparaison quand quelque chose ne donne pas le même résultat. Il ne contient aucun mot de passe : le laboratoire les génère au démarrage.

## Objectifs de cette session

| # | À la fin, tu peux… | L'exercice qui le démontre |
|---|---|---|
| 1 | **Démarrer** Vault en mode serveur avec Docker Compose, sans écrire aucun mot de passe dans les fichiers du laboratoire | Exercice 6 |
| 2 | **Initialiser** et **ouvrir** Vault avec 3 clés sur 5, et **expliquer** pourquoi il se referme tout seul au redémarrage | Exercice 7 |
| 3 | **Stocker, lire, versionner, supprimer et récupérer** des secrets avec `curl` sur l'API | Exercice 8 |
| 4 | **Écrire** une politique et **vérifier** qu'un token limité reçoit un 403 là où il n'a pas le droit d'aller | Exercice 9 |
| 5 | **Lire** le journal d'audit avec `jq` pour savoir qui a demandé quoi | Exercice 10 |

---

## Scénario (fiction) — Chapitre 5 : samedi, 13 h 40

Iván a changé le mot de passe de `app_tienda` à midi. Il lui a fallu une heure et demie pour redémarrer les quatre programmes. La macro de comptabilité n'est jamais réapparue ; Rocío, la comptable, va sortir le rapport du mois manuellement.

Doña Clara écoute tout sans interrompre. À la fin, elle ne dit qu'une chose :

« Je ne veux plus jamais dépendre du fait que quelqu'un se souvienne de l'endroit où il a écrit un mot de passe. »

Iván propose un coffre-fort pour les secrets. Doña Clara demande qui aura la clé.

« Vous, dit Iván.

— Non. S'il m'arrive quelque chose, personne n'ouvre. Et si quelqu'un me la prend, il ouvre tout seul. »

Iván sourit. Cette objection a une réponse qui date de 1979.

---

## Chapitre 6 : le samedi suivant, 3 h 17 du matin

Le coffre-fort existe. Cinq personnes détiennent chacune un morceau de sa clé. Les applis demandent leurs secrets avec leur propre pièce d'identité.

Le téléphone d'Iván vibre à nouveau. Même heure. Même serveur. Mais cette fois, le journal de la base de données dit autre chose :

```
03:17:02  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
03:17:32  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
03:18:02  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
```

Quelqu'un essaie encore avec l'ancien mot de passe. Toutes les trente secondes. Comme une horloge.

Iván reste à regarder l'écran. Les voleurs n'ont pas d'horaires fixes.

Qui en a ?

*(À suivre à la session 3.)*

---

## Pourquoi c'est important

Jusqu'à aujourd'hui, à Canasta Morada, « avoir accès » voulait dire « connaître le mot de passe ». Aujourd'hui, tu vas construire le contraire : un endroit où personne ne connaît rien, et où chacun **demande** ce dont il a besoin et **prouve** qui il est. C'est la différence entre une maison où tout le monde a un double de la clé et un immeuble avec une réception : là, on t'inscrit, on te demande où tu vas et on ne t'ouvre que cet étage.

Dans cette session, tu vas voir trois idées utilisées dans n'importe quel système sérieux, avec ou sans Vault :

- **Le scellement (seal).** Les données sont chiffrées sur le disque. Sans la clé maîtresse, Vault lui-même ne peut pas les lire.
- **Refusé par défaut.** Si une politique ne dit pas que tu peux, tu ne peux pas. La documentation le formule ainsi : « les politiques refusent par défaut » ([Policies](https://developer.hashicorp.com/vault/docs/concepts/policies)).
- **Tout est consigné.** Chaque requête, autorisée ou refusée, laisse une trace dans le journal.

## La réponse de 1979 : les clés de Shamir

En 1979, le cryptographe Adi Shamir a publié une façon de découper un secret en **N morceaux** de telle sorte que n'importe quel groupe de **K** morceaux le reconstitue, et qu'avec moins de K on ne sache rien. Pas même un tout petit peu.

Pense à la tirelire de la fête du village. Il y a cinq gardiens. Pour l'ouvrir, au moins trois doivent se réunir, chacun avec sa clé. Si l'un tombe malade, les quatre autres suffisent. Si l'on vole la clé de l'un d'eux, le voleur n'ouvre rien tout seul. Et personne, pas même le gardien en chef, ne peut l'ouvrir en cachette.

Vault fonctionne ainsi :

- À l'**initialisation**, Vault crée une **clé maîtresse** qui protège tout ce qu'il stocke. Par défaut, il la découpe en **5 morceaux** et en exige **3** pour la reconstituer ([vault operator init](https://developer.hashicorp.com/vault/docs/commands/operator/init)).
- Vault démarre **scellé** (*sealed*) : il a les données, mais chiffrées, et il ne les comprend pas. C'est la tirelire fermée.
- **Desceller** (*unseal*), c'est quand trois gardiens insèrent leur clé. À partir de là, Vault fonctionne normalement.
- Si Vault redémarre, il **se scelle de nouveau**. Il faut réunir trois clés une fois de plus.

La documentation officielle explique le scellement et l'algorithme de Shamir dans [Seal/Unseal](https://developer.hashicorp.com/vault/docs/concepts/seal).

---

## Étape 0 — Ce dont tu as besoin

Docker avec Compose, `curl`, `jq` (version 1.6 ou plus récente), `openssl` et `git`. Vérifie :

```
docker compose version
curl --version
jq --version
openssl version
```

Si l'un d'eux affiche « command not found », installe-le avant de continuer. Cette session utilise Vault 2.2.0, PostgreSQL 17.11 et MariaDB 11.8.8, figés dans le `compose.yaml` : ne les remplace pas par `latest`, car les commandes et les réponses de la leçon correspondent à ces versions.

## Étape 1 — Le dossier du laboratoire

Crée un dossier `lab-vault` avec cette structure. Le contenu de chaque fichier suit plus bas.

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

Le premier est le `.gitignore`. C'est la liste de ce que git ne doit jamais envoyer. Il vient **avant** toute autre chose parce que le laboratoire va générer des mots de passe, et nous voulons que, dès la première seconde, git ne les ajoute pas par inadvertance. Attention : `.gitignore` évite seulement que git ajoute des fichiers qu'il ne connaît pas encore. Il ne protège pas un fichier déjà validé auparavant, ni contre quelqu'un qui forcerait l'envoi avec `git add -f` ; c'est pourquoi il vaut mieux vérifier `git status` avant chaque `git commit`.

```
# Lo que el laboratorio genera al arrancar. NADA de esto se sube a git.
.env
secretos-locales/
vault/data/
vault/logs/
postgres/
mariadb/
```

Ensuite, `.env.ejemplo`. C'est une copie de référence **sans valeurs réelles**, pour que celui qui clone le dépôt sache quelles variables existent :

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

La configuration de Vault, `vault/config/vault.hcl` :

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

Trois choses qu'il vaut mieux comprendre :

- **`storage "file"`** : Vault stocke ses données, déjà chiffrées, dans un dossier. Il existe d'autres options pour la production avec plusieurs serveurs ; celle-ci est la plus simple ([Filesystem storage](https://developer.hashicorp.com/vault/docs/configuration/storage/filesystem)).
- **`tls_disable = true`** : pas de chiffrement de la connexion. Sur ton ordinateur portable, ça va. Sur un vrai serveur, **jamais** : les mots de passe circuleraient en clair sur le réseau.
- **Ce n'est pas le mode « dev ».** Vault a un mode de développement qui démarre ouvert, sans scellement et en gardant tout en mémoire. C'est pratique, mais il te cache justement ce que nous voulons apprendre aujourd'hui.

Le `compose.yaml`. Remarque deux détails : **aucun mot de passe n'est écrit**, seulement des variables comme `${POSTGRES_PASSWORD}`, et les données sont stockées dans des **dossiers montés** (`./vault/data`), et non dans des volumes Docker, pour que tu voies les fichiers et qu'ils ne se perdent pas si quelqu'un nettoie Docker :

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

PostgreSQL et MariaDB, tu les utilises aux sessions 3 et 4 ; nous les démarrons dès aujourd'hui pour ne pas retoucher le fichier ensuite. Le `:?falta .env…` veut dire : « si cette variable n'existe pas, ne démarre pas et affiche ce message ».

Trois détails de ce fichier :

- **`127.0.0.1:` devant chaque port** fait que Docker publie le service uniquement pour ton propre ordinateur. Sans cela, Vault (qui n'utilise pas TLS ici) et les deux bases seraient ouverts à n'importe qui sur ton réseau.
- **`user:`** fait que Vault s'exécute avec ton utilisateur. L'image officielle démarre avec un utilisateur sans privilèges (`vault`), et sous Linux, il ne pourrait pas écrire dans des dossiers que tu as créés toi-même. Le script de démarrage note ton numéro d'utilisateur dans `.env`.
- **Si un port est déjà utilisé** (le 8200, le 5432 ou le 3306), change-le avec `PUERTO_VAULT`, `PUERTO_POSTGRES` ou `PUERTO_MARIADB`, comme expliqué plus bas.

> **Sous Linux : deux dossiers à toi qui ne sont pas à toi.**
>
> Après avoir démarré le laboratoire sous Linux, lance `ls -ln` dans le dossier. Tu verras quelque chose comme ceci (nous avons retiré les colonnes sans importance ; mesuré sous Linux Mint 22.3, avec l'utilisateur 1000) :
>
> ```
> drwx------  999 1000  postgres
> drwxrwxr-x  999  999  mariadb
> drwx------ 1000 1000  secretos-locales
> drwxr-xr-x 1000 1000  vault
> ```
>
> Les dossiers `postgres` et `mariadb` n'appartiennent plus à ton utilisateur : ils appartiennent au 999. Et si tu lances `ls -l` sans le `n`, à la place du numéro, il peut apparaître le nom d'un service de ton système (sous Mint, c'est `dnsmasq` qui est apparu). Ce n'est ni un virus ni une erreur du laboratoire. Cela arrive parce que les images officielles de PostgreSQL et de MariaDB démarrent en tant qu'administrateur dans le conteneur, puis transmettent leurs fichiers à leur propre utilisateur interne, le numéro 999. Un **dossier monté** est le même dossier vu des deux côtés : ce que le conteneur fait à ses fichiers, ton disque le voit tel quel, numéro d'utilisateur compris. Ton Linux ne sait pas qui est le 999 du conteneur ; il ne voit que le numéro, et si, sur ton système, ce numéro a un propriétaire, il t'affiche son nom.
>
> Cela n'arrive pas à Vault parce que le `user:` du compose l'oblige à s'exécuter avec ton numéro. Pourquoi ne fait-on pas la même chose avec les bases de données ? Parce qu'elles ont besoin de démarrer en tant qu'administrateur pour se préparer la première fois, et leur imposer un autre utilisateur casse ce premier démarrage.
>
> Ce que cela signifie pour toi :
> - `ls postgres` te répondra « Permission non accordée ». Pour regarder à l'intérieur, utilise `sudo ls postgres`, ou mieux, demande au conteneur lui-même : `docker compose exec postgres ls /var/lib/postgresql/data`.
> - Si un jour tu veux recommencer le laboratoire de zéro, commence par `docker compose down`, puis supprime ces deux dossiers avec `sudo`, car ton utilisateur ne peut pas le faire.
> - Sous macOS et Windows, tu ne le verras pas : Docker s'exécute dans une machine virtuelle qui te montre les fichiers comme étant à toi.

## Étape 2 — Un script de démarrage qui échoue en mode fermé

`iniciar.sh` prépare tout. L'essentiel se trouve au point 1 : **avant de générer le moindre mot de passe, il vérifie que `.gitignore` le protège.** Sinon, il refuse de continuer. On appelle cela **échouer en mode fermé** (*fail closed*) : dans le doute, la porte reste fermée, comme le tourniquet du métro qui ne tourne pas si ta carte n'est pas passée.

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

`grep -qx` cherche une ligne qui soit **exactement** ce texte (`-x`) et n'affiche rien (`-q`) ; il dit seulement oui ou non. `openssl rand -hex 16` génère 16 octets aléatoires écrits sous la forme de 32 caractères hexadécimaux. `umask 077` fait que le `.env` naît lisible uniquement par toi. `id -u` et `id -g` sont ton numéro d'utilisateur et de groupe. Et le `unset` retire de ton terminal toute variable portant ces noms : Compose donne la priorité aux variables du terminal sur `.env`, et nous ne voulons pas qu'un mot de passe ou un port périmé l'emporte sans que tu le saches.

Donne-lui la permission d'exécution avec `chmod +x iniciar.sh`. Avant de le lancer pour de bon, vérifie qu'il échoue vraiment en mode fermé. Dans une copie du laboratoire où il manque au `.gitignore` la ligne `secretos-locales/`, voici ce qui se passe :

```
$ ./iniciar.sh
ALTO: .gitignore no tiene la regla 'secretos-locales/'.
Sin ella, las contraseñas que voy a generar podrían terminar en git. No sigo.
código de salida: 1
```

Il n'a créé aucun dossier ni aucun `.env`. Maintenant, avec le `.gitignore` complet :

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

Si, sur ta machine, tu utilises déjà le port 5432 (parce que tu as un autre PostgreSQL), démarre-le ainsi la première fois : `PUERTO_POSTGRES=15432 ./iniciar.sh`. Le script le note dans `.env`.

Et la preuve que git ne voit pas les secrets. Si tu fais `git init` dans le dossier et que tu demandes ce qui serait envoyé :

```
$ git status --short
?? .env.ejemplo
?? .gitignore
?? compose.yaml
?? iniciar.sh
?? vault/config/vault.hcl
```

Ni `.env`, ni `secretos-locales/`, ni les données. C'est ce que tu voulais.

## Étape 3 — Est-il en vie ?

Vault parle HTTP. Garde son adresse dans une variable pour ne pas la retaper à chaque fois :

```
export VAULT_ADDR="http://127.0.0.1:$(grep '^PUERTO_VAULT=' .env | cut -d= -f2)"
```

Lance cette ligne dans le dossier `lab-vault`. Le port est lu dans ton `.env`, donc cela fonctionne même si tu l'as changé. Que Docker affiche « Started » ne veut pas dire que Vault écoute déjà. Attends qu'il réponde :

```
until curl -fsS -o /dev/null "$VAULT_ADDR/v1/sys/seal-status"; do
  echo "Espero a que Vault inicie..."
  sleep 1
done
```

Demande-lui où en est son scellement. Cette route ne demande pas d'identification :

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

`initialized: false` : personne ne l'a jamais initialisé. `sealed: true` : il est scellé. `t` et `n` sont le seuil et le total des clés ; il n'y en a pas encore.

Une autre façon rapide de connaître l'état est le code HTTP de la route de santé. `-o /dev/null` jette la réponse et `-w` n'affiche que le code :

```
$ curl -s -o /dev/null -w "%{http_code}\n" $VAULT_ADDR/v1/sys/health
501
```

501 veut dire « non initialisé ». Tu verras comment cela change.

## Étape 4 — Initialiser : les cinq clés naissent

Cette requête crée la clé maîtresse, la découpe en 5 morceaux avec un seuil de 3, et te renvoie les morceaux ainsi qu'un **token root**. Tu l'enregistres directement dans un fichier du dossier `secretos-locales/`, que git ignore :

```
curl -s -X PUT $VAULT_ADDR/v1/sys/init \
  -d '{"secret_shares": 5, "secret_threshold": 3}' > secretos-locales/init.json
chmod 600 secretos-locales/init.json
```

`chmod 600` rend le fichier lisible uniquement par toi. Regarde-le sans afficher les valeurs complètes :

```
$ jq "{llaves: (.keys | length), token_root: (.root_token[0:9] + \"...\")}" secretos-locales/init.json
{
  "llaves": 5,
  "token_root": "hvs.RGQs7..."
}
```

Tes valeurs seront différentes. Chaque initialisation crée de nouvelles clés. Dans cette leçon, tu verras toujours les tokens tronqués, ainsi : `hvs.RGQs7...`.

Le **token root** est la clé du propriétaire : il peut absolument tout faire. Tu t'en serviras pour configurer le laboratoire.

> **Pas comme ça, et pourquoi**
>
> Stocker les cinq clés et le token root dans un fichier à côté du `compose.yaml` est une **concession du laboratoire**, pour que tu puisses t'entraîner seul sur ta machine. **Dans la vie réelle, cela ne se fait jamais ainsi.**
>
> - Les clés sont réparties entre des **personnes différentes**, une à chacune, justement pour que personne ne puisse ouvrir le coffre seul. Les rassembler dans un fichier, c'est avoir les cinq gardiens en une seule personne.
> - Le **token root est révoqué** dès que la configuration initiale est terminée. La documentation le recommande ainsi : ne l'utiliser que pour l'indispensable au début et le révoquer dès qu'on n'en a plus besoin ([Tokens](https://developer.hashicorp.com/vault/docs/concepts/tokens)). Si un jour il en faut un autre, on le génère en réunissant à nouveau les clés.
> - Un vrai serveur utilise TLS, pas `tls_disable`.
>
> Si un jour tu copies ce laboratoire sur un serveur, ces trois points sont les premiers que tu changes.

Vérifie à nouveau le scellement :

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

Initialisé, mais scellé. Il manque les gardiens.

## Étape 5 — Desceller avec 3 clés sur 5

Chaque appel à `sys/unseal` remet **une** clé. `jq -r '.keys[0]'` extrait la première du fichier, sans guillemets :

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

`progress: 1` : une sur trois. Répète avec `.keys[1]` :

```
{
  "sealed": true,
  "t": 3,
  "n": 5,
  "progress": 2
}
```

Et avec `.keys[2]` :

```
{
  "sealed": false,
  "t": 3,
  "n": 5,
  "progress": 0
}
```

`sealed: false`. Ouvert. La route de santé répond maintenant 200 :

```
$ curl -s -o /dev/null -w "%{http_code}\n" $VAULT_ADDR/v1/sys/health
200
```

Vérifie qu'il se scelle tout seul au redémarrage :

```
$ docker compose restart vault
$ curl -s $VAULT_ADDR/v1/sys/seal-status | jq "{sealed, progress}"
{
  "sealed": true,
  "progress": 0
}
```

Il sera ainsi chaque fois que tu allumeras ton ordinateur ou que tu redémarreras le conteneur. Pour ne pas retaper trois fois la même chose, ouvre-le avec une boucle :

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

Et si quelqu'un insère une fausse clé ?

```
$ curl -s -X PUT $VAULT_ADDR/v1/sys/unseal -d '{"key": "esta-no-es-una-llave"}'
{"errors":["'key' must be a valid hex or base64 string"]}
```

## Étape 6 — T'identifier : le token

Sans token, le guichet ne te sert pas :

```
$ curl -s -w " HTTP %{http_code}\n" $VAULT_ADDR/v1/sys/mounts
{"errors":["permission denied"]}
 HTTP 403
```

Exporte le token root dans une variable de ton terminal. **Ne le colle jamais dans un fichier qui sera envoyé** ; tu le lis là où il se trouve :

```
export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)
```

Le token voyage dans l'en-tête `X-Vault-Token`. Demande qui tu es :

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

`ttl: 0` veut dire qu'il n'expire jamais. Une autre raison de le révoquer dans la vie réelle.

Une précision : dans le laboratoire, la « pièce d'identité » de l'appli est un token que tu crées manuellement. Ainsi, on voit le mécanisme de près. Dans un vrai système, les applications obtiennent leur token toutes seules, en prouvant qui elles sont avec des méthodes comme AppRole, Kubernetes ou OIDC (la documentation de Vault les appelle *méthodes d'authentification*) ; cela sort du cadre de cette série.

## Étape 7 — Allumer le journal avant toute chose

Le journal passe en premier, pour que tout ce que tu feras à partir de maintenant soit consigné. Un **périphérique d'audit** de type fichier écrit une ligne JSON pour chaque requête et une autre pour chaque réponse ([File audit device](https://developer.hashicorp.com/vault/docs/audit/file)) :

```
$ curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/audit/archivo \
    -d '{"type": "file", "options": {"file_path": "/vault/logs/audit.log"}}'
HTTP 204
```

204 veut dire « c'est fait, et je n'ai rien à te raconter ». Le journal se trouve dans `./vault/logs/audit.log` sur ta machine, grâce au dossier monté.

## Étape 8 — Stocker des secrets : le moteur KV version 2

Active le moteur **KV v2** sur le chemin `secret/`. C'est un tiroir à secrets clé-valeur qui conserve des versions ([KV v2](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2)) :

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/secret -d '{"type": "kv", "options": {"version": "2"}}'
HTTP 204
```

Liste les moteurs présents :

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/mounts | jq -r ".data | keys[]"
agent-registry/
cubbyhole/
identity/
secret/
sys/
```

Le tien est `secret/`. Les autres sont fournis d'origine.

**Écrire.** Enregistre l'utilisateur et le mot de passe de l'appli de la boutique. Les valeurs sont factices ; dans la vie réelle, tu génères le mot de passe avec `openssl rand`, comme l'a fait le script :

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

Remarque le chemin : `secret/`**`data/`**`tienda/postgres`. Dans KV v2, les données vont sous `data/` et les informations sur les versions sous `metadata/`. C'est le piège numéro un de KV v2 ; il figure dans le tableau des erreurs.

**Lire :**

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

**Une nouvelle version.** Change le mot de passe :

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/secret/data/tienda/postgres \
    -d '{"data": {"usuario": "app_tienda", "password": "Mango-2026"}}' | jq -c ".data | {version, created_time}"
{"version":2,"created_time":"2026-10-18T14:47:29.522529264Z"}
```

La version 1 est toujours là. Demande-la avec `?version=1` :

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/postgres?version=1" | jq -c .data.data
{"password":"Pepino-2026","usuario":"app_tienda"}
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c ".data.data, .data.metadata.version"
{"password":"Mango-2026","usuario":"app_tienda"}
2
```

C'est comme l'historique des versions d'un document dans le cloud : tu peux revenir à celle d'hier si celle d'aujourd'hui s'est mal passée.

**Supprimer (avec filet de sécurité).** `DELETE` sur `data/` supprime la dernière version, mais de façon réversible :

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X DELETE $VAULT_ADDR/v1/secret/data/tienda/postgres
HTTP 204
```

À la lecture, il n'y a plus de données, la réponse indique l'heure de la suppression et le code est 404 :

```
null
"2026-10-18T14:47:29.564180533Z"
HTTP 404
```

**Récupérer.** `undelete` la remet :

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X POST \
    $VAULT_ADDR/v1/secret/undelete/tienda/postgres -d '{"versions": [2]}'
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c .data.data
{"password":"Mango-2026","usuario":"app_tienda"}
```

**Détruire (sans retour).** `destroy` supprime pour toujours les versions que tu indiques. Détruis la 1, l'ancien mot de passe :

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X PUT \
    $VAULT_ADDR/v1/secret/destroy/tienda/postgres -d '{"versions": [1]}'
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/postgres?version=1" | jq -c ".data.metadata | {version, destroyed}"
{"version":1,"destroyed":true}
```

**Les métadonnées** te racontent l'histoire du secret, y compris qui a créé chaque version :

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

Dans cette requête `jq`, `map_values(...)` parcourt chaque version et n'en conserve que deux informations : si elle a été détruite et qui l'a créée.

Et pour voir quels secrets se trouvent dans un dossier, le verbe `LIST` :

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X LIST $VAULT_ADDR/v1/secret/metadata/tienda | jq -c .data
{"keys":["postgres"]}
```

### L'alternative : la commande `vault` dans le conteneur

Tout ce qui précède se fait aussi avec la commande `vault`, qui se trouve dans le conteneur. `-e VAULT_TOKEN` lui transmet ta variable :

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

Enregistre avec elle un deuxième secret, celui de la paie, que tu utiliseras pour tester les permissions :

```
$ docker compose exec -e VAULT_TOKEN vault vault kv put secret/nomina/banco cuenta=0123456789 clave=Aguacate-99
====== Secret Path ======
secret/data/nomina/banco
...
version            1
```

Remarque que la commande ajoute `data/` toute seule. C'est pourquoi `curl` est plus instructif : tu vois le vrai chemin.

## Étape 9 — Politiques : à chacun sa clé

Une **politique** (*policy*) dit à quels chemins un token peut accéder et ce qu'il peut y faire. Crée le dossier `politicas/` et, dedans, le fichier `politicas/lectura-tienda.hcl` :

```hcl
# La app de la tienda puede LEER sus secretos. Nada más.
path "secret/data/tienda/*" {
  capabilities = ["read"]
}
```

`*` veut dire « n'importe quoi sous `tienda/` ». Les capacités les plus utilisées sont `read`, `create`, `update`, `delete` et `list`. Ce qui n'y figure pas est refusé.

Envoie-la. L'API attend le texte de la politique dans un JSON ; `jq --rawfile p archivo` lit le fichier et l'enregistre dans la variable `p` ; `-n` dit à `jq` de ne pas attendre de données en entrée, et le `\$p` porte une barre oblique inverse pour que ton terminal ne le confonde pas avec une variable à lui. Ainsi, `jq` enveloppe la politique dans le JSON sans que tu aies à l'échapper manuellement :

```
$ jq -n --rawfile p politicas/lectura-tienda.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/lectura-tienda -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X LIST $VAULT_ADDR/v1/sys/policies/acl | jq -c .data.keys
["default","default-ceiling","lectura-tienda","root"]
```

`-d @-` dit à `curl` : « le corps vient de l'entrée », c'est-à-dire de ce que `jq` lui a transmis par le pipe.

Maintenant, crée un **token pour l'appli**, avec cette politique et une heure de durée de vie. Le token complet va dans `secretos-locales/`, jamais à l'écran :

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

La politique `default` est incluse dans tous les tokens ; elle permet de faire des choses de base, comme consulter ton propre token. `lease_duration: 3600` correspond à 3 600 secondes : une heure.

Teste les trois cas. **Lire ce qui est à elle :**

```
$ curl -s -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c .data.data
{"password":"Mango-2026","usuario":"app_tienda"}
```

Code 200. **Lire la paie :**

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/nomina/banco
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

**Écrire dans ce qui est à elle :**

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" -X POST \
    $VAULT_ADDR/v1/secret/data/tienda/postgres -d '{"data": {"password": "me-la-robe"}}'
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Deux 403. Le guichet a dit non. Et tu peux demander à Vault ce qu'il te laisse faire sur chaque chemin, sans essayer :

```
$ curl -s -H "X-Vault-Token: $APP_TOKEN" -X POST $VAULT_ADDR/v1/sys/capabilities-self \
    -d '{"paths": ["secret/data/tienda/postgres", "secret/data/nomina/banco"]}' \
    | jq -c "{tienda: .[\"secret/data/tienda/postgres\"], nomina: .[\"secret/data/nomina/banco\"]}"
{"tienda":["read"],"nomina":["deny"]}
```

## Étape 10 — Le journal : qui a demandé quoi

Chaque ligne de `vault/logs/audit.log` est un JSON. Combien y en a-t-il déjà :

```
$ wc -l vault/logs/audit.log
      62 vault/logs/audit.log
```

Les dernières réponses, résumées : heure, qui, quelle opération, quel chemin et s'il y a eu une erreur :

```
$ tail -n 6 vault/logs/audit.log | jq -c "select(.type == \"response\") | {hora: .time, quien: .auth.display_name, operacion: .request.operation, ruta: .request.path, error: .error}"
{"hora":"2026-10-18T14:47:54.325141694Z","quien":"token-app-tienda","operacion":"update","ruta":"secret/data/tienda/postgres","error":"1 error occurred:\n\t* permission denied\n\n"}
{"hora":"2026-10-18T14:47:54.338083991Z","quien":"token-app-tienda","operacion":"update","ruta":"sys/capabilities-self","error":null}
{"hora":"2026-10-18T14:47:54.351637479Z","quien":"token-app-tienda","operacion":"read","ruta":"auth/token/lookup-self","error":null}
```

Voilà la tentative d'écriture de l'appli, avec son nom (`token-app-tienda` : Vault ajoute `token-` devant le `display_name`) et son `permission denied`. C'est ce qu'Iván n'avait pas le samedi : **le nom et le prénom de chaque tentative**.

Qui a lu le secret de la boutique ?

```
$ jq -c "select(.type == \"response\" and .request.path == \"secret/data/tienda/postgres\" and .request.operation == \"read\") | {quien: .auth.display_name, error}" vault/logs/audit.log
{"quien":"root","error":null}
...
{"quien":"token-app-tienda","error":null}
```

Plusieurs lectures de `root` (toi, en train de configurer) et une de l'appli.

Maintenant, le plus intéressant. Le journal a-t-il enregistré le mot de passe ?

```
$ jq -c "select(.type == \"response\" and .request.path == \"secret/data/tienda/postgres\" and .auth.display_name == \"token-app-tienda\") | .response.data" vault/logs/audit.log | head -1
{"data":{"password":"hmac-sha256:bbda6f946e50152cf8b72cd5a9716a077096420551a4c5a7cb395e4f7eddd734","usuario":"hmac-sha256:becdf07b09b37a0b8d310c8f5e99dac229b4cc1b80e092e4b9107ee0f7483212"},"metadata":{...}}
$ grep -c "Mango-2026" vault/logs/audit.log
0
```

Non. Par défaut, Vault écrit dans le journal une **empreinte** (un HMAC-SHA256) des valeurs de texte sensibles, et non la valeur ([Audit devices](https://developer.hashicorp.com/vault/docs/audit)). Les nombres et les valeurs oui/non, il ne les convertit pas en empreinte ; c'est pourquoi il vaut mieux stocker dans Vault des secrets de type texte, comme dans ce laboratoire. Une empreinte est comme l'empreinte digitale d'une personne : elle sert à vérifier si deux choses sont identiques, mais ne permet pas de reconstituer la personne. Ainsi, celui qui lit le journal n'emporte pas les mots de passe.

Et si un jour tu as besoin de savoir si le mot de passe apparu dans un chat est celui que l'appli a lu, tu demandes à Vault l'empreinte de ce texte et tu compares :

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/sys/audit-hash/archivo \
    -d '{"input": "Mango-2026"}' | jq -r .data.hash
hmac-sha256:bbda6f946e50152cf8b72cd5a9716a077096420551a4c5a7cb395e4f7eddd734
```

C'est la même empreinte. Elle correspond.

Pour finir, l'appli peut **révoquer son propre token** quand elle a terminé. Après cela, il ne lui sert plus à rien :

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/revoke-self
HTTP 204
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres
{"errors":["2 errors occurred:\n\t* permission denied\n\t* invalid token\n\n"]}
 HTTP 403
```

---

👉 **Si tu viens de la gestion :** les clés de Shamir sont l'équivalent technique des **signatures conjointes** d'un compte bancaire : pour déplacer de l'argent, deux mandataires sur trois signent, et aucun ne peut le faire seul. La politique avec le 403, c'est la **séparation des tâches** : celui qui saisit n'autorise pas, celui qui encaisse ne rapproche pas. Et le journal avec empreintes est un audit qui consigne qui a touché chaque dossier sans photocopier le dossier. S'il t'appartient de revoir les contrôles d'un système, pose des questions sur ces trois points avec ces mots ; presque toujours, on te comprend.

---

## Exercices de la session 2

Les solutions se trouvent à la fin.

**Exercice 6 — Le tourniquet.** Crée un nouveau dossier, `lab-prueba`, et copies-y seulement trois fichiers : `.gitignore`, `compose.yaml` et `iniciar.sh`. Fais-le ainsi, avec une copie neuve, et non en copiant ton dossier déjà utilisé : celui-là contient déjà un `.env` et l'exercice ne pourrait rien démontrer. Dans `lab-prueba`, supprime la ligne `.env` du `.gitignore` et lance `./iniciar.sh`.

**Comment vérifier :** avant de lancer le script, `ls -a` ne doit afficher aucun `.env`. Ensuite, il doit dire `ALTO: .gitignore no tiene la regla '.env'.`, sortir avec le code 1 (vérifie avec `echo $?` juste après) et **ne pas** créer le fichier `.env` (vérifie avec `ls -a`).

**Exercice 7 — Les gardiens.** Redémarre Vault avec `docker compose restart vault`. Ouvre-le en utilisant les clés 4 et 5 (`.keys[3]` et `.keys[4]`), puis la 1.

a) Le choix des trois clés que tu utilises a-t-il de l'importance ?
b) Que vois-tu dans `progress` après la deuxième clé ?

**Comment vérifier :** à la fin, `sys/health` doit répondre `200`.

**Exercice 8 — Ton propre secret avec des versions.** Enregistre dans `secret/data/tienda/correo` un utilisateur `avisos` et un mot de passe que tu génères avec `openssl rand -hex 12`. Ensuite, remplace-le par un autre généré de la même façon. Enfin :

a) Lis la version 1 et la 2.
b) Supprime la 2 avec `DELETE`, vérifie le 404 et récupère-la.
c) Affiche avec `metadata/` combien de versions il y a.

**Comment vérifier :** `current_version` doit être `2` et la lecture finale doit donner le deuxième mot de passe.

**Exercice 9 — Une politique pour la comptabilité.** Écris `politicas/contabilidad.hcl` : elle peut **lire** `secret/data/nomina/*` et **lister** `secret/metadata/nomina/*`, rien de plus. Envoie-la, crée un token avec elle (enregistre-le dans `secretos-locales/`) et teste :

a) Lire `secret/data/nomina/banco`.
b) Lire `secret/data/tienda/postgres`.
c) Écrire dans `secret/data/nomina/banco`.

**Comment vérifier :** a) 200 ; b) 403 ; c) 403. Et `sys/capabilities-self` pour le chemin de la paie doit dire `["read"]`.

**Exercice 10 — Le détective.** Avec `jq` sur `vault/logs/audit.log`, extrais une liste de **toutes les réponses avec erreur**, en indiquant qui et quel chemin.

**Comment vérifier :** doivent apparaître, au minimum, les deux 403 de `token-app-tienda` de l'étape 9 et les deux 403 de l'exercice 9 (b et c). Si ta liste est vide, vérifie que tu filtres sur `.type == "response"` et que tu testes `.error != null`.

---

## Erreurs courantes (et comment les repérer)

| Erreur | À quoi cela ressemble | Comment la repérer | Que faire |
|---|---|---|---|
| Oublier `data/` dans le chemin de KV v2 | `curl .../v1/secret/tienda/postgres` renvoie 404 avec l'avertissement `Invalid path for a versioned K/V secrets engine` | Le chemin n'a pas de `data/` | Données dans `secret/data/...` ; versions dans `secret/metadata/...` |
| Politique écrite sans `data/` | Tu as mis `path "secret/tienda/*"` et le token reçoit un 403 sur ce qui est à lui | `sys/capabilities-self` dit `deny` | La politique utilise le chemin de l'API : `secret/data/tienda/*` |
| Vault scellé après un redémarrage | Tout répond `{"errors":["Vault is sealed"]}` avec le code 503 | `sys/seal-status` dit `sealed: true` | Ouvre-le avec 3 clés. C'est ce qui doit arriver, pas une panne |
| La variable `VAULT_TOKEN` est vide | 403 même si tu utilises le token root | `echo ${#VAULT_TOKEN}` renvoie `0` | Chaque nouveau terminal démarre sans variables : exporte-la à nouveau |
| Apostrophes autour d'une variable | `-d '{"key": "$LLAVE"}'` envoie le texte `$LLAVE` | Vault dit que la clé n'est pas valide | Entre apostrophes, le terminal ne substitue pas les variables. Utilise des guillemets doubles et échappe les guillemets internes : `"{\"key\": \"$LLAVE\"}"` |
| Coller le token dans un fichier du dépôt | Le token apparaît dans `git status` ou dans un commit | `git log -p -S hvs.` le trouve | Les tokens vivent dans `secretos-locales/` et dans des variables du terminal. S'il a été envoyé : révoque-le |
| Port occupé au démarrage | `bind: address already in use` | `lsof -nP -iTCP:5432 -sTCP:LISTEN` montre un autre processus (remplace 5432 par 8200 ou 3306 s'il s'agit d'un autre service) | Change le port dans `.env` (`PUERTO_POSTGRES=15432`, `PUERTO_VAULT` ou `PUERTO_MARIADB`) et relance `docker compose up -d` ; si tu as changé `PUERTO_VAULT`, redéfinis `VAULT_ADDR` |

---

## Révision pour la prochaine session

La session 3 commence par ces trois questions. Réponds-y sans regarder :

1. Pourquoi Vault démarre-t-il scellé, et de combien de clés as-tu besoin par défaut pour l'ouvrir ?
2. Un token reçoit un 403. Quelles sont deux causes possibles, et quelle route de Vault te dit ce que ce token peut faire ?
3. Si quelqu'un vole le journal d'audit, emporte-t-il les mots de passe ? Pourquoi ?

🔁 **La semaine prochaine :** la sauvegarde volée contenait huit mille CURP, et la clé pour les lire se trouvait à côté. Tu apprends à chiffrer avec Vault sans que ton programme ait jamais la clé, tu stockes les données chiffrées dans PostgreSQL et tu découvres combien de fois cette sauvegarde a été emportée.

**Avant de partir :** arrête le laboratoire avec `docker compose stop`. Tes données restent dans les dossiers. La prochaine fois, `docker compose start` et ouvre le scellement avec la boucle de l'étape 5.

---

## Solutions (ne les regarde pas avant d'avoir essayé)

**Révision de la session 1.**

1. N'importe quelles quatre parmi : le mot de passe dans le code ou dans un fichier qui est envoyé ; le `.env` qui circule par chat ; le même mot de passe pour tout le monde et pour toujours ; personne ne sait qui l'a utilisé ; celui qui est parti le connaît encore ; la clé de chiffrement à côté des données.
2. Parce que git garde l'historique : le mot de passe reste dans les modifications précédentes, et quiconque a cloné le dépôt en a une copie. Supprimer ne défait pas les copies ; le changer, lui, les rend inutiles.
3. Il lui ressemble en ce que tu envoies des données et que tu reçois des données chiffrées sans que la clé sorte. Il en diffère en ce qu'un HSM est un appareil physique avec des protections contre les manipulations (dont la solidité dépend du modèle), et que Vault est un logiciel sur un serveur ; Transit est un moteur de Vault qui propose les opérations de chiffrement par API.

**Exercice 6.** La sortie est :

```
ALTO: .gitignore no tiene la regla '.env'.
Sin ella, las contraseñas que voy a generar podrían terminar en git. No sigo.
```

`echo $?` renvoie `1` et `ls -a` n'affiche pas `.env`.

**Exercice 7.** a) Peu importe : toute combinaison de 3 clés sur 5 convient. b) `progress: 2` et `sealed: true`. Avec la troisième, `sealed: false`.

**Exercice 8.** Une façon de faire :

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

Les deux premières renvoient `1` et `2` ; les deux lectures avec `?version=` montrent le premier et le deuxième mot de passe ; le `DELETE` renvoie `204`, la lecture suivante `404`, et `current_version` renvoie `2`. La dernière ligne affiche `true` si la lecture finale renvoie le deuxième mot de passe. Remarque que ces mots de passe, tu ne les as jamais écrits toi-même : ils sont sortis d'`openssl` et ont voyagé dans une variable.

**Exercice 9.** La politique :

```hcl
path "secret/data/nomina/*" {
  capabilities = ["read"]
}
path "secret/metadata/nomina/*" {
  capabilities = ["list"]
}
```

Elle s'envoie et s'utilise comme `lectura-tienda`, en changeant le nom. Les résultats attendus : 200, 403, 403.

**Exercice 10.**

```
jq -c 'select(.type == "response" and .error != null) | {quien: .auth.display_name, ruta: .request.path, error}' vault/logs/audit.log
```

Remarque qu'ici le filtre est entre apostrophes, et c'est pourquoi les guillemets doubles à l'intérieur ne portent pas de barre oblique inverse.

---

## La suite

À la session 3, tu utilises PostgreSQL depuis ton terminal avec `psql`. Vérifie que tu l'as avec `psql --version`. Sinon, installe le client : `sudo apt install postgresql-client` sous Linux, ou `brew install libpq` sous macOS (et suis l'indication qu'il te donne pour l'ajouter à ton `PATH`).

---

*J'écris à partir de ce que nous voyons tous les jours chez Hábil, où nous construisons des systèmes pour la banque, l'assurance et les entreprises au Mexique. Si, dans ton travail ou dans l'entreprise de ta famille, vous rencontrez un problème de ce genre, parlons-en : [habil.mx](https://www.habil.mx/fr/)*
