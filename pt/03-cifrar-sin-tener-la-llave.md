# Vault do zero (3): cifrar sem ter a chave

*O motor Transit do Vault cifra e decifra no lugar do programa, e a chave nunca chega a ele. Guardam-se CURP cifrados no PostgreSQL, rotaciona-se a chave sem perder nada e aprende-se a apagar dados destruindo uma chave.*

*Vault do zero · sessão 3 de 4*

## Revisão da sessão 2

Responder sem consultar. As respostas estão nas soluções.

1. Por que o Vault inicia selado, e quantas chaves são necessárias por padrão para abri-lo?
2. Um token recebe 403. Quais são duas causas possíveis, e qual rota do Vault diz o que esse token pode fazer?
3. Se alguém roubar o log de auditoria, leva as senhas? Por quê?

> **O laboratório desta sessão** está no repositório público [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Monte-o primeiro por conta própria; o repositório serve para comparar quando algo não sair igual. Não traz nenhuma senha: o laboratório as gera ao iniciar.

## Objetivos desta sessão

| # | Ao terminar, é possível… | Demonstrado no |
|---|---|---|
| 1 | **Cifrar e decifrar** um dado com o Transit usando `curl`, e **explicar** o que é base64 e por que não é cifragem | Exercício 11 |
| 2 | **Rotacionar** uma chave e **reenvelopar** (rewrap) dados antigos para a versão nova sem decifrá-los manualmente | Exercícios 12 e 14 |
| 3 | **Escrever** uma política que deixa cifrar mas não decifrar, e **comprovar** o 403 | Exercício 13 |
| 4 | **Guardar** dados cifrados no PostgreSQL com `psql` e **demonstrar** que quem lê a tabela não vê o dado | Passo 8 (guiado) e exercício 14 |
| 5 | **Vincular** um dado cifrado ao dono dele com `context`, e **destruir** uma chave para tornar ilegível o que ela cifrou | Exercício 15 e passo 10 |

---

## Cenário (ficção) — Capítulo 7: segunda-feira, 10:12

Iván não dormiu bem no fim de semana. O relógio das 3:17 não o deixa em paz.

Na segunda, ele pede ao provedor do servidor o log completo de downloads da pasta de backups. Não o de uma semana: o de toda a vida do servidor. Chega um arquivo de texto com milhares de linhas. Ele o filtra pelo endereço `185.xx.xx.xx`.

O primeiro download vindo desse endereço não foi no sábado passado.

Foi há dois anos e três meses.

E desde então, **todo sábado às 3:21**, alguém baixou o backup da noite. E a pasta com o `llave.txt`. Cento e dezessete sábados seguidos.

Valeria, que por fim confessou o caso do repositório público, sente o peito se aliviar. O erro dela foi há dez dias. Isto dura dois anos.

— Então não foi pelo que eu enviei — diz.

— Não — responde Iván. — O que foi enviado também era grave, e por isso trocamos tudo. Mas isto é outra coisa.

Dona Clara faz a pergunta incômoda:

— E quantas vezes levaram os CURP?

— Cento e dezessete.

---

## Capítulo 8: segunda-feira, 16:50

Enquanto Iván refaz a cifragem dos CURP, Rocío, a contadora, entra no escritório com um extrato do cartão da empresa. Está fazendo a conciliação do mês e há uma cobrança que ela nunca entendeu:

```
SERV VIRTUAL CLOUD  TR-REPORTES     USD 9.99
```

— Está assim há uns dois anos — diz. — Sempre achei que era algo daqui da empresa.

Iván procura no painel do provedor o endereço do servidor que paga essa cobrança.

`185.xx.xx.xx`.

TR.

*(Continua na sessão 4.)*

---

## Por que isso importa

O problema número 6 da sessão 1 era a chave junto dos dados. A Canasta Morada cifrava os CURP, sim, mas quem levou o backup levou também o `llave.txt`, e a cifragem não serviu de nada.

A solução não é esconder melhor o arquivo. É que **a chave não esteja em nenhum arquivo que o programa possa ler**. O programa diz ao Vault «cifre isto» e recebe o dado cifrado. Diz «decifre isto» e, se tiver permissão, recebe o dado original. A chave fica no Vault, protegida pelo selo que foi aberto na semana passada com três chaves.

Isso é o motor **Transit**. A documentação o descreve como «criptografia como serviço» ou «cifragem como serviço», e esclarece que o Vault **não guarda** os dados que recebe: o resultado é guardado onde se quiser ([Transit](https://developer.hashicorp.com/vault/docs/secrets/transit)).

Assim, se amanhã alguém levar o backup do banco de dados, leva textos como `vault:v2:SmfKDK1u...`. Sem acesso ao Vault, eles não servem de nada.

## Três palavras antes de começar

**Cifrar.** Misturar um dado com uma **chave** para que só quem tenha a chave possa voltar a lê-lo. Quando, criança, se escreviam mensagens em código trocando cada letra pela seguinte do alfabeto, a chave era «uma letra adiante». O Transit usa por padrão AES-256 no modo GCM, que é muitíssimo mais forte e ainda detecta se alguém alterou o dado cifrado ([API do Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)).

**Base64.** Uma forma de escrever qualquer dado, até um binário, usando só letras, números, `+`, `/` e `=`. O Transit pede os dados em base64 porque assim um dado qualquer (um texto, uma imagem pequena) pode viajar dentro de um JSON. Atenção ao tamanho: a API do Vault limita por padrão cada requisição a 32 MB, e o base64 deixa os dados um terço maiores. Para arquivos grandes, cifra-se com outra técnica, sem mandá-los inteiros ao Transit. **Base64 não é cifragem.** É como a língua do P: «copasapa» parece segredo, mas qualquer pessoa que conheça a regra lê. Experimentar:

```
$ echo -n "PEPE000101HDFXXX01" | base64
UEVQRTAwMDEwMUhERlhYWDAx
$ echo "UEVQRTAwMDEwMUhERlhYWDAx" | base64 -d; echo
PEPE000101HDFXXX01
```

O `-n` do `echo` evita que uma quebra de linha entre no final; sem ele, seria cifrado «CURP + Enter». Os CURP desta lição são inventados e não correspondem a nenhuma pessoa; levam `XXX` para que isso fique evidente. Não usar dados de pessoas reais nas práticas.

**Versão de chave.** Uma chave do Transit pode ter várias versões. Quando é **rotacionada**, nasce uma versão nova que passa a ser usada para cifrar o que vem; as antigas ficam guardadas para poder decifrar o que veio antes. É como trocar todo ano a combinação do cadeado do depósito, guardando as combinações anteriores num envelope, para o caso de aparecer uma caixa velha.

---

## Passo 1 — Subir o laboratório e ligar o Transit

**Dois recursos do terminal que serão usados o tempo todo.** `NOME=$(comando)` executa o `comando` e guarda o resultado em `NOME`. `$NOME` insere depois esse resultado. Experimentar: `SALUDO=$(echo hola); echo "$SALUDO"` deve mostrar `hola`. No bloco seguinte, `LLAVE=$(...)` guarda temporariamente uma chave de desbloqueio; se algo falhar, conferir se `LLAVE` não ficou vazia com `echo "${#LLAVE}"` (deve dar um número maior que 0).

Se o laboratório foi desligado, ligá-lo, abrir o selo e exportar o token, como na sessão 2:

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

Ligar o motor Transit no caminho `transit/`:

```
$ curl -s -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/sys/mounts/transit -d '{"type": "transit"}'
HTTP 204
```

**Controle de estado.** O `docker compose stop` preserva o Transit, as chaves e a tabela. Se ao montar o Transit aparecer `HTTP 400` com `path is already in use`, ele já estava montado: seguir para o passo 2. Se a chave `curp` ou a tabela `clientes` já existirem, não repetir as inserções do passo 8. Ver primeiro o que há com `psql -c "SELECT id, nombre, left(curp, 9) FROM clientes;"` e continuar só se essas linhas forem reconhecidas como trabalho anterior.

## Passo 2 — Criar uma chave

Uma chave chamada `curp`. Não se manda nada: o Vault a gera por dentro.

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp
HTTP 200
```

Olhá-la:

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

Reparar no que **não** aparece: a chave. Em `keys` só há um número por versão, que é a data em que foi criada. `exportable: false` diz que não pode ser retirada. Comprovar:

```
$ curl -s -w " HTTP %{http_code}\n" -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/export/encryption-key/curp
{"errors":["private key material is not exportable"]}
 HTTP 400
```

Nem o token root consegue retirá-la. Se ao criá-la tivesse sido pedido `exportable: true`, seria possível, e essa decisão não tem volta; por isso vem desligada.

## Passo 3 — Cifrar

O texto vai em base64 dentro de `plaintext`. O `$(...)` faz a conversão na hora:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq .data
{
  "ciphertext": "vault:v1:A2se3zo5aKjY51c/tlquYpJrN/L8DDNh2BPzqvcrXfYwkW8yVVimMMzir5DRpw==",
  "key_version": 1
}
```

Esse `ciphertext` é o que será guardado. Tem três partes separadas por dois-pontos:

- `vault`: foi cifrado pelo Vault.
- `v1`: com a **versão 1** da chave.
- O restante: o dado cifrado.

Cifrar **o mesmo CURP outra vez**:

```
vault:v1:qy8hRw2+KeTOHWr/RJ7D4tPbSlRDiTk96lZGn9+Jijp+lJRyUlfZph3upajdFw==
```

É diferente. Cada cifragem leva um ingrediente aleatório (um *nonce*), e por isso duas cifragens do mesmo dado nunca se parecem. Assim ninguém pode olhar a tabela e dizer «estes dois clientes têm o mesmo CURP». (O Transit tem um modo chamado *convergente* que faz o contrário, de propósito, para permitir buscas; aqui ele não é usado.)

## Passo 4 — Decifrar

Envia-se o `ciphertext` e recebe-se base64:

```
$ C=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext)
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$C\"}" | jq .data
{
  "plaintext": "UEVQRTAwMDEwMUhERlhYWDAx"
}
```

E volta-se ao texto com `base64 -d`:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$C\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

Se alguém entregar lixo com cara de cifragem, o Vault não adivinha:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"vault:v1:estonoescifrado\"}"
{"errors":["invalid ciphertext: could not decode base64"]}
 HTTP 400
```

## Passo 5 — Rotacionar a chave sem perder nada

Guardar num arquivo uma cifragem feita com a versão 1, para usar depois:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext | tee v1.txt
vault:v1:0uoMoZKeXU+18t3TiH3yOlTX7vL9wlNUWlMf1W4XapYdoVq2Z1OWVAg7hIgWlA==
```

O `tee` mostra o resultado na tela e ainda o guarda no arquivo. Agora **rotacionar**:

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp/rotate
HTTP 200
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/curp | jq -c ".data | {latest_version, min_decryption_version, versiones: (.keys | keys)}"
{"latest_version":2,"min_decryption_version":1,"versiones":["1","2"]}
```

O que é novo sai com `v2`:

```
vault:v2:uzo5CXHaWgjXF3iUCzzefTFzOecaAcho3WjVJqnjVJ0IQIR3mk1DioElROdsxA==
```

E o que é antigo **ainda se decifra**, porque a versão 1 continua guardada:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

Rotacionar não quebra nada. Por isso pode ser feito com frequência; existe até o `auto_rotate_period`, para que o Vault rotacione sozinho uma chave de tempos em tempos.

## Passo 6 — Reenvelopar (rewrap): subir o antigo para a versão nova

Rotacionar não muda o que já está guardado: o banco de dados continua cheio de `v1`. Para subi-los para `v2` existe o **rewrap** (reenvelopar): entrega-se a cifragem antiga e ele devolve uma nova com a última versão. A documentação esclarece que nesse processo **o dado original não é revelado** ([Transit](https://developer.hashicorp.com/vault/docs/secrets/transit)): nem a pessoa nem o programa veem o CURP.

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/rewrap/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}" | jq -c .data | tee rewrap.json
{"ciphertext":"vault:v2:qR2K9Q5TmpKsG4umLEMX2bguVD1/R4nC+iNhKxAT5jrKGAc1clF5977n49Q85w==","key_version":2}
```

É como levar os papéis velhos ao cartório para receberem o selo novo, sem que ninguém os leia.

Quando tudo já estiver reenvelopado, diz-se ao Vault que **não aceite** cifragens mais antigas que a versão 2:

```
$ curl -s -w "HTTP %{http_code}\n" -o /dev/null -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/curp/config -d '{"min_decryption_version": 2}'
HTTP 200
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat v1.txt)\"}"
{"errors":["ciphertext or signature version is disallowed by policy (too old)"]}
 HTTP 400
```

O `v1` já não serve. O reenvelopado, sim:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(jq -r .ciphertext rewrap.json)\"}" | jq -r .data.plaintext | base64 -d; echo
PEPE000101HDFXXX01
```

Isto é o que a Canasta Morada precisava: se uma cópia velha do banco de dados andar por aí, com cifragens `v1`, com esta configuração essa cópia já não pode ser decifrada. Atenção: **não é apagamento criptográfico**. O Vault ainda conserva a versão 1 da chave, e um operador autorizado poderia baixar de novo o mínimo para permitir decifrá-la (a documentação descreve isso como um ajuste que faz parte de uma política de rotação). Destruir uma chave de verdade é o passo 10.

## Passo 7 — Uma política que cifra mas não decifra

O formulário de cadastro de clientes precisa **cifrar** CURP. Nunca precisa lê-los. Criar `politicas/solo-cifrar-curp.hcl`:

```hcl
# El formulario de alta puede CIFRAR curps, pero nunca descifrarlas.
path "transit/encrypt/curp" {
  capabilities = ["update"]
}
```

No Transit, cifrar e decifrar são operações de escrita (`POST`), e nas políticas isso se chama `update`. Para esta chave, que já existe, `update` é a capacidade mínima correta. Atenção: a rota `transit/encrypt/<chave>` aceita `create` ou `update`, e com `create` o Vault pode criar uma chave que não existia, com valores predeterminados, a menos que essa criação automática tenha sido desativada ([Transit: Encrypt data](https://developer.hashicorp.com/vault/api-docs/secret/transit#encrypt-data)). Não deduzir a capacidade da política só pelo verbo HTTP.

Enviá-la e criar um token para o formulário. Dura 3 horas, o tempo da sessão com os exercícios; se expirasse antes, um 403 se pareceria com o 403 que se procura no exercício 13:

```
$ jq -n --rawfile p politicas/solo-cifrar-curp.hcl "{policy: \$p}" \
    | curl -s -w "HTTP %{http_code}\n" -X PUT -H "X-Vault-Token: $VAULT_TOKEN" \
      $VAULT_ADDR/v1/sys/policies/acl/solo-cifrar-curp -d @-
HTTP 204
$ curl -s -H "X-Vault-Token: $VAULT_TOKEN" -X POST $VAULT_ADDR/v1/auth/token/create \
    -d '{"policies": ["solo-cifrar-curp"], "ttl": "3h", "display_name": "formulario-alta"}' \
    | jq -r .auth.client_token > secretos-locales/token-formulario.txt
```

O formulário cifra o CURP de uma cliente nova:

```
$ F=$(cat secretos-locales/token-formulario.txt)
$ curl -s -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n MARA990909MDFXXX02 | base64)\"}" | jq -r .data.ciphertext | tee maria.txt
vault:v2:4LM7LCPcgym6rQAPOMQGWR4DIk1qi4NdtoaBM/yecdQfWsG9iCypdv7IST71dQ==
```

Mas, se tentar lê-lo, ou rotacionar a chave:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$(cat maria.txt)\"}"
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/keys/curp/rotate
{"errors":["1 error occurred:\n\t* permission denied\n\n"]}
 HTTP 403
```

Se alguém roubar o token do formulário, pode inserir CURP cifrados, mas não consegue ler nenhum. É uma caixa de correio: qualquer pessoa joga cartas, só o carteiro abre.

## Passo 8 — Guardar no PostgreSQL

O PostgreSQL já está rodando desde a sessão 2. A senha dele está no `.env`, que o script gerou. Carregá-la no terminal sem copiá-la manualmente: o `set -a` faz tudo o que for lido ser exportado, e o `source .env` lê o arquivo.

```
set -a; source .env; set +a
export PGHOST=127.0.0.1 PGPORT=$PUERTO_POSTGRES PGUSER=postgres PGDATABASE=tienda PGPASSWORD=$POSTGRES_PASSWORD
```

O `psql` lê sozinho essas variáveis `PG...`; assim a senha não é escrita no comando, onde ficaria no histórico. Isso é aceitável num laboratório local, mas o `PGPASSWORD` deixa a senha no ambiente do processo, e a documentação do PostgreSQL desaconselha isso porque, em alguns sistemas, outros processos podem vê-la. Em produção, usa-se um arquivo de senhas com permissões estritas ou, melhor, o Vault.

Criar a tabela de clientes:

```
$ psql -c "CREATE TABLE clientes (id serial PRIMARY KEY, nombre text NOT NULL, curp text NOT NULL);"
CREATE TABLE
```

Inserir o Pepe com o CURP cifrado. Primeiro cifra-se, depois guarda-se o resultado:

```
$ CIF=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n PEPE000101HDFXXX01 | base64)\"}" | jq -r .data.ciphertext)
$ psql -c "INSERT INTO clientes (nombre, curp) VALUES ('Pepe', '$CIF');"
INSERT 0 1
```

E a María, cifrada pelo token do formulário, que não pode ler:

```
$ F=$(cat secretos-locales/token-formulario.txt)
$ CIF=$(curl -s -X POST -H "X-Vault-Token: $F" $VAULT_ADDR/v1/transit/encrypt/curp \
    -d "{\"plaintext\": \"$(echo -n MARA990909MDFXXX02 | base64)\"}" | jq -r .data.ciphertext)
$ psql -c "INSERT INTO clientes (nombre, curp) VALUES ('María', '$CIF');"
INSERT 0 1
```

Agora, olhar a tabela como a veria alguém com permissão de leitura (`SELECT`) sobre `clientes`, o proprietário dela, um superusuário ou quem tenha o backup. Conectar-se ao banco de dados não basta: no PostgreSQL é necessária essa permissão ([Privilégios](https://www.postgresql.org/docs/17/ddl-priv.html)). Aqui funciona porque entramos como `postgres`:

```
$ psql -c "SELECT * FROM clientes;"
 id | nombre |                                   curp
----+--------+---------------------------------------------------------------------------
  1 | Pepe   | vault:v2:GCD4q2/Fp+YtLKT185oGtoSBJ4M9wE5oKrOaDy93Hlmf84Nzh/4ZxWW+E62chg==
  2 | María  | vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
(2 rows)
```

Dizem `v2` porque a chave foi rotacionada no passo 5. E o backup, que é o que levavam da Canasta Morada todo sábado:

```
$ docker compose exec postgres pg_dump -U postgres -t clientes tienda | grep -A3 "^COPY"
COPY public.clientes (id, nombre, curp) FROM stdin;
1	Pepe	vault:v2:GCD4q2/Fp+YtLKT185oGtoSBJ4M9wE5oKrOaDy93Hlmf84Nzh/4ZxWW+E62chg==
2	María	vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
\.
```

Nenhum CURP legível. E já não há `llave.txt` para levar.

Quem tem permissão de decifrar lê da tabela e pede ao Vault:

```
$ CIF=$(psql -At -c "SELECT curp FROM clientes WHERE nombre = 'María';"); echo "$CIF"
vault:v2:SmfKDK1u10+e2oXoVbWwDphXApm4rxduP5fxY6CrpQcvoNTZB3Vg6Z4m9BEYlA==
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/curp \
    -d "{\"ciphertext\": \"$CIF\"}" | jq -r .data.plaintext | base64 -d; echo
MARA990909MDFXXX02
```

O `-At` pede ao `psql` só o valor, sem cabeçalhos nem bordas.

## Passo 9 — Vincular a cifragem ao dono: `context`

Imagine que a Canasta Morada comece a guardar cadastros de duas empresas que compram dela no atacado, a Empresa Norte e a Empresa Sur, na mesma tabela. Um erro de programação, ou alguém mal-intencionado, poderia pegar um cadastro cifrado da Norte, colá-lo na linha da Sur e pedir que o decifrem «como se fosse da Sur».

O Transit tem uma defesa para isso: as **chaves derivadas**. Ao criar a chave com `derived: true`, cada operação precisa trazer um `context`: um dado extra, em base64, do qual o Vault deriva uma chave diferente. Com outro `context`, outra chave ([API do Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)). É como um envelope que só abre com o selo da empresa a que se destina.

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/expedientes -d '{"derived": true}'
HTTP 200
```

Sem `context`, ele se recusa:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
    -d "{\"plaintext\": \"$(echo -n diagnostico-confidencial | base64)\"}"
{"errors":["missing 'context' for key derivation; the key was created using a derived key, which means additional, per-request information must be included in order to perform operations with the key"]}
 HTTP 400
```

Cifrar para a Empresa Norte:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
    -d "{\"plaintext\": \"$(echo -n diagnostico-confidencial | base64)\", \"context\": \"$(echo -n empresa-norte | base64)\"}" \
    | jq -r .data.ciphertext | tee ctx.txt
vault:v1:8lKFunrcJVIzLnq9q4ZNszSLDOotf4gqtenuKek8QTuCIh4yq1ldoqtjMbsojged+/0aPQ==
```

Com o `context` correto, lê-se:

```
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
    -d "{\"ciphertext\": \"$(cat ctx.txt)\", \"context\": \"$(echo -n empresa-norte | base64)\"}" | jq -r .data.plaintext | base64 -d; echo
diagnostico-confidencial
```

Fazendo-se passar pela Empresa Sur:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
    -d "{\"ciphertext\": \"$(cat ctx.txt)\", \"context\": \"$(echo -n empresa-sur | base64)\"}"
{"errors":["cipher: message authentication failed"]}
 HTTP 400
```

`message authentication failed`: a verificação do AES-GCM detectou que isso não bate. O cadastro da Norte só abre como da Norte. Na vida real, o `context` costuma ser o identificador do cliente ou da empresa dona do dado.

Um esclarecimento importante: o `context` **não é uma senha nem uma autorização**. É um valor enviado por quem chama; se alguém tem permissão de decifrar essa chave e conhece o valor `empresa-norte`, pode pedir a decifragem com ele. Por isso a aplicação deve tirar o `context` de um dado confiável que não possa ser alterado (por exemplo, o dono registrado do cadastro), e as políticas devem limitar quem pode decifrar cada chave.

## Passo 10 — Apagar destruindo a chave

Último padrão, e o mais drástico. Um cliente vai embora e pede que os dados dele sejam apagados. Estão no banco de dados, nos backups de ontem à noite, nos de um mês atrás. Apagar em cada cópia é quase impossível.

Se cada cliente tem **a própria chave**, há outra saída: **destruir a chave**. Tudo o que foi cifrado com ela fica ilegível, esteja onde estiver. Isso é conhecido como apagamento criptográfico.

Criar uma chave para um cliente e cifrar algo dele:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 200
$ curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/cliente-que-se-va \
    -d "{\"plaintext\": \"$(echo -n datos-de-don-chema | base64)\"}" | jq -r .data.ciphertext | tee borrar.txt
vault:v1:tjerbuHJyEbw+3IiLl0rC/hSEa78E61i9Yg9CancZegxpnBsybXKvkGZ2DwtzQ==
```

Tentar apagá-la:

```
$ curl -s -w " HTTP %{http_code}\n" -X DELETE -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
{"errors":["error deleting policy cliente-que-se-va: deletion is not allowed for this key"]}
 HTTP 400
```

O Vault não deixa, por padrão. A documentação o chama de «uma operação potencialmente catastrófica» e exige ligar antes o `deletion_allowed` ([API do Transit](https://developer.hashicorp.com/vault/api-docs/secret/transit)). É a trava de segurança da pistola. Tirá-la e apagar:

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" \
    $VAULT_ADDR/v1/transit/keys/cliente-que-se-va/config -d '{"deletion_allowed": true}'
HTTP 200
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X DELETE -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 204
```

Agora tentar decifrar o que é de dom Chema:

```
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/cliente-que-se-va \
    -d "{\"ciphertext\": \"$(cat borrar.txt)\"}"
{"errors":["encryption key not found"]}
 HTTP 400
```

E se alguém criar outra chave com o mesmo nome?

```
$ curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/keys/cliente-que-se-va
HTTP 200
$ curl -s -w " HTTP %{http_code}\n" -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/cliente-que-se-va \
    -d "{\"ciphertext\": \"$(cat borrar.txt)\"}"
{"errors":["cipher: message authentication failed"]}
 HTTP 400
```

Mesmo nome, chave nova. O que é antigo continua ilegível: no banco de dados, no backup de ontem à noite e no de um ano atrás.

**Um aviso honesto.** Isto vale para as cópias dos **dados**. Se forem guardados backups **do próprio Vault** (da pasta de dados dele), um backup feito antes da exclusão ainda contém a chave. Para que o apagamento criptográfico seja completo, os backups do Vault também precisam expirar.

### A alternativa com o comando `vault`

```
$ docker compose exec -e VAULT_TOKEN vault vault write transit/encrypt/curp plaintext=$(echo -n PEPE000101HDFXXX01 | base64)
Key            Value
---            -----
ciphertext     vault:v3:7yIAAelQRE+2zGnTO+J0EJcPExHspE4elzod4VDFrTrTSkl4bAYZ9ygbQ25C1Q==
key_version    3
```

(Neste teste saiu a versão 3 porque os exercícios 12 e 14 já tinham sido feitos. Se este comando for executado agora, antes dos exercícios, o normal é que o resultado comece com `vault:v2:`. O número muda a cada rotação: não compará-lo com o do exemplo, e sim com o `latest_version` da chave `curp`.)

---

👉 **Para quem é de Administração:** a cifragem como serviço segue o mesmo princípio da **custódia de valores**: a transportadora guarda o dinheiro, quem contratou fica só com o comprovante, e para retirar é preciso autorização. A política «cifra mas não decifra» é o **guichê de depósitos**: qualquer pessoa deposita, só o procurador retira. E o apagamento destruindo a chave importa para a proteção de dados pessoais: quando um cliente exerce o direito de ter os dados dele eliminados, a área jurídica vai perguntar «e nos backups?». Esta técnica é uma resposta técnica que se pode demonstrar, mas não substitui a análise jurídica: a eliminação pode implicar um período de bloqueio antes de suprimir, prazos de guarda e exceções que a lei fixa.

---

## Exercícios da sessão 3

**Exercício 11 — Um CURP de mentira.** Inventar um CURP de mentira (com `XXX` no meio, como os da lição). Cifrá-lo duas vezes com a chave `curp` e decifrá-lo.

**Dica para quem travar.** No comando do passo 3 só muda o texto que vai dentro do `echo -n`. Guardar o resultado com `C=$(... | jq -r .data.ciphertext)`, como no passo 4, e para decifrar reutilizar esse mesmo comando trocando só o `ciphertext` por `$C`.

d) Completar sem consultar: «Base64 é __________. Não é cifragem porque __________. Nesta prática, a proteção começa quando __________.»

**Como conferir:** os dois `ciphertext` devem ser diferentes entre si, os dois devem começar com o mesmo `vault:vN:`, e ao decifrar com `base64 -d` deve sair o CURP exato, sem quebra de linha extra. Se no final aparecer uma linha vazia a mais, o `-n` foi esquecido no `echo`. Para o item d), comparar com a solução.

**Exercício 12 — Rotacionar e reenvelopar.** Cifrar o CURP e guardá-lo em `mio.txt`. Rotacionar a chave `curp`. Reenvelopar o `mio.txt`.

**Como conferir:** o número depois de `vault:v` no reenvelopado deve ser igual ao `latest_version` da chave (consultar com `GET transit/keys/curp`). E o reenvelopado deve decifrar para o CURP.

**Exercício 13 — A caixa de correio.** Com o token do formulário (`secretos-locales/token-formulario.txt`):

a) Cifrar um CURP.
b) Tentar decifrá-lo.
c) Tentar cifrar com outra chave, `expedientes`.
d) Agora escrever a política. Completar as lacunas sem olhar o passo 7:

