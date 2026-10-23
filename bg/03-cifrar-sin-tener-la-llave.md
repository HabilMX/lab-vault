# Vault от нулата (3): шифроване, без да държиш ключа

*Механизмът Transit на Vault шифрова и дешифрова вместо теб, а ключът никога не стига до програмата ти. Записваш шифровани CURP в PostgreSQL, ротираш ключа, без да губиш нищо, и се учиш да изтриваш данни, като унищожиш един ключ.*

*Vault от нулата · сесия 3 от 4*

## Преговор на сесия 2

Отговори, без да гледаш. Отговорите са в решенията.

1. Защо Vault стартира запечатан и колко ключа ти трябват по подразбиране, за да го отвориш?
2. Един token получава 403. Кои са две възможни причини и кой маршрут на Vault ти казва какво може да прави този token?
3. Ако някой открадне одитния журнал, отнася ли паролите? Защо?

> **Лабораторията на тази сесия** е в публичното хранилище [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Първо я изгради сам; хранилището е за сравнение, когато нещо не ти излезе същото. Не съдържа нито една парола: лабораторията ги генерира при стартиране.

## Цели на тази сесия

| # | Накрая можеш да… | Доказва се с |
|---|---|---|
| 1 | **Шифроваш и дешифроваш** стойност с Transit, като ползваш `curl`, и **обясниш** какво е base64 и защо не е шифроване | Упражнение 11 |
| 2 | **Ротираш** ключ и **обвиеш наново** (rewrap) стари данни към новата версия, без сам да ги дешифроваш | Упражнения 12 и 14 |
| 3 | **Напишеш** политика, която позволява шифроване, но не и дешифроване, и **провериш** 403 | Упражнение 13 |
| 4 | **Запишеш** шифровани данни в PostgreSQL с `psql` и **докажеш**, че който чете таблицата, не вижда стойността | Стъпка 8 (с водене) и упражнение 14 |
| 5 | **Обвържеш** шифровани данни с техния собственик чрез `context` и **унищожиш** ключ, за да направиш нечетливо онова, което е шифровал | Упражнение 15 и стъпка 10 |

---

## Сценарий (измислица) — Глава 7: понеделник, 10:12

Иван не е спал добре през уикенда. Часовникът на 3:17 не го оставя на мира.

В понеделник иска от доставчика на сървъра пълния журнал на изтеглянията от папката с резервните копия. Не този за една седмица: този за целия живот на сървъра. Получава текстов файл с хиляди редове. Филтрира го по адреса `185.xx.xx.xx`.

Първото изтегляне от този адрес не е било миналата събота.

Било е преди две години и три месеца.

И оттогава, **всяка събота в 3:21**, някой е теглил копието от нощта. И папката с `llave.txt`. Сто и седемнайсет поредни съботи.

Валерия, която най-накрая си призна за публичното хранилище, усеща как гърдите ѝ олекват. Нейната грешка беше преди десет дни. Това трае две години.

— Значи не е било заради онова, което качих — казва тя.

— Не — отговаря Иван. — И онова, което качи, беше сериозно, и затова сменихме всичко. Но това е друго нещо.

Доня Клара задава неудобния въпрос:

— А колко пъти са взели CURP?

— Сто и седемнайсет.

---

## Глава 8: понеделник, 16:50

Докато Иван преработва шифроването на CURP, Росио, счетоводителката, влиза в офиса с извлечение от картата на фирмата. Прави месечното съгласуване и има една такса, която никога не е разбирала:

```
SERV VIRTUAL CLOUD  TR-REPORTES     USD 9.99
```

— Така е от около две години — казва тя. — Винаги съм мислила, че е нещо ваше.

Иван търси в таблото на доставчика адреса на сървъра, който плаща тази такса.

`185.xx.xx.xx`.

TR.

*(Продължава в сесия 4.)*

---

## Защо е важно

Проблем номер 6 от сесия 1 беше ключът до данните. Canasta Morada шифроваше CURP, да, но който отнесе резервното копие, отнесе и `llave.txt`, и шифроването не помогна с нищо.

Решението не е да се скрие файлът по-добре. То е **ключът да не е в никакъв файл, който програмата може да чете**. Програмата казва на Vault „шифровай ми това“ и получава шифрованата стойност. Казва му „дешифровай ми това“ и, ако има право, получава оригиналната стойност. Ключът остава във Vault, защитен от печата, който отвори миналата седмица с три ключа.

Това е механизмът **Transit**. Документацията го описва като „криптография като услуга“ или „шифроване като услуга“ и уточнява, че Vault **не пази** данните, които му изпращаш: резултатът го пазиш, където поискаш ([Transit](https://developer.hashicorp.com/vault/docs/secrets/transit)).

Така, ако утре някой отнесе резервното копие на базата данни, ще отнесе текстове като `vault:v2:SmfKDK1u...`. Без достъп до Vault те не му вършат работа.

## Три думи, преди да започнем

**Шифроване.** Смесване на стойност с **ключ**, така че само който има ключа, да може да я прочете отново. Когато като дете си писал съобщения с код, като заменяш всяка буква със следващата в азбуката, ключът е бил „една буква напред“. Transit ползва по подразбиране AES-256 в режим GCM, който е много по-силен и освен това открива дали някой е променил шифрованата стойност ([API на Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)).

**Base64.** Начин да запишеш всякакви данни, дори двоични, като ползваш само букви, цифри, `+`, `/` и `=`. Transit иска данните в base64, защото така произволна стойност (текст, малка картинка) може да пътува вътре в JSON. Внимавай с размера: API на Vault по подразбиране ограничава всяка заявка до 32 МБ, а base64 прави данните с една трета по-големи. За големи файлове се шифрова с друга техника, а не като се пращат цели на Transit. **Base64 не е шифроване.** Все едно детската тайна реч, в която след всяка сричка се вмъква „фа“: „мафамафа“ вместо „мама“ изглежда тайно, но всеки, който знае правилото, го чете. Опитай:

```
$ echo -n "PEPE000101HDFXXX01" | base64
UEVQRTAwMDEwMUhERlhYWDAx
$ echo "UEVQRTAwMDEwMUhERlhYWDAx" | base64 -d; echo
PEPE000101HDFXXX01
```

`-n` на `echo` не позволява в края да се вмъкне нов ред; без него би шифровал „CURP + Enter“. CURP в този урок са измислени и не съответстват на никой човек; носят `XXX`, за да си личи. Не ползвай данни на реални хора в упражненията си.

**Версия на ключ.** Един ключ на Transit може да има няколко версии. Когато го **ротираш**, се ражда нова версия, която се използва за шифроване на онова, което идва; старите остават, за да може да се дешифрира онова отпреди. Все едно да сменяш всяка година комбинацията на катинара на склада, като пазиш предишните комбинации в плик, в случай че се появи някоя стара кутия.

---

## Стъпка 1 — Стартирай лабораторията и включи Transit

**Два елемента на терминала, които ще ползваш непрекъснато.** `ИМЕ=$(команда)` изпълнява `команда` и записва резултата ѝ в `ИМЕ`. `$ИМЕ` вмъква после този резултат. Опитай: `SALUDO=$(echo hola); echo "$SALUDO"` трябва да покаже `hola`. В следващия блок `LLAVE=$(...)` записва временно ключ за отключване; ако нещо не стане, провери дали `LLAVE` не е останала празна, с `echo "${#LLAVE}"` (трябва да даде число, по-голямо от 0).

Ако си изключил лабораторията, включи я, отвори печата и експортирай token-а, както в сесия 2:

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

Включи механизма Transit на пътя `transit/`:

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/transit -d '{"type": "transit"}'
HTTP 204
```

**Проверка на състоянието.** `docker compose stop` запазва Transit, ключовете и таблицата. Ако при монтирането на Transit получиш `HTTP 400` с `path is already in use`, значи вече е бил монтиран: продължи със стъпка 2. Ако ключът `curp` или таблицата `clientes` вече съществуват, не повтаряй вмъкванията от стъпка 8. Първо виж какво има, с `psql -c "SELECT id, nombre, left(curp, 9) FROM clientes;"`, и продължи само ако разпознаваш тези редове като предишна работа.

## Стъпка 2 — Създай ключ

Ключ на име `curp`. Не пращаш нищо: Vault го генерира вътре.

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp
HTTP 200
```

Погледни го:

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

Обърни внимание на онова, което **не** се появява: ключът. В `keys` има само по едно число за версия, което е датата на създаването ѝ. `exportable: false` казва, че не може да се изнесе. Провери:

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/export/encryption-key/curp
{"errors":["private key material is not exportable"]}
 HTTP 400
```

Дори root token-ът не може да го изнесе. Ако при създаването беше поискал `exportable: true`, щеше да може, а това решение няма връщане; затова е изключено по подразбиране.

## Стъпка 3 — Шифроване

Пращаш текста в base64 вътре в `plaintext`. `$(...)` прави преобразуването в момента:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq .data
{
  "ciphertext": "vault:v1:A2se3zo5aKjY51c/tlquYpJrN/L8DDNh2BPzqvcrXfYwkW8yVVimMMzir5DRpw==",
  "key_version": 1
}
```

Този `ciphertext` е онова, което ще запазиш. Има три части, разделени с двоеточия:

- `vault`: шифровано от Vault.
- `v1`: с **версия 1** на ключа.
- Останалото: шифрованата стойност.

Шифровай **същото CURP отново**:

```
vault:v1:qy8hRw2+KeTOHWr/RJ7D4tPbSlRDiTk96lZGn9+Jijp+lJRyUlfZph3upajdFw==
```

Различно е. Всяко шифроване носи случайна съставка (*nonce*) и затова две шифрования на една и съща стойност никога не си приличат. Така никой не може да погледне таблицата и да каже „тези двама клиенти имат еднакво CURP“. (Transit има режим, наречен *convergent*, който прави обратното, нарочно, за да може да се търси; тук не го ползваме.)

## Стъпка 4 — Дешифроване

Пращаш `ciphertext` и получаваш base64:

```
$ C=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext)
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$C\"}" | jq .data
{
  "plaintext": "UEVQRTAwMDEwMUhERlhYWDAx"
}
```

И го връщаш в текст с `base64 -d`:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$C\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

Ако някой ти подаде боклук с вид на шифроване, Vault не гадае:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"vault:v1:estonoescifrado\"}"
{"errors":["invalid ciphertext: could not decode base64"]}
 HTTP 400
```

## Стъпка 5 — Ротация на ключа, без да губиш нищо

Запиши във файл шифроване, направено с версия 1, за да го ползваш по-късно:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext | tee v1.txt
vault:v1:0uoMoZKeXU+18t3TiH3yOlTX7vL9wlNUWlMf1W4XapYdoVq2Z1OWVAg7hIgWlA==
```

`tee` показва резултата на екрана и освен това го записва във файла. Сега **ротирай**:

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp/rotate
HTTP 200
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp | jq -c ".data | {latest_version, min_decryption_version, versiones: (.keys | keys)}"
{"latest_version":2,"min_decryption_version":1,"versiones":["1","2"]}
```

Новото излиза с `v2`:

```
vault:v2:uzo5CXHaWgjXF3iUCzzefTFzOecaAcho3WjVJqnjVJ0IQIR3mk1DioElROdsxA==
```

А старото **още се дешифрова**, защото версия 1 още е запазена:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

Ротацията не чупи нищо. Затова може да се прави често; има дори `auto_rotate_period`, за да ротира Vault ключ сам през определено време.

## Стъпка 6 — Обвиване наново (rewrap): качване на старото към новата версия

Ротацията не променя онова, което вече е записано: базата ти си остава пълна с `v1`. За да ги качиш към `v2`, има **rewrap** (обвиване наново): даваш му старото шифроване и той ти връща ново с последната версия. Документацията уточнява, че при този процес **оригиналната стойност не се разкрива** ([Transit](https://developer.hashicorp.com/vault/docs/secrets/transit)): нито ти, нито програмата ти виждате CURP.

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/rewrap/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}" | jq -c .data | tee rewrap.json
{"ciphertext":"vault:v2:qR2K9Q5TmpKsG4umLEMX2bguVD1/R4nC+iNhKxAT5jrKGAc1clF5977n49Q85w==","key_version":2}
```

Все едно да занесеш старите си документи при нотариуса, за да им сложи новия печат, без никой да ги чете.

Когато вече си обвил наново всичко, казваш на Vault **да не приема** шифрования, по-стари от версия 2:

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/curp/config -d '{"min_decryption_version": 2}'
HTTP 200
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}"
{"errors":["ciphertext or signature version is disallowed by policy (too old)"]}
 HTTP 400
```

`v1` вече не върши работа. Обвитият наново — да:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(jq -r .ciphertext rewrap.json)\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

Това е, от което Canasta Morada имаше нужда: ако някое старо копие на базата данни се мотае някъде, с шифрования `v1`, при тази конфигурация то вече не може да се дешифрова. Внимание: **това не е криптографско изтриване**. Vault още пази версия 1 на ключа и упълномощен оператор би могъл отново да смъкне минимума, за да позволи дешифрирането ѝ (документацията го описва като настройка, част от политиката за ротация). Истинското унищожаване на ключ е стъпка 10.

## Стъпка 7 — Политика, която шифрова, но не дешифрова

Формулярът за регистрация на клиенти има нужда да **шифрова** CURP. Никога няма нужда да ги чете. Създай `politicas/solo-cifrar-curp.hcl`:

```hcl
# El formulario de alta puede CIFRAR curps, pero nunca descifrarlas.
path "transit/encrypt/curp" {
  capabilities = ["update"]
}
```

В Transit шифроването и дешифроването са операции за запис (`POST`), а в политиките това се нарича `update`. За този ключ, който вече съществува, `update` е минималната правилна възможност. Внимание: маршрутът `transit/encrypt/<ключ>` приема `create` или `update`, а с `create` Vault може да създаде ключ, който не е съществувал, със стойности по подразбиране, освен ако това автоматично създаване не е изключено ([Transit: Encrypt data](https://developer.hashicorp.com/vault/api-docs/secret/transit#encrypt-data)). Не извеждай възможността на политиката само от HTTP глагола.

Качи я и създай token за формуляра. Трае 3 часа, колкото трае сесията с упражненията; ако изтече по-рано, един 403 би приличал на 403, който търсиш в упражнение 13:

```
$ jq -n --rawfile p politicas/solo-cifrar-curp.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/solo-cifrar-curp -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/create \
    -d '{"policies": ["solo-cifrar-curp"], "ttl": "3h", "display_name": "formulario-alta"}' \
    | jq -r .auth.client_token > secretos-locales/token-formulario.txt
```

Формулярът шифрова CURP на нова клиентка:

```
$ F=$(cat secretos-locales/token-formulario.txt)
$ curl -s -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n MARA990909MDFXXX02 | base64)\"}" | jq -r .data.ciphertext | tee maria.txt
vault:v2:4LM7LCPcgym6rQAPOMQGWR4DIk1qi4NdtoaBM/yecdQfWsG9iCypdv7IST71dQ==
```

Но ако се опита да го прочете или да ротира ключа:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat maria.txt)\"}"
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/keys/curp/rotate
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Ако някой открадне token-а на формуляра, може да вкарва шифровани CURP, но не може да прочете нито едно. Това е пощенска кутия: всеки пуска писма, отваря само пощальонът.

## Стъпка 8 — Записване в PostgreSQL

PostgreSQL работи от сесия 2. Паролата му е в `.env`, който скриптът е генерирал. Зареди я в терминала си, без да я преписваш на ръка: `set -a` прави така, че всичко, което прочетеш, да се експортира, а `source .env` чете файла.

```
set -a; source .env; set +a
export PGHOST=127.0.0.1 PGPORT=$PUERTO_POSTGRES PGUSER=postgres PGDATABASE=tienda PGPASSWORD=$POSTGRES_PASSWORD
```

`psql` чете сам тези променливи `PG...`; така не пишеш паролата в командата, където би останала в историята ти. Това е приемливо в локална лаборатория, но `PGPASSWORD` оставя паролата в средата на процеса, а документацията на PostgreSQL не го препоръчва, защото в някои системи други процеси могат да я видят. В продукция се ползва файл с пароли със строги права или, още по-добре, Vault.

Създай таблицата с клиентите:

```
$ psql -c "CREATE TABLE clientes (id serial PRIMARY KEY, nombre text NOT NULL, curp text NOT NULL);"
CREATE TABLE
```

Вмъкни Пепе с шифрованото му CURP. Първо шифроваш, после записваш резултата:

```
$ CIF=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext)
$ psql -c "INSERT INTO clientes (nombre, curp) VALUES ('Pepe', '$CIF');"
INSERT 0 1
```

И Мария, шифрована с token-а на формуляра, който не може да чете:

```
$ F=$(cat secretos-locales/token-formulario.txt)
$ CIF=$(curl -s -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n MARA990909MDFXXX02 | base64)\"}" | jq -r .data.ciphertext)
$ psql -c "INSERT INTO clientes (nombre, curp) VALUES ('María', '$CIF');"
INSERT 0 1
```

Сега погледни таблицата така, както би я видял някой с право за четене (`SELECT`) върху `clientes`, нейният собственик, суперпотребител или който притежава резервното копие. Свързването с базата данни не е достатъчно: в PostgreSQL е нужно това право ([Привилегии](https://www.postgresql.org/docs/17/ddl-priv.html)). Тук работи, защото влязохме като `postgres`:

```
$ psql -c "SELECT * FROM clientes;"
 id | nombre |                                   curp
