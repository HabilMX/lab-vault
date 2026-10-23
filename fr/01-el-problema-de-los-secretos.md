# Vault de zéro (1) : le problème des secrets

*Un vendredi à 18 h 04, une stagiaire pousse un fichier sur GitHub. À 3 h 17 du matin, quelqu'un entre dans la base de données. Pourquoi cela arrive, pourquoi c'est si fréquent, et ce dont une entreprise a besoin pour que cela ne lui arrive pas.*

*Vault de zéro · session 1 sur 4*

Cette série compte quatre sessions, une par semaine. Tu apprends à stocker des mots de passe, des clés et d'autres secrets dans HashiCorp Vault, à chiffrer des données sans garder la clé dans ton programme et à faire en sorte que les mots de passe des bases de données se changent tout seuls. Tout se fait dans le terminal : `curl`, `psql`, `mariadb` et Docker Compose. Le seul programme, tu l'écris à la fin, et il fait moins de 30 lignes.

| Session | Ce que tu vois | Pratique |
|---|---|---|
| **1 — Le problème des secrets** | Ce qui tourne mal quand les mots de passe vivent dans des fichiers, ce qu'il faut pour l'éviter et ce qu'est Vault | Exercices 1 à 5, avec `grep` et `git` |
| **2 — Démarrer Vault et stocker des secrets** | Vault avec Docker Compose, le scellement (seal) et ses clés, stocker et lire des secrets avec `curl`, permissions et journal d'audit | Exercices 6 à 10 |
| **3 — Chiffrer sans avoir la clé** | Le moteur Transit : chiffrer, déchiffrer et faire tourner les clés ; stocker dans PostgreSQL des données que personne d'autre ne peut lire | Exercices 11 à 15 |
| **4 — Des mots de passe qui changent tout seuls** | Des utilisateurs de base de données qui expirent, des mots de passe qui tournent tout seuls et un script Python qui ne stocke aucun mot de passe | Exercices 16 à 20, autoévaluation et révision de la série |

Chaque session dure environ 2 heures : à peu près une pour lire et suivre l'exemple, et une autre pour pratiquer. À partir de la session 2, chacune commence par **3 questions de révision** sur la précédente, auxquelles tu réponds sans regarder.

**Ce que tu dois savoir avant :** utiliser le terminal (te déplacer entre les dossiers, créer des fichiers, lancer des commandes), les bases de `git` (`git add`, `git commit` et `git status` ; savoir qu'un fichier « nouveau » est un fichier que git ne connaît pas encore) et les bases de Docker (ce qu'est une image et un conteneur, et `docker compose up`). **Ce qu'il te faut aujourd'hui :** un terminal et `git` en version 2.28 ou plus récente (vérifie avec `git --version`). Docker, tu t'en sers à partir de la session 2.

Tout au long de la série, tu vas suivre une histoire. C'est un **scénario** : l'entreprise et les personnes sont inventées. Les données du monde réel qui apparaissent dans l'histoire, elles, sont vraies, et chacune indique sa source.

