# Vault de zéro

**Par Dorian Chávez, fondateur de Hábil et architecte d'intégration.**

Des mots de passe qui ne vivent pas dans le code, des clés que personne ne détient et des identifiants qui expirent tout seuls.

**À qui il s'adresse :** aux étudiants en informatique et à qui programme déjà ou administre des serveurs et veut cesser de stocker
des mots de passe dans des fichiers ; et aux personnes de la gestion qui veulent comprendre quoi demander lorsqu'on audite qui a accès
à quoi. C'est un cours de niveau intermédiaire : on n'explique pas ce qu'est un terminal ni un conteneur, mais chaque nouveau mot est
expliqué au moment où il apparaît. Chaque session comporte un encadré « Si tu viens de la gestion » avec la même idée appliquée au contrôle
interne d'une entreprise.

**Ce que tu sauras faire à la fin :**

- Trouver des mots de passe écrits dans des fichiers et démontrer avec `git` que les supprimer ne les retire pas de l'historique.
- Démarrer Vault en mode serveur, le desceller avec 3 clés sur 5 et stocker des secrets avec des permissions et un journal d'audit.
- Chiffrer et déchiffrer des données avec le moteur Transit sans que la clé n'atteigne ton programme, et faire la rotation de cette clé sans rien perdre.
- Demander des utilisateurs PostgreSQL et MariaDB qui naissent quand tu les demandes et expirent tout seuls, et connecter un programme Python
  sans écrire le moindre mot de passe.

**Ce dont tu as besoin avant de commencer :** savoir utiliser le terminal, `git` de base (`add`, `commit`, `status`) et Docker de base (ce
qu'est une image et un conteneur). Pour la session 1, un terminal et `git` 2.28 ou plus récent suffisent. À partir de la session 2 : Docker
avec Compose, `curl`, `jq` 1.6 ou plus récent et `openssl`. Testé sous Linux Mint 22.3 avec l'image officielle
`hashicorp/vault:2.2.0`, et sous macOS ; il n'a pas été testé sous Windows.

## Les quatre sessions

Quatre sessions d'environ 2 heures chacune : à peu près une pour lire et suivre l'exemple, et une autre pour pratiquer. Toutes
suivent la même histoire : une boutique, un mot de passe poussé sur GitHub un vendredi à 18 h 04 et quelqu'un qui
est entré dans la base de données à 3 h 17 du matin.

| Session | | Ce que tu apprends |
|---|---|---|
| 1 | [Le problème des secrets](01-el-problema-de-los-secretos.md) | les six façons dont un secret s'échappe ; les chercher avec `grep` et `git` ; ce qu'est Vault et ce qu'il n'est pas |
| 2 | [Démarrer Vault et stocker des secrets](02-levantar-vault-y-guardar-secretos.md) | Docker Compose, le scellement et les clés de Shamir, des secrets avec `curl`, les politiques et le journal d'audit |
| 3 | [Chiffrer sans avoir la clé](03-cifrar-sin-tener-la-llave.md) | le moteur Transit : chiffrer, déchiffrer, faire la rotation, lier le chiffrement à son propriétaire et supprimer en détruisant la clé |
| 4 | [Des mots de passe qui changent tout seuls](04-contrasenas-que-se-cambian-solas.md) | identifiants dynamiques dans PostgreSQL et MariaDB, rotation automatique, le bouton d'urgence et Python sans mots de passe |

## Le laboratoire

Tout ce qui est utilisé à partir de la session 2 se trouve à la racine de ce dépôt : `compose.yaml`, le script `iniciar.sh`, les
politiques, les rôles et le programme Python. Il ne contient aucun mot de passe : le laboratoire les génère au démarrage. La façon de
le démarrer est décrite dans le [README principal](../README.md).

## Où il est publié

Une session par semaine dans « En construcción », le Substack de Hábil, le samedi à 8 h 00, du 7 au 28 novembre
2026 : https://enconstruccionmx.substack.com