----+--------+---------------------------------------------------------------------------
  1 | Pepe   | vault:v2:GCD4q2/Fp+YtLKT185oGtoSBJ4M9wE5oKrOaDy93Hlmf84Nzh/4ZxWW+E62chg==
  2 | María  | vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
(2 rows)
```

Казват `v2`, защото си ротирал ключа в стъпка 5. А резервното копие, което отнасяха от Canasta Morada всяка събота:

```
$ docker compose exec postgres pg_dump -U postgres -t clientes tienda | grep -A3 "^COPY"
COPY public.clientes (id, nombre, curp) FROM stdin;
1	Pepe	vault:v2:GCD4q2/Fp+YtLKT185oGtoSBJ4M9wE5oKrOaDy93Hlmf84Nzh/4ZxWW+E62chg==
2	María	vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
\.
```

Нито едно четимо CURP. И вече няма `llave.txt`, който да се отнесе.

Който има право да дешифрова, чете от таблицата и пита Vault:

```
$ CIF=$(psql -At -c "SELECT curp FROM clientes WHERE nombre = 'María';"); echo "$CIF"
vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$CIF\"}" | jq -r .data.plaintext | base64 -d; echo
MARA990909MDFXXX02
```

`-At` иска от `psql` само стойността, без заглавия и рамки.

## Стъпка 9 — Обвързване на шифроването със собственика: `context`

Представи си, че Canasta Morada започва да пази досиета на две фирми, които купуват от нея на едро, Empresa Norte и Empresa Sur, в една и съща таблица. Програмна грешка или злонамерен човек би могъл да вземе шифровано досие на Norte, да го постави в реда на Sur и да поиска да го дешифрират „като на Sur“.

Transit има защита за това: **производните ключове** (*derived keys*). Когато създадеш ключа с `derived: true`, всяка операция трябва да носи `context`: допълнителна стойност, в base64, от която Vault извежда различен ключ. С друг `context` — друг ключ ([API на Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)). Все едно плик, който се отваря само с печата на фирмата, до която е адресиран.

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/expedientes -d '{"derived": true}'
HTTP 200
```