```hcl
path "transit/____/curp" {
  capabilities = ["____"]
}
```

Enviá-la com o nome `solo-cifrar-prueba`, criar com ela um token de teste (os comandos do passo 7 trocando os nomes) e repetir a), b) e c) com esse token.

**Como conferir:** a) recebe-se um `vault:v...`; b) 403; c) 403, porque a política só menciona `transit/encrypt/curp`. Se o item a) devolver 403, não contar como correto: o token pode ter expirado. Criar outro com o comando do passo 7, carregar `F` de novo e recomeçar; a prova só vale a partir de quando cifrar com `F` devolve `vault:v...`. Em d), `encrypt/curp` funciona; `decrypt/curp` e `encrypt/expedientes` dão 403.

**Exercício 14 — Reenvelopar uma tabela inteira.** Rotacionar a chave `curp` outra vez. Depois percorrer a tabela `clientes` e reenvelopar cada CURP.

**Primeiro, um teste que não mexe em nada.** Antes de qualquer `UPDATE`, conferir se o laço lê bem a tabela:

```
psql -At -F " " -c "SELECT id, curp FROM clientes;" | while read ID CIF; do
  echo "ID=$ID | CIF=$CIF"
done
```

O `|` passa cada linha ao laço, o `-F " "` pede ao `psql` que separe as colunas com um espaço, e o `read` põe a primeira coluna em `ID` e a segunda em `CIF`. Deve aparecer uma linha por cliente antes de seguir.