> **Le laboratoire du cours** se trouve dans le dépôt public [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Pour cette session, tu n'en as pas encore besoin : à la session 2, tu le montes toi-même, fichier par fichier, et le dépôt te sert de point de comparaison. Il ne contient aucun mot de passe ; le laboratoire les génère au démarrage.

## Objectifs de cette session

À la fin, tu seras capable de faire ces cinq choses. À côté de chacune figure l'exercice qui la démontre.

| # | À la fin, tu peux… | L'exercice qui le démontre |
|---|---|---|
| 1 | **Repérer** des mots de passe et des clés écrits dans un fichier de configuration, avec `grep` | Exercice 1 |
| 2 | **Nommer** les six manières les plus courantes dont les secrets s'échappent, et **associer** chacune à ce qui l'évite | Exercice 2 |
| 3 | **Démontrer** avec `git` que supprimer un fichier ne supprime pas le mot de passe de l'historique | Exercice 3 |
| 4 | **Protéger** un fichier `.env` pour que `git` ne l'envoie pas, et **le vérifier** | Exercice 4 |
| 5 | **Expliquer** ce que fait Vault, ce qu'il ne fait pas, et sous quelle licence il s'utilise | Exercice 5 |

---

## Scénario (fiction) — Chapitre 1 : vendredi, 18 h 04

Guadalajara. Les bureaux de **Canasta Morada**, une épicerie en ligne : quatorze personnes, deux camionnettes et une appli où l'on commande des tortillas, des œufs et du savon, livrés en une heure.

Valeria a 21 ans et elle est stagiaire depuis trois mois. Aujourd'hui, elle a terminé son premier vrai écran : celui de « mes commandes ». Ça fonctionne. Elle y a passé deux semaines. Elle est fière.

Il est 18 h 04. Elle a des billets pour un concert à 20 h. Elle ouvre le terminal et tape ce qu'elle a tapé cent fois :

```
git add .
git commit -m "pantalla de mis pedidos"
git push
```

Le point après `add` veut dire « tout ». Tout ce qu'il y a dans le dossier. Y compris un fichier appelé `.env`, où l'appli garde sa configuration. Et dans ce fichier, une ligne :

```
DB_PASSWORD=Tamal-Verde-2024
```

C'est le mot de passe de la base de données de Canasta Morada. Celle des commandes, des clients, des adresses.

Un détail de plus : Valeria n'a pas poussé le code dans le dépôt privé de l'entreprise. Elle l'a poussé dans une copie qu'elle a faite sur son compte GitHub personnel, pour la montrer dans son portfolio. Et son compte est **public**.

Elle ferme son ordinateur portable. Elle part au concert.

Personne ne s'en aperçoit.

---

## Chapitre 2 : samedi, 3 h 17 du matin

Le téléphone d'Iván vibre sur la table de chevet. Iván est le seul développeur expérimenté de Canasta Morada ; il y travaille depuis cinq ans. L'alerte dit : **« Serveur de base de données : utilisation du processeur à 98 % »**.

Iván pense à une grosse commande. Un samedi à trois heures du matin, personne ne commande d'épicerie, mais on ne sait jamais. Il se rendort.

À 7 h 40, il ouvre son ordinateur, le café à la main. Le journal de la base de données dit ceci :

```
03:17:02  conexión autorizada: usuario=app_tienda  origen=185.xx.xx.xx
03:17:05  SELECT * FROM clientes
03:21:40  SELECT * FROM pedidos
```

L'utilisateur est `app_tienda`. C'est l'utilisateur de l'appli. Le mot de passe est le bon. Pour la base de données, tout est en ordre : quelqu'un est arrivé avec la bonne clé et a ouvert la porte.

Mais cette adresse d'origine n'appartient à aucun serveur de Canasta Morada.

---

## Chapitre 3 : samedi, 9 h 00. La réunion

Doña Clara, la propriétaire, arrive en survêtement. Il y a Iván, Valeria — qui n'a presque pas dormi et ne sait pas encore que c'est elle — et un ordinateur portable sur la table.

« Qui est entré ? » demande doña Clara.

Iván ne sait pas répondre. Et les raisons pour lesquelles il ne sait pas sont le sujet de cette session.

**Premier indice.** `app_tienda` n'est pas une personne. C'est le mot de passe que se partagent l'appli, le site web, le programme qui envoie les commandes aux camionnettes et la macro Excel avec laquelle la comptabilité sort le rapport du mois. Quatre programmes. Et trois personnes le connaissent. Plus Toño.

« Qui est Toño ?

— Celui qui était là avant moi. Il est parti il y a huit mois.

— Et il le connaît toujours ?

— On ne l'a jamais changé. »

**Deuxième indice.** « Eh bien, changez-le tout de suite », dit doña Clara.

Iván explique : si on change le mot de passe maintenant, les quatre programmes tombent en panne en même temps. Il faut entrer dans chacun, modifier son fichier, le redémarrer. On est samedi et il y a des commandes. Et la macro Excel, personne ne sait où elle l'a écrit.

**Troisième indice.** Valeria demande à voix basse ce qu'il en est des CURP. L'appli stocke la CURP des clients qui paient avec des bons d'achat, et elles sont censées être chiffrées.

« Oui, elles sont chiffrées, dit Iván. La clé est sur le serveur, dans un fichier qui s'appelle `llave.txt`.

— Sur le même serveur que les sauvegardes ? »

Silence.

---

## Chapitre 4 : samedi, 9 h 26

Iván ouvre le dossier des sauvegardes. Chaque nuit, à 2 h 00, le serveur enregistre une copie complète de la base de données.

La sauvegarde de la nuit dernière a été téléchargée à **3 h 21**.

Et le dossier voisin, celui qui contient `llave.txt`, aussi.

Dans cette sauvegarde figurent les noms, les adresses et les CURP de huit mille clients.

*(À suivre à la session 2.)*

---

## Pourquoi c'est important : ce n'est pas exagéré

L'histoire de Canasta Morada est inventée. Ce qui lui arrive, non. Ces cas et ces chiffres sont réels et publics :

- **Chaque année, des millions de secrets apparaissent sur GitHub public.** L'entreprise GitGuardian examine les modifications envoyées sur GitHub public et compte les mots de passe et les clés qu'elle y trouve. Dans son rapport de 2026, elle a compté **28,65 millions de nouveaux secrets** publiés pendant 2025, soit 34 % de plus que l'année précédente. Et le pire : parmi les identifiants qu'elle avait trouvés valides en 2022, **plus de 64 % fonctionnaient encore** lorsqu'elle les a testés à nouveau en janvier 2026. Autrement dit, selon GitGuardian, ces identifiants n'ont jamais été corrigés : le mot de passe divulgué ouvrait encore la porte des années plus tard. Source : [GitGuardian, *The State of Secrets Sprawl 2026*](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/).
- **Un dépôt privé ne te sauve pas.** En 2016, des intrus sont entrés dans le compte GitHub d'ingénieurs d'Uber en utilisant des mots de passe réutilisés issus d'autres fuites. Dans un dépôt **privé**, ils ont trouvé une clé d'accès à Amazon Web Services. Avec elle, ils ont téléchargé les données d'environ 25,6 millions de noms et d'adresses électroniques et d'environ 607 000 permis de conduire. La Commission fédérale du commerce des États-Unis (FTC) l'a documenté : [analyse de l'affaire Uber, 2018](https://www.ftc.gov/system/files/documents/cases/1523054_uber_technologies_revised_analysis.pdf).
- **Un seul lien peut tout ouvrir.** En 2023, l'entreprise de sécurité Wiz a trouvé, dans un dépôt public de chercheurs de Microsoft, un lien contenant une autorisation d'accès à un compte de stockage. L'autorisation n'était pas en lecture seule : elle donnait un **contrôle total**, expirait en 2051 et permettait de voir 38 téraoctets, dont des sauvegardes d'ordinateurs et plus de 30 000 messages internes de Teams. Source : [Wiz, 18 septembre 2023](https://www.wiz.io/blog/38-terabytes-of-private-data-accidentally-exposed-by-microsoft-ai-researchers).

GitGuardian rapporte aussi qu'environ 28 % des incidents qu'elle détecte ne naissent pas dans le code, mais dans des outils comme Slack, Jira ou Confluence. Le mot de passe collé dans le chat « juste pour que tu le copies » compte aussi.

---

## Les six manières dont un secret s'échappe

Avant de voir des solutions, donne un nom à chaque problème. Un **secret** est toute donnée qui donne accès à quelque chose : un mot de passe, une clé de chiffrement, un jeton (token) d'API. Pense à la clé de ta maison : elle n'a pas de valeur en soi, elle en a par la porte qu'elle ouvre.

### 1. Le mot de passe écrit dans le code ou dans un fichier qui est envoyé

C'est ce qu'a fait Valeria. Le fichier `.env` est une habitude très utile : il sépare la configuration du code. Mais si le fichier voyage avec le code, la séparation ne sert à rien. C'est comme coller la clé de la maison avec du ruban adhésif sur la porte, côté intérieur, puis envoyer des photos de la porte.

Et il y a un piège de plus : **dans git, supprimer n'est pas supprimer.** Git garde l'historique de chaque modification. Si tu as envoyé le mot de passe et que tu le retires dans la modification suivante, il reste dans la précédente. Tu le vérifies à l'exercice 3.

### 2. Le `.env` qu'on passe par WhatsApp

« Dis, tu me passes le `.env` ? — Tiens. » Et c'est là qu'il reste : dans la conversation, dans la sauvegarde du téléphone et sur l'ordinateur de celui qui a ouvert WhatsApp Web dans un café. Chaque copie est une porte de plus que personne ne surveille.

### 3. Le même mot de passe pour tout le monde et pour toujours

À Canasta Morada, quatre programmes et quatre personnes utilisent `app_tienda`. C'est comme le cadenas de la réserve d'une école dont tous les enseignants connaissent la combinaison depuis 2019. Si un jour il manque quelque chose, impossible de savoir qui a ouvert.

Et comme le changer casse tout en même temps, personne ne le change. « Pour toujours » n'est pas une décision : c'est ce qui arrive quand changer fait mal.

### 4. Personne ne sait qui l'a utilisé

La base de données a enregistré « `app_tienda` est entré ». Elle n'a pas enregistré « l'appli est entrée », ni « Toño est entré », ni « quelqu'un est entré depuis un autre pays avec le mot de passe volé ». Quand tout le monde utilise la même identité, le journal ne sert pas à grand-chose.

### 5. Celui qui est parti le connaît encore

Toño est parti il y a huit mois, en bons termes. Mais il a emporté dans sa tête le mot de passe de la base de données, celui du serveur de messagerie et celui du compte de paiements. Il n'a rien fait de mal. Personne ne peut non plus le garantir. Et si son vieil ordinateur portable a été vendu sur Marketplace avec un fichier de configuration dedans, ça ne dépend même plus de lui.

### 6. La clé de chiffrement à côté des données

Chiffrer, en bref, c'est mélanger une donnée avec une clé pour que seul celui qui a la clé puisse la lire. Canasta Morada chiffrait bien les CURP. Mais elle a rangé la clé dans `llave.txt`, sur le même serveur que les sauvegardes. C'est comme avoir un coffre-fort et laisser la combinaison sur un post-it collé dessus. Le voleur a emporté les deux d'un seul coup.

---

## Ce qu'il faut

Si tu étais Iván et que tu devais concevoir comment Canasta Morada devrait fonctionner lundi, que demanderais-tu ? Voici la liste que dresse presque n'importe quelle équipe de sécurité. Chaque point s'attaque à un ou plusieurs des six problèmes.

| # | Exigence | S'attaque au problème | Selon doña Clara |
|---|---|---|---|
| R1 | **Stocker les secrets en un seul endroit, chiffrés**, et non éparpillés dans des fichiers | 1, 2 | « Que les clés vivent dans un coffre-fort, pas dans les tiroirs » |
| R2 | **Donner l'accès par identité et par permission** : chaque programme et chaque personne a ses propres identifiants, et ne peut lire que ce qui la concerne | 3, 4 | « Que chacun ait sa clé, et que celle de la cuisine n'ouvre pas le coffre » |
| R3 | **Journal d'audit** : qui a demandé quel secret, quand, et si on le lui a donné | 4 | « Que l'on note qui a ouvert » |
| R4 | **Des identifiants qui expirent tout seuls** | 3, 5 | « Que les clés fondent au bout d'un moment » |
| R5 | **Rotation automatique** : changer les mots de passe sans que personne ait à modifier des fichiers | 3, 5 | « Que changer la serrure n'oblige pas à fermer la boutique » |
| R6 | **Révoquer d'un coup** : si quelque chose fuite, annuler tous les identifiants concernés avec une seule commande | 5 | « Un bouton d'urgence » |
| R7 | **Le chiffrement en tant que service** : les programmes demandent « chiffre-moi ceci » et reçoivent la donnée chiffrée, mais n'ont jamais la clé | 6 | « Que la clé du coffre ne quitte jamais la banque » |

Remarque une chose : aucune de ces exigences ne dit « que les gens fassent plus attention ». Valeria n'est pas négligente ; c'est une personne fatiguée un vendredi à six heures. Une bonne conception ne dépend pas du fait que personne ne se trompe jamais. Elle dépend du fait que, lorsque quelqu'un se trompe, les dégâts soient petits.

---

## Ce qu'est Vault

**HashiCorp Vault** est un programme qui fait exactement cette liste. Il tourne comme un serveur ; les programmes et les personnes lui parlent en HTTP (avec `curl`, par exemple) ou avec sa commande `vault`.

Pense à Vault comme à la **chambre forte d'une banque avec un guichet** :

- Toi, tu n'entres pas dans la chambre forte. Tu fais la queue au guichet et tu demandes.
- La caissière vérifie ta pièce d'identité (ton **token**) et ce qui t'est permis (ta **politique**, ou *policy*).
- Si c'est pour toi, elle te donne ce que tu as demandé. Sinon, elle te dit non : un **403**.
- Si la banque a activé le journal — dans Vault, c'est toi qui l'actives —, tout est consigné.
- Et certaines choses, elle ne te les remet même pas : tu lui donnes ton document, la caissière le scelle dans la chambre forte et te le rend scellé. Le sceau ne quitte jamais la banque. C'est cela, le chiffrement en tant que service.

| Exigence | Comment Vault la couvre | Où tu la pratiques |
|---|---|---|
| R1 Stockage centralisé et chiffré | Moteur **KV** (de *key-value*, clé-valeur) : il stocke des secrets chiffrés ; avec **KV v2**, il conserve en plus les versions | Session 2 |
| R2 Accès par identité et politique | **Tokens** et **politiques** : chaque token ne fait que ce que sa politique permet ; tout le reste est refusé | Session 2 |
| R3 Audit | **Périphériques d'audit** (*audit devices*) : une fois activés, presque chaque requête et chaque réponse sont consignées dans un journal, les valeurs sensibles étant protégées | Session 2 |
| R4 Identifiants qui expirent | **Baux** (*leases*) avec une durée de vie (**TTL**) ; moteur **Database** avec des utilisateurs dynamiques | Session 4 |
| R5 Rotation automatique | Rôles statiques du moteur Database avec `rotation_period` (ils tournent tout seuls à intervalle régulier) ; et `rotate-root` pour changer immédiatement le mot de passe d'administration avec lequel Vault se connecte à la base | Session 4 |
| R6 Révoquer d'un coup | Révocation d'un bail ou de tous ceux qui commencent par un préfixe | Session 4 |
| R7 Chiffrement en tant que service | Moteur **Transit** : il chiffre et déchiffre, fait tourner les clés et ne stocke pas tes données | Session 3 |

Un **moteur** (*secrets engine*) est une partie de Vault spécialisée dans un type de secret, comme les guichets de la banque : un pour les dépôts, un autre pour les chèques. Tu actives ceux dont tu as besoin.

---

## Ce que Vault n'est pas (et une note sur la licence)

**Vault n'est pas un HSM.** Un **HSM** (*hardware security module*) est un appareil physique qui stocke des clés et effectue les opérations de chiffrement à l'intérieur, avec des protections contre les manipulations. Selon le modèle et sa configuration, les clés peuvent être impossibles à extraire et l'appareil peut effacer son contenu si quelqu'un tente de l'ouvrir de force. Les banques les utilisent, par exemple, pour les codes PIN des cartes.

Le moteur Transit de Vault ressemble à cela par sa façon de travailler : tu envoies des données et tu reçois des données chiffrées, et la clé reste dans Vault. La documentation officielle le décrit comme du « chiffrement en tant que service » et précise que Vault ne stocke pas les données que tu lui envoies ([Transit, documentation de Vault](https://developer.hashicorp.com/vault/docs/secrets/transit)). Mais Vault est un logiciel qui tourne sur un serveur, pas du matériel. Et Transit permet, si tu le configures ainsi, de créer des clés exportables ou d'importer tes propres clés ; par défaut, il ne permet pas de les exporter (tu le vérifieras à la session 3).

Ce qui existe : **Vault Enterprise**, la version payante, peut utiliser un vrai HSM pour protéger sa propre clé maîtresse et pour s'ouvrir seul au démarrage, avec des équipements compatibles avec la norme PKCS#11 ([Vault HSM support](https://developer.hashicorp.com/vault/docs/enterprise/hsm)). Dans cette série, nous utilisons la version communautaire, qui n'en dispose pas.

**À propos de la licence.** Pendant des années, Vault a été un logiciel libre sous licence MPL 2.0. Le 10 août 2023, HashiCorp a annoncé que ses nouvelles versions passaient sous la **Business Source License (BSL) 1.1** ([annonce de HashiCorp](https://www.hashicorp.com/blog/hashicorp-adopts-business-source-license)). En bref : tu peux utiliser Vault gratuitement dans ton entreprise, mais il y a des limites si tu veux proposer un produit qui concurrence HashiCorp. En février 2025, IBM a finalisé le rachat de HashiCorp ([communiqué d'IBM](https://newsroom.ibm.com/2025-02-27-ibm-completes-acquisition-of-hashicorp,-creates-comprehensive,-end-to-end-hybrid-cloud-platform)).

En réaction au changement de licence, une partie de la communauté a repris le dernier code ouvert et a poursuivi de son côté : **OpenBao**, qui est aujourd'hui un projet de l'OpenSSF, au sein de la Linux Foundation, sous licence MPL 2.0 ([openbao.org](https://openbao.org/)). On appelle cela un *fork*, une bifurcation : comme une recette de famille qui se divise et dont chaque branche de la famille poursuit la préparation à sa façon. Presque tout ce que tu apprendras dans cette série te servira aussi avec OpenBao ; l'encadré ci-dessous dit ce qui change.

> **Vault et OpenBao : le même coffre-fort, deux propriétaires**
>
> OpenBao est parti du dernier Vault sous licence libre, la 1.14 : la BSL couvre « Vault Version 1.15.0 or later » ([licence de Vault](https://github.com/hashicorp/vault/blob/main/LICENSE)). À partir de là, chacun suit son chemin :
>
> | | HashiCorp Vault | OpenBao |
> |---|---|---|
> | Licence | BSL 1.1 : autorise l'usage interne et en production ; restreint la possibilité de le proposer comme produit concurrent de l'offre payante d'IBM | MPL 2.0, libre ([licence d'OpenBao](https://github.com/openbao/openbao/blob/main/LICENSE)) |
> | Qui s'en occupe | IBM, propriétaire de HashiCorp | La communauté, en tant que projet de l'OpenSSF, au sein de la Linux Foundation ([openbao.org](https://openbao.org/)) |
> | Commande | `vault` | `bao` |
> | Variables | `VAULT_ADDR`, `VAULT_TOKEN` | `BAO_ADDR`, `BAO_TOKEN` ; en leur absence, il lit les `VAULT_` ([commandes](https://openbao.org/docs/commands/)) |
> | Image | `hashicorp/vault` | `openbao/openbao`, sur Docker Hub, Quay et le registre de conteneurs de GitHub ([installation](https://openbao.org/docs/install/)) ; au 20 octobre 2026, la plus récente est la 2.7.1, du 1er octobre ([versions](https://github.com/openbao/openbao/releases)) |
> | Espaces séparés par entreprise (*namespaces*) | Uniquement dans la version payante ([Vault](https://developer.hashicorp.com/vault/docs/enterprise/namespaces)) | Inclus depuis la 2.3, de 2025 ([OpenBao](https://openbao.org/docs/concepts/namespaces/)) |
>
> Chez Hábil, nous avons choisi OpenBao, la version libre, pour chiffrer les documents de nos systèmes : une API compatible, une licence ouverte et aucune dépendance envers un seul fournisseur.
>
> Cette série utilise l'image officielle de HashiCorp Vault 2.2.0, celle avec laquelle chaque commande a été testée. Avec OpenBao, les appels `curl` ne changent pas : les chemins commencent par `/v1/` et le token voyage dans le même en-tête `X-Vault-Token` ([API d'OpenBao](https://openbao.org/docs/api/)). Pour les commandes, on remplace `vault` par `bao`. Mais changer les noms ne suffit pas, pour trois raisons :
>
> - Le laboratoire stocke les données avec `storage "file"`, et OpenBao 2.7 a supprimé cette option ([notes de la 2.7.0](https://github.com/openbao/openbao/blob/main/CHANGELOG.md)) ; on y utilise une autre option, comme le stockage intégré `raft` ([stockage](https://openbao.org/docs/configuration/storage/)).
> - Dans le conteneur, les dossiers sont `/openbao/config`, `/openbao/file` et `/openbao/logs`, et non `/vault/...` ([Dockerfile d'OpenBao](https://github.com/openbao/openbao/blob/main/Dockerfile)).
> - Aujourd'hui, les tokens commencent par `s.`, `b.` ou `r.`, et non par `hvs.` ; OpenBao prévient que ce format peut changer, donc ne construis rien qui dépende du préfixe ([tokens](https://openbao.org/docs/concepts/tokens/)) : la recherche de `hvs.` que tu verras plus loin ne les trouverait pas.
>
> Nous n'avons pas exécuté le laboratoire avec OpenBao.

---

👉 **Si tu viens de la gestion :** les six problèmes de cette session sont des problèmes de contrôle interne, pas de programmation. « Le même mot de passe pour tout le monde », c'est la même chose que « tout le monde signe avec le même cachet » : si un chèque suspect sort, personne à qui poser la question. « Celui qui est parti le connaît encore », c'est un départ de personnel resté inachevé : tu lui as retiré son badge du bâtiment, mais pas la clé de la caisse. Quand on auditera les systèmes de ton entreprise, les questions du tableau des exigences (qui a accès ? est-ce consigné ? est-ce que ça expire ? peut-on l'annuler d'un coup ?) sont les mêmes que celles que tu poserais sur les signatures d'un compte bancaire.

---

## Exercices de la session 1

Les solutions se trouvent à la fin de ce numéro. Chaque exercice t'indique comment vérifier toi-même si tu as réussi.

**Exercice 1 — Chasse aux secrets avec `grep`.** Crée un fichier `config-tienda.yaml` avec ce contenu (toutes les valeurs sont inventées) :

```yaml
# Configuración de la app de la tienda
app:
  nombre: tienda-en-linea
  puerto: 8080
base_de_datos:
  servidor: db.ejemplo.local
  usuario: app_tienda
  password: Tamal-Verde-2024
pagos:
  url: https://pagos.ejemplo.local/v1
  api_key: pk_prueba_51HcXyZ-esto-es-inventado
correo:
  servidor: smtp.ejemplo.local
  conexion: smtp://avisos:Churro99@smtp.ejemplo.local:587
cifrado:
  llave_aes: MDEyMzQ1Njc4OUFCQ0RFRg==
reportes:
  hora: "06:00"
  clave_sms: Elote-2023
```

D'abord, à l'œil : combien de secrets vois-tu ? Écris-le sur papier. Ensuite, lance cette recherche. `grep` cherche du texte dans des fichiers ; `-n` affiche le numéro de ligne, `-i` ignore la casse et `-E` permet d'utiliser `|` pour dire « ceci ou cela » :

```
grep -niE 'pass|key|llave|secret|token|://[^/ ]+:[^@ ]+@' config-tienda.yaml
```

Le dernier morceau, `://[^/ ]+:[^@ ]+@`, cherche les adresses qui contiennent un utilisateur et un mot de passe, comme `smtp://usuario:contraseña@servidor`.

a) Combien de lignes `grep` a-t-il trouvées ? Cela correspond-il à ton décompte à l'œil ?
b) Il y a un secret que `grep` n'a pas trouvé. Lequel ? Modifie le motif pour qu'il le trouve aussi.

**Comment vérifier :** avec le motif d'origine, `grep -c` (qui compte les lignes au lieu de les afficher) doit donner `4`. Avec ton motif corrigé, il doit donner `5`.

**Exercice 2 — Associe.** Pour chaque situation, écris de quel problème parmi les six il s'agit et quelle exigence (R1 à R7) l'évite. Il peut y avoir plus d'une exigence.

a) Un stagiaire termine son service. Trois mois plus tard, son utilisateur de la base de données fonctionne toujours.
b) La clé pour déchiffrer les cartes des clients se trouve dans une variable du programme même qui les stocke.
c) Quelqu'un a supprimé une table. Le journal dit que c'était `admin`, et l'utilisateur `admin` est utilisé par cinq personnes.
d) Pour « aller vite », le chef colle le mot de passe du serveur dans le canal général de Slack.

**Comment vérifier :** compare avec les solutions. Si tu as indiqué une autre exigence quelque part, vérifie si elle l'évite vraiment ou si elle ne fait que le rendre moins grave.

**Exercice 3 — Dans git, supprimer n'est pas supprimer.** Dans un dossier nouveau et vide, lance ceci ligne par ligne. Les deux lignes de `git config` disent à git qui tu es ; sans elles, sur un ordinateur tout neuf, `git commit` refuse de fonctionner. Elles ne valent que pour ce dossier :

```
git init -b main .
git config user.name "Estudiante"
git config user.email "estudiante@ejemplo.invalid"
echo "DB_PASSWORD=Tamal-Verde-2024" > .env
echo 'print("hola")' > app.py
git add .
git commit -m "primera version"
git rm .env
git commit -m "quito el .env"
```

Le fichier n'est plus dans le dossier. Maintenant, cherche le mot de passe dans l'historique. `-S` cherche les modifications où un texte est apparu ou a disparu, et `-p` affiche la modification complète :

```
git log -p -S Tamal-Verde-2024 --oneline
```

**Comment vérifier :** la sortie contient le correctif complet de chaque modification ; parmi ses lignes, tu dois voir les deux modifications, celle qui a ajouté la ligne (`+DB_PASSWORD=...`) et celle qui l'a retirée (`-DB_PASSWORD=...`). Si quelqu'un clone ton dépôt, il a les deux. Écris en une phrase ce que tu devrais faire de ce mot de passe, en plus de le supprimer.

**Exercice 4 — Que git ne la voie même pas.** Dans le même dossier que l'exercice 3, recrée un `.env` avec un autre mot de passe et regarde ce que dit git :

```
echo "DB_PASSWORD=Pozole-Rojo-2025" > .env
git status --short
```

Maintenant, fais en sorte que git l'ignore. Crée un fichier `.gitignore` avec une seule ligne, `.env`, et relance `git status --short`.

**Comment vérifier :** avant de créer `.gitignore`, git affiche `?? .env` (un nouveau fichier qui pourrait être envoyé). Ensuite, `.env` n'apparaît plus ; seulement `?? .gitignore`. Pour être sûr de la règle qui l'ignore, lance `git check-ignore -v .env` ; il doit répondre avec le nom du fichier et la ligne de la règle.

**Exercice 5 — Explique-le à doña Clara.** Écris un paragraphe de 90 mots au maximum, sans mots techniques non expliqués, qui répond à ceci : qu'est-ce que Vault ? Quel problème de Canasta Morada résoudrait-il en premier ? Est-ce la même chose qu'un HSM ? Est-ce un logiciel libre ?

**Comment vérifier :** d'abord, auto-évalue-toi : ton paragraphe doit dire (1) que Vault stocke les secrets en un seul endroit et contrôle qui les demande ; (2) quel problème de Canasta Morada tu attaquerais en premier ; (3) que ce n'est pas un HSM ; et (4) que les versions actuelles de Vault utilisent la licence BSL 1.1, qui peut s'utiliser sans frais mais n'est pas un logiciel libre, et qu'OpenBao utilise la MPL 2.0. Ensuite, fais-le lire à quelqu'un qui n'étudie pas l'informatique : s'il peut répondre aux quatre questions avec ses propres mots, c'est bon.

---

## Erreurs courantes (et comment les repérer)

| Erreur | À quoi cela ressemble | Comment la repérer | Que faire |
|---|---|---|---|
| Croire que supprimer le fichier règle la fuite | « Je l'ai retiré du dépôt, c'est bon » | `git log -p -S <texte>` le trouve encore | Considère le mot de passe comme grillé : **change-le**. Nettoyer l'historique aide, mais les copies déjà téléchargées ne s'effacent pas |
| Ajouter `.env` au `.gitignore` après l'avoir envoyé | `git status` ne l'affiche plus, mais il est toujours dans le dépôt | `git ls-files` le liste toujours | `.gitignore` n'affecte que les nouveaux fichiers. Retire-le de l'index avec `git rm --cached .env` et change le mot de passe |
| Croire que `grep` a tout trouvé | Le décompte est bon… pour les noms qui te sont venus à l'esprit | L'exercice 1 : `clave_sms` lui échappe | Utilise `grep` pour une vérification rapide, pas comme une garantie. Il existe des outils conçus pour cela, qui cherchent des centaines de formats |
| Penser qu'un dépôt privé est sûr | « Personne ne le voit, il est privé » | L'affaire Uber : le dépôt était privé | Privé réduit le risque, il ne l'élimine pas. Les secrets ne vont pas dans le code, point |
| Partager le `.env` par chat « juste cette fois » | Le fichier se retrouve sur trois téléphones et dans le cloud | Cherche le mot `PASSWORD` dans ta messagerie | Chaque copie est une porte de plus. À partir de la session 2, chacun demande ce qui le concerne à Vault |

---

## Révision pour la prochaine session

La session 2 commence par ces trois questions. Réponds-y sans regarder la leçon :

1. Nomme quatre des six manières dont un secret s'échappe.
2. Pourquoi changer le mot de passe après une fuite est-il obligatoire, même si tu l'as déjà supprimé de git ?
3. En quoi le moteur Transit de Vault ressemble-t-il à un HSM, et en quoi en diffère-t-il ?

🔁 **La semaine prochaine :** Iván décide de construire le coffre-fort. Tu démarres Vault avec Docker Compose, tu l'ouvres avec trois clés sur cinq, tu stockes tes premiers secrets avec `curl` et tu vois comment Vault dit non à celui qui demande ce qui ne le concerne pas. Et dans le journal d'audit apparaît quelque chose que personne n'attendait.

---

## Solutions (ne les regarde pas avant d'avoir essayé)

**Exercice 1.** Avec le motif d'origine, la sortie est :

```
8:  password: Tamal-Verde-2024
11:  api_key: pk_prueba_51HcXyZ-esto-es-inventado
14:  conexion: smtp://avisos:Churro99@smtp.ejemplo.local:587
16:  llave_aes: MDEyMzQ1Njc4OUFCQ0RFRg==
```

a) Quatre lignes. Si, à l'œil, tu en as compté cinq, tu avais raison : il y a cinq secrets.

b) `clave_sms: Elote-2023` lui échappe, parce que « clave » ne figurait pas dans le motif. Ajoute-le :

```
grep -niE 'pass|key|llave|clave|secret|token|://[^/ ]+:[^@ ]+@' config-tienda.yaml
```

Maintenant, la ligne `19:  clave_sms: Elote-2023` apparaît aussi. La leçon n'est pas « ajoute plus de mots » ; c'est qu'une recherche de texte ne trouve que ce que tu as pensé à chercher.

**Exercice 2.**

a) Problème 5 (celui qui est parti le connaît encore). Ils sont évités par R4 (identifiants qui expirent) et R6 (révoquer d'un coup). R2 aide, car avec des identifiants par personne, tu sais lequel annuler.

b) Problème 6 (la clé à côté des données). Il est évité par R7 (chiffrement en tant que service) : le programme demande de chiffrer et de déchiffrer, mais n'a jamais la clé.

c) Problèmes 3 et 4 (le même pour tous ; personne ne sait qui). Ils sont évités par R2 (identité propre pour chacun) et R3 (journal d'audit).

d) Problème 2 (le secret qui voyage par chat). Il est évité par R1 (un seul endroit) et R2 (chacun demande ce qui le concerne). Et comme il a déjà fuité, il faut R5 : le changer.

**Exercice 3.** La sortie complète inclut, pour chaque modification, les en-têtes du correctif (`diff --git ...`, `index ...`). Les lignes qui comptent sont celles-ci :

```
cbe77a9 quito el .env
-DB_PASSWORD=Tamal-Verde-2024
250264c primera version
+DB_PASSWORD=Tamal-Verde-2024
```

Tes identifiants de modification (les sept caractères du début) seront différents ; c'est normal. La phrase que nous cherchions : **il faut changer le mot de passe dans la base de données**, parce que quiconque a cloné le dépôt l'a.

**Exercice 4.** Avant le `.gitignore` :

```
?? .env
```

Après :

```
?? .gitignore
```

Et `git check-ignore -v .env` répond :

```
.gitignore:1:.env	.env
```

Cela veut dire : « je l'ignore à cause de la ligne 1 du fichier `.gitignore`, qui dit `.env` ». À la session 2, tu verras un script de démarrage qui refuse de créer des mots de passe si cette règle n'existe pas.

**Exercice 5.** Une réponse possible : « Vault est un coffre-fort avec guichet pour les mots de passe et les clés des systèmes. Chaque programme et chaque personne a sa propre pièce d'identité et ne reçoit que ce qui la concerne, et tout est consigné. Ce que je résoudrais en premier à Canasta Morada, c'est que quatre programmes et quatre personnes partagent le même mot de passe. Ce n'est pas un HSM : un HSM est un appareil physique ; Vault est un programme, même s'il peut chiffrer sans remettre la clé. On peut l'utiliser gratuitement, avec une licence qui impose des limites à qui voudrait concurrencer son éditeur ; il existe une version sœur sous licence libre, qui s'appelle OpenBao. »

---

## La suite

À la session 2, tu utilises Docker Compose. Avant d'y arriver, vérifie que tu as ces outils avec `docker compose version`, `curl --version`, `jq --version` et `openssl version`. S'il te manque `jq`, qui sert à lire les réponses au format JSON, installe-le ainsi : sous Debian ou Ubuntu, `sudo apt-get install jq` ; sous Fedora, `sudo dnf install jq` ; sous Arch, `sudo pacman -S jq` ; sous macOS avec Homebrew installé, `brew install jq`. Il te faut `jq` 1.6 ou plus récent.

---

*J'écris à partir de ce que nous voyons tous les jours chez Hábil, où nous construisons des systèmes pour la banque, l'assurance et les entreprises au Mexique. Si, dans ton travail ou dans l'entreprise de ta famille, vous rencontrez un problème de ce genre, parlons-en : [habil.mx](https://www.habil.mx/fr/)*