Без `context` отказва:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
    -d "{\"plaintext\": \"$(echo -n diagnostico-confidencial | base64)\"}"
{"errors":["missing 'context' for key derivation; the key was created using a derived key, which means additional, per-request information must be included in order to perform operations with the key"]}
 HTTP 400
```

Шифровай за Empresa Norte:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
    -d "{\"plaintext\": \"$(echo -n diagnostico-confidencial | base64)\", \"context\": \"$(echo -n empresa-norte | base64)\"}" \
    | jq -r .data.ciphertext | tee ctx.txt
vault:v1:8lKFunrcJVIzLnq9q4ZNszSLDOotf4gqtenuKek8QTuCIh4yq1ldoqtjMbsojged+/0aPQ==
```

С правилния `context` се чете:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
    -d "{\"ciphertext\": \"$(cat ctx.txt)\", \"context\": \"$(echo -n empresa-norte | base64)\"}" | jq -r .data.plaintext | base64 -d; echo
diagnostico-confidencial
```

Представяйки се за Empresa Sur:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
    -d "{\"ciphertext\": \"$(cat ctx.txt)\", \"context\": \"$(echo -n empresa-sur | base64)\"}"
{"errors":["cipher: message authentication failed"]}
 HTTP 400
```

`message authentication failed`: проверката на AES-GCM е открила, че това не съвпада. Досието на Norte се отваря само като на Norte. В реалния живот `context` обикновено е идентификаторът на клиента или на фирмата, собственик на данните.