Agora o esqueleto de verdade; completá-lo. O `if` evita que, se o Vault falhar, seja gravado na tabela um `null` no lugar do CURP cifrado:

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

**Como conferir:** `psql -c "SELECT id, nombre, left(curp, 9) AS version FROM clientes;"` deve mostrar a mesma versão nova em todas as linhas, e cada CURP deve continuar decifrando bem.

**Exercício 15 — O envelope errado.** Com a chave `expedientes`, cifrar a palavra `credito-aprobado` com o context `empresa-sur`. Decifrá-la com `empresa-sur`, depois com `empresa-norte` e depois sem context.

e) Sem executar outra exclusão, completar: «Recriar `cliente-que-se-va` não recupera o que foi cifrado antes porque __________. Antes de permitir a exclusão de uma chave, é preciso conferir __________.»

**Como conferir:** a primeira dá `credito-aprobado`; a segunda, `cipher: message authentication failed`; a terceira, `missing 'context' for key derivation`. O item e) se compara com a solução.

---

## Erros comuns (e como perceber)

| Erro | Como aparece | Como perceber | O que fazer |
|---|---|---|---|
| Mandar o texto sem base64 | Costuma sair `{"errors":["illegal base64 data at input byte N"]}` com código 400. Mas, se o texto for por acaso um base64 válido, o Vault o aceita e cifra bytes diferentes dos desejados | O valor de `plaintext` fica igual ao texto original | Sempre `$(echo -n TEXTO | base64)` |
| Esquecer o `-n` no `echo` | Ao decifrar aparece uma linha vazia a mais | O base64 termina diferente: `...WDAxCg==` em vez de `...WDAx` | `echo -n` não acrescenta a quebra de linha |
| Achar que base64 é cifragem | «Já está protegido, parece esquisito» | Qualquer pessoa lê com `base64 -d` | Base64 é só uma forma de escrever. A cifragem quem faz é o Transit |
| Subir `min_decryption_version` antes de reenvelopar | Os dados antigos dão `disallowed by policy (too old)` | Há linhas com `vault:v1:` na tabela | Reenvelopar tudo primeiro; subir o mínimo no final. Se já aconteceu e ainda há cifragens `v1`: repetir o comando de configuração do passo 6 com `{"min_decryption_version": 1}`, confirmar que o `v1.txt` volta a decifrar, reenvelopar tudo e só no final subir o mínimo para a versão nova |
| Política do Transit com `read` | O token recebe 403 ao cifrar | `sys/capabilities-self` não diz `update` | Cifrar e decifrar são `update` |
| Chave derivada sem `context` | `missing 'context' for key derivation` | A chave diz `derived: true` | Mandar sempre o mesmo `context`, em base64, para cifrar e decifrar |
| Apagar uma chave «para testar» | Tudo o que foi cifrado com ela fica ilegível para sempre | `encryption key not found` | Não há volta. Por isso existe o `deletion_allowed`: deixá-lo desligado, salvo quando se quer mesmo destruir |

