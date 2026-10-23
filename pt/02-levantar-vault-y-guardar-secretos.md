# Vault do zero (2): subir o Vault e guardar segredos

*Um cofre que ninguém consegue abrir sozinho, um guichê que diz não a quem pede o que não lhe cabe e um log que anota tudo. Com Docker Compose e `curl`.*

*Vault do zero · sessão 2 de 4*

## Revisão da sessão 1

Responder sem consultar. As respostas estão nas soluções, no final.

1. Nomear quatro das seis formas pelas quais um segredo vaza.
2. Por que trocar a senha depois de um vazamento é obrigatório, mesmo que ela já tenha sido apagada do git?
3. Em que o motor Transit do Vault se parece com um HSM e em que se diferencia?

> **O laboratório desta sessão** está no repositório público [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Monte-o primeiro por conta própria; o repositório serve para comparar quando algo não sair igual. Não traz nenhuma senha: o laboratório as gera ao iniciar.

## Objetivos desta sessão

| # | Ao terminar, é possível… | Demonstrado no |
|---|---|---|
| 1 | **Subir** o Vault em modo servidor com Docker Compose, sem escrever nenhuma senha nos arquivos do laboratório | Exercício 6 |
| 2 | **Inicializar** e **abrir** o Vault com 3 de 5 chaves, e **explicar** por que ele se fecha sozinho ao reiniciar | Exercício 7 |
| 3 | **Guardar, ler, versionar, apagar e recuperar** segredos com `curl` na API | Exercício 8 |
| 4 | **Escrever** uma política e **comprovar** que um token limitado recebe 403 onde deve | Exercício 9 |
| 5 | **Ler** o log de auditoria com `jq` para saber quem pediu o quê | Exercício 10 |

---

## Cenário (ficção) — Capítulo 5: sábado, 13:40

Iván trocou a senha do `app_tienda` ao meio-dia. Levou uma hora e meia para subir de novo os quatro programas. A macro da contabilidade nunca apareceu; Rocío, a contadora, vai tirar o relatório do mês manualmente.

Dona Clara escuta tudo sem interromper. No fim, diz uma única coisa:

— Não quero voltar a depender de alguém se lembrar de onde escreveu uma senha.

Iván propõe um cofre para segredos. Dona Clara pergunta quem vai ficar com a chave.

— A senhora — diz Iván.

— Não. Se acontecer algo comigo, ninguém abre. E, se alguém a tirar de mim, abre sozinho.

Iván sorri. Essa objeção tem uma resposta de 1979.

---

## Capítulo 6: o sábado seguinte, 3:17 da madrugada

O cofre já existe. Cinco pessoas têm um pedaço da chave dele. Os apps pedem os próprios segredos com a identificação própria.

O celular de Iván vibra de novo. Mesma hora. Mesmo servidor. Mas agora o log do banco de dados diz outra coisa:

```
03:17:02  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
03:17:32  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
03:18:02  FALLO de autenticación: usuario=app_tienda  origen=185.xx.xx.xx
```

Alguém continua tentando com a senha antiga. A cada trinta segundos. Como um relógio.

Iván fica olhando a tela. Ladrões não têm horário fixo.

Quem tem?

*(Continua na sessão 3.)*

---

## Por que isso importa

Até hoje, na Canasta Morada, «ter acesso» queria dizer «saber a senha». Hoje se constrói o contrário: um lugar onde ninguém sabe nada, e cada um **pede** o que precisa e **demonstra** quem é. É a diferença entre uma casa em que todos têm cópia da chave e um prédio com recepção: ali anotam o visitante, perguntam aonde vai e só abrem aquele andar.

Nesta sessão aparecem três ideias usadas em qualquer sistema sério, com ou sem Vault:

- **O selo.** Os dados ficam cifrados no disco. Sem a chave-mestra, nem o próprio Vault consegue lê-los.
- **Negado por padrão.** Se uma política não diz que pode, não pode. A documentação diz assim: «as políticas negam por padrão» ([Policies](https://developer.hashicorp.com/vault/docs/concepts/policies)).
- **Tudo fica anotado.** Cada requisição, permitida ou negada, deixa rastro no log.

## A resposta de 1979: as chaves de Shamir

Em 1979, o criptógrafo Adi Shamir publicou uma forma de partir um segredo em **N pedaços** de modo que qualquer grupo de **K** pedaços o reconstrua, e com menos de K não se sabe nada. Nem um pouquinho.

Pense no cofrinho da festa do povoado. Há cinco guardiões. Para abri-lo, é preciso que se juntem pelo menos três, cada um com a chave própria. Se um adoece, os outros quatro bastam. Se roubam a chave de um, o ladrão não abre nada sozinho. E ninguém, nem o guardião principal, consegue abri-lo escondido.

O Vault funciona assim:

- Ao ser **inicializado**, o Vault cria uma **chave-mestra** que protege tudo o que ele guarda. Por padrão, ele a divide em **5 pedaços** e exige **3** para reconstruí-la ([vault operator init](https://developer.hashicorp.com/vault/docs/commands/operator/init)).
- O Vault inicia **selado** (*sealed*): tem os dados, mas cifrados, e não os entende. É o cofrinho fechado.
- **Abrir o selo** (*unseal*) é três guardiões colocarem a chave. A partir daí, o Vault trabalha normalmente.
- Se o Vault reinicia, **volta a se selar**. É preciso juntar três chaves de novo.

A documentação oficial explica o selo e o algoritmo de Shamir em [Seal/Unseal](https://developer.hashicorp.com/vault/docs/concepts/seal).

---

## Passo 0 — O que é preciso ter

Docker com Compose, `curl`, `jq` (versão 1.6 ou mais recente), `openssl` e `git`. Conferir:

```
docker compose version
curl --version
jq --version
openssl version
```

Se algum marcar «command not found», instalar antes de seguir. Esta sessão usa o Vault 2.2.0, o PostgreSQL 17.11 e o MariaDB 11.8.8, fixados no `compose.yaml`: não trocar por `latest`, porque os comandos e as respostas da lição são os dessas versões.

## Passo 1 — A pasta do laboratório

Criar uma pasta `lab-vault` com esta estrutura. O conteúdo de cada arquivo vem abaixo.

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

O primeiro é o `.gitignore`. É a lista do que o git nunca deve enviar. Vem **antes** de qualquer outra coisa porque o laboratório vai gerar senhas, e queremos que, desde o primeiro segundo, o git não as adicione por descuido. Atenção: o `.gitignore` só evita que o git adicione arquivos que ele ainda não conhece. Não protege um arquivo que já foi confirmado antes, nem contra alguém que force o envio com `git add -f`; por isso convém conferir o `git status` antes de cada `git commit`.

```
# Lo que el laboratorio genera al arrancar. NADA de esto se sube a git.
.env
secretos-locales/
vault/data/
vault/logs/
postgres/
mariadb/
```

Depois, o `.env.ejemplo`. É uma cópia de referência **sem valores reais**, para que quem clonar o repositório saiba quais variáveis existem:

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

A configuração do Vault, `vault/config/vault.hcl`:

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

Três coisas que convém entender:

- **`storage "file"`**: o Vault guarda os dados, já cifrados, numa pasta. Há outras opções para produção com vários servidores; esta é a mais simples ([Filesystem storage](https://developer.hashicorp.com/vault/docs/configuration/storage/filesystem)).
- **`tls_disable = true`**: sem cifragem na conexão. Num notebook, tudo bem. Num servidor de verdade, **jamais**: as senhas viajariam em texto puro pela rede.
- **Não é o modo «dev».** O Vault tem um modo de desenvolvimento que inicia aberto, sem selo e guardando tudo na memória. É cômodo, mas esconde justamente o que queremos aprender hoje.

O `compose.yaml`. Reparar em dois detalhes: **não há nenhuma senha escrita**, só variáveis como `${POSTGRES_PASSWORD}`, e os dados são guardados em **pastas montadas** (`./vault/data`), não em volumes do Docker, para que os arquivos possam ser vistos e não se percam se alguém limpar o Docker:

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

O PostgreSQL e o MariaDB são usados nas sessões 3 e 4; sobem desde hoje para não ser preciso mexer no arquivo depois. O `:?falta .env…` quer dizer: «se esta variável não existir, não inicie e mostre esta mensagem».

Três detalhes deste arquivo:

- **`127.0.0.1:` na frente de cada porta** faz o Docker publicar o serviço só para o próprio computador. Sem isso, o Vault (que aqui não usa TLS) e os dois bancos ficariam abertos a qualquer pessoa da rede.
- **`user:`** faz o Vault rodar com o usuário de quem o iniciou. A imagem oficial inicia com um usuário sem privilégios (`vault`), e no Linux ele não conseguiria escrever em pastas criadas por quem está praticando. O script de inicialização anota o número desse usuário no `.env`.
- **Se alguma porta já estiver em uso** (a 8200, a 5432 ou a 3306), trocá-la com `PUERTO_VAULT`, `PUERTO_POSTGRES` ou `PUERTO_MARIADB`, como se explica abaixo.

> **No Linux: duas pastas que são de quem as criou, mas não são.**
>
> Depois de subir o laboratório no Linux, rodar `ls -ln` na pasta. Aparece algo assim (recortamos as colunas que não importam; medido no Linux Mint 22.3, com o usuário 1000):
>
> ```
> drwx------  999 1000  postgres
> drwxrwxr-x  999  999  mariadb
> drwx------ 1000 1000  secretos-locales
> drwxr-xr-x 1000 1000  vault
> ```
>
> As pastas `postgres` e `mariadb` já não pertencem ao usuário: pertencem ao 999. E, se `ls -l` for rodado sem o `n`, no lugar do número pode aparecer o nome de um serviço do sistema (no Mint apareceu `dnsmasq`). Não é um vírus nem um erro do laboratório. Acontece porque as imagens oficiais do PostgreSQL e do MariaDB iniciam como administrador dentro do contêiner e depois passam os arquivos para o usuário interno delas, o número 999. Uma **pasta montada** é a mesma pasta vista de dois lados: o que o contêiner faz com os arquivos dele, o disco enxerga tal qual, número de usuário incluído. O Linux não sabe quem é o 999 do contêiner; só vê o número, e, se no sistema esse número tiver dono, mostra o nome dele.
>
> Com o Vault isso não acontece porque o `user:` do compose o obriga a rodar com o número do usuário. Por que não se faz o mesmo com os bancos de dados? Porque eles precisam iniciar como administrador para se preparar na primeira vez, e forçar outro usuário quebra essa primeira inicialização.
>
> O que isso significa na prática:
> - `ls postgres` vai responder «Permissão negada». Para olhar dentro, usar `sudo ls postgres` ou, melhor, perguntar ao próprio contêiner: `docker compose exec postgres ls /var/lib/postgresql/data`.
> - Se um dia o laboratório precisar ser recomeçado do zero, primeiro `docker compose down` e depois apagar essas duas pastas com `sudo`, porque o usuário comum não consegue.
> - No macOS e no Windows isso não aparece: o Docker roda dentro de uma máquina virtual que mostra os arquivos como se fossem do usuário.

## Passo 2 — Um script de inicialização que falha fechado

O `iniciar.sh` prepara tudo. O importante está no ponto 1: **antes de gerar qualquer senha, ele confere se o `.gitignore` a protege.** Se não, recusa-se a continuar. Isso se chama **falhar fechado** (*fail closed*): na dúvida, a porta fica fechada, como a catraca do metrô que não gira se o cartão não passou.

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

O `grep -qx` procura uma linha que seja **exatamente** esse texto (`-x`) e não imprime nada (`-q`); só diz sim ou não. O `openssl rand -hex 16` gera 16 bytes aleatórios escritos como 32 caracteres hexadecimais. O `umask 077` faz o `.env` nascer legível só pelo dono. O `id -u` e o `id -g` são o número de usuário e de grupo. E o `unset` tira do terminal qualquer variável com esses nomes: o Compose dá prioridade às variáveis do terminal sobre o `.env`, e não queremos que uma senha ou uma porta velha vença sem que ninguém perceba.

Dar permissão de execução com `chmod +x iniciar.sh`. Antes de rodá-lo para valer, comprovar que ele realmente falha fechado. Numa cópia do laboratório em que ao `.gitignore` falta a linha `secretos-locales/`, isto é o que acontece:

```
$ ./iniciar.sh
ALTO: .gitignore no tiene la regla 'secretos-locales/'.
Sin ella, las contraseñas que voy a generar podrían terminar en git. No sigo.
código de salida: 1
```

Não criou nenhuma pasta nem nenhum `.env`. Agora, com o `.gitignore` completo:

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

Se na máquina já se usa a porta 5432 (porque há outro PostgreSQL), iniciar assim na primeira vez: `PUERTO_POSTGRES=15432 ./iniciar.sh`. O script a anota no `.env`.

E a prova de que o git não enxerga os segredos. Fazendo `git init` na pasta e perguntando o que seria enviado:

```
$ git status --short
?? .env.ejemplo
?? .gitignore
?? compose.yaml
?? iniciar.sh
?? vault/config/vault.hcl
```

Nem `.env`, nem `secretos-locales/`, nem os dados. É o que se queria.

## Passo 3 — Está vivo?

O Vault fala HTTP. Guardar o endereço dele numa variável para não digitá-lo toda vez:

```
export VAULT_ADDR="http://127.0.0.1:$(grep '^PUERTO_VAULT=' .env | cut -d= -f2)"
```

Rodar essa linha dentro da pasta `lab-vault`. A porta é lida do `.env`, então funciona mesmo que tenha sido trocada. O Docker dizer «Started» não quer dizer que o Vault já esteja escutando. Esperar até que ele responda:

```
until curl -fsS -o /dev/null "$VAULT_ADDR/v1/sys/seal-status"; do
  echo "Espero a que Vault inicie..."
  sleep 1
done
```

Perguntar a ele como está o selo. Esta rota não exige identificação:

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

`initialized: false`: nunca foi inicializado. `sealed: true`: está selado. `t` e `n` são o limiar e o total de chaves; ainda não há nenhuma.

Outra forma rápida de saber o estado é o código HTTP da rota de saúde. O `-o /dev/null` descarta a resposta e o `-w` imprime só o código:

```
$ curl -s -o /dev/null -w "%{http_code}\n" $VAULT_ADDR/v1/sys/health
501
```

501 quer dizer «não inicializado». Vai-se ver como isso muda.

## Passo 4 — Inicializar: nascem as cinco chaves

Esta requisição cria a chave-mestra, a divide em 5 pedaços com limiar de 3 e devolve os pedaços e um **token root**. Ela é gravada direto num arquivo da pasta `secretos-locales/`, que o git ignora:

```
curl -s -X PUT $VAULT_ADDR/v1/sys/init \
  -d '{"secret_shares": 5, "secret_threshold": 3}' > secretos-locales/init.json
chmod 600 secretos-locales/init.json
```

O `chmod 600` deixa o arquivo legível só pelo dono. Olhá-lo sem mostrar os valores completos:

```
$ jq "{llaves: (.keys | length), token_root: (.root_token[0:9] + \"...\")}" secretos-locales/init.json
{
  "llaves": 5,
  "token_root": "hvs.RGQs7..."
}
```

Os valores serão outros. Cada inicialização cria chaves novas. Nesta lição os tokens aparecem sempre cortados, assim: `hvs.RGQs7...`.

O **token root** é a chave de dono: pode fazer absolutamente tudo. Será usado para configurar o laboratório.

> **Assim não, e por quê**
>
> Guardar as cinco chaves e o token root num arquivo ao lado do `compose.yaml` é uma **concessão do laboratório**, para que seja possível praticar sozinho na própria máquina. **Na vida real, nunca se faz assim.**
>
> - As chaves são repartidas entre **pessoas diferentes**, uma para cada, justamente para que ninguém consiga abrir o cofre sozinho. Juntá-las num arquivo é ter os cinco guardiões numa só pessoa.
> - O **token root é revogado** assim que termina a configuração inicial. A documentação recomenda isso: usá-lo só para o indispensável no começo e revogá-lo quando deixa de ser necessário ([Tokens](https://developer.hashicorp.com/vault/docs/concepts/tokens)). Se um dia for preciso outro, ele é gerado juntando as chaves de novo.
> - Um servidor de verdade usa TLS, não `tls_disable`.
>
> Se um dia este laboratório for copiado para um servidor, estas três coisas são as primeiras a mudar.

Conferir o selo outra vez:

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

Inicializado, mas selado. Faltam os guardiões.

## Passo 5 — Abrir o selo com 3 de 5 chaves

Cada chamada a `sys/unseal` entrega **uma** chave. O `jq -r '.keys[0]'` tira a primeira do arquivo, sem aspas:

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

`progress: 1`: uma de três. Repetir com `.keys[1]`:

```
{
  "sealed": true,
  "t": 3,
  "n": 5,
  "progress": 2
}
```

E com `.keys[2]`:

```
{
  "sealed": false,
  "t": 3,
  "n": 5,
  "progress": 0
}
```

`sealed: false`. Aberto. A saúde agora responde 200:

```
$ curl -s -o /dev/null -w "%{http_code}\n" $VAULT_ADDR/v1/sys/health
200
```

Comprovar que ele se sela sozinho ao reiniciar:

```
$ docker compose restart vault
$ curl -s $VAULT_ADDR/v1/sys/seal-status | jq "{sealed, progress}"
{
  "sealed": true,
  "progress": 0
}
```

Assim vai estar toda vez que o computador for ligado ou o contêiner for reiniciado. Para não digitar três vezes a mesma coisa, abrir o selo com um laço:

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

E se alguém colocar uma chave falsa?

```
$ curl -s -X PUT $VAULT_ADDR/v1/sys/unseal -d '{"key": "esta-no-es-una-llave"}'
{"errors":["'key' must be a valid hex or base64 string"]}
```

## Passo 6 — Identificar-se: o token

Sem token, o guichê não atende:

```
$ curl -s -w " HTTP %{http_code}\n" $VAULT_ADDR/v1/sys/mounts
{"errors":["permission denied"]}
 HTTP 403
```

Exportar o token root para uma variável do terminal. **Nunca colá-lo num arquivo que seja enviado**; ele é lido de onde está:

```
export VAULT_TOKEN=$(jq -r .root_token secretos-locales/init.json)
```

O token viaja no cabeçalho `X-Vault-Token`. Perguntar quem se é:

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

`ttl: 0` quer dizer que nunca expira. Outra razão para revogá-lo na vida real.

Um esclarecimento: no laboratório, a «identificação» do app é um token criado manualmente. Assim se vê o mecanismo de perto. Num sistema real, as aplicações obtêm o token sozinhas, provando quem são com métodos como AppRole, Kubernetes ou OIDC (a documentação do Vault os chama de *métodos de autenticação*); isso fica fora desta série.

## Passo 7 — Ligar o log antes de tudo

O log vem primeiro, para que tudo o que for feito daqui em diante fique registrado. Um **dispositivo de auditoria** do tipo arquivo escreve uma linha JSON para cada requisição e outra para cada resposta ([File audit device](https://developer.hashicorp.com/vault/docs/audit/file)):

```
$ curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/audit/archivo \
    -d '{"type": "file", "options": {"file_path": "/vault/logs/audit.log"}}'
HTTP 204
```

204 quer dizer «feito, e não tenho nada a contar». O log fica em `./vault/logs/audit.log` na máquina, graças à pasta montada.

## Passo 8 — Guardar segredos: o motor KV versão 2

Ativar o motor **KV v2** no caminho `secret/`. É uma gaveta de segredos chave-valor que guarda versões ([KV v2](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2)):

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/secret -d '{"type": "kv", "options": {"version": "2"}}'
HTTP 204
```

Listar os motores que existem:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/sys/mounts | jq -r ".data | keys[]"
agent-registry/
cubbyhole/
identity/
secret/
sys/
```

O criado agora é o `secret/`. Os demais já vêm de fábrica.

**Escrever.** Guardar o usuário e a senha do app da loja. Os valores são de brinquedo; na vida real a senha é gerada com `openssl rand`, como fez o script:

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

Reparar no caminho: `secret/`**`data/`**`tienda/postgres`. No KV v2, os dados vão sob `data/` e as informações sobre as versões, sob `metadata/`. É a armadilha número um do KV v2; está na tabela de erros.

**Ler:**

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

**Uma versão nova.** Trocar a senha:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/secret/data/tienda/postgres \
    -d '{"data": {"usuario": "app_tienda", "password": "Mango-2026"}}' | jq -c ".data | {version, created_time}"
{"version":2,"created_time":"2026-10-18T14:47:29.522529264Z"}
```

A versão 1 continua lá. Pedir a versão 1 com `?version=1`:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/postgres?version=1" | jq -c .data.data
{"password":"Pepino-2026","usuario":"app_tienda"}
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c ".data.data, .data.metadata.version"
{"password":"Mango-2026","usuario":"app_tienda"}
2
```

É como o histórico de versões de um documento na nuvem: dá para voltar à de ontem se a de hoje deu errado.

**Apagar (com rede de segurança).** O `DELETE` sobre `data/` apaga a última versão, mas de forma reversível:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X DELETE $VAULT_ADDR/v1/secret/data/tienda/postgres
HTTP 204
```

Ao ler, já não há dados, a resposta traz a hora da exclusão e o código é 404:

```
null
"2026-10-18T14:47:29.564180533Z"
HTTP 404
```

**Recuperar.** O `undelete` a traz de volta:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X POST \
    $VAULT_ADDR/v1/secret/undelete/tienda/postgres -d '{"versions": [2]}'
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c .data.data
{"password":"Mango-2026","usuario":"app_tienda"}
```

**Destruir (sem volta).** O `destroy` apaga para sempre as versões indicadas. Destruir a 1, a senha antiga:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" -X PUT \
    $VAULT_ADDR/v1/secret/destroy/tienda/postgres -d '{"versions": [1]}'
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" "$VAULT_ADDR/v1/secret/data/tienda/postgres?version=1" | jq -c ".data.metadata | {version, destroyed}"
{"version":1,"destroyed":true}
```

**Os metadados** contam a história do segredo, inclusive quem criou cada versão:

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

Nessa consulta do `jq`, o `map_values(...)` percorre cada versão e deixa só dois dados dela: se foi destruída e quem a criou.

E, para ver quais segredos existem numa pasta, o verbo `LIST`:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X LIST $VAULT_ADDR/v1/secret/metadata/tienda | jq -c .data
{"keys":["postgres"]}
```

### A alternativa: o comando `vault` dentro do contêiner

Tudo o que foi feito acima também se faz com o comando `vault`, que vem dentro do contêiner. O `-e VAULT_TOKEN` passa a variável para ele:

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

Guardar com ele um segundo segredo, o da folha de pagamento, que será usado para testar permissões:

```
$ docker compose exec -e VAULT_TOKEN vault vault kv put secret/nomina/banco cuenta=0123456789 clave=Aguacate-99
====== Secret Path ======
secret/data/nomina/banco
...
version            1
```

Reparar que o comando acrescenta o `data/` sozinho. Por isso o `curl` ensina mais: mostra o caminho real.

## Passo 9 — Políticas: cada um com a chave própria

Uma **política** (*policy*) diz quais caminhos um token pode tocar e o que ele pode fazer neles. Criar a pasta `politicas/` e dentro dela o arquivo `politicas/lectura-tienda.hcl`:

```hcl
# La app de la tienda puede LEER sus secretos. Nada más.
path "secret/data/tienda/*" {
  capabilities = ["read"]
}
```

O `*` quer dizer «qualquer coisa sob `tienda/`». As capacidades mais usadas são `read`, `create`, `update`, `delete` e `list`. O que não está escrito está negado.

Enviá-la. A API espera o texto da política dentro de um JSON; o `jq --rawfile p archivo` lê o arquivo e o guarda na variável `p`; o `-n` diz ao `jq` para não esperar dados de entrada, e o `\$p` leva barra invertida para que o terminal não o confunda com uma variável dele. Assim o `jq` embrulha a política no JSON sem que seja preciso escapá-la manualmente:

```
$ jq -n --rawfile p politicas/lectura-tienda.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/lectura-tienda -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X LIST $VAULT_ADDR/v1/sys/policies/acl | jq -c .data.keys
["default","default-ceiling","lectura-tienda","root"]
```

O `-d @-` diz ao `curl` «o corpo vem da entrada», ou seja, do que o `jq` passou pelo pipe.

Agora criar um **token para o app**, com essa política e uma hora de vida. O token completo vai para `secretos-locales/`, nunca para a tela:

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

A política `default` vem incluída em todos os tokens; permite fazer coisas básicas, como consultar o próprio token. `lease_duration: 3600` são 3.600 segundos: uma hora.

Testar os três casos. **Ler o que é dele:**

```
$ curl -s -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres | jq -c .data.data
{"password":"Mango-2026","usuario":"app_tienda"}
```

Código 200. **Ler a folha de pagamento:**

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/nomina/banco
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

**Escrever no que é dele:**

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" -X POST \
    $VAULT_ADDR/v1/secret/data/tienda/postgres -d '{"data": {"password": "me-la-robe"}}'
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Dois 403. O guichê disse não. E é possível perguntar ao Vault o que ele permite em cada caminho, sem tentar:

```
$ curl -s -H "X-Vault-Token: $APP_TOKEN" -X POST $VAULT_ADDR/v1/sys/capabilities-self \
    -d '{"paths": ["secret/data/tienda/postgres", "secret/data/nomina/banco"]}' \
    | jq -c "{tienda: .[\"secret/data/tienda/postgres\"], nomina: .[\"secret/data/nomina/banco\"]}"
{"tienda":["read"],"nomina":["deny"]}
```

## Passo 10 — O log: quem pediu o quê

Cada linha de `vault/logs/audit.log` é um JSON. Quantas já existem:

```
$ wc -l vault/logs/audit.log
      62 vault/logs/audit.log
```

As últimas respostas, resumidas: hora, quem, qual operação, qual caminho e se houve erro:

```
$ tail -n 6 vault/logs/audit.log | jq -c "select(.type == \"response\") | {hora: .time, quien: .auth.display_name, operacion: .request.operation, ruta: .request.path, error: .error}"
{"hora":"2026-10-18T14:47:54.325141694Z","quien":"token-app-tienda","operacion":"update","ruta":"secret/data/tienda/postgres","error":"1 error occurred:\n\t* permission denied\n\n"}
{"hora":"2026-10-18T14:47:54.338083991Z","quien":"token-app-tienda","operacion":"update","ruta":"sys/capabilities-self","error":null}
{"hora":"2026-10-18T14:47:54.351637479Z","quien":"token-app-tienda","operacion":"read","ruta":"auth/token/lookup-self","error":null}
```

Ali está a tentativa de escrita do app, com o nome dele (`token-app-tienda`: o Vault põe `token-` na frente do `display_name`) e o `permission denied`. Isto é o que Iván não tinha no sábado: **nome e sobrenome de cada tentativa**.

Quem leu o segredo da loja?

```
$ jq -c "select(.type == \"response\" and .request.path == \"secret/data/tienda/postgres\" and .request.operation == \"read\") | {quien: .auth.display_name, error}" vault/logs/audit.log
{"quien":"root","error":null}
...
{"quien":"token-app-tienda","error":null}
```

Várias leituras de `root` (de quem estava configurando) e uma do app.

Agora, o interessante. O log guardou a senha?

```
$ jq -c "select(.type == \"response\" and .request.path == \"secret/data/tienda/postgres\" and .auth.display_name == \"token-app-tienda\") | .response.data" vault/logs/audit.log | head -1
{"data":{"password":"hmac-sha256:bbda6f946e50152cf8b72cd5a9716a077096420551a4c5a7cb395e4f7eddd734","usuario":"hmac-sha256:becdf07b09b37a0b8d310c8f5e99dac229b4cc1b80e092e4b9107ee0f7483212"},"metadata":{...}}
$ grep -c "Mango-2026" vault/logs/audit.log
0
```

Não. Por padrão, o Vault escreve no log uma **impressão** (um HMAC-SHA256) dos valores de texto sensíveis, não o valor ([Audit devices](https://developer.hashicorp.com/vault/docs/audit)). Os números e os valores sim/não ele não converte em impressão; por isso convém guardar no Vault segredos de texto, como neste laboratório. Uma impressão é como a impressão digital de uma pessoa: serve para comprovar se duas coisas são a mesma, mas não permite reconstruir a pessoa. Assim, quem ler o log não leva as senhas.

E, se um dia for preciso saber se a senha que apareceu num chat é a que o app leu, pede-se ao Vault a impressão desse texto e compara-se:

```
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/sys/audit-hash/archivo \
    -d '{"input": "Mango-2026"}' | jq -r .data.hash
hmac-sha256:bbda6f946e50152cf8b72cd5a9716a077096420551a4c5a7cb395e4f7eddd734
```

É a mesma impressão. Bate.

Para fechar, o app pode **revogar o próprio token** quando termina. Depois disso, ele não serve mais:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/revoke-self
HTTP 204
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $APP_TOKEN" $VAULT_ADDR/v1/secret/data/tienda/postgres
{"errors":["2 errors occurred:\n\t* permission denied\n\t* invalid token\n\n"]}
 HTTP 403
```

---

👉 **Para quem é de Administração:** as chaves de Shamir são o equivalente técnico das **assinaturas conjuntas** de uma conta bancária: para movimentar dinheiro assinam dois de três procuradores, e nenhum pode sozinho. A política com 403 é a **segregação de funções**: quem lança não autoriza, quem cobra não concilia. E o log com impressões é uma auditoria que registra quem mexeu em cada processo sem fotocopiar o processo. Quem tiver de revisar os controles de um sistema deve perguntar por estas três coisas com essas palavras; quase sempre se é entendido.

---

## Exercícios da sessão 2

As soluções estão no final.

**Exercício 6 — A catraca.** Criar uma pasta nova, `lab-prueba`, e copiar para lá só três arquivos: `.gitignore`, `compose.yaml` e `iniciar.sh`. Fazer assim, com cópia nova, e não copiando a pasta já usada: essa já traz um `.env` e o exercício não demonstraria nada. Dentro de `lab-prueba`, apagar a linha `.env` do `.gitignore` e rodar `./iniciar.sh`.

**Como conferir:** antes de rodar o script, `ls -a` não deve mostrar nenhum `.env`. Depois, deve dizer `ALTO: .gitignore no tiene la regla '.env'.`, sair com código 1 (conferir com `echo $?` logo em seguida) e **não** criar o arquivo `.env` (conferir com `ls -a`).

**Exercício 7 — Os guardiões.** Reiniciar o Vault com `docker compose restart vault`. Abrir o Vault usando as chaves 4 e 5 (`.keys[3]` e `.keys[4]`) e depois a 1.

a) Importa quais três chaves são usadas?
b) O que aparece em `progress` depois da segunda chave?

**Como conferir:** no final, `sys/health` deve responder `200`.

**Exercício 8 — Um segredo próprio com versões.** Guardar em `secret/data/tienda/correo` um usuário `avisos` e uma senha gerada com `openssl rand -hex 12`. Depois trocá-la por outra gerada do mesmo jeito. No fim:

a) Ler a versão 1 e a 2.
b) Apagar a 2 com `DELETE`, comprovar o 404 e recuperá-la.
c) Mostrar com `metadata/` quantas versões existem.

**Como conferir:** `current_version` deve ser `2` e a leitura final deve dar a segunda senha.

**Exercício 9 — Uma política para a contabilidade.** Escrever `politicas/contabilidad.hcl`: pode **ler** `secret/data/nomina/*` e **listar** `secret/metadata/nomina/*`, nada mais. Enviá-la, criar um token com ela (guardá-lo em `secretos-locales/`) e testar:

a) Ler `secret/data/nomina/banco`.
b) Ler `secret/data/tienda/postgres`.
c) Escrever em `secret/data/nomina/banco`.

**Como conferir:** a) 200; b) 403; c) 403. E `sys/capabilities-self` para o caminho da folha de pagamento deve dizer `["read"]`.

**Exercício 10 — O detetive.** Com `jq` sobre `vault/logs/audit.log`, tirar uma lista de **todas as respostas com erro**, mostrando quem e qual caminho.

**Como conferir:** devem aparecer, no mínimo, os dois 403 do `token-app-tienda` do passo 9 e os dois 403 do exercício 9 (b e c). Se a lista sair vazia, conferir se o filtro usa `.type == "response"` e se a pergunta é por `.error != null`.

---

## Erros comuns (e como perceber)

| Erro | Como aparece | Como perceber | O que fazer |
|---|---|---|---|
| Esquecer o `data/` no caminho do KV v2 | `curl .../v1/secret/tienda/postgres` dá 404 com o aviso `Invalid path for a versioned K/V secrets engine` | O caminho não tem `data/` | Dados em `secret/data/...`; versões em `secret/metadata/...` |
| Política escrita sem `data/` | Foi colocado `path "secret/tienda/*"` e o token recebe 403 no que é dele | `sys/capabilities-self` diz `deny` | A política usa o caminho da API: `secret/data/tienda/*` |
| Vault selado depois de reiniciar | Tudo responde `{"errors":["Vault is sealed"]}` com código 503 | `sys/seal-status` diz `sealed: true` | Abrir com 3 chaves. É o que deve acontecer, não uma falha |
| A variável `VAULT_TOKEN` vazia | 403 mesmo usando o token root | `echo ${#VAULT_TOKEN}` dá `0` | Cada terminal novo começa sem variáveis: exportá-la de novo |
| Aspas simples em volta de uma variável | `-d '{"key": "$LLAVE"}'` manda o texto `$LLAVE` | O Vault diz que a chave não é válida | Dentro de aspas simples, o terminal não substitui variáveis. Usar aspas duplas e escapar as internas: `"{\"key\": \"$LLAVE\"}"` |
| Colar o token num arquivo do repo | O token aparece no `git status` ou num commit | `git log -p -S hvs.` o encontra | Os tokens vivem em `secretos-locales/` e em variáveis do terminal. Se foi enviado: revogá-lo |
| Porta ocupada ao iniciar | `bind: address already in use` | `lsof -nP -iTCP:5432 -sTCP:LISTEN` mostra outro processo (trocar 5432 por 8200 ou 3306 se for outro serviço) | Trocar a porta no `.env` (`PUERTO_POSTGRES=15432`, `PUERTO_VAULT` ou `PUERTO_MARIADB`) e rodar de novo `docker compose up -d`; se `PUERTO_VAULT` mudou, definir `VAULT_ADDR` de novo |

---

## Revisão para a próxima sessão

A sessão 3 começa com estas três perguntas. Responder sem consultar:

1. Por que o Vault inicia selado, e quantas chaves são necessárias por padrão para abri-lo?
2. Um token recebe 403. Quais são duas causas possíveis, e qual rota do Vault diz o que esse token pode fazer?
3. Se alguém roubar o log de auditoria, leva as senhas? Por quê?

🔁 **Na próxima semana:** o backup roubado tinha oito mil CURP, e a chave para lê-los estava ao lado. Aprende-se a cifrar com o Vault sem que o programa jamais tenha a chave, guardam-se os dados cifrados no PostgreSQL e descobre-se quantas vezes aquele backup foi levado.

**Antes de sair:** desligar o laboratório com `docker compose stop`. Os dados ficam nas pastas. Na próxima vez, `docker compose start` e abrir o selo com o laço do passo 5.

---

## Soluções (não olhe antes de tentar)

**Revisão da sessão 1.**

1. Quaisquer quatro entre: a senha no código ou num arquivo que é enviado; o `.env` que circula por chat; a mesma senha para todos e para sempre; ninguém sabe quem a usou; quem saiu ainda a sabe; a chave de cifragem junto dos dados.
2. Porque o git guarda o histórico: a senha continua nas alterações anteriores, e qualquer pessoa que tenha clonado o repositório tem uma cópia. Apagar não desfaz as cópias; trocar a senha, sim, as torna inúteis.
3. Parece-se no fato de que se enviam dados e se recebem dados cifrados sem que a chave saia. Diferencia-se porque um HSM é um aparelho físico com proteções contra violação (quão fortes são depende do modelo), e o Vault é software num servidor; o Transit é um motor do Vault que oferece as operações de cifragem por API.

**Exercício 6.** A saída é:

```
ALTO: .gitignore no tiene la regla '.env'.
Sin ella, las contraseñas que voy a generar podrían terminar en git. No sigo.
```

O `echo $?` dá `1` e o `ls -a` não mostra `.env`.

**Exercício 7.** a) Não importa: qualquer combinação de 3 das 5 serve. b) `progress: 2` e `sealed: true`. Com a terceira, `sealed: false`.

**Exercício 8.** Uma forma:

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

As duas primeiras dão `1` e `2`; as duas leituras com `?version=` mostram a primeira e a segunda senha; o `DELETE` dá `204`, a leitura seguinte `404`, e `current_version` dá `2`. A última linha imprime `true` se a leitura final traz a segunda senha. Reparar que essas senhas nunca foram escritas à mão: saíram do `openssl` e viajaram numa variável.

**Exercício 9.** A política:

```hcl
path "secret/data/nomina/*" {
  capabilities = ["read"]
}
path "secret/metadata/nomina/*" {
  capabilities = ["list"]
}
```

Ela é enviada e usada igual à `lectura-tienda`, trocando o nome. Os resultados esperados: 200, 403, 403.

**Exercício 10.**

```
jq -c 'select(.type == "response" and .error != null) | {quien: .auth.display_name, ruta: .request.path, error}' vault/logs/audit.log
```

Reparar que aqui o filtro vai entre aspas simples, e por isso as aspas duplas de dentro não levam barra invertida.

---

## O que vem a seguir

Na sessão 3 usa-se o PostgreSQL pelo terminal com o `psql`. Conferir se ele está instalado com `psql --version`. Se não, instalar o cliente: `sudo apt install postgresql-client` no Linux, ou `brew install libpq` no macOS (e seguir a indicação que ele dá para adicioná-lo ao `PATH`).

---

*Escrevo a partir do que vemos todos os dias na Hábil, onde construímos sistemas para bancos, seguradoras e empresas no México. Se no trabalho ou no negócio da família de quem lê surgir um problema assim, vamos conversar: [habil.mx](https://www.habil.mx/pt/)*