Едно важно уточнение: `context` **не е парола, нито разрешение**. Това е стойност, която подава извикващият; ако някой има право да дешифрова този ключ и знае стойността `empresa-norte`, може да поиска дешифрирането с нея. Затова приложението трябва да взема `context` от надеждна стойност, която не може да се променя (например регистрирания собственик на досието), а политиките трябва да ограничават кой може да дешифрова всеки ключ.

## Стъпка 10 — Изтриване чрез унищожаване на ключа

Последният модел и най-драстичният. Един клиент си тръгва и иска да изтриеш данните му. Те са в базата данни, в резервните копия от снощи, в тези отпреди месец. Да изтриваш във всяко копие е почти невъзможно.

Ако всеки клиент има **собствен ключ**, има друг изход: **да унищожиш ключа**. Всичко, шифровано с него, става нечетливо, където и да е. Това е известно като криптографско изтриване.

Създай ключ за един клиент и шифровай нещо негово:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 200
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/cliente-que-se-va \
    -d "{\"plaintext\": \"$(echo -n datos-de-don-chema | base64)\"}" | jq -r .data.ciphertext | tee borrar.txt
vault:v1:tjerbuHJyEbw+3IiLl0rC/hSEa78E61i9Yg9CancZegxpnBsybXKvkGZ2DwtzQ==
```

Опитай да го изтриеш:

```
$ curl -s -w " HTTP %{http_code}\n" -X DELETE -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
{"errors":["error deleting policy cliente-que-se-va: deletion is not allowed for this key"]}
 HTTP 400