---

## Revisão para a próxima sessão

A sessão 4 começa com estas três perguntas. Responder sem consultar:

1. O que significam as três partes de `vault:v2:SmfKDK1u...`?
2. A chave foi rotacionada. O que acontece com os dados que já estavam cifrados, e qual operação os sobe para a versão nova sem que ninguém veja o dado?
3. Por que um token que só pode cifrar é útil para um formulário de cadastro?

🔁 **Na próxima semana:** a Canasta Morada descobre de quem é o servidor `185.xx.xx.xx`. Faz-se com que as senhas do PostgreSQL e do MariaDB nasçam, expirem e mudem sozinhas, e escreve-se um programa em Python que se conecta ao banco de dados sem conhecer nenhuma senha.

**Antes de sair:** `docker compose stop`. Na próxima vez, `start`, abrir o selo e exportar o token.

---

## Soluções (não olhe antes de tentar)

**Revisão da sessão 2.**

1. Porque os dados dele estão cifrados em disco com uma chave-mestra que ele não guarda inteira: está partida em pedaços (Shamir). Por padrão são 5 pedaços e são necessários 3.
2. Que a política não inclui essa rota ou essa capacidade (por exemplo, a rota sem `data/`), ou que o token expirou ou foi revogado. O `sys/capabilities-self` diz o que o token pode fazer em cada rota.
3. Não, com a configuração padrão. O Vault registra uma impressão (HMAC-SHA256) da maioria dos valores de texto sensíveis, não o valor; serve para comparar, não para reconstruir. Verificar sempre a configuração do dispositivo de auditoria antes de presumir isso: com `log_raw=true`, com atributos isentos de impressão ou com valores que não são texto, o dado pode ficar sem proteção ([Auditoria](https://developer.hashicorp.com/vault/docs/audit)).

**Exercício 11.** Com um CURP de exemplo, `ABCD020202HDFXXX03`:

```
curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/curp \
  -d "{\"plaintext\": \"$(echo -n ABCD020202HDFXXX03 | base64)\"}" | jq -r .data.ciphertext
```

Duas vezes dão dois textos diferentes com o mesmo prefixo. Para decifrar, o comando do passo 4 com o `ciphertext` obtido.

Item d): «Base64 é uma forma de escrever dados (uma codificação). Não é cifragem porque qualquer pessoa pode revertê-lo. Nesta prática, a proteção começa quando o Transit cifra o dado com a chave.»

**Exercício 12.** Rotaciona-se com `POST transit/keys/curp/rotate`, reenvelopa-se com `POST transit/rewrap/curp` mandando `{"ciphertext": "<o conteúdo de mio.txt>"}`. Se antes a última versão era a 2, depois de rotacionar é a 3 e o reenvelopado começa com `vault:v3:`.

**Exercício 13.** a) Igual ao passo 7. b) e c) `{"errors":["1 error occurred:\n\t* permission denied\n\n"]}` com `HTTP 403`. d) As lacunas são `encrypt` e `update`: a mesma política do passo 7 com outro nome.

