# Vault от нулата (2): стартиране на Vault и съхраняване на тайни

*Сейф, който никой не може да отвори сам, гише, което казва „не“ на този, който иска онова, което не му се полага, и журнал, който записва всичко. С Docker Compose и `curl`.*

*Vault от нулата · сесия 2 от 4*

## Преговор на сесия 1

Отговори, без да гледаш. Отговорите са в решенията, в края.

1. Назови четири от шестте начина, по които една тайна изтича.
2. Защо смяната на паролата след теч е задължителна, дори вече да си я изтрил от git?
3. В какво механизмът Transit на Vault прилича на HSM и в какво се различава?

> **Лабораторията на тази сесия** е в публичното хранилище [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Първо я изгради сам; хранилището е за сравнение, когато нещо не ти излезе същото. Не съдържа нито една парола: лабораторията ги генерира при стартиране.

## Цели на тази сесия

| # | Накрая можеш да… | Доказва се с |
|---|---|---|
| 1 | **Стартираш** Vault в сървърен режим с Docker Compose, без да пишеш никаква парола във файловете на лабораторията | Упражнение 6 |
| 2 | **Инициализираш** и **отвориш** Vault с 3 от 5 ключа и **обясниш** защо се затваря сам при рестарт | Упражнение 7 |
| 3 | **Записваш, четеш, версионираш, изтриваш и възстановяваш** тайни с `curl` през API | Упражнение 8 |
| 4 | **Напишеш** политика и **провериш**, че ограничен token получава 403 там, където трябва | Упражнение 9 |
| 5 | **Четеш** одитния журнал с `jq`, за да разбереш кой какво е поискал | Упражнение 10 |

---

## Сценарий (измислица) — Глава 5: събота, 13:40

Иван смени паролата на `app_tienda` по обяд. Отне му час и половина да стартира отново четирите програми. Макросът на счетоводството така и не се появи; Росио, счетоводителката, ще извади отчета за месеца ръчно.

Доня Клара слуша всичко, без да прекъсва. Накрая казва само едно нещо:

— Не искам никога вече да завися от това дали някой си спомня къде е записал една парола.

Иван предлага сейф за тайни. Доня Клара пита кой ще държи ключа.

— Вие — казва Иван.

— Не. Ако ми се случи нещо, никой няма да отваря. А ако някой ми го вземе, ще отваря сам.

Иван се усмихва. Това възражение има отговор от 1979 г.

---

## Глава 6: следващата събота, 3:17 през нощта

Сейфът съществува. Петима души имат по едно парче от ключа му. Приложенията искат тайните си със собствената си самоличност.

Телефонът на Иван отново вибрира. Същият час. Същият сървър. Но сега журналът на базата данни казва друго:

```
03:17:02  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
03:17:32  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
03:18:02  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
```

Някой продължава да опитва със старата парола. На всеки трийсет секунди. Като часовник.

Иван остава загледан в екрана. Крадците нямат фиксиран график.

А кой има?

*(Продължава в сесия 3.)*

---

## Защо е важно

Досега в Canasta Morada „да имаш достъп“ означаваше „да знаеш паролата“. Днес ще изградиш обратното: място, където никой нищо не знае, а всеки **иска** онова, от което има нужда, и **доказва** кой е. Това е разликата между къща, в която всички имат копие на ключа, и сграда с рецепция: там те записват, питат те къде отиваш и ти отварят само този етаж.

В тази сесия ще видиш три идеи, които се използват във всяка сериозна система, с Vault или без него:

- **Печатът (seal).** Данните са шифровани на диска. Без главния ключ дори самият Vault не може да ги чете.
- **Забранено по подразбиране.** Ако една политика не казва, че можеш, не можеш. Документацията го казва така: „политиките забраняват по подразбиране“ ([Policies](https://developer.hashicorp.com/vault/docs/concepts/policies)).
- **Всичко се записва.** Всяка заявка, разрешена или отказана, оставя следа в журнала.

## Отговорът от 1979 г.: ключовете на Шамир

През 1979 г. криптографът Ади Шамир публикува начин да се раздели една тайна на **N парчета** така, че всяка група от **K** парчета да я възстановява, а с по-малко от K да не се знае нищо. Ни най-малко.

Помисли за касичката на селския празник. Има петима пазители. За да се отвори, трябва да се съберат поне трима, всеки със своя ключ. Ако един се разболее, останалите четирима стигат. Ако на един му откраднат ключа, крадецът сам не отваря нищо. И никой, дори главният пазител, не може да я отвори тайно.

Vault работи така:

- При **инициализиране** Vault създава **главен ключ**, който защитава всичко, което пази. По подразбиране го разделя на **5 парчета** и изисква **3**, за да го възстанови ([vault operator init](https://developer.hashicorp.com/vault/docs/commands/operator/init)).
- Vault стартира **запечатан** (*sealed*): има данните, но шифровани, и не ги разбира. Това е затворената касичка.
- **Отварянето на печата** (*unseal*) е, когато трима пазители пъхнат ключа си. Оттам нататък Vault работи нормално.
- Ако Vault се рестартира, **запечатва се отново**. Трябва пак да се съберат три ключа.

Официалната документация обяснява печата и алгоритъма на Шамир в [Seal/Unseal](https://developer.hashicorp.com/vault/docs/concepts/seal).

---

## Стъпка 0 — Какво ти трябва

Docker с Compose, `curl`, `jq` (версия 1.6 или по-нова), `openssl` и `git`. Провери:

```
docker compose version
curl --version
jq --version
openssl version
```

Ако някой покаже „command not found“, инсталирай го, преди да продължиш. Тази сесия ползва Vault 2.2.0, PostgreSQL 17.11 и MariaDB 11.8.8, зададени фиксирано в `compose.yaml`: не ги заменяй с `latest`, защото командите и отговорите в урока са на тези версии.

## Стъпка 1 — Папката на лабораторията

Създай папка `lab-vault` с тази структура. Съдържанието на всеки файл е по-долу.

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

Първият е `.gitignore`. Това е списъкът с онова, което git никога не бива да качва. Идва **преди** всичко друго, защото лабораторията ще генерира пароли и искаме от първата секунда git да не ги добавя по невнимание. Внимание: `.gitignore` само пречи на git да добавя файлове, които още не познава. Не защитава файл, който вече е бил записан преди това, нито от някой, който принуди качването с `git add -f`; затова е добре да проверяваш `git status` преди всеки `git commit`.

```
# Lo que el laboratorio genera al arrancar. NADA de esto se sube a git.
.env
secretos-locales/
vault/data/
vault/logs/
postgres/
mariadb/
```

После `.env.ejemplo`. Това е справочно копие **без реални стойности**, за да знае който клонира хранилището какви променливи съществуват:

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

Конфигурацията на Vault, `vault/config/vault.hcl`:

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

Три неща, които е добре да разбереш:

- **`storage "file"`**: Vault пази данните си, вече шифровани, в една папка. Има други опции за продукция с няколко сървъра; тази е най-простата ([Filesystem storage](https://developer.hashicorp.com/vault/docs/configuration/storage/filesystem)).
- **`tls_disable = true`**: без шифроване на връзката. На лаптопа ти е добре. На истински сървър — **никога**: паролите биха пътували като обикновен текст по мрежата.
- **Не е режим „dev“.** Vault има режим за разработка, който стартира отворен, без печат и пази всичко в паметта. Удобен е, но крие точно онова, което искаме да научим днес.

`compose.yaml`. Обърни внимание на две подробности: **няма записана никаква парола**, а само променливи като `${POSTGRES_PASSWORD}`, и данните се пазят в **монтирани папки** (`./vault/data`), а не в томове (volumes) на Docker, за да виждаш файловете и да не се губят, ако някой почисти Docker:

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

PostgreSQL и MariaDB ги ползваш в сесии 3 и 4; стартираме ги от днес, за да не пипаме файла после. Изразът `:?falta .env…` значи: „ако тази променлива не съществува, не стартирай и покажи това съобщение“.

Три подробности за този файл:

- **`127.0.0.1:` пред всеки порт** кара Docker да публикува услугата само за твоя компютър. Без това Vault (който тук не ползва TLS) и двете бази щяха да са отворени за всеки в мрежата ти.
- **`user:`** кара Vault да работи с твоя потребител. Официалният образ стартира с потребител без привилегии (`vault`), а в Linux той не би могъл да пише в папки, които си създал ти. Скриптът за стартиране записва номера на потребителя ти в `.env`.
- **Ако някой порт вече е зает** (8200, 5432 или 3306), смени го с `PUERTO_VAULT`, `PUERTO_POSTGRES` или `PUERTO_MARIADB`, както е обяснено по-долу.

> **В Linux: две папки, които са твои, но не са.**
>
> След като стартираш лабораторията в Linux, пусни `ls -ln` в папката. Ще видиш нещо такова (изрязали сме колоните, които нямат значение; измерено на Linux Mint 22.3, с потребител 1000):
>
> ```
> drwx------  999 1000  postgres
> drwxrwxr-x  999  999  mariadb
> drwx------ 1000 1000  secretos-locales
> drwxr-xr-x 1000 1000  vault
> ```
>
> Папките `postgres` и `mariadb` вече не са на твоя потребител: те са на 999. А ако пуснеш `ls -l` без `n`, вместо номера може да се появи името на някоя услуга на системата ти (в Mint излезе `dnsmasq`). Не е вирус, нито грешка на лабораторията. Случва се, защото официалните образи на PostgreSQL и MariaDB стартират като администратор вътре в контейнера и след това предават файловете си на собствения си вътрешен потребител, номер 999. **Монтираната папка** е същата папка, погледната от две страни: каквото контейнерът направи с файловете си, дискът ти го вижда такова, каквото е, заедно с номера на потребителя. Твоят Linux не знае кой е 999 на контейнера; вижда само номера, и ако в системата ти този номер има собственик, показва името му.
>
> На Vault това не му се случва, защото `user:` в compose го принуждава да работи с твоя номер. Защо същото не се прави с базите данни? Защото те трябва да стартират като администратор, за да се подготвят първия път, а принудителният друг потребител чупи този първи старт.
>
> Какво означава това за теб:
> - `ls postgres` ще ти каже „Отказан достъп“. За да погледнеш вътре, ползвай `sudo ls postgres` или още по-добре попитай самия контейнер: `docker compose exec postgres ls /var/lib/postgresql/data`.
> - Ако някой ден поискаш да започнеш лабораторията отначало, първо `docker compose down`, после изтрий тези две папки със `sudo`, защото твоят потребител не може.
> - В macOS и Windows няма да го видиш: Docker работи във виртуална машина, която ти показва файловете като твои.

## Стъпка 2 — Скрипт за стартиране, който отказва при съмнение (fail closed)

`iniciar.sh` подготвя всичко. Важното е в точка 1: **преди да генерира каквато и да е парола, проверява дали `.gitignore` я защитава.** Ако не, отказва да продължи. Това се нарича **отказ при съмнение** (*fail closed*): при съмнение вратата остава затворена, като турникета в метрото, който не се върти, ако картата ти не е минала.

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

`grep -qx` търси ред, който да е **точно** този текст (`-x`), и не печата нищо (`-q`); казва само да или не. `openssl rand -hex 16` генерира 16 случайни байта, записани като 32 шестнайсетични знака. `umask 077` прави така, че `.env` да се създава четим само от теб. `id -u` и `id -g` са номерът на потребителя ти и на групата ти. А `unset` маха от терминала ти всяка променлива с тези имена: Compose дава приоритет на променливите от терминала пред `.env` и не искаме стара парола или стар порт да надделеят, без да разбереш.

Дай му право за изпълнение с `chmod +x iniciar.sh`. Преди да го пуснеш истински, провери, че наистина отказва при съмнение. В копие на лабораторията, където в `.gitignore` липсва редът `secretos-locales/`, ето какво се случва:

```
$ ./iniciar.sh
ALTO: .gitignore no tiene la regla 'secretos-locales/'.
Sin ella, las contraseñas que voy a generar podrían terminar en git. No sigo.
código de salida: 1
```

Не създаде нито папка, нито `.env`. Сега, с пълния `.gitignore`:

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

Ако на твоята машина вече ползваш порт 5432 (защото имаш друг PostgreSQL), стартирай го така първия път: `PUERTO_POSTGRES=15432 ./iniciar.sh`. Скриптът го записва в `.env`.

И доказателството, че git не вижда тайните. Ако направиш `git init` в папката и попиташ какво би качил:

```
$ git status --short
?? .env.ejemplo
?? .gitignore
?? compose.yaml
?? iniciar.sh
?? vault/config/vault.hcl
```

Нито `.env`, нито `secretos-locales/`, нито данните. Това е, което искаше.

## Стъпка 3 — Жив ли е?

Vault говори HTTP. Запази адреса му в променлива, за да не го пишеш всеки път:

```
export VAULT_ADDR="http://127.0.0.1:$(grep '^PUERTO_VAULT=' .env | cut -d= -f2)"
```

Пусни този ред в папката `lab-vault`. Портът се чете от твоя `.env`, така че работи, дори да си го сменил. Това, че Docker казва „Started“, не значи, че Vault вече слуша. Изчакай да отговори:

```
until curl -fsS -o /dev/null "$VAULT_ADDR/v1/sys/seal-status"; do
  echo "Espero a que Vault inicie..."
  sleep 1
done
```

Попитай го как е печатът му. Този маршрут не иска самоличност:

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

`initialized: false`: никога не е бил инициализиран. `sealed: true`: запечатан е. `t` и `n` са прагът и общият брой ключове; още няма.

Друг бърз начин да разбереш състоянието е HTTP кодът на маршрута за здраве. `-o /dev/null` изхвърля отговора, а `-w` печата само кода:

```
$ curl -s -o /dev/null -w "%{http_code}\n" $VAULT_ADDR/v1/sys/health
501
```

501 значи „не е инициализиран“. Ще видиш как се променя.

## Стъпка 4 — Инициализиране: раждат се петте ключа

Тази заявка създава главния ключ, разделя го на 5 парчета с праг 3 и ти връща парчетата и един **root token**. Записваш го директно във файл в папката `secretos-locales/`, която git пренебрегва:

```
curl -s -X PUT $VAULT_ADDR/v1/sys/init \
  -d '{"secret_shares": 5, "secret_threshold": 3}' > secretos-locales/init.json
chmod 600 secretos-locales/init.json
```

`chmod 600` оставя файла четим само за теб. Погледни го, без да показваш пълните стойности:

```
$ jq "{llaves: (.keys | length), token_root: (.root_token[0:9] + \"...\")}" secretos-locales/init.json
{
  "llaves": 5,
  "token_root": "hvs.RGQs7..."
}
```

Твоите стойности ще са други. Всяко инициализиране създава нови ключове. В този урок винаги ще виждаш token-ите отрязани, така: `hvs.RGQs7...`.

**Root token-ът** е ключът на собственика: може да прави абсолютно всичко. Ще го ползваш, за да настроиш лабораторията.

> **Така не, и защо**
>
> Да пазиш петте ключа и root token-а във файл до `compose.yaml` е **отстъпка на лабораторията**, за да можеш да упражняваш сам на машината си. **В реалния живот никога не се прави така.**
>
> - Ключовете се разпределят между **различни хора**, по един на всеки, точно за да не може никой да отвори сейфа сам. Да ги събереш във файл значи да имаш петимата пазители в един човек.
> - **Root token-ът се отнема (revoke)** веднага щом приключи първоначалната настройка. Документацията го препоръчва така: ползва се само за най-необходимото в началото и се отнема, щом вече не е нужен ([Tokens](https://developer.hashicorp.com/vault/docs/concepts/tokens)). Ако някой ден се наложи друг, генерира се, като се съберат отново ключовете.
> - Истинският сървър ползва TLS, а не `tls_disable`.
>
> Ако някой ден копираш тази лаборатория на сървър, тези три неща са първите, които променяш.

Провери печата отново:

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

Инициализиран, но запечатан. Липсват пазителите.

## Стъпка 5 — Отваряне на печата с 3 от 5 ключа

Всяко извикване на `sys/unseal` предава **един** ключ. `jq -r '.keys[0]'` взема първия от файла, без кавички:

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

`progress: 1`: един от три. Повтори с `.keys[1]`:

```
{
  "sealed": true,
  "t": 3,
  "n": 5,
  "progress": 2
}
```

И с `.keys[2]`:

```
{
  "sealed": false,
  "t": 3,
  "n": 5,
  "progress": 0
}
```

`sealed: false`. Отворен. Маршрутът за здраве вече отговаря 200:

```
$ curl -s -o /dev/null -w "%{http_code}\n" $VAULT_ADDR/v1/sys/health
200
```

Провери, че се запечатва сам при рестарт:

```
$ docker compose restart vault
$ curl -s $VAULT_ADDR/v1/sys/seal-status | jq "{sealed, progress}"
{
  "sealed": true,
  "progress": 0
}
```

Така ще е всеки път, когато включиш компютъра си или рестартираш контейнера. За да не пишеш три пъти едно и също, отвори го с цикъл:

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

А ако някой пъхне фалшив ключ?

```
$ curl -s -X PUT $VAULT_ADDR/v1/sys/unseal -d '{"key": "esta-no-es-una-llave"}'
{"errors":["'key' must be a valid hex or base64 string"]}
```

## Стъпка 6 — Да се легитимираш: token-ът

Без token гишето не те обслужва:

```
$ curl -s -w " HTTP %{http_code}\n" $VAULT_ADDR/v1/sys/mounts
{"errors":["permission denied"]}
 HTTP 403
```

Експортирай root token-а в променлива на терминала си. **Никога не го лепи във файл, който се качва**; четеш го оттам, където е:

```
export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)
```

Token-ът пътува в заглавната част `X-Vault-Token`. Попитай кой си:

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

`ttl: 0` значи, че никога не изтича. Още една причина да се отнема в реалния живот.

Едно уточнение: в лабораторията „самоличността“ на приложението е token, който създаваш ръчно. Така се вижда механизмът отблизо. В истинска система приложенията получават token сами, като доказват кои са с методи като AppRole, Kubernetes или OIDC (документацията на Vault ги нарича *методи за автентикация*); това е извън тази серия.

## Стъпка 7 — Включване на журнала преди всичко

Журналът е първи, за да се записва всичко, което правиш оттук нататък. **Одитно устройство** (*audit device*) от тип файл записва по един JSON ред за всяка заявка и по един за всеки отговор ([File audit device](https://developer.hashicorp.com/vault/docs/audit/file)):

```
$ curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/audit/archivo \
    -d '{"type": "file", "options": {"file_path": "/vault/logs/audit.log"}}'
HTTP 204
```

204 значи „направено и нямам какво да ти разкажа“. Журналът остава в `./vault/logs/audit.log` на твоята машина, благодарение на монтираната папка.

## Стъпка 8 — Съхраняване на тайни: механизмът KV версия 2

Включи механизма **KV v2** на пътя `secret/`. Това е чекмедже за тайни от тип ключ-стойност, което пази версии ([KV v2](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2)):

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/secret -d '{"type": "kv", "options": {"version": "2"}}'
HTTP 204
```

Изброй механизмите, които има:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/mounts | jq -r ".data | keys[]"
agent-registry/
cubbyhole/
identity/
secret/
sys/
```

Твоят е `secret/`. Останалите са там по подразбиране.

**Запис.** Запиши потребителя и паролата на приложението на магазина. Стойностите са за пример; в реалния живот паролата я генерираш с `openssl rand`, както направи скриптът:

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

Обърни внимание на пътя: `secret/`**`data/`**`tienda/postgres`. В KV v2 данните са под `data/`, а информацията за версиите — под `metadata/`. Това е капан номер едно на KV v2; има го в таблицата с грешки.

**Четене:**

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

**Нова версия.** Смени паролата:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/secret/data/tienda/postgres \
    -d '{"data": {"usuario": "app_tienda", "password": "Mango-2026"}}' | jq -c ".data | {version, created_time}"
{"version":2,"created_time":"2026-10-18T14:47:29.522529264Z"}
```

Версия 1 още е там. Поискай я с `?version=1`:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/postgres?version=1" | jq -c .data.data
{"password":"Pepino-2026","usuario":"app_tienda"}
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c ".data.data, .data.metadata.version"
{"password":"Mango-2026","usuario":"app_tienda"}
2
```

Все едно историята на версиите на документ в облака: можеш да се върнеш към вчерашната, ако днешната е излязла лоша.

**Изтриване (със застраховка).** `DELETE` върху `data/` изтрива последната версия, но обратимо:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X DELETE $VAULT_ADDR/v1/secret/data/tienda/postgres
HTTP 204
```

При четене вече няма данни, отговорът носи часа на изтриването и кодът е 404:

```
null
"2026-10-18T14:47:29.564180533Z"
HTTP 404
```

**Възстановяване.** `undelete` я връща:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X POST \
    $VAULT_ADDR/v1/secret/undelete/tienda/postgres -d '{"versions": [2]}'
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c .data.data
{"password":"Mango-2026","usuario":"app_tienda"}
```

**Унищожаване (без връщане).** `destroy` изтрива завинаги версиите, които посочиш. Унищожи 1, старата парола:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X PUT \
    $VAULT_ADDR/v1/secret/destroy/tienda/postgres -d '{"versions": [1]}'
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/postgres?version=1" | jq -c ".data.metadata | {version, destroyed}"
{"version":1,"destroyed":true}
```

**Метаданните** ти разказват историята на тайната, включително кой е създал всяка версия:

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

В тази заявка на `jq` `map_values(...)` обхожда всяка версия и оставя от нея само две стойности: дали е унищожена и кой я е създал.

А за да видиш какви тайни има в една папка, глаголът `LIST`:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X LIST $VAULT_ADDR/v1/secret/metadata/tienda | jq -c .data
{"keys":["postgres"]}
```

### Алтернативата: командата `vault` вътре в контейнера

Всичко горепосочено се прави и с командата `vault`, която е вътре в контейнера. `-e VAULT_TOKEN` ѝ предава твоята променлива:

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

Запиши с нея втора тайна, тази на заплатите, която ще ползваш за изпитване на правата:

```
$ docker compose exec -e VAULT_TOKEN vault vault kv put secret/nomina/banco cuenta=0123456789 clave=Aguacate-99
====== Secret Path ======
secret/data/nomina/banco
...
version            1
```

Обърни внимание, че командата добавя `data/` сама. Затова `curl` учи повече: виждаш истинския път.

## Стъпка 9 — Политики: всеки със своя ключ

**Политиката** (*policy*) казва до кои пътища може да се докосва един token и какво може да прави в тях. Създай папката `politicas/` и в нея файла `politicas/lectura-tienda.hcl`:

```hcl
# La app de la tienda puede LEER sus secretos. Nada más.
path "secret/data/tienda/*" {
  capabilities = ["read"]
}
```

`*` значи „всичко под `tienda/`“. Най-използваните възможности са `read`, `create`, `update`, `delete` и `list`. Което го няма, е забранено.

Качи я. API очаква текста на политиката вътре в JSON; `jq --rawfile p archivo` чете файла и го записва в променливата `p`; `-n` казва на `jq` да не очаква входни данни, а `\$p` има обратна наклонена черта, за да не го помисли терминалът ти за своя променлива. Така `jq` обвива политиката в JSON, без да се налага да я екранираш ръчно:

```
$ jq -n --rawfile p politicas/lectura-tienda.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/lectura-tienda -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X LIST $VAULT_ADDR/v1/sys/policies/acl | jq -c .data.keys
["default","default-ceiling","lectura-tienda","root"]
```

`-d @-` казва на `curl` „тялото идва от входа“, тоест от онова, което му е подал `jq` през тръбата (pipe).

Сега създай **token за приложението**, с тази политика и един час живот. Пълният token отива в `secretos-locales/`, никога на екрана:

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

Политиката `default` е включена във всички token-и; позволява основни неща, като да провериш собствения си token. `lease_duration: 3600` са 3600 секунди: един час.

Изпробвай трите случая. **Четене на своето:**

```
$ curl -s -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c .data.data
{"password":"Mango-2026","usuario":"app_tienda"}
```

Код 200. **Четене на заплатите:**

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/nomina/banco
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

**Запис в своето:**

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" -X POST \
    $VAULT_ADDR/v1/secret/data/tienda/postgres -d '{"data": {"password": "me-la-robe"}}'
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Два пъти 403. Гишето каза „не“. И можеш да попиташ Vault какво ти позволява на всеки път, без да опитваш:

```
$ curl -s -H "X-Vault-Token: $APP_TOKEN" -X POST $VAULT_ADDR/v1/sys/capabilities-self \
    -d '{"paths": ["secret/data/tienda/postgres", "secret/data/nomina/banco"]}' \
    | jq -c "{tienda: .[\"secret/data/tienda/postgres\"], nomina: .[\"secret/data/nomina/banco\"]}"
{"tienda":["read"],"nomina":["deny"]}
```

## Стъпка 10 — Журналът: кой какво е поискал

Всеки ред на `vault/logs/audit.log` е JSON. Колко вече има:

```
$ wc -l vault/logs/audit.log
      62 vault/logs/audit.log
```

Последните отговори, обобщени: час, кой, коя операция, кой път и дали е имало грешка:

```
$ tail -n 6 vault/logs/audit.log | jq -c "select(.type == \"response\") | {hora: .time, quien: .auth.display_name, operacion: .request.operation, ruta: .request.path, error: .error}"
{"hora":"2026-10-18T14:47:54.325141694Z","quien":"token-app-tienda","operacion":"update","ruta":"secret/data/tienda/postgres","error":"1 error occurred:\n\t* permission denied\n\n"}
{"hora":"2026-10-18T14:47:54.338083991Z","quien":"token-app-tienda","operacion":"update","ruta":"sys/capabilities-self","error":null}
{"hora":"2026-10-18T14:47:54.351637479Z","quien":"token-app-tienda","operacion":"read","ruta":"auth/token/lookup-self","error":null}
```

Ето опита за запис на приложението, с неговото име (`token-app-tienda`: Vault слага `token-` пред `display_name`) и неговото `permission denied`. Това е, което Иван нямаше в събота: **име и фамилия на всеки опит**.

Кой е чел тайната на магазина?

```
$ jq -c "select(.type == \"response\" and .request.path == \"secret/data/tienda/postgres\" and .request.operation == \"read\") | {quien: .auth.display_name, error}" vault/logs/audit.log
{"quien":"root","error":null}
...
{"quien":"token-app-tienda","error":null}
```

Няколко четения от `root` (ти, докато настройваш) и едно от приложението.

Сега интересното. Записал ли е журналът паролата?

```
$ jq -c "select(.type == \"response\" and .request.path == \"secret/data/tienda/postgres\" and .auth.display_name == \"token-app-tienda\") | .response.data" vault/logs/audit.log | head -1
{"data":{"password":"hmac-sha256:bbda6f946e50152cf8b72cd5a9716a077096420551a4c5a7cb395e4f7eddd734","usuario":"hmac-sha256:becdf07b09b37a0b8d310c8f5e99dac229b4cc1b80e092e4b9107ee0f7483212"},"metadata":{...}}
$ grep -c "Mango-2026" vault/logs/audit.log
0
```

Не. По подразбиране Vault записва в журнала **отпечатък** (HMAC-SHA256) на чувствителните текстови стойности, а не самата стойност ([Audit devices](https://developer.hashicorp.com/vault/docs/audit)). Числата и стойностите да/не не ги превръща в отпечатък; затова е добре във Vault да пазиш текстови тайни, както в тази лаборатория. Отпечатъкът е като пръстов отпечатък на човек: служи, за да провериш дали две неща са едно и също, но не ти позволява да възстановиш човека. Така който прочете журнала, не си отнася паролите.

А ако някой ден ти трябва да разбереш дали паролата, появила се в един чат, е онази, която приложението е прочело, питаш Vault за отпечатъка на този текст и сравняваш:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/sys/audit-hash/archivo \
    -d '{"input": "Mango-2026"}' | jq -r .data.hash
hmac-sha256:bbda6f946e50152cf8b72cd5a9716a077096420551a4c5a7cb395e4f7eddd734
```

Същият отпечатък е. Съвпада.

За финал приложението може да **отнеме собствения си token**, когато приключи. След това вече не му върши работа:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/revoke-self
HTTP 204
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres
{"errors":["2 errors occurred:\n\t* permission denied\n\t* invalid token\n\n"]}
 HTTP 403
```

---

👉 **Ако идваш от бизнес администрацията:** ключовете на Шамир са техническият еквивалент на **съвместните подписи** на банкова сметка: за да се преместят пари, подписват двама от трима упълномощени и никой не може сам. Политиката с 403 е **разделението на задълженията**: който въвежда, не одобрява; който събира, не съгласува. А журналът с отпечатъци е одит, който записва кой е докосвал всяко досие, без да копира досието. Ако ти се налага да преглеждаш контролите на една система, питай за тези три неща с тези думи; почти винаги те разбират.

---

## Упражнения към сесия 2

Решенията са в края.

**Упражнение 6 — Турникетът.** Създай нова папка, `lab-prueba`, и копирай там само три файла: `.gitignore`, `compose.yaml` и `iniciar.sh`. Направи го така, с ново копие, а не като копираш вече ползваната си папка: тя вече има `.env` и упражнението нямаше да докаже нищо. В `lab-prueba` изтрий реда `.env` от `.gitignore` и пусни `./iniciar.sh`.

**Как проверяваш:** преди да пуснеш скрипта, `ls -a` не бива да показва никакъв `.env`. След това трябва да каже `ALTO: .gitignore no tiene la regla '.env'.`, да излезе с код 1 (провери с `echo $?` веднага след това) и **да не** създаде файла `.env` (провери с `ls -a`).

**Упражнение 7 — Пазителите.** Рестартирай Vault с `docker compose restart vault`. Отвори го с ключове 4 и 5 (`.keys[3]` и `.keys[4]`), а после с 1.

а) Има ли значение кои три ключа ползваш?
б) Какво виждаш в `progress` след втория ключ?

**Как проверяваш:** накрая `sys/health` трябва да отговори `200`.

**Упражнение 8 — Собствена тайна с версии.** Запиши в `secret/data/tienda/correo` потребител `avisos` и парола, която генерираш с `openssl rand -hex 12`. После я смени с друга, генерирана по същия начин. Накрая:

а) Прочети версия 1 и 2.
б) Изтрий 2 с `DELETE`, провери 404 и я възстанови.
в) Покажи с `metadata/` колко версии има.

**Как проверяваш:** `current_version` трябва да е `2`, а последното четене трябва да даде втората парола.

**Упражнение 9 — Политика за счетоводството.** Напиши `politicas/contabilidad.hcl`: може да **чете** `secret/data/nomina/*` и да **изброява** `secret/metadata/nomina/*`, нищо повече. Качи я, създай token с нея (запази го в `secretos-locales/`) и изпробвай:

а) Четене на `secret/data/nomina/banco`.
б) Четене на `secret/data/tienda/postgres`.
в) Запис в `secret/data/nomina/banco`.

**Как проверяваш:** а) 200; б) 403; в) 403. А `sys/capabilities-self` за пътя на заплатите трябва да казва `["read"]`.

**Упражнение 10 — Детективът.** С `jq` върху `vault/logs/audit.log` извади списък на **всички отговори с грешка**, като показваш кой и кой път.

**Как проверяваш:** трябва да се появят поне двата 403 на `token-app-tienda` от стъпка 9 и двата 403 от упражнение 9 (б и в). Ако списъкът ти е празен, провери дали филтрираш по `.type == "response"` и дали питаш за `.error != null`.

---

## Често срещани грешки (и как да ги забележиш)

| Грешка | Как изглежда | Как да я забележиш | Какво да направиш |
|---|---|---|---|
| Забравен `data/` в пътя на KV v2 | `curl .../v1/secret/tienda/postgres` дава 404 със съобщение `Invalid path for a versioned K/V secrets engine` | В пътя няма `data/` | Данни в `secret/data/...`; версии в `secret/metadata/...` |
| Политика, написана без `data/` | Сложил си `path "secret/tienda/*"` и token-ът получава 403 за своето | `sys/capabilities-self` казва `deny` | Политиката ползва пътя на API: `secret/data/tienda/*` |
| Vault запечатан след рестарт | Всичко отговаря `{"errors":["Vault is sealed"]}` с код 503 | `sys/seal-status` казва `sealed: true` | Отвори го с 3 ключа. Така трябва да е, не е повреда |
| Празна променлива `VAULT_TOKEN` | 403, макар да ползваш root token-а | `echo ${#VAULT_TOKEN}` дава `0` | Всеки нов терминал започва без променливи: експортирай я отново |
| Единични кавички около променлива | `-d '{"key": "$LLAVE"}'` праща текста `$LLAVE` | Vault казва, че ключът не е валиден | Вътре в единични кавички терминалът не замества променливи. Ползвай двойни кавички и екранирай вътрешните: `"{\"key\": \"$LLAVE\"}"` |
| Token, залепен във файл на хранилището | Token-ът се появява в `git status` или в commit | `git log -p -S hvs.` го намира | Token-ите живеят в `secretos-locales/` и в променливи на терминала. Ако е качен: отнеми го |
| Зает порт при стартиране | `bind: address already in use` | `lsof -nP -iTCP:5432 -sTCP:LISTEN` показва друг процес (замени 5432 с 8200 или 3306, ако е друга услуга) | Смени порта в `.env` (`PUERTO_POSTGRES=15432`, `PUERTO_VAULT` или `PUERTO_MARIADB`) и пусни отново `docker compose up -d`; ако си сменил `PUERTO_VAULT`, дефинирай пак `VAULT_ADDR` |

---

## Преговор за следващата сесия

Сесия 3 започва с тези три въпроса. Отговори, без да гледаш:

1. Защо Vault стартира запечатан и колко ключа ти трябват по подразбиране, за да го отвориш?
2. Един token получава 403. Кои са две възможни причини и кой маршрут на Vault ти казва какво може да прави този token?
3. Ако някой открадне одитния журнал, отнася ли паролите? Защо?

🔁 **Следващата седмица:** откраднатото резервно копие съдържаше осем хиляди CURP, а ключът за четенето им беше до тях. Учиш се да шифроваш с Vault, без програмата ти някога да има ключа, записваш шифрованите данни в PostgreSQL и откриваш колко пъти е било изтеглено това копие.

**Преди да тръгнеш:** изключи лабораторията с `docker compose stop`. Данните ти остават в папките. Следващия път `docker compose start` и отвори печата с цикъла от стъпка 5.

---

## Решения (не ги гледай, преди да опиташ)

**Преговор на сесия 1.**

1. Кои да е четири от: паролата в кода или във файл, който се качва; `.env`, който пътува по чата; една и съща парола за всички и завинаги; никой не знае кой я е използвал; който си е тръгнал, още я знае; ключът за шифроване до данните.
2. Защото git пази историята: паролата остава в предишните промени и всеки, който е клонирал хранилището, има копие. Изтриването не отменя копията; смяната на паролата ги прави безполезни.
3. Прилича в това, че изпращаш данни и получаваш шифровани данни, без ключът да излиза. Различава се в това, че HSM е физическо устройство със защита срещу злоупотреба (колко силна е зависи от модела), а Vault е софтуер на сървър; Transit е механизъм на Vault, който предлага операциите по шифроване през API.

**Упражнение 6.** Изходът е:

```
ALTO: .gitignore no tiene la regla '.env'.
Sin ella, las contraseñas que voy a generar podrían terminar en git. No sigo.
```

`echo $?` дава `1`, а `ls -a` не показва `.env`.

**Упражнение 7.** а) Няма значение: върши работа всяка комбинация от 3 от 5. б) `progress: 2` и `sealed: true`. С третия — `sealed: false`.

**Упражнение 8.** Един начин:

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

Първите две дават `1` и `2`; двете четения с `?version=` показват първата и втората парола; `DELETE` дава `204`, следващото четене `404`, а `current_version` дава `2`. Последният ред печата `true`, ако последното четене върне втората парола. Обърни внимание, че тези пароли никога не си ги писал ти: излязоха от `openssl` и пътуваха в променлива.

**Упражнение 9.** Политиката:

```hcl
path "secret/data/nomina/*" {
  capabilities = ["read"]
}
path "secret/metadata/nomina/*" {
  capabilities = ["list"]
}
```

Качва се и се ползва като `lectura-tienda`, като се сменя името. Очакваните резултати: 200, 403, 403.

**Упражнение 10.**

```
jq -c 'select(.type == "response" and .error != null) | {quien: .auth.display_name, ruta: .request.path, error}' vault/logs/audit.log
```

Обърни внимание, че тук филтърът е в единични кавички и затова двойните кавички вътре нямат обратна наклонена черта.

---

## Какво следва

В сесия 3 ползваш PostgreSQL от терминала си с `psql`. Провери, че го имаш, с `psql --version`. Ако не, инсталирай клиента: `sudo apt install postgresql-client` в Linux или `brew install libpq` в macOS (и следвай указанието, което дава, за добавянето му в `PATH`).

---

*Пиша от онова, което виждаме всеки ден в Hábil, където изграждаме системи за банки, застрахователи и компании в Мексико. Ако в работата си или в семейния бизнес се сблъскате с такъв проблем, нека си поговорим: [habil.mx](https://www.habil.mx/bg/)*