```

Vault не те оставя, по подразбиране. Документацията го нарича „потенциално катастрофална операция“ и изисква първо да включиш `deletion_allowed` ([API на Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)). Това е предпазителят на пистолета. Свали го и изтрий:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/cliente-que-se-va/config -d '{"deletion_allowed": true}'
HTTP 200
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X DELETE -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 204
```

Сега опитай да дешифроваш онова на дон Чема:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/cliente-que-se-va \
    -d "{\"ciphertext\": \"$(cat borrar.txt)\"}"
{"errors":["encryption key not found"]}
 HTTP 400
```

А ако някой създаде друг ключ със същото име?

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 200
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/cliente-que-se-va \
    -d "{\"ciphertext\": \"$(cat borrar.txt)\"}"
{"errors":["cipher: message authentication failed"]}
 HTTP 400
```

Същото име, нов ключ. Старото си остава нечетливо: в базата данни, в копието от снощи и в това отпреди година.

**Едно честно предупреждение.** Това важи за копията на **твоите данни**. Ако пазиш резервни копия **на самия Vault** (на неговата папка с данни), копие, направено преди изтриването, още съдържа ключа. За да е пълно криптографското изтриване, резервните копия на Vault също трябва да изтекат.

### Алтернативата с командата `vault`

```
$ docker compose exec -e VAULT_TOKEN vault vault write transit/encrypt/curp plaintext=$(echo -n PEPE000101HDFXXX01 | base64)
Key            Value
---            -----
ciphertext     vault:v3:7yIAAelQRE+2zGnTO+J0EJcPExHspE4elzod4VDFrTrTSkl4bAYZ9ygbQ25C1Q==
key_version    3
```