**Exercício 14.** As lacunas são `rewrap` e `$ID`. Cada rotação cria uma versão nova: se o exercício 12 foi feito antes, esta rotação leva a chave à versão 4 e aparece `vault:v4:`; se não, à 3. No teste desta lição, depois de rotacionar para a versão 3:

```
 id | nombre |  version
----+--------+-----------
  1 | Pepe   | vault:v3:
  2 | María  | vault:v3:
(2 rows)
```

Ninguém viu um único CURP durante o processo: nem a pessoa, nem o terminal, nem o laço. Se o `if` imprimir «No actualicé», essa linha ficou como estava; corrigir o problema e rodar o laço de novo.

**Exercício 15.**

```
CTX_SUR=$(echo -n empresa-sur | base64)
C=$(curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/encrypt/expedientes \
  -d "{\"plaintext\": \"$(echo -n credito-aprobado | base64)\", \"context\": \"$CTX_SUR\"}" | jq -r .data.ciphertext)
curl -s -X POST -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_ADDR/v1/transit/decrypt/expedientes \
  -d "{\"ciphertext\": \"$C\", \"context\": \"$CTX_SUR\"}" | jq -r .data.plaintext | base64 -d; echo
```

Para as outras duas, trocar o context por `$(echo -n empresa-norte | base64)` ou tirar o campo `context`. Os erros são os do passo 9.

Item e): «porque a chave nova é um material criptográfico diferente, ainda que leve o mesmo nome»; «que a chave é só desse cliente e que alguém com autoridade autorizou destruí-la, porque não há volta».

---

## O que vem a seguir

Na sessão 4 usa-se também o cliente do MariaDB. Conferir com `mariadb --version`. Se não estiver instalado: `sudo apt install mariadb-client` no Debian ou no Ubuntu (em outras distribuições Linux, o gerenciador de pacotes que ela usar), ou `brew install mariadb` no macOS. E, para o script final, Python 3.10 ou mais recente: `python3 --version`.

---

*Escrevo a partir do que vemos todos os dias na Hábil, onde construímos sistemas para bancos, seguradoras e empresas no México. Se no trabalho ou no negócio da família de quem lê surgir um problema assim, vamos conversar: [habil.mx](https://www.habil.mx/pt/)*
