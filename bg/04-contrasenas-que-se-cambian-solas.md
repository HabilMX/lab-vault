# Vault от нулата (4): пароли, които се сменят сами

*Потребители на база данни, които се раждат, когато ги поискаш, и умират след две минути, пароли, които се ротират всяка минута, без никой да редактира файл, и програма на Python, която се свързва с PostgreSQL, без да знае нито една парола. И краят на загадката от 3:17.*

*Vault от нулата · сесия 4 от 4*

## Преговор на сесия 3

Отговори, без да гледаш. Отговорите са в решенията.

1. Какво означават трите части на `vault:v2:SmfKDK1u...`?
2. Ротирал си ключа. Какво става с данните, които вече са били шифровани, и коя операция ги качва към новата версия, без никой да види стойността?
3. Защо един token, който може само да шифрова, е полезен за формуляр за регистрация?

> **Лабораторията на тази сесия** е в публичното хранилище [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Първо я изгради сам; хранилището е за сравнение, когато нещо не ти излезе същото. Не съдържа нито една парола: лабораторията ги генерира при стартиране.

## Цели на тази сесия

| # | Накрая можеш да… | Доказва се с |
|---|---|---|
| 1 | **Настроиш** механизма Database на Vault със специален потребител, без да ползваш суперпотребителя | Стъпки 2 и 3 |
| 2 | **Поискаш** динамични идентификационни данни, **влезеш** с `psql` и **провериш**, че спират да работят при изтичане или при отнемане | Упражнения 16, 17 и 19 |
| 3 | **Поставиш** съществуващ потребител под автоматична ротация и **докажеш**, че старата парола вече не влиза | Упражнение 18 |
| 4 | **Създадеш** динамични идентификационни данни само за четене в MariaDB с клиента `mariadb`, провериш, че не могат да променят данни, и ги отнемеш | Стъпка 10 |
| 5 | **Изпълниш и промениш** скрипт на Python, който иска идентификационните си данни от Vault, пита PostgreSQL и не пази никаква парола за база данни | Стъпка 12 и упражнение 20 |

---

## Сценарий (измислица) — Глава 9: вторник, 9:00

Иван набира номер, който не е набирал от осем месеца.

— Тоньо? Иван е, от Canasta Morada. Слушай, един странен въпрос. Говори ли ти нещо сървър на име TR-REPORTES?

Мълчание. После смях.

— Не думай! Още ли е включен?

Тоньо разказва без свян. Преди две години и половина счетоводството поискало седмичен отчет за клиентите, които плащат с ваучери, с тяхното CURP, за да съгласува данните с фирмата за ваучерите. Базата данни била много натоварена през деня, затова Тоньо наел евтин сървър в облака, с картата на фирмата, и му сложил една програма:

- Всяка събота в 3:17 се свързвала с базата данни с паролата на `app_tienda`.
- Теглела резервното копие от нощта и `llave.txt`, за да дешифрира CURP.
- Сглобявала Excel файл и го пращала на имейла `reportes@`.

— А като си тръгнах, забравих да ви кажа. Извинявай.

Росио проверява: пощенската кутия `reportes@` има сто и седемнайсет непрочетени имейла. Никой не я е гледал, откакто предишният шеф на счетоводството си тръгнал.

Не е имало никакъв крадец.

Имало е нещо по-лошо: отворена врата, за чието съществуване никой не е знаел. Сто и седемнайсет копия на осем хиляди CURP, с ключа до тях, на сървър, който никой не е контролирал, в друга държава, плащан всеки месец с картата на фирмата.

А без журнал по самоличност и без идентификационни данни, които изтичат, било невъзможно да се различи от атака.

---

## Глава 10: събота, 3:17. Един месец по-късно

Сървърът TR-REPORTES вече го няма; Иван го изтри заедно с Тоньо по видеоразговор, като гледаха заедно всяка папка.

Отчетът за ваучерите сега го прави нова програма, вътре в сървърите на Canasta Morada. В 3:17 тя иска от Vault идентификационни данни за базата данни. Vault създава потребител, който секунда по-рано не е съществувал, с право само за четене и с дата на изтичане. Програмата работи четири минути. В 3:21 потребителят вече не съществува.

Паролата на базата данни, с която Vault създава тези потребители, никой не я знае: нито Иван, нито доня Клара. Vault я смени още първия ден.

Телефонът на Иван не вибрира.

Валерия пише доклада за инцидента. В последния ред слага: *„Никога няма да узнаем дали някой е видял публичното хранилище през онези часове. Затова сменихме паролата. Следващия път, когато някой качи `.env` по погрешка, там няма да е паролата на приложението, нито тази на Vault. Въпреки това онова, което съдържа този файл — като паролите за администриране — трябва да се смени незабавно.“*

*(Край на сценария.)*

---

## Защо е важно

В сесии 2 и 3 тайните вече не живееха във файлове, но си оставаха **едни и същи с месеци**. Ако някой прочетеше паролата на `app_tienda` във Vault, тя му вършеше работа, докато някой не я смени на ръка.

Днес правиш последната стъпка: **пароли, които не съществуват, докато не ги поискаш, и които умират сами**. Това е разликата между ключа от дома ти и пропуска за посетител на офис сграда. Ключът служи с години. Пропускът ти го дават на рецепцията на твое име, отваря само етажа, към който отиваш, а в 6 вечерта спира да работи. Ако го изгубиш в асансьора, никого не го е грижа.

## Идеите на днес

**Динамични идентификационни данни.** Потребител на база данни, който Vault създава в момента, в който го поискаш, със случайна парола, и който изтрива, когато изтече. Всяка програма, и всеки път, когато поиска, получава различен. Ако изтече, върши работа минути.

**Lease и TTL.** Всички динамични идентификационни данни идват с lease (договор за ползване с краен срок). **TTL** (*time to live*, време на живот) е колко трае. Като паркинга на мола: билетът ти отбелязва часа на влизане и изтича; ако искаш повече време, плащаш пак (подновяваш) до някакъв максимум.

**Отнемане (revoke).** Анулиране на lease преди срока. Vault изтрива потребителя от базата данни в същия момент.

**Статична роля с ротация.** Има потребители, които не можеш да подмениш с нов всеки път, защото други системи ги познават по име. За тях Vault запазва потребителя и му **сменя паролата** през определен период, с `rotation_period`. Който има нужда от нея, я иска от Vault и винаги получава действащата ([Database secrets engine](https://developer.hashicorp.com/vault/docs/secrets/databases)).

**Идентификационните данни на Vault в базата данни.** За да създава и изтрива потребители, на Vault му е нужен собствен потребител в базата данни. Документацията предупреждава, че ако поискаш от Vault да ротира тази парола с `rotate-root`, след това **никой** няма да я знае, и препоръчва да се създаде специален потребител за Vault вместо да се ползва суперпотребителят ([API на механизма Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). Това правим: потребител `vault_admin` с точно необходимите права, а не `postgres`, който може всичко.

---

## Стъпка 1 — Подготви терминала

Лабораторията работи, печатът е отворен, token-ът е експортиран и променливите на PostgreSQL са заредени от `.env`:

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

Обърни внимание, че този път **не** експортираме `PGUSER` или `PGPASSWORD`: днес ще влизаш в PostgreSQL с няколко различни потребители и всяка команда ще казва кой.

Изходите в този урок са реални, но идват от независими изпълнения; затова часовете, имената на потребителите и номерата на версиите (като `vault:v3:`, което зависи от това колко пъти си ротирал ключа в сесия 3) не образуват една последователност. Твоите ще са различни.

## Стъпка 2 — Потребител за Vault и един стар за ротация

Създай в PostgreSQL двама потребители, със случайно генерирана начална парола, която се записва в `secretos-locales/` (git я пренебрегва):

- `vault_admin`: онзи, който ще ползва Vault. Може да създава потребители (`CREATEROLE`) и да дава право за четене върху таблиците (`WITH GRANT OPTION`). Не е суперпотребител.
- `reportes`: потребител „от край време“, като онзи, който ползват отчетите. Ще го поставиш под автоматична ротация.

Всеки получава **собствена** начална парола: ако споделяха една и съща, който се докопа до тази на `reportes`, щеше да влезе като `vault_admin`, който може да създава потребители.

**Контролна точка преди повтаряне.** Тази стъпка очаква нова лаборатория. Ако я повториш, ще запишеш нови пароли във файловете на `secretos-locales/`, които вече не съвпадат с онези, които има PostgreSQL. Ако видиш `role already exists` или че механизмът `database/` вече съществува, не генерирай отново началните файлове: провери състоянието и направи само стъпките, които липсват.

| Ако видиш | Значи | Какво да направиш |
|---|---|---|
| `CREATE ROLE` или `HTTP 204` | Напреднал си добре | Продължи |
| `role "vault_admin" already exists` | Стъпка 2 вече е минала, изцяло или частично | Не генерирай наново началните файлове |
| `path is already in use` | Механизмът Database вече е монтиран | Прескочи към четене или настройка на връзката (стъпка 3) |

`psql -v nombre=...` дефинира променлива, която вътре се ползва като `:'nombre'`. Така паролата не остава буквално в командата, нито в историята ти. `psql` я замества, преди да изпрати SQL към PostgreSQL, така че паролата все пак пътува вътре в израза; затова извън лабораторията се ползва TLS и се избягва записването на изрази, които съдържат пароли:

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

Последният ред дава на `vault_admin` право да администрира `reportes`, което му трябва, за да му смени паролата. От PostgreSQL 16 нататък потребител с `CREATEROLE` може да променя само потребителите, които е създал или които са му възложени по този начин.

## Стъпка 3 — Свързване на Vault с PostgreSQL

Включи механизма Database:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/database -d '{"type": "database"}'
HTTP 204
```

Сега връзката. Паролата на `vault_admin` я чете `jq` от файла с `--arg`: не я пишеш ти, не се появява в историята ти. В `connection_url` `{{username}}` и `{{password}}` ги попълва Vault, а сървърът се казва `postgres`, защото Vault го търси по име вътре в мрежата на Docker Compose, а не по `127.0.0.1`. `allowed_roles` казва кои роли могат да ползват тази връзка:

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

Vault провери връзката, преди да я запази (`verify_connection` е включено по подразбиране); ако паролата беше грешна, тук щеше да ти каже. Прочети настройката:

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

Паролата не се появява. След като Vault я има, не я връща дори на root token-а.

## Стъпка 4 — Роля за динамични идентификационни данни

**Ролята** е рецептата за създаване на потребител. Запази я в `roles/lector-postgres.json`. Този файл, `politicas/app-python.hcl` и `python/clientes.py` вече са в папката на лабораторията; ако предпочиташ да ги напишеш сам, създай папките с `mkdir -p roles politicas python`, отвори файла в редактора си, постави целия блок, без да го променяш, и го запази, преди да изпълниш следващата команда:

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

- `creation_statements`: SQL, който Vault изпълнява при създаването на потребителя. `VALID UNTIL '{{expiration}}'` кара самия PostgreSQL да отхвърли паролата при изтичане, дори Vault да се забави с изтриването. Това е примерът от документацията ([PostgreSQL](https://developer.hashicorp.com/vault/docs/secrets/databases/postgresql)).
- `revocation_statements`: SQL за изтриването му. Защо го пишем на ръка, ще видиш в стъпка 6, с истинска грешка.
- `default_ttl` от 2 минути, за да видиш изтичането, без да чакаш; в реалния живот обикновено са минути или часове. `max_ttl`: дори да подновяваш, никога повече от 10.

Качи го. `-d @archivo` казва на `curl` да прати съдържанието на файла:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/roles/lector -d @roles/lector-postgres.json
HTTP 204
```

## Стъпка 5 — Поискай идентификационни данни и влез

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

Потребител, който секунда по-рано не е съществувал. Името носи кой го е поискал (`root`), ролята (`lector`), случайно парче и часа във формат Unix. В тази лаборатория `root` не е човек: това е просто token за администриране. В продукция не се дава на хора, нито на приложения; всеки човек или програма влиза със собствена самоличност (например OIDC, AppRole или Kubernetes), за да може името на временния потребител наистина да казва кой го е поискал. Влез с него:

```
$ export PGUSER=$(jq -r .data.username secretos-locales/creds-lector.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-lector.json)
$ psql -c "SELECT current_user, nombre, left(curp, 9) FROM clientes;"
                 current_user                  | nombre |   left
-----------------------------------------------+--------+-----------
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | Pepe   | vault:v3:
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | María  | vault:v3:
(2 rows)
```

Работи, и обърни внимание: дори със собствен потребител CURP си остават шифровани. Този четец може да види таблицата, но не и CURP; за това би му трябвало допълнително право в Transit. Опитай да изтриеш:

```
$ psql -c "DELETE FROM clientes;"
ERROR:  permission denied for table clientes
```

Само за четене, както казва ролята. А от суперпотребителя можеш да видиш новия потребител с датата му на изтичане:

```
$ PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -c "SELECT rolname, rolvaliduntil FROM pg_roles WHERE rolname LIKE 'v-%';"
                    rolname                    |     rolvaliduntil
-----------------------------------------------+------------------------
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | 2026-10-18 14:52:54+00
(1 row)
```

## Стъпка 6 — Отнемане… и истинска грешка

**Бележка за четене.** Първият блок възпроизвежда грешка от предишен опит. Не изпълнявай командите, които ползват `secretos-locales/creds-lector-2.json`: този файл не се създава в сегашния ход. В твоята лаборатория ролята от стъпка 4 вече носи `revocation_statements`; правилното отнемане го упражняваш ти в упражнение 17, с `creds-16.json`.

Когато за първи път изпробвахме този урок, ролята **нямаше** `revocation_statements`. Поискахме втори набор идентификационни данни и го отнехме преди срока със `sys/leases/revoke`:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-lector-2.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
{"errors":["failed to revoke entry: resp: (*logical.Response)(nil) err: could not perform all revocation statements: ERROR: permission denied for sequence clientes_id_seq (SQLSTATE 42501)"]}
```

Код 400. Без `revocation_statements` Vault ползва SQL за изтриване по подразбиране на добавката за PostgreSQL, която се опитва да отнеме от потребителя правата върху **всичко** в схемата `public`, включително върху последователностите (броячите, които генерират `id`). Нашият `vault_admin`, с точно необходимите права, няма власт над последователността `clientes_id_seq` и PostgreSQL каза „не“. Временният потребител остана наполовина: без права върху таблицата, но неизтрит.

Добра грешка е: появява се **защото** не дадохме суперпотребителя на Vault. Правилното решение не е да му дадем повече власт, а да му кажем точно какво да прави. Затова ролята от стъпка 4 носи своите `revocation_statements`: да вземат онова, което е дадено, и да изтрият потребителя. С поправената роля, качена отново, същото отнемане работи:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-lector-2.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
HTTP 204
$ PGUSER=$(jq -r .data.username secretos-locales/creds-lector-2.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-lector-2.json) psql -At -c "SELECT count(*) FROM clientes;"
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-QyRyJ1vdjmrPY6U0KXl2-1792335063"
```

Потребителят вече не съществува. Ако си копирал ролята от стъпка 4 цялата, първото ти отнемане излиза вече както трябва.

`"sync": true` е важно: по подразбиране Vault само **слага на опашка** отнемането и отговаря `204` веднага, без да чака базата данни да изтрие потребителя. Със `sync` изчаква да приключи и така проверката ти дали можеш да влезеш веднага след това не зависи от късмета ([sys/leases](https://developer.hashicorp.com/vault/api-docs/system/leases)).

## Стъпка 7 — Изчакване да изтече

Сега първите идентификационни данни, тези от стъпка 5. Не прави нищо: изчакай да минат двете им минути. Vault ги отнема сам и го записва в своя запис (`docker compose logs vault`):

```
2026-10-18T14:52:49.642Z [INFO]  expiration: revoked lease: lease_id=database/creds/lector/rOpuliUuxFqc2UbdHMofQV8S
```

Опитай да влезеш:

```
$ date -u +%T; psql -At -c "SELECT count(*) FROM clientes;"
14:53:32
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049"
```

Никой не ги е отнел на ръка. Никой не е редактирал файл. Умряха сами. Това е онова, което би спасило Canasta Morada: паролата на скрипта на Тоньо би спряла да работи само две минути след старта още в първата събота.

## Стъпка 8 — Автоматична ротация на съществуващ потребител

`reportes` съществува отпреди и други системи го познават по име. Провери, че днес влиза с началната парола:

```
$ PGUSER=reportes PGPASSWORD=$(cat secretos-locales/reportes_inicial.txt) psql -At -c "SELECT current_user;"
reportes
```

Постави го под **статична роля**, която ротира всяка минута (минимумът, който API приема, е 5 секунди; една минута е, за да го видиш, без да заспиш):

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-roles/reportes \
    -d '{"db_name": "postgres", "username": "reportes", "rotation_period": "1m"}'
HTTP 204
```

Документацията обяснява, че Vault **ротира паролата при създаване на статичната роля**, защото трябва да я знае ([API на механизма Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). Така че началната вече е умряла:

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

Който има нужда да влезе като `reportes`, иска от Vault действащата парола в момента:

```
$ PGUSER=reportes PGPASSWORD=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password) \
    psql -At -c "SELECT current_user, count(*) FROM clientes GROUP BY 1;"
reportes|2
```

Изчакай две-три минути и питай отново. `last_vault_rotation` е напреднало само, а журналът на Vault го потвърждава:

```
2026-10-18T14:52:59.517Z [INFO]  secrets.database.database_4731c3d7: successfully rotated static role: name=reportes ttl=60
```

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -c ".data | {password: (.password[0:6] + \"...\"), last_vault_rotation, ttl}"
{"password":"OH0KOU...","last_vault_rotation":"2026-10-18T14:53:59.530969477Z","ttl":11}
```

А ако не искаш да чакаш, ротираш ти с `rotate-role`. Друга нова парола; тази от преди малко вече не влиза (проверяваш го в упражнение 18).

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-role/reportes
HTTP 204
```

Ако вместо „всяка минута“ ти трябва „всяка неделя в 4 сутринта“, има `rotation_schedule`, във формат тип cron с пет полета; не може да се ползва заедно с `rotation_period`. Vault го тълкува в **UTC**, а не по часа на твоя град: за 4:00 сутринта в неделя в Мексико (UTC-6) се пише `0 10 * * SUN`; нагласи сметката за твоята часова зона ([API на механизма Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). В този урок не го изпробвахме.

## Стъпка 9 — Никой да не знае паролата на Vault: `rotate-root`

Началната парола на `vault_admin` е в `secretos-locales/vault_admin_inicial.txt`. Днес работи:

```
$ PGUSER=vault_admin PGPASSWORD=$(cat secretos-locales/vault_admin_inicial.txt) psql -At -c "SELECT current_user;"
vault_admin
```

Поискай от Vault да я смени с такава, която знае само той:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-root/postgres
HTTP 204
$ PGUSER=vault_admin PGPASSWORD=$(cat secretos-locales/vault_admin_inicial.txt) psql -At -c "SELECT current_user;"
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "vault_admin"
```

Файлът вече е боклук. А Vault продължава да работи, защото той знае новата:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector | jq -c "{username: .data.username, lease_duration}"
{"username":"v-root-lector-R3rwerQPR0yvfCxuAxYI-1792335221","lease_duration":120}
```

Сега никой човек не знае паролата, с която се създават потребителите на базата данни. Ако някой качи по погрешка конфигурационен файл, там вече няма тази на `vault_admin`. Внимавай с онова, което остава: `.env` още пази паролите за администриране на PostgreSQL и MariaDB на лабораторията, а `rotate-root` не ги сменя. В реалния живот и тези не бива да живеят във файл.

## Стъпка 10 — Същото с MariaDB

MariaDB също работи от сесия 2. Паролата ѝ за `root` е в `.env`. Клиентът `mariadb` чете паролата от променливата `MYSQL_PWD`, така че и нея не я пишеш в командата. Създай таблица с продукти и потребителя `vault_admin` на MariaDB:

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

Това предупреждение го дава новият клиент на MariaDB, когато се свързва, без да валидира самоличността на сървъра (TLS); в лабораторията няма значение. Ако ти пречи, добави `--skip-ssl-verify-server-cert`.

За MariaDB се ползва добавката `mysql-database-plugin`; документацията на Vault покрива MySQL и MariaDB на една и съща страница ([MySQL/MariaDB](https://developer.hashicorp.com/vault/docs/secrets/databases/mysql-maria)). Обърни внимание, че адресът има друга форма:

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

Ролята, в `roles/lector-mariadb.json`:

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

Тук не се наложи да пишем `revocation_statements`: изтриването по подразбиране на добавката за MySQL проработи с тези права. Влез, прочети и опитай да промениш цени:

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

Отнеми и опитай отново:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-maria.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
HTTP 204
$ MYSQL_PWD=$(jq -r .data.password secretos-locales/creds-maria.json) mariadb -h 127.0.0.1 -P $PUERTO_MARIADB \
    -u $(jq -r .data.username secretos-locales/creds-maria.json) tienda -e "SELECT 1;"
ERROR 1045 (28000): Access denied for user 'v-root-lector-mar-24LwvJevZDrYbE'@'172.21.0.1' (using password: YES)
```

(Адресът `172.21.0.1` е на твоята машина, погледната от мрежата на Docker; твоят може да е друг.) И коренът:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-root/mariadb
HTTP 204
$ MYSQL_PWD=$(cat secretos-locales/vault_admin_maria_inicial.txt) mariadb --skip-ssl-verify-server-cert -h 127.0.0.1 -P $PUERTO_MARIADB -u vault_admin -e "SELECT CURRENT_USER();"
ERROR 1045 (28000): Access denied for user 'vault_admin'@'172.21.0.1' (using password: YES)
```

## Стъпка 11 — Бутонът за паника

Помниш ли изискване R6 от сесия 1, отнемане наведнъж? Ако подозираш, че всички идентификационни данни на една роля са изтекли, ги анулираш заедно по префикс. С командата `vault`:

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

Внимавай с онова, което този изход показа: „queued“ значи, че Vault е приел заповедта и я е сложил на опашка, а празният списък казва само, че вече няма lease. Онова, което наистина има значение, е ефектът в PostgreSQL. Преброй временните потребители преди отнемането и няколко секунди след него:

```
PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -At -c "SELECT count(*) FROM pg_roles WHERE rolname LIKE 'v-root-lector-%';"
```

Преди отнемането трябва да даде повече от `0` (по един за всеки още жив набор от данни); след това — `0`. Ако още не е `0`, изчакай малко и повтори: опашката работи във фонов режим. Този брой потвърждава, че потребителите вече не съществуват.

Четири lease, анулирани с една заповед. Отнемането по префикс изисква специално право (`sudo`) на маршрута ([sys/leases](https://developer.hashicorp.com/vault/api-docs/system/leases)); затова тук го направихме с root token-а.

## Стъпка 12 — Единствената програма: Python без пароли

Дотук всичко беше през терминала. Сега онова, което прави всяко истинско приложение: да поиска идентификационните си данни от Vault и да се свърже. Първо политика за програмата, `politicas/app-python.hcl`:

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

Качи я и създай token от 30 минути за програмата:

```
$ jq -n --rawfile p politicas/app-python.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/app-python -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/create \
    -d '{"policies": ["app-python"], "ttl": "30m", "display_name": "app-python"}' \
    | jq -r .auth.client_token > secretos-locales/token-python.txt
```

Инсталирай конектора на PostgreSQL за Python във виртуална среда:

```
python3 -m venv .venv
.venv/bin/pip install "psycopg[binary]"
```

**Днес не ти трябва да владееш целия Python.** Приеми този файл като готова програма и гледай само четири зони: `TOKEN` чете тайна от средата; `vault(...)` говори с Vault; `cred = ...` иска временния потребител; а блокът `with psycopg.connect(...)` ползва този потребител в PostgreSQL. В упражнение 20 променяш само как завършва програмата.

И програмата, `python/clientes.py`. Ползва `urllib`, който идва с Python, за да говори с Vault, и `psycopg` за PostgreSQL. Те са 24 реда:

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

Какво прави, по ред: функцията `vault` изпраща заявка към Vault с token-а в заглавната част (ако ѝ подадеш `datos`, е `POST`; ако не, `GET`) и връща частта `data` от отговора. Иска динамични идентификационни данни, свързва се с тях, чете клиентите и дешифрова всяко CURP с Transit.

Пусни я с token-а на програмата:

```
$ export VAULT_TOKEN=$(cat secretos-locales/token-python.txt)
$ .venv/bin/python python/clientes.py
Vault me prestó el usuario v-token-ap-lector-9FQ5IlE2i1HAUlZvuxZG-1792335175
Pepe   vault:v3:VEk...  ->  PEPE000101HDFXXX01
María  vault:v3:hKW...  ->  MARA990909MDFXXX02
```

Потърси във файла парола на PostgreSQL или на Transit: няма. Програмата наистина получава token на Vault от средата; този token също е тайна, но не е записан в кода, има ограничени права и трае само 30 минути. Името на потребителя вече започва с `v-token-ap`: Vault отбелязва, че го е поискал token `app-python`, а не root. Пусни я пак и ти заема **друг** потребител. А ако програмата се опита да излезе извън политиката си:

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Без token дори не стартира:

```
$ unset VAULT_TOKEN; .venv/bin/python python/clientes.py
...
KeyError: 'VAULT_TOKEN'
```

Когато приключиш, върни се към root token-а: `export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)`.

> **А от Java, .NET или Go?**
>
> Онова, което направи с `curl` и Python, се прави от всеки език, защото Vault говори HTTP. Почти никой не го програмира на ръка: всеки език има библиотеки. HashiCorp поддържа списък, който разграничава официалните от тези на общността ([Client libraries](https://developer.hashicorp.com/vault/api-docs/libraries)):
>
> - **Go:** `github.com/hashicorp/vault/api`, клиентът, който HashiCorp поддържа официално.
> - **Java със Spring:** [Spring Cloud Vault](https://spring.io/projects/spring-cloud-vault) зарежда тайните от Vault в конфигурацията на приложението и може да иска идентификационни данни за база данни в момента. HashiCorp го изброява сред библиотеките на общността.
> - **Java с Quarkus:** разширението [Quarkus Vault](https://docs.quarkiverse.io/quarkus-vault/dev/index.html), от проекта Quarkiverse, покрива KV, Transit и динамични идентификационни данни за връзката с базата данни. И то е на общността.
> - **.NET:** [VaultSharp](https://github.com/rajanadar/VaultSharp) е най-известният вариант. **Не е официален**: това е проект на общността. Списъкът на HashiCorp споменава още един експериментален клиент за .NET, който според същата страница не е готов за продукция.
>
> И има начин да не пипаш кода: **Vault Agent**, програма, която работи до приложението ти, легитимира се пред Vault, подновява своя token и записва тайните във файл по шаблон; приложението ти само чете този файл ([Vault Agent](https://developer.hashicorp.com/vault/docs/agent-and-proxy/agent)). В Kubernetes **инжекторът на Vault Agent** го добавя сам към подовете, които го поискат с анотации, и оставя тайните в том в паметта, споделен с приложението ([Agent Injector](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/injector)).

> **А как изглежда това в истинска система?**
>
> Представи си платформа, която обслужва много фирми едновременно и пази за всяка от тях паролите на нейните доставчици: достъпа до банката ѝ, до системата ѝ за фактури, до куриера ѝ. Ако една фирма види тайните на друга, бизнесът свършва.
>
> Добрият дизайн не привързва програмата към Vault. Първо определя **компонент с кратък контракт**: „запечатай тази тайна за тази фирма“ и „отвори я“. Вътре всяка фирма има **собствен ключ, с версии**, като ключа на Transit, който си ротирал в сесия 3: ако един ключ се ротира, запечатаното преди още се отваря, а с `min_decryption_version` на старото се слага срок на годност.
>
> Зад този контракт се свързва доставчикът:
>
> - за **тестовете** — версия, която пази всичко в паметта и се изтрива накрая;
> - за **продукцията** — адаптер, който вика Transit с по един ключ за фирма (`transit/encrypt/empresa-a`, `transit/encrypt/empresa-b`), или услуга за ключове на някой облак.
>
> Този доставчик може да е HashiCorp Vault или OpenBao, неговата свободна версия, която има съвместим механизъм Transit ([Transit в OpenBao](https://openbao.org/docs/secrets/transit/)); в Hábil избрахме OpenBao.
>
> Останалата част от системата никога не знае кой от двамата е свързан. Така може да се тества всичко, без да се стартира Vault, и да се сменя доставчикът, без да се пренаписва програмата. Обърни внимание на онова, което **не** прави: програмата никога не докосва ключа. Иска „запечатай“ и „отвори“, а ключът остава във Vault, както видя с `curl` в сесия 3.

---

👉 **Ако идваш от бизнес администрацията:** динамичните идентификационни данни са **пропускът за посетител**, пренесен в системите: издава се на името на този, който го иска, отваря само необходимото и изтича сам. Автоматичната ротация е **периодичната смяна на комбинацията** на сейфа, но без никой да се налага да записва новата. А бутонът за паника отговаря на въпроса, който задава всеки одитор след инцидент: „колко време ви отне да анулирате достъпите?“. С това отговорът е „една команда“. В случая на Canasta Morada въпросът, който наистина имаше значение, беше друг: „кой плаща този сървър от 9,99 долара?“. Прегледът на повтарящите се такси по картата на фирмата също е контрол на достъпа.

---

## Упражнения към сесия 4

**Упражнение 16 — Твоят пропуск.** Поискай идентификационни данни от ролята `lector`, влез с `psql` и преброй клиентите. После опитай `INSERT INTO clientes (nombre, curp) VALUES ('Intruso', 'x');`.

```
# Pista: guarda la credencial para usarla en el ejercicio 17.
# Archivo sugerido: secretos-locales/creds-16.json
# Ruta que debes consultar: database/creds/lector
```

**Как проверяваш:** броят дава `2` (или колкото имаш); `INSERT` дава `ERROR:  permission denied for table clientes`.

**Упражнение 17 — Отнеми ги сам.** Отнеми идентификационните данни от упражнение 16 със `sys/leases/revoke` и опитай да влезеш отново. Направи го в рамките на 2 минути: ако Vault вече ги е отнел и маршрутът отговаря, че lease не съществува, това не е грешка в правата. Поискай други, замени `creds-16.json` и ги отнеми веднага.

**Как проверяваш:** отнемането отговаря `HTTP 204`, а `psql` отговаря `password authentication failed`. От суперпотребителя `SELECT count(*) FROM pg_roles WHERE rolname = '<потребителят>';` дава `0`.

**Упражнение 18 — Паролата от преди минута.** Запази действащата парола на `reportes` в променлива, ротирай с `rotate-role/reportes` и опитай да влезеш с онази, която си запазил.

**Как проверяваш:** със запазената — `password authentication failed for user "reportes"`. С онази, която Vault ти дава след ротацията, влиза.

**Упражнение 19 — Пропуск от 30 секунди.** Смени `default_ttl` на ролята `lector` на 30 секунди, без да редактираш файла, с `jq`:

```
jq '.default_ttl = "30s"' roles/lector-postgres.json \
  | curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/roles/lector -d @-
```

Поискай идентификационни данни, влез веднага, изчакай 40 секунди и опитай отново. Запази данните в `secretos-locales/creds-19.json` и сложи `PGUSER=... PGPASSWORD=... psql` пред всеки опит, като четеш стойностите от файла с `jq` както в стъпка 5: онова, което експортира в упражнения 16 и 17, принадлежи на вече отнет потребител и би ти дало неуспех, който не е от TTL.

**Как проверяваш:** `lease_duration` казва `30`; първият опит влиза; вторият дава `password authentication failed`. Накрая върни ролята както си беше, като качиш отново `roles/lector-postgres.json`.

**Упражнение 20 — Програмата да си прибира боклука.** Всеки път, когато `clientes.py` работи, оставя жив временен потребител, докато изтече. Направи така, че да **отнема собствения си token** с `auth/token/revoke-self` и да го прави **винаги**, дори нещо да се провали по средата (ползвай `try` и `finally`). Когато един token се отнеме, Vault отнема и идентификационните данни, поискани с него. Тръгни от този скелет, който вече подрежда структурата:

```python
try:
    cred = vault("database/creds/lector")
    # pega aquí el bloque with psycopg.connect(...) que ya existe
finally:
    # aquí va la petición POST a auth/token/revoke-self
    pass
```

**Как проверяваш:** преди да я пуснеш, преброй от суперпотребителя потребителите, които започват с `v-token-ap`; след като я пуснеш, броят трябва да остане същият като преди (потребителят е създаден и изтрит). Ако я пуснеш пак със същия token, трябва да се провали с `HTTP Error 403`, защото token-ът вече не съществува. За да повториш проверката след този 403, създай нов token със същата команда от стъпка 12, запази го отново в `secretos-locales/token-python.txt` и експортирай `VAULT_TOKEN` пак. 403 е очакваният само за вече отнетия token.

---

## Често срещани грешки (и как да ги забележиш)

| Грешка | Как изглежда | Как да я забележиш | Какво да направиш |
|---|---|---|---|
| Да ползваш `127.0.0.1` в `connection_url` | При записване на конфигурацията: `error verifying connection: ... dial tcp 127.0.0.1:5432: connect: connection refused`, код 400 | Сървърът в URL не е името на услугата; вътре в контейнера на Vault `127.0.0.1` е самият Vault | В Docker Compose Vault стига до базата данни по име: `postgres`, `mariadb` |
| Роля, която не е в `allowed_roles` | `"escritor" is not an allowed role`, код 500 | Името на ролята не се появява в `database/config/<връзка>` | Добави я в `allowed_roles` на връзката |
| Отнемане, което се проваля при точно необходими права | `permission denied for sequence ...` при отнемане | Ролята няма `revocation_statements` | Напиши своите `revocation_statements`; не давай суперпотребител на Vault, за да изчезне грешката |
| Да запазиш паролата на `vault_admin` и после да ротираш корена | Файлът вече не върши работа | `rotate-root` отговори 204 | Това искаме: никой човек не я знае. Ако ти трябва да влезеш, ползвай суперпотребителя на базата данни, а не този на Vault |
| Да очакваш идентификационните данни да траят повече от `max_ttl` | Подновяваш и все пак изтичат | `lease_duration` спира да расте | `max_ttl` е таванът. Поискай нови данни |
| Да залепиш token-а на програмата в кода | Token-ът е записан във файл, който git следи | `git status` показва файла като променен, а `grep -rn hvs. python/` намира token-а | Token-ът влиза през променлива на средата или, още по-добре, с Vault Agent. Ако е качен, отнеми го |
| `psql` влиза без да иска парола | Мислиш, че данните още са живи | Свързал си се през локалния сокет вътре в контейнера | Свържи се като в урока, през мрежата (`-h 127.0.0.1` от твоята машина), където PostgreSQL наистина проверява паролата |

---

## Самооценка на серията

Отговори, без да гледаш. Ако сгрешиш повече от две, върни се към посочената сесия.

1. Каква е разликата между `DELETE` върху `secret/data/...` и `destroy`? *(Сесия 2)*
2. Напиши по памет политика, която позволява четене на `secret/data/app/*` и нищо повече. *(Сесия 2)*
3. Защо 403 е добра новина, когато изпитваш политика? *(Сесия 2)*
4. Какво ти трябва, за да дешифроваш `vault:v1:...`, ако ключът има `min_decryption_version: 2`? *(Сесия 3)*
5. Какво печели една система с производни ключове и `context`? *(Сесия 3)*
6. Каква е разликата между динамични идентификационни данни и статична роля? *(Сесия 4)*
7. Защо връзката на Vault с базата данни ползва `vault_admin`, а не суперпотребителя? *(Сесия 4)*
8. Един стажант напуска фирмата. С онова, което изгради, кои пароли би трябвало да смениш на ръка? *(Всички)*

## Преговор на серията

| Сесия | Проблемът | Какво го решава | Командата, която не бива да забравяш |
|---|---|---|---|
| 1 | Тайни във файлове, в чатове, споделени и вечни | Изисквания R1 до R7 | `git log -p -S <текст>` |
| 2 | Никой не знае кой има достъп, нито кой го е ползвал | Печат на Шамир, token-и, политики, журнал | `curl -H "X-Vault-Token: ..." $VAULT_ADDR/v1/secret/data/...` |
| 3 | Ключът за шифроване живее до данните | Transit: шифроване, без да държиш ключа, ротация, rewrap | `POST transit/encrypt/<ключ>` с `plaintext` в base64 |
| 4 | Една и съща парола на базата данни за всички и завинаги | Динамични идентификационни данни, ротация, `rotate-root`, отнемане | `GET database/creds/<роля>` |

**За да изключиш всичко в края на серията:** `docker compose down`. Данните ти остават в папките `vault/`, `postgres/` и `mariadb/`. Ако искаш да започнеш отначало, изтрий тези папки, `secretos-locales/` и `.env` и пусни пак `./iniciar.sh`.

---

## Решения (не ги гледай, преди да опиташ)

**Преговор на сесия 3.**

1. `vault`: шифровано от Vault; `v2`: с версия 2 на ключа; останалото: шифрованата стойност, в base64.
2. Остават шифровани със старата си версия и могат да се дешифроват, докато тази версия не падне под `min_decryption_version`. `rewrap` ги качва към новата версия, без да разкрие стойността.
3. Защото ако някой открадне този token, може да вкарва шифровани данни, но не може да прочете никакви. Вредата от един теч е много по-малка.

**Упражнение 16.**

```
curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector > secretos-locales/creds-16.json
export PGUSER=$(jq -r .data.username secretos-locales/creds-16.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-16.json)
psql -At -c "SELECT count(*) FROM clientes;"
psql -c "INSERT INTO clientes (nombre, curp) VALUES ('Intruso', 'x');"
```

**Упражнение 17.** Командата от стъпка 6, с `lease_id` от `creds-16.json`. Направи го, преди да минат 2 минути; ако Vault те изпревари, поискай други данни и ги отнеми веднага.

**Упражнение 18.**

```
VIEJA=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password)
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-role/reportes
PGUSER=reportes PGPASSWORD=$VIEJA psql -At -c "SELECT 1;"
NUEVA=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password)
PGUSER=reportes PGPASSWORD=$NUEVA psql -At -c "SELECT 1;"
```

В опита към този урок командата, която ползва `$VIEJA` (третата), даде `FATAL:  password authentication failed for user "reportes"`. Внимание: понеже ролята ротира всяка минута, „старата“ може да умре от автоматичната ротация преди тази от твоята ротация. Резултатът е същият. Последната команда, с `$NUEVA`, печата `1`; ако и тя се провали, поискай отново от Vault действащата парола и я изпълни пак, защото ротацията от една минута може да е станала между две команди.

**Упражнение 19.**

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

В опита:

```
{"lease_duration":30,"username":"v-root-lector-wlrG6BL0dqUomIbQDDrV-1792336140"}
```

Първият опит върна `2`. Четирийсет секунди по-късно:

```
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-wlrG6BL0dqUomIbQDDrV-1792336140"
```

**Упражнение 20.** Сложи вътре в `try` искането на идентификационните данни и всичко, което ползва базата данни, а отнемането във `finally`, който се изпълнява, каквото и да стане (дори да се провали самото искане на данните):

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

Така, ако заявката, връзката или някоя справка се провалят, token-ът се отнема въпреки това. `data=b"{}"` превръща заявката в `POST`, което иска този маршрут. В опита към този урок:

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

Потребителят `v-token-ap-lector-xQMN...` се роди и умря в рамките на едно и също изпълнение. Програмата вече не оставя нищо след себе си.

**Самооценка.**

1. `DELETE` изтрива последната версия обратимо (`undelete` я връща); `destroy` я изтрива завинаги.
2. `path "secret/data/app/*" { capabilities = ["read"] }`
3. Защото доказва, че политиката забранява онова, което трябва да забранява. Политика, която никога не дава 403, вероятно дава повече от необходимото.
4. Нищо не го дешифрова, докато минимумът е 2. Правилното беше да се обвие наново, преди да се вдигне минимумът; иначе трябва да се смъкне `min_decryption_version`, да се обвие наново и пак да се вдигне.
5. Че шифровани данни за един собственик не могат да се дешифроват, сякаш са на друг, дори да се ползва същият ключ.
6. Динамичните създават нов потребител всеки път и го изтриват при изтичане; статичната роля запазва потребител, който вече съществува, и му сменя паролата през определен период.
7. Защото `rotate-root` оставя паролата в ръцете на Vault, а документацията препоръчва специален потребител. Освен това при точно необходими права грешка или теч във Vault не дава пълен контрол над базата данни.
8. Нито една не се сменя на ръка. Отнемаш неговия token във Vault и с него — динамичните му идентификационни данни (или всички, които е създал, по префикс). Едно изключение: ако е знаел паролата на статичната роля `reportes`, ротирай я веднага с `POST /v1/database/rotate-role/reportes`; отнемането на token-а му не променя тази парола, която би продължила да работи до следващата ротация. Това е разликата с Canasta Morada в началото на серията.

---

## Какво следва

Тази серия използва Vault с един-единствен сървър, без TLS и с ключовете във файл, защото е лаборатория. Ако искаш да продължиш, следващите теми са: TLS на listener-а, методи за автентикация на машини (AppRole, Kubernetes) вместо token-и, създавани на ръка, съхранение с няколко сървъра за висока достъпност и резервни копия на самия Vault.

---

*Пиша от онова, което виждаме всеки ден в Hábil, където изграждаме системи за банки, застрахователи и компании в Мексико. Ако в работата си или в семейния бизнес се сблъскате с такъв проблем, нека си поговорим: [habil.mx](https://www.habil.mx/bg/)*

*Ако в твоята фирма паролите на базите данни още живеят във файл, в Hábil изграждаме това като част от осигуряването на инфраструктурата: [самоличност, ключове и тайни](https://www.habil.mx/bg/).*