(В този опит излезе версия 3, защото упражнения 12 и 14 вече бяха направени. Ако изпълниш тази команда сега, преди упражненията, нормално е твоят резултат да започва с `vault:v2:`. Числото се променя с всяка ротация: не го сравнявай с това от примера, сравнявай го с `latest_version` на ключа `curp`.)

---

👉 **Ако идваш от бизнес администрацията:** шифроването като услуга е същият принцип като **попечителството над ценности**: фирмата за превоз пази парите в брой, ти имаш само разписката, а за да теглиш, ти е нужно разрешение. Политиката „шифрова, но не дешифрова“ е **гишето за депозити**: всеки внася, тегли само упълномощеният. А изтриването чрез унищожаване на ключа има значение за защитата на личните данни: когато един клиент упражни правото си данните му да бъдат заличени, юридическият отдел ще попита „а в резервните копия?“. Тази техника е технически отговор, който може да се демонстрира, но не замества правния анализ: заличаването може да включва период на блокиране преди изтриване, срокове за съхранение и изключения, определени от закона.

---

## Упражнения към сесия 3

**Упражнение 11 — Симулирано CURP.** Измисли симулирано CURP (с `XXX` по средата, като тези от урока). Шифровай го два пъти с ключа `curp` и го дешифровай.

**Подсказка, ако се затрудниш.** От командата в стъпка 3 сменяш само текста, който е вътре в `echo -n`. Запиши резултата с `C=$(... | jq -r .data.ciphertext)`, както в стъпка 4, а за дешифроване преизползвай същата команда, като смениш само `ciphertext` с `$C`.

г) Допълни, без да гледаш: „Base64 е __________. Не е шифроване, защото __________. В това упражнение защитата започва, когато __________.“

**Как проверяваш:** двата `ciphertext` трябва да са различни помежду си, и двата трябва да започват със същото `vault:vN:`, а при дешифроване с `base64 -d` трябва да излезе точно твоето CURP, без допълнителен нов ред. Ако накрая видиш излишен празен ред, си забравил `-n` в `echo`. За точка г) сравни с решението.

**Упражнение 12 — Ротация и rewrap.** Шифровай своето CURP и го запиши в `mio.txt`. Ротирай ключа `curp`. Обвий наново `mio.txt`.

**Как проверяваш:** числото след `vault:v` в обвитото наново трябва да е равно на `latest_version` на ключа (провери с `GET transit/keys/curp`). А обвитото наново трябва да се дешифрова до твоето CURP.

**Упражнение 13 — Пощенската кутия.** С token-а на формуляра (`secretos-locales/token-formulario.txt`):

а) Шифровай едно CURP.
б) Опитай да го дешифроваш.
в) Опитай да шифроваш с друг ключ, `expedientes`.
г) Сега напиши политиката сам. Попълни празните места, без да гледаш стъпка 7:

```hcl
path "transit/____/curp" {
  capabilities = ["____"]
}
```

Качи я с името `solo-cifrar-prueba`, създай с нея пробен token (командите от стъпка 7 със сменени имена) и повтори а), б) и в) с този token.

