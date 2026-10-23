# Vault do zero (4): senhas que mudam sozinhas

*Usuários de banco de dados que nascem quando são pedidos e morrem em dois minutos, senhas que rotacionam a cada minuto sem que ninguém edite um arquivo, e um programa em Python que se conecta ao PostgreSQL sem conhecer nenhuma senha. E o fim do mistério das 3:17.*

*Vault do zero · sessão 4 de 4*

## Revisão da sessão 3

Responder sem consultar. As respostas estão nas soluções.

1. O que significam as três partes de `vault:v2:SmfKDK1u...`?
2. A chave foi rotacionada. O que acontece com os dados que já estavam cifrados, e qual operação os sobe para a versão nova sem que ninguém veja o dado?
3. Por que um token que só pode cifrar é útil para um formulário de cadastro?

> **O laboratório desta sessão** está no repositório público [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Monte-o primeiro por conta própria; o repositório serve para comparar quando algo não sair igual. Não traz nenhuma senha: o laboratório as gera ao iniciar.

## Objetivos desta sessão

| # | Ao terminar, é possível… | Demonstrado no |
|---|---|---|
| 1 | **Configurar** o motor Database do Vault com um usuário dedicado, sem usar o superusuário | Passos 2 e 3 |
| 2 | **Pedir** credenciais dinâmicas, **entrar** com `psql` e **comprovar** que deixam de servir ao expirar ou ao serem revogadas | Exercícios 16, 17 e 19 |
| 3 | **Colocar** um usuário existente sob rotação automática e **demonstrar** que a senha antiga já não entra | Exercício 18 |
| 4 | **Criar** uma credencial dinâmica somente de leitura no MariaDB com o cliente `mariadb`, comprovar que ela não consegue modificar dados e revogá-la | Passo 10 |
| 5 | **Executar e modificar** um script em Python que pede as credenciais ao Vault, consulta o PostgreSQL e não guarda nenhuma senha de banco de dados | Passo 12 e exercício 20 |

---

## Cenário (ficção) — Capítulo 9: terça-feira, 9:00

Iván disca um número que não discava havia oito meses.

— Toño? É o Iván, da Canasta Morada. Escuta, uma pergunta estranha. Te lembra algum servidor chamado TR-REPORTES?

Silêncio. Depois, uma gargalhada.

— Não acredito! Ainda está ligado?

Toño conta sem constrangimento. Há dois anos e meio, a contabilidade pediu um relatório semanal dos clientes que pagam com vale-alimentação, com o CURP, para conferir com a empresa dos vales. O banco de dados ficava muito carregado durante o dia, então Toño alugou um servidor barato na nuvem, com o cartão da empresa, e colocou nele um programa:

- Todo sábado às 3:17 ele se conectava ao banco de dados com a senha do `app_tienda`.
- Baixava o backup da noite e o `llave.txt`, para decifrar os CURP.
- Montava um Excel e o mandava para o e-mail `reportes@`.

— E quando saí, esqueci de avisar. Desculpa.

Rocío confere: a caixa `reportes@` tem cento e dezessete e-mails sem abrir. Ninguém a olhava desde que o chefe de contabilidade anterior saiu.

Não havia nenhum ladrão.

Havia algo pior: uma porta aberta que ninguém sabia que existia. Cento e dezessete cópias de oito mil CURP, com a chave ao lado, num servidor que ninguém controlava, em outro país, pago todo mês com o cartão da empresa.

E, sem log por identidade nem credenciais que expiram, era impossível distinguir aquilo de um ataque.

---

## Capítulo 10: sábado, 3:17. Um mês depois

O servidor TR-REPORTES não existe mais; Iván o apagou com o Toño em videochamada, olhando juntos cada pasta.

O relatório dos vales agora é feito por um programa novo, dentro dos servidores da Canasta Morada. Às 3:17 ele pede ao Vault uma credencial para o banco de dados. O Vault cria um usuário que não existia um segundo antes, com permissão só de leitura e com data de expiração. O programa trabalha quatro minutos. Às 3:21 o usuário já não existe.

A senha do banco de dados que o Vault usa para criar esses usuários ninguém sabe: nem Iván, nem dona Clara. O Vault a trocou no primeiro dia.

O celular de Iván não vibra.

Valeria escreve o relatório do incidente. Na última linha, coloca: *«Nunca vamos saber se alguém viu o repositório público naquelas horas. Por isso trocamos a senha. Da próxima vez que alguém enviar um `.env` por engano, ali não estará a senha da aplicação nem a do Vault. Mesmo assim, o que esse arquivo contiver — como as senhas de administração — precisa ser trocado imediatamente.»*

*(Fim do cenário.)*

---

## Por que isso importa

Nas sessões 2 e 3, os segredos já não viviam em arquivos, mas continuavam sendo **os mesmos durante meses**. Se alguém lesse a senha do `app_tienda` no Vault, ela servia até que alguém a trocasse manualmente.

Hoje se dá o último passo: **senhas que não existem até que sejam pedidas e que morrem sozinhas**. É a diferença entre a chave de casa e o crachá de visitante de um prédio comercial. A chave serve por anos. O crachá é entregue na recepção com o nome da pessoa, abre só o andar aonde ela vai e às 6 da tarde deixa de funcionar. Se for perdido no elevador, ninguém se importa.

## As ideias de hoje

**Credencial dinâmica.** Um usuário de banco de dados que o Vault cria no momento em que é pedido, com uma senha aleatória, e que apaga quando expira. Cada programa, e cada vez que pede, recebe um diferente. Se vazar, serve por minutos.

**Concessão (*lease*) e TTL.** Cada credencial dinâmica vem com uma concessão: um contrato com data de vencimento. O **TTL** (*time to live*, tempo de vida) é quanto ela dura. Como o estacionamento do shopping: o tíquete marca a hora de entrada e vence; para mais tempo, paga-se de novo (renova-se), até um máximo.

**Revogar.** Cancelar uma concessão antes do tempo. O Vault apaga o usuário do banco de dados naquele momento.

**Papel estático com rotação.** Há usuários que não dá para trocar por um novo a cada vez, porque outros sistemas os conhecem pelo nome. Para esses, o Vault conserva o usuário e **troca a senha** de tempos em tempos, com `rotation_period`. Quem precisa dela a pede ao Vault e sempre recebe a vigente ([Database secrets engine](https://developer.hashicorp.com/vault/docs/secrets/databases)).

**A credencial do Vault no banco de dados.** Para criar e apagar usuários, o Vault precisa de um usuário próprio no banco de dados. A documentação adverte que, se o Vault for instruído a rotacionar essa senha com `rotate-root`, depois **ninguém** vai conhecê-la, e recomenda criar um usuário dedicado ao Vault em vez de usar o superusuário ([API do motor Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). É o que fazemos: um usuário `vault_admin` com as permissões justas, e não o `postgres`, que pode tudo.

---

## Passo 1 — Preparar o terminal

Laboratório no ar, selo aberto, token exportado e variáveis do PostgreSQL carregadas a partir do `.env`:

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

Reparar que desta vez **não** se exporta `PGUSER` nem `PGPASSWORD`: hoje a entrada no PostgreSQL será feita com vários usuários diferentes, e cada comando dirá qual.

As saídas desta lição são reais, mas vêm de execuções independentes; por isso as horas, os nomes de usuário e os números de versão (como `vault:v3:`, que depende de quantas vezes a chave foi rotacionada na sessão 3) não formam uma sequência única. As saídas de quem praticar serão diferentes.

## Passo 2 — Um usuário para o Vault, e um antigo para rotacionar

Criar no PostgreSQL dois usuários, com uma senha inicial gerada ao acaso e guardada em `secretos-locales/` (o git a ignora):

- `vault_admin`: o que o Vault usará. Pode criar usuários (`CREATEROLE`) e dar permissão de leitura sobre as tabelas (`WITH GRANT OPTION`). Não é superusuário.
- `reportes`: um usuário «de longa data», como o que os relatórios usam. Será colocado sob rotação automática.

Cada um recebe a **própria** senha inicial: se compartilhassem a mesma, quem obtivesse a de `reportes` entraria como `vault_admin`, que pode criar usuários.

**Ponto de controle antes de repetir.** Este passo espera um laboratório novo. Se for repetido, seriam escritas senhas novas nos arquivos de `secretos-locales/` que já não coincidem com as que o PostgreSQL tem. Se aparecer `role already exists` ou se o motor `database/` já existir, não gerar de novo os arquivos iniciais: conferir o estado e fazer só os passos que faltam.

| Se aparecer | Significa | O que fazer |
|---|---|---|
| `CREATE ROLE` ou `HTTP 204` | Avançou bem | Seguir |
| `role "vault_admin" already exists` | O passo 2 já rodou, total ou parcialmente | Não gerar de novo os arquivos iniciais |
| `path is already in use` | O motor Database já está montado | Pular para ler ou configurar a conexão (passo 3) |

O `psql -v nombre=...` define uma variável que lá dentro é usada como `:'nombre'`. Assim a senha não fica literal no comando nem no histórico. O `psql` a substitui antes de enviar o SQL ao PostgreSQL, então a senha viaja, sim, dentro da instrução; por isso, fora do laboratório, usa-se TLS e evita-se registrar as instruções que contêm senhas:

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

A última linha dá ao `vault_admin` permissão para administrar o `reportes`, que é o de que ele precisa para trocar a senha dele. Desde o PostgreSQL 16, um usuário com `CREATEROLE` só pode modificar os usuários que criou ou que lhe foram atribuídos dessa forma.

## Passo 3 — Conectar o Vault ao PostgreSQL

Ligar o motor Database:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/database -d '{"type": "database"}'
HTTP 204
```

Agora a conexão. A senha do `vault_admin` é lida pelo `jq` do arquivo com `--arg`: ninguém a digita, não aparece no histórico. Em `connection_url`, `{{username}}` e `{{password}}` são preenchidos pelo Vault, e o servidor se chama `postgres` porque o Vault o procura pelo nome dentro da rede do Docker Compose, não por `127.0.0.1`. `allowed_roles` diz quais papéis podem usar esta conexão:

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

O Vault testou a conexão antes de guardá-la (`verify_connection` vem ligado); se a senha estivesse errada, aqui ele avisaria. Ler a configuração:

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

A senha não aparece. Depois que o Vault a tem, não a devolve nem ao token root.

## Passo 4 — Um papel para credenciais dinâmicas

Um **papel** (*role*) é a receita para criar um usuário. Guardá-la em `roles/lector-postgres.json`. Esse arquivo, o `politicas/app-python.hcl` e o `python/clientes.py` já vêm na pasta do laboratório; para escrevê-los manualmente, criar as pastas com `mkdir -p roles politicas python`, abrir o arquivo no editor, colar o bloco completo sem modificá-lo e salvá-lo antes de executar o comando seguinte:

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

- `creation_statements`: o SQL que o Vault executa ao criar o usuário. `VALID UNTIL '{{expiration}}'` faz o próprio PostgreSQL rejeitar a senha ao vencer, ainda que o Vault demore a apagar o usuário. É o exemplo da documentação ([PostgreSQL](https://developer.hashicorp.com/vault/docs/secrets/databases/postgresql)).
- `revocation_statements`: o SQL para apagá-lo. Por que ele é escrito à mão será visto no passo 6, com um erro real.
- `default_ttl` de 2 minutos para que a expiração seja vista sem esperar; na vida real costumam ser minutos ou horas. `max_ttl`: mesmo renovando, nunca mais de 10.

Enviá-lo. O `-d @archivo` diz ao `curl` para mandar o conteúdo do arquivo:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/roles/lector -d @roles/lector-postgres.json
HTTP 204
```

## Passo 5 — Pedir uma credencial e entrar

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

Um usuário que não existia um segundo atrás. O nome leva quem o pediu (`root`), o papel (`lector`), um pedaço aleatório e a hora em formato Unix. Neste laboratório, `root` não é uma pessoa: é apenas o token de administração. Em produção, ele não é entregue a pessoas nem a aplicações; cada pessoa ou programa entra com a própria identidade (por exemplo OIDC, AppRole ou Kubernetes), para que o nome do usuário temporário diga, sim, quem o pediu. Entrar com ele:

```
$ export PGUSER=$(jq -r .data.username secretos-locales/creds-lector.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-lector.json)
$ psql -c "SELECT current_user, nombre, left(curp, 9) FROM clientes;"
                 current_user                  | nombre |   left
-----------------------------------------------+--------+-----------
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | Pepe   | vault:v3:
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | María  | vault:v3:
(2 rows)
```

Funciona, e reparar: mesmo com usuário próprio, os CURP continuam cifrados. Esse leitor pode ver a tabela, mas não os CURP; para isso precisaria também de permissão no Transit. Tentar apagar:

```
$ psql -c "DELETE FROM clientes;"
ERROR:  permission denied for table clientes
```

Somente leitura, como diz o papel. E, pelo superusuário, é possível ver o usuário novo com a data de expiração:

```
$ PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -c "SELECT rolname, rolvaliduntil FROM pg_roles WHERE rolname LIKE 'v-%';"
                    rolname                    |     rolvaliduntil
-----------------------------------------------+------------------------
 v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049 | 2026-10-18 14:52:54+00
(1 row)
```

## Passo 6 — Revogar… e um erro de verdade

**Nota de leitura.** O primeiro bloco reproduz um erro de um teste anterior. Não executar os comandos que usam `secretos-locales/creds-lector-2.json`: esse arquivo não é criado no percurso atual. No laboratório de quem pratica, o papel do passo 4 já traz os `revocation_statements`; a revogação correta é praticada no exercício 17, com o `creds-16.json`.

Na primeira vez que esta lição foi testada, o papel **não** tinha `revocation_statements`. Foi pedida uma segunda credencial e ela foi revogada antes do tempo com `sys/leases/revoke`:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-lector-2.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
{"errors":["failed to revoke entry: resp: (*logical.Response)(nil) err: could not perform all revocation statements: ERROR: permission denied for sequence clientes_id_seq (SQLSTATE 42501)"]}
```

Código 400. Sem `revocation_statements`, o Vault usa o SQL de exclusão padrão do plugin do PostgreSQL, que tenta tirar do usuário as permissões sobre **tudo** o que há no esquema `public`, inclusive as sequências (os contadores que geram os `id`). O `vault_admin`, com permissões justas, não tem autoridade sobre a sequência `clientes_id_seq`, e o PostgreSQL disse não. O usuário temporário ficou pela metade: sem permissões sobre a tabela, mas sem ser apagado.

É um bom erro: aparece **porque** não demos o superusuário ao Vault. A solução correta não é dar mais poder, e sim dizer exatamente o que fazer. Por isso o papel do passo 4 traz os `revocation_statements`: tirar o que foi dado e apagar o usuário. Com o papel corrigido e enviado de novo, a mesma revogação funciona:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-lector-2.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
HTTP 204
$ PGUSER=$(jq -r .data.username secretos-locales/creds-lector-2.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-lector-2.json) psql -At -c "SELECT count(*) FROM clientes;"
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-QyRyJ1vdjmrPY6U0KXl2-1792335063"
```

O usuário já não existe. Quem copiou o papel do passo 4 completo já tem a primeira revogação funcionando.

O `"sync": true` é importante: por padrão o Vault apenas **põe na fila** a revogação e responde `204` na hora, sem esperar que o banco de dados apague o usuário. Com `sync` ele espera terminar, e assim o teste de entrada logo depois não depende do acaso ([sys/leases](https://developer.hashicorp.com/vault/api-docs/system/leases)).

## Passo 7 — Esperar a expiração

Agora a primeira credencial, a do passo 5. Não fazer nada: esperar os 2 minutos passarem. O Vault a revoga sozinho e anota isso no registro dele (`docker compose logs vault`):

```
2026-10-18T14:52:49.642Z [INFO]  expiration: revoked lease: lease_id=database/creds/lector/rOpuliUuxFqc2UbdHMofQV8S
```

Tentar entrar:

```
$ date -u +%T; psql -At -c "SELECT count(*) FROM clientes;"
14:53:32
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-rlOTkY9LU7LJR2xA22DB-1792335049"
```

Ninguém a revogou manualmente. Ninguém editou um arquivo. Ela morreu sozinha. Isto é o que teria salvado a Canasta Morada: a senha do script do Toño teria deixado de servir em dois minutos, já no primeiro sábado.

## Passo 8 — Rotação automática de um usuário existente

O `reportes` existe desde antes e outros sistemas o conhecem pelo nome. Conferir que hoje ele entra com a senha inicial:

```
$ PGUSER=reportes PGPASSWORD=$(cat secretos-locales/reportes_inicial.txt) psql -At -c "SELECT current_user;"
reportes
```

Colocá-lo sob um **papel estático** que rotaciona a cada minuto (o mínimo que a API aceita são 5 segundos; um minuto serve para ver sem cochilar):

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-roles/reportes \
    -d '{"db_name": "postgres", "username": "reportes", "rotation_period": "1m"}'
HTTP 204
```

A documentação explica que o Vault **rotaciona a senha ao criar o papel estático**, porque precisa conhecê-la ([API do motor Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). Então a inicial já morreu:

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

Quem precisa entrar como `reportes` pede ao Vault a senha vigente na hora:

```
$ PGUSER=reportes PGPASSWORD=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password) \
    psql -At -c "SELECT current_user, count(*) FROM clientes GROUP BY 1;"
reportes|2
```

Esperar uns dois minutos e perguntar de novo. O `last_vault_rotation` avançou sozinho, e o registro do Vault confirma:

```
2026-10-18T14:52:59.517Z [INFO]  secrets.database.database_4731c3d7: successfully rotated static role: name=reportes ttl=60
```

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -c ".data | {password: (.password[0:6] + \"...\"), last_vault_rotation, ttl}"
{"password":"OH0KOU...","last_vault_rotation":"2026-10-18T14:53:59.530969477Z","ttl":11}
```

E, para não esperar, a rotação pode ser feita com `rotate-role`. Outra senha nova; a de um momento atrás já não entra (isso é comprovado no exercício 18).

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-role/reportes
HTTP 204
```

Se em vez de «a cada minuto» for preciso «todo domingo às 4 da manhã», existe o `rotation_schedule`, com formato tipo cron de cinco campos; não pode ser usado junto com `rotation_period`. O Vault o interpreta em **UTC**, não no horário da cidade: para as 4:00 da manhã do domingo na Cidade do México (UTC-6) escreve-se `0 10 * * SUN`; ajustar a conta ao fuso de cada um ([API do motor Database](https://developer.hashicorp.com/vault/api-docs/secret/databases)). Nesta lição não foi testado.

## Passo 9 — Que ninguém saiba a senha do Vault: `rotate-root`

A senha inicial do `vault_admin` está em `secretos-locales/vault_admin_inicial.txt`. Hoje ela funciona:

```
$ PGUSER=vault_admin PGPASSWORD=$(cat secretos-locales/vault_admin_inicial.txt) psql -At -c "SELECT current_user;"
vault_admin
```

Pedir ao Vault que a troque por uma que só ele conheça:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-root/postgres
HTTP 204
$ PGUSER=vault_admin PGPASSWORD=$(cat secretos-locales/vault_admin_inicial.txt) psql -At -c "SELECT current_user;"
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "vault_admin"
```

O arquivo agora é lixo. E o Vault continua trabalhando, porque ele, sim, sabe a nova:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector | jq -c "{username: .data.username, lease_duration}"
{"username":"v-root-lector-R3rwerQPR0yvfCxuAxYI-1792335221","lease_duration":120}
```

Agora nenhuma pessoa conhece a senha com que os usuários do banco de dados são criados. Se alguém enviar por engano um arquivo de configuração, nele já não estará a do `vault_admin`. Atenção ao que sim continua: o `.env` ainda guarda as senhas de administração do PostgreSQL e do MariaDB do laboratório, e o `rotate-root` não as troca. Na vida real, essas também não deveriam viver num arquivo.

## Passo 10 — O mesmo com o MariaDB

O MariaDB também roda desde a sessão 2. A senha de `root` dele está no `.env`. O cliente `mariadb` lê a senha da variável `MYSQL_PWD`, então ela também não é escrita no comando. Criar uma tabela de produtos e o usuário `vault_admin` do MariaDB:

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

Esse aviso vem do cliente novo do MariaDB ao se conectar sem validar a identidade do servidor (TLS); no laboratório não importa. Se incomodar, acrescentar `--skip-ssl-verify-server-cert`.

Para o MariaDB usa-se o plugin `mysql-database-plugin`; a documentação do Vault cobre MySQL e MariaDB na mesma página ([MySQL/MariaDB](https://developer.hashicorp.com/vault/docs/secrets/databases/mysql-maria)). Reparar que o endereço tem outra forma:

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

O papel, em `roles/lector-mariadb.json`:

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

Aqui não foi preciso escrever `revocation_statements`: a exclusão padrão do plugin de MySQL funcionou com estas permissões. Entrar, ler e tentar mudar preços:

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

Revogar e testar de novo:

```
$ jq -n --arg l "$(jq -r .lease_id secretos-locales/creds-maria.json)" "{lease_id: \$l, sync: true}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/leases/revoke -d @-
HTTP 204
$ MYSQL_PWD=$(jq -r .data.password secretos-locales/creds-maria.json) mariadb -h 127.0.0.1 -P $PUERTO_MARIADB \
    -u $(jq -r .data.username secretos-locales/creds-maria.json) tienda -e "SELECT 1;"
ERROR 1045 (28000): Access denied for user 'v-root-lector-mar-24LwvJevZDrYbE'@'172.21.0.1' (using password: YES)
```

(O endereço `172.21.0.1` é o da máquina visto da rede do Docker; o de quem pratica pode ser outro.) E a raiz:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-root/mariadb
HTTP 204
$ MYSQL_PWD=$(cat secretos-locales/vault_admin_maria_inicial.txt) mariadb --skip-ssl-verify-server-cert -h 127.0.0.1 -P $PUERTO_MARIADB -u vault_admin -e "SELECT CURRENT_USER();"
ERROR 1045 (28000): Access denied for user 'vault_admin'@'172.21.0.1' (using password: YES)
```

## Passo 11 — O botão de pânico

Vale lembrar o requisito R6 da sessão 1: revogar de uma vez. Se houver suspeita de que todas as credenciais de um papel vazaram, elas são canceladas juntas por prefixo. Com o comando `vault`:

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

Atenção ao que essa saída demonstrou: «queued» quer dizer que o Vault aceitou a ordem e a pôs na fila, e a lista vazia só diz que já não há concessões. O que realmente importa é o efeito no PostgreSQL. Contar os usuários temporários antes de revogar e alguns segundos depois:

```
PGUSER=postgres PGPASSWORD=$POSTGRES_PASSWORD psql -At -c "SELECT count(*) FROM pg_roles WHERE rolname LIKE 'v-root-lector-%';"
```

Antes de revogar deve dar mais de `0` (um para cada credencial ainda viva); depois, `0`. Se ainda não for `0`, esperar um pouco e repetir: a fila trabalha em segundo plano. Essa contagem é o que confirma que os usuários já não existem.

Quatro concessões canceladas com uma ordem. Revogar por prefixo exige permissão especial (`sudo`) na rota ([sys/leases](https://developer.hashicorp.com/vault/api-docs/system/leases)); por isso aqui foi feito com o token root.

## Passo 12 — O único programa: Python sem senhas

Até aqui, tudo pelo terminal. Agora, o que faz qualquer aplicação real: pedir a credencial ao Vault e conectar-se. Primeiro, uma política para o programa, `politicas/app-python.hcl`:

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

Enviá-la e criar um token de 30 minutos para o programa:

```
$ jq -n --rawfile p politicas/app-python.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/app-python -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/create \
    -d '{"policies": ["app-python"], "ttl": "30m", "display_name": "app-python"}' \
    | jq -r .auth.client_token > secretos-locales/token-python.txt
```

Instalar o conector do PostgreSQL para Python num ambiente virtual:

```
python3 -m venv .venv
.venv/bin/pip install "psycopg[binary]"
```

**Hoje não é preciso dominar o Python inteiro.** Tratar este arquivo como um programa já resolvido e olhar só quatro zonas: `TOKEN` lê um segredo do ambiente; `vault(...)` fala com o Vault; `cred = ...` pede o usuário temporário; e o bloco `with psycopg.connect(...)` usa esse usuário no PostgreSQL. No exercício 20 só muda a forma como o programa termina.

E o programa, `python/clientes.py`. Usa o `urllib`, que vem com o Python, para falar com o Vault, e o `psycopg` para o PostgreSQL. São 24 linhas:

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

O que ele faz, em ordem: a função `vault` manda uma requisição ao Vault com o token no cabeçalho (se receber `datos`, é um `POST`; se não, um `GET`) e devolve a parte `data` da resposta. Pede uma credencial dinâmica, conecta-se com ela, lê os clientes e decifra cada CURP com o Transit.

Rodá-lo com o token do programa:

```
$ export VAULT_TOKEN=$(cat secretos-locales/token-python.txt)
$ .venv/bin/python python/clientes.py
Vault me prestó el usuario v-token-ap-lector-9FQ5IlE2i1HAUlZvuxZG-1792335175
Pepe   vault:v3:VEk...  ->  PEPE000101HDFXXX01
María  vault:v3:hKW...  ->  MARA990909MDFXXX02
```

Procurar no arquivo uma senha do PostgreSQL ou do Transit: não há. O programa, sim, recebe um token do Vault pelo ambiente; esse token também é secreto, mas não fica escrito no código, tem permissões limitadas e dura só 30 minutos. O nome do usuário agora começa com `v-token-ap`: o Vault anota que foi um token `app-python` quem o pediu, e não o root. Rodar de novo e ele empresta **outro** usuário. E, se o programa tentar sair da política dele:

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Sem token, nem inicia:

```
$ unset VAULT_TOKEN; .venv/bin/python python/clientes.py
...
KeyError: 'VAULT_TOKEN'
```

Ao terminar, voltar ao token root: `export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)`.

> **E a partir de Java, .NET ou Go?**
>
> O que foi feito com `curl` e Python pode ser feito de qualquer linguagem, porque o Vault fala HTTP. Quase ninguém programa isso à mão: cada linguagem tem bibliotecas. A HashiCorp mantém uma lista que distingue as oficiais das da comunidade ([Client libraries](https://developer.hashicorp.com/vault/api-docs/libraries)):
>
> - **Go:** `github.com/hashicorp/vault/api`, o cliente que a HashiCorp mantém oficialmente.
> - **Java com Spring:** o [Spring Cloud Vault](https://spring.io/projects/spring-cloud-vault) carrega os segredos do Vault na configuração da aplicação e pode pedir credenciais de banco de dados na hora. A HashiCorp o lista entre as bibliotecas da comunidade.
> - **Java com Quarkus:** a extensão [Quarkus Vault](https://docs.quarkiverse.io/quarkus-vault/dev/index.html), do projeto Quarkiverse, cobre KV, Transit e credenciais dinâmicas para a conexão com o banco de dados. Também é da comunidade.
> - **.NET:** o [VaultSharp](https://github.com/rajanadar/VaultSharp) é a opção mais conhecida. **Não é oficial**: é um projeto da comunidade. A lista da HashiCorp menciona ainda um cliente .NET experimental que, segundo a mesma página, não está pronto para produção.
>
> E há uma forma de não mexer no código: o **Vault Agent**, um programa que roda ao lado da aplicação, identifica-se no Vault, renova o token dele e escreve os segredos num arquivo a partir de um modelo; a aplicação só lê esse arquivo ([Vault Agent](https://developer.hashicorp.com/vault/docs/agent-and-proxy/agent)). No Kubernetes, o **injetor do Vault Agent** o adiciona sozinho aos pods que o pedem por anotações, e deixa os segredos num volume em memória compartilhado com a aplicação ([Agent Injector](https://developer.hashicorp.com/vault/docs/deploy/kubernetes/injector)).

> **E como isso se vê num sistema de verdade?**
>
> Imagine uma plataforma que atende muitas empresas ao mesmo tempo e guarda, de cada uma, senhas dos fornecedores: o acesso ao banco, ao emissor de notas, à transportadora. Se uma empresa vê os segredos de outra, acabou o negócio.
>
> Um bom projeto não amarra o programa ao Vault. Define primeiro um **componente com um contrato curto**: «sele este segredo para esta empresa» e «abra-o». Por dentro, cada empresa tem **a própria chave, com versões**, igual à chave do Transit que foi rotacionada na sessão 3: se uma chave é rotacionada, o que foi selado antes continua abrindo, e com `min_decryption_version` coloca-se uma data de validade no que é antigo.
>
> Atrás desse contrato conecta-se o provedor:
>
> - para os **testes**, uma versão que guarda tudo na memória e se apaga ao terminar;
> - para **produção**, um adaptador que chama o Transit com uma chave por empresa (`transit/encrypt/empresa-a`, `transit/encrypt/empresa-b`), ou um serviço de chaves de uma nuvem.
>
> Esse provedor pode ser o HashiCorp Vault ou o OpenBao, a versão livre, que tem um motor Transit compatível ([Transit no OpenBao](https://openbao.org/docs/secrets/transit/)); na Hábil escolhemos o OpenBao.
>
> O resto do sistema nunca sabe qual dos dois está conectado. Assim dá para testar tudo sem subir o Vault, e trocar de provedor sem reescrever o programa. Reparar no que ele **não** faz: o programa nunca toca a chave. Pede «sele» e «abra», e a chave fica no Vault, como se viu com `curl` na sessão 3.

---

👉 **Para quem é de Administração:** as credenciais dinâmicas são o **crachá de visitante** levado aos sistemas: é emitido em nome de quem o pede, abre só o necessário e vence sozinho. A rotação automática é a **troca periódica de combinação** do cofre, mas sem que ninguém precise anotar a nova. E o botão de pânico responde à pergunta que qualquer auditor faz depois de um incidente: «quanto tempo levaram para cancelar os acessos?». Com isso, a resposta é «um comando». No caso da Canasta Morada, a pergunta que realmente importava era outra: «quem paga esse servidor de 9,99 dólares?». Revisar as cobranças recorrentes do cartão da empresa também é controle de acessos.

---

## Exercícios da sessão 4

**Exercício 16 — O crachá.** Pedir uma credencial do papel `lector`, entrar com `psql` e contar os clientes. Depois tentar `INSERT INTO clientes (nombre, curp) VALUES ('Intruso', 'x');`.

```
# Pista: guarda la credencial para usarla en el ejercicio 17.
# Archivo sugerido: secretos-locales/creds-16.json
# Ruta que debes consultar: database/creds/lector
```

**Como conferir:** a contagem dá `2` (ou quantos houver); o `INSERT` dá `ERROR:  permission denied for table clientes`.

**Exercício 17 — Revogue por conta própria.** Revogar a credencial do exercício 16 com `sys/leases/revoke` e tentar entrar de novo. Fazer isso dentro dos 2 minutos: se o Vault já a tiver revogado e a rota responder que a concessão não existe, não é um erro de permissões. Pedir outra credencial, substituir o `creds-16.json` e revogá-la em seguida.

**Como conferir:** a revogação responde `HTTP 204` e o `psql` responde `password authentication failed`. Pelo superusuário, `SELECT count(*) FROM pg_roles WHERE rolname = '<o usuário>';` dá `0`.

**Exercício 18 — A senha de um minuto atrás.** Guardar a senha vigente do `reportes` numa variável, rotacionar com `rotate-role/reportes` e tentar entrar com a que foi guardada.

**Como conferir:** com a guardada, `password authentication failed for user "reportes"`. Com a que o Vault dá depois de rotacionar, entra.

**Exercício 19 — Crachá de 30 segundos.** Mudar o `default_ttl` do papel `lector` para 30 segundos, sem editar o arquivo, com `jq`:

```
jq '.default_ttl = "30s"' roles/lector-postgres.json \
  | curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/database/roles/lector -d @-
```

Pedir uma credencial, entrar de imediato, esperar 40 segundos e tentar de novo. Guardar a credencial em `secretos-locales/creds-19.json` e pôr `PGUSER=... PGPASSWORD=... psql` na frente de cada tentativa, lendo os valores do arquivo com `jq` como no passo 5: o que foi exportado nos exercícios 16 e 17 pertence a um usuário já revogado e daria uma falha que não é a do TTL.

**Como conferir:** `lease_duration` diz `30`; a primeira tentativa entra; a segunda dá `password authentication failed`. Ao terminar, devolver o papel ao que era, enviando de novo o `roles/lector-postgres.json`.

**Exercício 20 — Que o programa recolha o próprio lixo.** Toda vez que o `clientes.py` roda, deixa um usuário temporário vivo até expirar. Fazer com que ele **revogue o próprio token** com `auth/token/revoke-self`, e que faça isso **sempre**, mesmo que algo falhe no meio (usar `try` e `finally`). Quando um token é revogado, o Vault revoga também as credenciais pedidas com ele. Partir deste esqueleto, que já arruma a estrutura:

```python
try:
    cred = vault("database/creds/lector")
    # pega aquí el bloque with psycopg.connect(...) que ya existe
finally:
    # aquí va la petición POST a auth/token/revoke-self
    pass
```

**Como conferir:** antes de rodá-lo, contar pelo superusuário os usuários que começam com `v-token-ap`; depois de rodá-lo, a contagem deve ficar igual à de antes (o usuário foi criado e apagado). Se for rodado de novo com o mesmo token, deve falhar com `HTTP Error 403`, porque o token já não existe. Para repetir o teste depois desse 403, criar um token novo com o mesmo comando do passo 12, guardá-lo de novo em `secretos-locales/token-python.txt` e exportar `VAULT_TOKEN` outra vez. O 403 é o esperado só para o token já revogado.

---

## Erros comuns (e como perceber)

| Erro | Como aparece | Como perceber | O que fazer |
|---|---|---|---|
| Usar `127.0.0.1` na `connection_url` | Ao salvar a configuração: `error verifying connection: ... dial tcp 127.0.0.1:5432: connect: connection refused`, código 400 | O servidor da URL não é o nome do serviço; dentro do contêiner do Vault, `127.0.0.1` é o próprio Vault | Dentro do Docker Compose, o Vault chega ao banco de dados pelo nome: `postgres`, `mariadb` |
| Papel que não está em `allowed_roles` | `"escritor" is not an allowed role`, código 500 | O nome do papel não aparece em `database/config/<conexão>` | Acrescentá-lo em `allowed_roles` da conexão |
| Revogação que falha com permissões justas | `permission denied for sequence ...` ao revogar | O papel não tem `revocation_statements` | Escrever os `revocation_statements`; não dar superusuário ao Vault para o erro sumir |
| Guardar a senha do `vault_admin` e depois rotacionar a raiz | O arquivo já não serve | `rotate-root` respondeu 204 | É o que queremos: nenhuma pessoa a conhece. Se for preciso entrar, usar o superusuário do banco de dados, não o do Vault |
| Esperar que a credencial dure mais que o `max_ttl` | Renova-se e mesmo assim vence | `lease_duration` deixa de crescer | `max_ttl` é o teto. Pedir uma credencial nova |
| Colar o token do programa no código | O token fica escrito num arquivo que o git rastreia | `git status` mostra o arquivo como modificado, e `grep -rn hvs. python/` encontra o token | O token entra por variável de ambiente ou, melhor, com o Vault Agent. Se foi enviado, revogá-lo |
| `psql` entra sem pedir senha | Parece que a credencial continua viva | A conexão foi pelo socket local dentro do contêiner | Conectar como na lição, pela rede (`-h 127.0.0.1` a partir da máquina), onde o PostgreSQL confere a senha |

---

## Autoavaliação da série

Responder sem consultar. Se errar mais de duas, voltar à sessão indicada.

1. Qual é a diferença entre `DELETE` sobre `secret/data/...` e `destroy`? *(Sessão 2)*
2. Escrever de memória uma política que deixe ler `secret/data/app/*` e nada mais. *(Sessão 2)*
3. Por que um 403 é uma boa notícia quando se testa uma política? *(Sessão 2)*
4. O que é preciso para decifrar um `vault:v1:...` se a chave tem `min_decryption_version: 2`? *(Sessão 3)*
5. O que um sistema ganha com chaves derivadas e `context`? *(Sessão 3)*
6. Que diferença há entre uma credencial dinâmica e um papel estático? *(Sessão 4)*
7. Por que a conexão do Vault com o banco de dados usa o `vault_admin` e não o superusuário? *(Sessão 4)*
8. Um estagiário sai da empresa. Com o que foi construído, quais senhas seria preciso trocar à mão? *(Todas)*

## Revisão da série

| Sessão | O problema | O que o resolve | O comando que não se deve esquecer |
|---|---|---|---|
| 1 | Segredos em arquivos, em chats, compartilhados e eternos | Requisitos R1 a R7 | `git log -p -S <texto>` |
| 2 | Ninguém sabe quem tem acesso nem quem o usou | Selo de Shamir, tokens, políticas, log de auditoria | `curl -H "X-Vault-Token: ..." $VAULT_ADDR/v1/secret/data/...` |
| 3 | A chave de cifragem vive junto dos dados | Transit: cifrar sem ter a chave, rotacionar, reenvelopar | `POST transit/encrypt/<chave>` com `plaintext` em base64 |
| 4 | A mesma senha de banco de dados para todos e para sempre | Credenciais dinâmicas, rotação, `rotate-root`, revogação | `GET database/creds/<papel>` |

**Para desligar tudo ao terminar a série:** `docker compose down`. Os dados ficam nas pastas `vault/`, `postgres/` e `mariadb/`. Para recomeçar do zero, apagar essas pastas, `secretos-locales/` e `.env`, e rodar de novo `./iniciar.sh`.

---

## Soluções (não olhe antes de tentar)

**Revisão da sessão 3.**

1. `vault`: foi cifrado pelo Vault; `v2`: com a versão 2 da chave; o restante: o dado cifrado, em base64.
2. Continuam cifrados com a versão antiga e podem ser decifrados enquanto essa versão não ficar abaixo de `min_decryption_version`. O `rewrap` os sobe para a versão nova sem revelar o dado.
3. Porque, se alguém roubar esse token, pode inserir dados cifrados, mas não consegue ler nenhum. O dano de um vazamento é muito menor.

**Exercício 16.**

```
curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/creds/lector > secretos-locales/creds-16.json
export PGUSER=$(jq -r .data.username secretos-locales/creds-16.json) PGPASSWORD=$(jq -r .data.password secretos-locales/creds-16.json)
psql -At -c "SELECT count(*) FROM clientes;"
psql -c "INSERT INTO clientes (nombre, curp) VALUES ('Intruso', 'x');"
```

**Exercício 17.** O comando do passo 6, com o `lease_id` do `creds-16.json`. Fazer antes que passem os 2 minutos; se o Vault se adiantar, pedir outra credencial e revogá-la em seguida.

**Exercício 18.**

```
VIEJA=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password)
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/rotate-role/reportes
PGUSER=reportes PGPASSWORD=$VIEJA psql -At -c "SELECT 1;"
NUEVA=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/database/static-creds/reportes | jq -r .data.password)
PGUSER=reportes PGPASSWORD=$NUEVA psql -At -c "SELECT 1;"
```

No teste desta lição, a ordem que usa `$VIEJA` (a terceira) deu `FATAL:  password authentication failed for user "reportes"`. Atenção: como o papel rotaciona a cada minuto, a «velha» pode morrer pela rotação automática antes da rotação manual. O resultado é o mesmo. A última ordem, com `$NUEVA`, imprime `1`; se essa também falhar, pedir de novo ao Vault a senha vigente e executá-la outra vez, porque a rotação de um minuto pode ter ocorrido entre uma ordem e outra.

**Exercício 19.**

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

No teste:

```
{"lease_duration":30,"username":"v-root-lector-wlrG6BL0dqUomIbQDDrV-1792336140"}
```

A primeira tentativa devolveu `2`. Quarenta segundos depois:

```
psql: error: connection to server at "127.0.0.1", port 5432 failed: FATAL:  password authentication failed for user "v-root-lector-wlrG6BL0dqUomIbQDDrV-1792336140"
```

**Exercício 20.** Colocar dentro do `try` o pedido da credencial e tudo o que usa o banco de dados, e a revogação no `finally`, que é executado aconteça o que acontecer (mesmo que o próprio pedido da credencial falhe):

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

Assim, se o pedido, a conexão ou uma consulta falharem, o token é revogado do mesmo jeito. O `data=b"{}"` transforma a requisição em um `POST`, que é o que essa rota pede. No teste desta lição:

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

O usuário `v-token-ap-lector-xQMN...` nasceu e morreu dentro da mesma execução. O programa já não deixa nada para trás.

**Autoavaliação.**

1. `DELETE` apaga a última versão de forma reversível (`undelete` a traz de volta); `destroy` a apaga para sempre.
2. `path "secret/data/app/*" { capabilities = ["read"] }`
3. Porque demonstra que a política nega o que deve negar. Uma política que nunca dá 403 provavelmente dá demais.
4. Nada o decifra enquanto o mínimo for 2. O correto era reenvelopá-lo antes de subir o mínimo; se não, é preciso baixar o `min_decryption_version`, reenvelopar e voltar a subi-lo.
5. Que um dado cifrado para um dono não possa ser decifrado como se fosse de outro, mesmo usando a mesma chave.
6. A dinâmica cria um usuário novo a cada vez e o apaga ao expirar; a estática conserva um usuário que já existe e troca a senha dele de tempos em tempos.
7. Porque o `rotate-root` deixa a senha nas mãos do Vault, e a documentação recomenda um usuário dedicado. Além disso, com permissões justas, um erro ou um vazamento no Vault não dá controle total do banco de dados.
8. Nenhuma se troca à mão. Revoga-se o token dele no Vault e, com ele, as credenciais dinâmicas (ou todas as que criou, por prefixo). Uma exceção: se o estagiário conhecia a senha do papel estático `reportes`, rotacioná-la de imediato com `POST /v1/database/rotate-role/reportes`; revogar o token dele não muda essa senha, que continuaria servindo até a rotação seguinte. Essa é a diferença em relação à Canasta Morada no começo da série.

---

## O que vem a seguir

Esta série usou o Vault com um único servidor, sem TLS e com as chaves num arquivo, porque é um laboratório. Para seguir adiante, os próximos temas são: TLS no listener, métodos de autenticação para máquinas (AppRole, Kubernetes) em vez de tokens criados à mão, armazenamento com vários servidores para alta disponibilidade e backups do próprio Vault.

---

*Escrevo a partir do que vemos todos os dias na Hábil, onde construímos sistemas para bancos, seguradoras e empresas no México. Se no trabalho ou no negócio da família de quem lê surgir um problema assim, vamos conversar: [habil.mx](https://www.habil.mx/pt/)*

*Se na empresa de quem lê as senhas dos bancos de dados ainda vivem num arquivo, na Hábil montamos isso como parte do provisionamento de infraestrutura: [identidade, chaves e segredos](https://www.habil.mx/pt/).*