**Как проверяваш:** а) получаваш `vault:v...`; б) 403; в) 403, защото политиката споменава само `transit/encrypt/curp`. Ако точка а) върне 403, не я смятай за вярна: може token-ът да е изтекъл. Създай друг с командата от стъпка 7, зареди отново `F` и започни пак; проверката важи, откакто шифроването с `F` върне `vault:v...`. В г) `encrypt/curp` работи; `decrypt/curp` и `encrypt/expedientes` дават 403.

**Упражнение 14 — Обвиване наново на цяла таблица.** Ротирай ключа `curp` още веднъж. После мини през таблицата `clientes` и обвий наново всяко CURP.

**Първо, проверка, която не пипа нищо.** Преди всеки `UPDATE` провери дали цикълът чете добре таблицата:

```
psql -At -F " " -c "SELECT id, curp FROM clientes;" | while read ID CIF; do
  echo "ID=$ID | CIF=$CIF"
done
```

`|` подава всеки ред на цикъла, `-F " "` иска от `psql` да раздели колоните с интервал, а `read` слага първата колона в `ID` и втората в `CIF`. Преди да продължиш, трябва да видиш по един ред за всеки клиент.

Сега истинският скелет; допълни го. `if` не позволява, ако Vault се провали, в таблицата да се запише `null` вместо шифрованото CURP:

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

**Как проверяваш:** `psql -c "SELECT id, nombre, left(curp, 9) AS version FROM clientes;"` трябва да показва същата нова версия във всички редове, а всяко CURP трябва да продължава да се дешифрова правилно.

**Упражнение 15 — Грешният плик.** С ключа `expedientes` шифровай думата `credito-aprobado` с context `empresa-sur`. Дешифровай я с `empresa-sur`, после с `empresa-norte` и после без context.

д) Без да изпълняваш ново изтриване, допълни: „Повторното създаване на `cliente-que-se-va` не възстановява шифрованото преди това, защото __________. Преди да разреша изтриването на един ключ, трябва да проверя __________.“

**Как проверяваш:** първото дава `credito-aprobado`; второто — `cipher: message authentication failed`; третото — `missing 'context' for key derivation`. Точка д) се сравнява с решението.

---

## Често срещани грешки (и как да ги забележиш)

| Грешка | Как изглежда | Как да я забележиш | Какво да направиш |
|---|---|---|---|
| Да пратиш текста без base64 | Обикновено излиза `{"errors":["illegal base64 data at input byte N"]}` с код 400. Но ако текстът случайно е валиден base64, Vault го приема и шифрова други байтове от тези, които си искал | Стойността на `plaintext` изглежда като оригиналния ти текст | Винаги `$(echo -n ТЕКСТ | base64)` |
| Да забравиш `-n` в `echo` | При дешифроване се появява излишен празен ред | Base64 завършва различно: `...WDAxCg==` вместо `...WDAx` | `echo -n` не добавя новия ред |
| Да вярваш, че base64 е шифроване | „Вече е защитено, изглежда странно“ | `base64 -d` го чете всеки | Base64 е само начин на запис. Шифроването го прави Transit |
| Да вдигнеш `min_decryption_version`, преди да обвиеш наново | Старите данни дават `disallowed by policy (too old)` | В таблицата има редове с `vault:v1:` | Първо обвий наново всичко; вдигни минимума накрая. Ако ти се е случило и още имаш шифрования `v1`: повтори командата за настройка от стъпка 6 с `{"min_decryption_version": 1}`, потвърди, че `v1.txt` отново се дешифрова, обвий наново всичко и едва накрая вдигни минимума до новата версия |
| Политика на Transit с `read` | Token-ът получава 403 при шифроване | `sys/capabilities-self` не казва `update` | Шифроването и дешифроването са `update` |
| Производен ключ без `context` | `missing 'context' for key derivation` | Ключът казва `derived: true` | Пращай винаги същия `context`, в base64, за шифроване и дешифроване |
| Изтриване на ключ „за проба“ | Всичко, шифровано с него, става нечетливо завинаги | `encryption key not found` | Няма връщане. Затова съществува `deletion_allowed`: дръж го изключен, освен когато наистина искаш да унищожиш |

---

## Преговор за следващата сесия

Сесия 4 започва с тези три въпроса. Отговори, без да гледаш:

1. Какво означават трите части на `vault:v2:SmfKDK1u...`?
2. Ротирал си ключа. Какво става с данните, които вече са били шифровани, и коя операция ги качва към новата версия, без никой да види стойността?
3. Защо един token, който може само да шифрова, е полезен за формуляр за регистрация?

🔁 **Следващата седмица:** Canasta Morada открива чий е сървърът `185.xx.xx.xx`. Ти правиш така, че паролите на PostgreSQL и MariaDB да се раждат, да изтичат и да се сменят сами, и пишеш програма на Python, която се свързва с базата данни, без да знае никаква парола.

**Преди да тръгнеш:** `docker compose stop`. Следващия път `start`, отвори печата и експортирай token-а.

---

## Решения (не ги гледай, преди да опиташ)

**Преговор на сесия 2.**

1. Защото данните му са шифровани на диска с главен ключ, който не пази цял: разделен е на парчета (Shamir). По подразбиране са 5 парчета и трябват 3.
2. Че политиката не включва този маршрут или тази възможност (например маршрута без `data/`), или че token-ът е изтекъл или е бил отнет. `sys/capabilities-self` ти казва какво може да прави token-ът на всеки маршрут.
3. Не, при конфигурацията по подразбиране. Vault записва отпечатък (HMAC-SHA256) на повечето чувствителни текстови стойности, а не самата стойност; служи за сравнение, не за възстановяване. Проверявай винаги конфигурацията на одитното устройство, преди да го приемеш за даденост: с `log_raw=true`, с атрибути, изключени от отпечатване, или със стойности, които не са текст, данните могат да останат неприкрити ([Одит](https://developer.hashicorp.com/vault/docs/audit)).

**Упражнение 11.** С примерно CURP, `ABCD020202HDFXXX03`:

```
curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
  -d "{\"plaintext\": \"$(echo -n ABCD020202HDFXXX03 | base64)\"}" | jq -r .data.ciphertext
```

Два пъти дават два различни текста със същия префикс. За да дешифроваш, командата от стъпка 4 с твоя `ciphertext`.

Точка г): „Base64 е начин за записване на данни (кодиране). Не е шифроване, защото всеки може да го обърне. В това упражнение защитата започва, когато Transit шифрова стойността с ключа.“

**Упражнение 12.** Ротираш с `POST transit/keys/curp/rotate`, обвиваш наново с `POST transit/rewrap/curp`, като пращаш `{"ciphertext": "<съдържанието на mio.txt>"}`. Ако преди последната версия е била 2, след ротацията е 3 и обвитото наново започва с `vault:v3:`.

**Упражнение 13.** а) Както в стъпка 7. б) и в) `{"errors":["1 error occurred:\n\t* permission denied\n\n"]}` с `HTTP 403`. г) Празните места са `encrypt` и `update`: същата политика като в стъпка 7 с друго име.

**Упражнение 14.** Празните места са `rewrap` и `$ID`. Всяка ротация създава нова версия: ако преди това си направил упражнение 12, тази ротация води ключа до версия 4 и ще видиш `vault:v4:`; ако не, до 3. В опита към този урок, след ротация до версия 3:

```
 id | nombre |  version
----+--------+-----------
  1 | Pepe   | vault:v3:
  2 | María  | vault:v3:
(2 rows)
```

Никой не видя нито едно CURP по време на процеса: нито ти, нито терминалът, нито цикълът. Ако `if` отпечата „No actualicé“, този ред е останал както си е бил; поправи проблема и пусни цикъла отново.

**Упражнение 15.**

```
CTX_SUR=$(echo -n empresa-sur | base64)
C=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
  -d "{\"plaintext\": \"$(echo -n credito-aprobado | base64)\", \"context\": \"$CTX_SUR\"}" | jq -r .data.ciphertext)
curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
  -d "{\"ciphertext\": \"$C\", \"context\": \"$CTX_SUR\"}" | jq -r .data.plaintext | base64 -d; echo
```

За другите две смени context с `$(echo -n empresa-norte | base64)` или махни полето `context`. Грешките са тези от стъпка 9.

Точка д): „защото новият ключ е различен криптографски материал, дори да носи същото име“; „че ключът е само на този клиент и че някой с власт е разрешил унищожаването му, защото няма връщане“.

---

## Какво следва

В сесия 4 ползваш и клиента на MariaDB. Провери го с `mariadb --version`. Ако го нямаш: `sudo apt install mariadb-client` в Debian или Ubuntu (в други дистрибуции на Linux — пакетният мениджър, който ползва твоята), или `brew install mariadb` в macOS. А за крайния скрипт — Python 3.10 или по-нов: `python3 --version`.

---

*Пиша от онова, което виждаме всеки ден в Hábil, където изграждаме системи за банки, застрахователи и компании в Мексико. Ако в работата си или в семейния бизнес се сблъскате с такъв проблем, нека си поговорим: [habil.mx](https://www.habil.mx/bg/)*
