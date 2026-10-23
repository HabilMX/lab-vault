# Vault do zero (1): o problema dos segredos

*Numa sexta-feira, às 18:04, uma estagiária sobe um arquivo para o GitHub. Às 3:17 da madrugada, alguém entra no banco de dados. Por que isso acontece, por que é tão comum e o que uma empresa precisa para que não aconteça com ela.*

*Vault do zero · sessão 1 de 4*

Esta série tem quatro sessões, uma por semana. Aprende-se a guardar senhas, chaves e outros segredos no HashiCorp Vault, a cifrar dados sem ter a chave no programa e a fazer as senhas dos bancos de dados mudarem sozinhas. Tudo pelo terminal: `curl`, `psql`, `mariadb` e Docker Compose. O único programa é escrito no final, e tem menos de 30 linhas.

| Sessão | O que se vê | Prática |
|---|---|---|
| **1 — O problema dos segredos** | O que dá errado quando as senhas vivem em arquivos, o que é preciso para evitar isso e o que é o Vault | Exercícios 1 a 5, com `grep` e `git` |
| **2 — Subir o Vault e guardar segredos** | Vault com Docker Compose, o selo (seal) e as chaves dele, guardar e ler segredos com `curl`, permissões e log de auditoria | Exercícios 6 a 10 |
| **3 — Cifrar sem ter a chave** | O motor Transit: cifrar, decifrar e rotacionar chaves; guardar no PostgreSQL dados que ninguém mais consegue ler | Exercícios 11 a 15 |
| **4 — Senhas que mudam sozinhas** | Usuários de banco de dados que expiram, senhas que rotacionam sozinhas e um script em Python que não guarda nenhuma senha | Exercícios 16 a 20, autoavaliação e revisão da série |

Cada sessão dura umas 2 horas: mais ou menos uma para ler e acompanhar o exemplo, e outra para praticar. A partir da sessão 2, cada uma começa com **3 perguntas de revisão** da anterior, para responder sem consultar.

**O que é preciso saber antes:** usar o terminal (navegar entre pastas, criar arquivos, rodar comandos), `git` básico (`git add`, `git commit` e `git status`; saber que um arquivo «novo» é um que o git ainda não conhece) e Docker básico (o que é uma imagem e um contêiner, e `docker compose up`). **O que é preciso ter hoje:** um terminal e o `git` na versão 2.28 ou mais recente (confira com `git --version`). O Docker só entra a partir da sessão 2.

Ao longo da série, acompanha-se uma história. É um **cenário**: a empresa e as pessoas são inventadas. Os dados do mundo real que aparecem dentro da história são verdadeiros, e cada um traz a fonte indicada.

> **O laboratório do curso** está no repositório público [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). Nesta sessão ele ainda não é necessário: na sessão 2 o laboratório é montado arquivo por arquivo, e o repositório serve para comparar. Não traz nenhuma senha; o laboratório as gera ao iniciar.

## Objetivos desta sessão

Ao terminar, será possível fazer estas cinco coisas. Ao lado de cada uma está o exercício que a demonstra.

| # | Ao terminar, é possível… | Demonstrado no |
|---|---|---|
| 1 | **Encontrar** senhas e chaves escritas em um arquivo de configuração, com `grep` | Exercício 1 |
| 2 | **Nomear** as seis formas mais comuns pelas quais os segredos vazam, e **relacionar** cada uma com o que a evita | Exercício 2 |
| 3 | **Demonstrar** com `git` que apagar um arquivo não apaga a senha do histórico | Exercício 3 |
| 4 | **Proteger** um arquivo `.env` para que o `git` não o envie, e **comprovar** isso | Exercício 4 |
| 5 | **Explicar** o que o Vault faz, o que não faz e sob qual licença é usado | Exercício 5 |

---

## Cenário (ficção) — Capítulo 1: sexta-feira, 18:04

Guadalajara. Escritórios da **Canasta Morada**, uma mercearia on-line: quatorze pessoas, duas vans e um app em que se pedem tortillas, ovos e sabão e tudo chega em uma hora.

Valeria tem 21 anos e está há três meses como estagiária. Hoje terminou a primeira tela de verdade: a de «meus pedidos». Funciona. Levou duas semanas. Está orgulhosa.

São 18:04. Ela tem ingressos para um show às 20:00. Abre o terminal e digita o que já digitou cem vezes:

```
git add .
git commit -m "pantalla de mis pedidos"
git push
```

O ponto depois de `add` significa «tudo». Tudo o que há na pasta. Inclusive um arquivo chamado `.env`, onde o app guarda a configuração. E dentro desse arquivo, uma linha:

```
DB_PASSWORD=Tamal-Verde-2024
```

É a senha do banco de dados da Canasta Morada. O dos pedidos, dos clientes, dos endereços.

Mais um detalhe: Valeria não enviou o código para o repositório privado da empresa. Enviou para uma cópia que fez na conta pessoal dela no GitHub, para mostrar no portfólio. E a conta dela é **pública**.

Ela fecha o notebook. Vai ao show.

Ninguém percebe.

---

## Capítulo 2: sábado, 3:17 da madrugada

O celular de Iván vibra na mesa de cabeceira. Iván é o único desenvolvedor experiente da Canasta Morada; está lá há cinco anos. O alerta diz: **«Servidor de banco de dados: uso do processador em 98%»**.

Iván pensa num pedido grande. Num sábado às três da manhã ninguém pede mantimentos, mas vai saber. Volta a dormir.

Às 7:40 abre o notebook com o café na mão. O log do banco de dados diz isto:

```
03:17:02  conexión autorizada: usuario=app_tienda  origen=185.xx.xx.xx
03:17:05  SELECT * FROM clientes
03:21:40  SELECT * FROM pedidos
```

O usuário é `app_tienda`. É o usuário do app. A senha é a correta. Para o banco de dados, está tudo em ordem: alguém chegou com a chave certa e abriu a porta.

Mas esse endereço de origem não é de nenhum servidor da Canasta Morada.

---

## Capítulo 3: sábado, 9:00. A reunião

Dona Clara, a proprietária, chega de moletom. Estão lá Iván, Valeria — que quase não dormiu e ainda não sabe que foi ela — e um notebook sobre a mesa.

— Quem entrou? — pergunta dona Clara.

Iván não sabe responder. E as razões pelas quais não sabe são o tema desta sessão.

**Primeira pista.** `app_tienda` não é uma pessoa. É a senha que o app, o site, o programa que manda os pedidos para as vans e a macro de Excel com que a contabilidade tira o relatório do mês compartilham. Quatro programas. E mais: três pessoas a sabem. E o Toño.

— Quem é o Toño?

— O que estava antes de mim. Saiu há oito meses.

— E ele ainda a sabe?

— Nunca a trocamos.

**Segunda pista.** — Então troquem agora — diz dona Clara.

Iván explica: se trocar a senha agora, os quatro programas caem ao mesmo tempo. É preciso entrar em cada um, editar o arquivo, reiniciar. É sábado e há pedidos. E a macro de Excel, ninguém sabe onde a tem escrita.

**Terceira pista.** Valeria pergunta em voz baixa sobre os CURP. O app guarda o CURP dos clientes que pagam com vale-alimentação, e supõe-se que estejam cifrados.

— Estão cifrados, sim — diz Iván. — A chave fica no servidor, num arquivo chamado `llave.txt`.

— No mesmo servidor onde estão os backups?

Silêncio.

---

## Capítulo 4: sábado, 9:26

Iván abre a pasta dos backups. Toda noite, às 2:00, o servidor guarda uma cópia completa do banco de dados.

O backup da noite passada foi baixado às **3:21**.

E a pasta ao lado, a que tem o `llave.txt`, também.

Nesse backup estão os nomes, os endereços e os CURP de oito mil clientes.

*(Continua na sessão 2.)*

---

## Por que isso importa: não é exagero

A história da Canasta Morada é inventada. O que acontece com ela, não. Estes casos e números são reais e públicos:

- **Todo ano aparecem milhões de segredos no GitHub público.** A empresa GitGuardian examina as alterações enviadas ao GitHub público e conta as senhas e chaves que encontra. No relatório de 2026, contou **28,65 milhões de segredos novos** enviados durante 2025, 34% mais que no ano anterior. E o pior: das credenciais que encontrou válidas em 2022, **mais de 64% continuavam funcionando** quando foram testadas de novo em janeiro de 2026. Ou seja, segundo a GitGuardian, essas credenciais nunca foram corrigidas: a senha vazada continuava abrindo a porta anos depois. Fonte: [GitGuardian, *The State of Secrets Sprawl 2026*](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/).
- **Um repositório privado não salva ninguém.** Em 2016, invasores entraram na conta do GitHub de engenheiros da Uber usando senhas reutilizadas de outros vazamentos. Em um repositório **privado** encontraram uma chave de acesso à Amazon Web Services. Com ela baixaram dados de cerca de 25,6 milhões de nomes e e-mails e de cerca de 607.000 carteiras de motorista. Quem documentou foi a Comissão Federal de Comércio dos Estados Unidos (FTC): [análise do caso Uber, 2018](https://www.ftc.gov/system/files/documents/cases/1523054_uber_technologies_revised_analysis.pdf).
- **Um único link pode abrir tudo.** Em 2023, a empresa de segurança Wiz encontrou, em um repositório público de pesquisadores da Microsoft, um link com uma permissão de acesso a uma conta de armazenamento. A permissão não era de leitura: era de **controle total**, vencia em 2051 e permitia ver 38 terabytes, incluindo backups de computadores e mais de 30.000 mensagens internas do Teams. Fonte: [Wiz, 18 de setembro de 2023](https://www.wiz.io/blog/38-terabytes-of-private-data-accidentally-exposed-by-microsoft-ai-researchers).

A GitGuardian também informa que cerca de 28% dos incidentes que detecta não nascem no código, e sim em ferramentas como Slack, Jira ou Confluence. A senha colada no chat «só para copiar» também conta.

---

## As seis formas pelas quais um segredo vaza

Antes de ver soluções, convém dar nome a cada problema. Um **segredo** é qualquer dado que dá acesso a algo: uma senha, uma chave de cifragem, um token de uma API. Pense na chave de casa: ela não vale por si mesma, vale pela porta que abre.

### 1. A senha escrita no código ou num arquivo que é enviado

Foi o que a Valeria fez. O arquivo `.env` é um costume muito útil: separa a configuração do código. Mas, se o arquivo viaja junto com o código, a separação não serve de nada. É como colar a chave da casa com fita adesiva na porta, por dentro, e depois mandar fotos da porta.

E há uma armadilha extra: **no git, apagar não é apagar.** O git guarda o histórico de cada alteração. Se a senha foi enviada e na alteração seguinte é removida, continua na anterior. Isso se comprova no exercício 3.

### 2. O `.env` que circula pelo WhatsApp

— Ei, me passa o `.env`? — Toma. E ali fica: no chat, no backup do celular e no computador de quem abriu o WhatsApp Web num café. Cada cópia é mais uma porta que ninguém vigia.

### 3. A mesma senha para todos e para sempre

Na Canasta Morada, quatro programas e quatro pessoas usam `app_tienda`. É como o cadeado do depósito de uma escola cuja combinação todos os professores sabem desde 2019. Se um dia sumir alguma coisa, não há como saber quem abriu.

E, como trocar a senha quebra tudo ao mesmo tempo, ninguém troca. «Para sempre» não é uma decisão: é o que acontece quando mudar dói.

### 4. Ninguém sabe quem a usou

O banco de dados registrou «entrou `app_tienda`». Não registrou «entrou o app», nem «entrou o Toño», nem «entrou alguém de outro país com a senha roubada». Quando todos usam a mesma identidade, o log serve de pouco.

### 5. Quem saiu ainda a sabe

O Toño saiu há oito meses, em bons termos. Mas levou de cabeça a senha do banco de dados, a do servidor de e-mail e a da conta de pagamentos. Não fez nada de errado. Mas também ninguém pode garantir isso. E, se o notebook velho dele foi vendido no Marketplace com um arquivo de configuração dentro, já não depende nem dele.

### 6. A chave de cifragem junto dos dados

Cifrar, em resumo, é misturar um dado com uma chave para que só quem tenha a chave consiga lê-lo. A Canasta Morada cifrava os CURP, sim. Mas guardou a chave em `llave.txt`, no mesmo servidor dos backups. É como ter um cofre e deixar a combinação num post-it colado em cima. O ladrão levou as duas coisas na mesma viagem.

---

## O que é preciso

Quem estivesse no lugar do Iván e tivesse de projetar como a Canasta Morada deveria funcionar na segunda-feira, o que pediria? Esta é a lista que quase qualquer equipe de segurança faz. Cada ponto ataca um ou vários dos seis problemas.

| # | Requisito | Ataca o problema | Nas palavras de dona Clara |
|---|---|---|---|
| R1 | **Guardar os segredos em um só lugar, cifrados**, e não espalhados em arquivos | 1, 2 | «Que as chaves vivam num cofre, não nas gavetas» |
| R2 | **Dar acesso por identidade e por permissão**: cada programa e cada pessoa tem a própria credencial e só pode ler o que lhe cabe | 3, 4 | «Que cada um tenha a própria chave, e que a da cozinha não abra o cofre» |
| R3 | **Log de auditoria**: quem pediu qual segredo, quando e se lhe foi entregue | 4 | «Que fique anotado quem abriu» |
| R4 | **Credenciais que expiram sozinhas** | 3, 5 | «Que as chaves derretam depois de um tempo» |
| R5 | **Rotação automática**: trocar senhas sem que ninguém precise editar arquivos | 3, 5 | «Que trocar a fechadura não obrigue a fechar a loja» |
| R6 | **Revogar de uma vez**: se algo vazar, cancelar todas as credenciais afetadas com um único comando | 5 | «Um botão de pânico» |
| R7 | **Cifragem como serviço**: os programas pedem «cifre isto» e recebem o dado cifrado, mas nunca têm a chave | 6 | «Que a chave do cofre nunca saia do banco» |

Repare numa coisa: nenhum desses requisitos diz «que as pessoas tenham mais cuidado». A Valeria não é descuidada; é uma pessoa cansada numa sexta-feira às seis da tarde. Um bom projeto não depende de que ninguém erre nunca. Depende de que, quando alguém errar, o dano seja pequeno.

---

## O que é o Vault

O **HashiCorp Vault** é um programa que faz exatamente essa lista. Roda como um servidor; os programas e as pessoas falam com ele por HTTP (com `curl`, por exemplo) ou pelo comando `vault`.

Pense no Vault como o **cofre de um banco com guichê**:

- Ninguém entra no cofre. Fica-se na fila do guichê e faz-se o pedido.
- A atendente confere a identificação (o **token**) e o que é permitido (a **política**, ou *policy*).
- Se for o caso, entrega o que foi pedido. Se não, diz que não: um **403**.
- Se o banco estiver com o log ligado — no Vault, é preciso ligá-lo —, tudo fica anotado.
- E algumas coisas nem chegam a ser entregues: entrega-se o documento, a atendente o sela no cofre e o devolve selado. O selo nunca sai do banco. Isso é a cifragem como serviço.

| Requisito | Como o Vault o cobre | Onde se pratica |
|---|---|---|
| R1 Guardar de forma centralizada e cifrada | Motor **KV** (de *key-value*, chave-valor): guarda segredos cifrados; com o **KV v2**, também conserva versões | Sessão 2 |
| R2 Acesso por identidade e política | **Tokens** e **políticas**: cada token só faz o que a política dele permite; todo o resto é negado | Sessão 2 |
| R3 Auditoria | **Dispositivos de auditoria** (*audit devices*): depois de ativados, quase toda requisição e toda resposta ficam num log, com os valores sensíveis protegidos | Sessão 2 |
| R4 Credenciais que expiram | **Concessões** (*leases*) com tempo de vida (**TTL**); motor **Database** com usuários dinâmicos | Sessão 4 |
| R5 Rotação automática | Papéis estáticos do motor Database com `rotation_period` (rotacionam sozinhos de tempos em tempos); e `rotate-root` para trocar de imediato a senha administrativa com que o Vault se conecta ao banco | Sessão 4 |
| R6 Revogar de uma vez | Revogação de uma concessão ou de todas as que começam com um prefixo | Sessão 4 |
| R7 Cifragem como serviço | Motor **Transit**: cifra e decifra, rotaciona chaves e não guarda os dados | Sessão 3 |

Um **motor** (*secrets engine*) é uma parte do Vault especializada em um tipo de segredo, como os guichês do banco: um para depósitos, outro para cheques. Ativam-se os que forem necessários.

---

## O que o Vault não é (e uma nota sobre licença)

**O Vault não é um HSM.** Um **HSM** (*hardware security module*) é um aparelho físico que guarda chaves e faz operações de cifragem por dentro, com proteções contra violação. Conforme o modelo e a configuração, as chaves podem ser impossíveis de extrair e o aparelho pode apagar o conteúdo se alguém tentar abri-lo à força. Os bancos os usam, por exemplo, para os PIN dos cartões.

O motor Transit do Vault se parece com isso na forma de trabalhar: enviam-se dados e recebem-se dados cifrados, e a chave fica no Vault. A documentação oficial o descreve como «cifragem como serviço» e esclarece que o Vault não guarda os dados que recebe ([Transit, documentação do Vault](https://developer.hashicorp.com/vault/docs/secrets/transit)). Mas o Vault é software rodando num servidor, não hardware. E o Transit permite, se for configurado assim, criar chaves exportáveis ou importar chaves próprias; por padrão, não deixa exportá-las (isso será comprovado na sessão 3).

O que existe: o **Vault Enterprise**, a versão paga, pode usar um HSM de verdade para proteger a própria chave-mestra e para abrir-se sozinho ao iniciar, com equipamentos compatíveis com o padrão PKCS#11 ([Vault HSM support](https://developer.hashicorp.com/vault/docs/enterprise/hsm)). Nesta série usamos a versão comunitária, que não tem esse recurso.

**Sobre a licença.** Durante anos o Vault foi software livre, com licença MPL 2.0. Em 10 de agosto de 2023, a HashiCorp anunciou que as versões novas passariam para a **Business Source License (BSL) 1.1** ([anúncio da HashiCorp](https://www.hashicorp.com/blog/hashicorp-adopts-business-source-license)). Em resumo: o Vault pode ser usado de graça numa empresa, mas há limites para quem quer oferecer um produto que concorra com a HashiCorp. Em fevereiro de 2025, a IBM concluiu a compra da HashiCorp ([comunicado da IBM](https://newsroom.ibm.com/2025-02-27-ibm-completes-acquisition-of-hashicorp,-creates-comprehensive,-end-to-end-hybrid-cloud-platform)).

Como resposta à mudança de licença, uma parte da comunidade pegou o último código aberto e seguiu por conta própria: o **OpenBao**, que hoje é um projeto da OpenSSF, dentro da Linux Foundation, com licença MPL 2.0 ([openbao.org](https://openbao.org/)). Isso se chama *fork*, uma bifurcação: como uma receita de família que se divide e cada ramo da família continua a fazer do próprio jeito. Quase tudo o que se aprende nesta série serve também no OpenBao; o quadro abaixo diz o que muda.

> **Vault e OpenBao: o mesmo cofre, dois donos**
>
> O OpenBao nasceu do último Vault com licença livre, o 1.14: a BSL cobre «Vault Version 1.15.0 or later» ([licença do Vault](https://github.com/hashicorp/vault/blob/main/LICENSE)). A partir daí, cada um segue o próprio caminho:
>
> | | HashiCorp Vault | OpenBao |
> |---|---|---|
> | Licença | BSL 1.1: permite o uso interno e em produção; restringe oferecê-lo como produto que concorra com a oferta paga da IBM | MPL 2.0, livre ([licença do OpenBao](https://github.com/openbao/openbao/blob/main/LICENSE)) |
> | Quem cuida | IBM, dona da HashiCorp | A comunidade, como projeto da OpenSSF, dentro da Linux Foundation ([openbao.org](https://openbao.org/)) |
> | Comando | `vault` | `bao` |
> | Variáveis | `VAULT_ADDR`, `VAULT_TOKEN` | `BAO_ADDR`, `BAO_TOKEN`; se não existirem, lê as `VAULT_` ([comandos](https://openbao.org/docs/commands/)) |
> | Imagem | `hashicorp/vault` | `openbao/openbao`, no Docker Hub, no Quay e no registro de contêineres do GitHub ([instalação](https://openbao.org/docs/install/)); em 20 de outubro de 2026, a mais recente é a 2.7.1, de 1º de outubro ([versões](https://github.com/openbao/openbao/releases)) |
> | Espaços separados por empresa (*namespaces*) | Só na versão paga ([Vault](https://developer.hashicorp.com/vault/docs/enterprise/namespaces)) | Incluídos desde a 2.3, de 2025 ([OpenBao](https://openbao.org/docs/concepts/namespaces/)) |
>
> Na Hábil escolhemos o OpenBao, a versão livre, para cifrar os documentos dos nossos sistemas: uma API compatível, licença aberta e nenhuma dependência de um único fornecedor.
>
> Esta série usa a imagem oficial do HashiCorp Vault 2.2.0, com a qual cada comando foi testado. No OpenBao, as chamadas com `curl` não mudam: as rotas começam com `/v1/` e o token viaja no mesmo cabeçalho `X-Vault-Token` ([API do OpenBao](https://openbao.org/docs/api/)). Nos comandos, troca-se `vault` por `bao`. Mas trocar nomes não basta, por três detalhes:
>
> - O laboratório guarda os dados com `storage "file"`, e o OpenBao 2.7 removeu essa opção ([notas da 2.7.0](https://github.com/openbao/openbao/blob/main/CHANGELOG.md)); lá se usa outra, como o armazenamento integrado `raft` ([armazenamento](https://openbao.org/docs/configuration/storage/)).
> - Dentro do contêiner, as pastas são `/openbao/config`, `/openbao/file` e `/openbao/logs`, e não `/vault/...` ([Dockerfile do OpenBao](https://github.com/openbao/openbao/blob/main/Dockerfile)).
> - Hoje os tokens começam com `s.`, `b.` ou `r.`, e não com `hvs.`; o OpenBao avisa que esse formato pode mudar, então não se deve construir nada que dependa do prefixo ([tokens](https://openbao.org/docs/concepts/tokens/)): a busca por `hvs.` que aparece mais adiante não os encontraria.
>
> O laboratório não foi executado com o OpenBao.

---

👉 **Para quem é de Administração:** os seis problemas desta sessão são problemas de controle interno, não de programação. «A mesma senha para todos» é o mesmo que «todos assinam com o mesmo carimbo»: se sair um cheque estranho, não há a quem perguntar. «Quem saiu ainda a sabe» é um desligamento de pessoal que não terminou: tirou-se o crachá do prédio, mas não a chave do caixa pequeno. Quando forem auditar os sistemas de uma empresa, as perguntas da tabela de requisitos (quem tem acesso? fica registrado? expira? dá para cancelar de uma vez?) são as mesmas que se fariam sobre as assinaturas de uma conta bancária.

---

## Exercícios da sessão 1

As soluções estão no final desta edição. Cada exercício diz como conferir sozinho se deu certo.

**Exercício 1 — Caça aos segredos com `grep`.** Criar um arquivo `config-tienda.yaml` com este conteúdo (todos os valores são inventados):

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

Primeiro, a olho: quantos segredos aparecem? Anotar no papel. Depois, rodar esta busca. O `grep` procura texto em arquivos; `-n` mostra o número da linha, `-i` ignora maiúsculas e `-E` permite usar `|` para dizer «isto ou aquilo»:

```
grep -niE 'pass|key|llave|secret|token|://[^/ ]+:[^@ ]+@' config-tienda.yaml
```

O último pedaço, `://[^/ ]+:[^@ ]+@`, procura endereços que levam usuário e senha dentro, como `smtp://usuario:contraseña@servidor`.

a) Quantas linhas o `grep` encontrou? Bate com a contagem a olho?
b) Há um segredo que o `grep` não encontrou. Qual? Modificar o padrão para que ele também o encontre.

**Como conferir:** com o padrão original, `grep -c` (que conta linhas em vez de mostrá-las) deve dar `4`. Com o padrão corrigido, deve dar `5`.

**Exercício 2 — Relacione.** Para cada situação, escrever qual dos seis problemas é e qual requisito (R1 a R7) o evita. Pode haver mais de um requisito.

a) Um estagiário termina o estágio. Três meses depois, o usuário dele no banco de dados continua funcionando.
b) A chave para decifrar os cartões dos clientes está numa variável do mesmo programa que os guarda.
c) Alguém apagou uma tabela. O log diz que foi o `admin`, e o usuário `admin` é usado por cinco pessoas.
d) Para «fazer rápido», o líder cola a senha do servidor no canal geral do Slack.

**Como conferir:** comparar com as soluções. Se em alguma foi indicado outro requisito, verificar se ele realmente evita o problema ou só o torna menos grave.

**Exercício 3 — No git, apagar não é apagar.** Numa pasta nova e vazia, rodar isto linha por linha. As duas linhas de `git config` dizem ao git quem está usando; sem elas, num computador recém-comprado, o `git commit` se recusa a funcionar. Valem só para esta pasta:

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

O arquivo não está mais na pasta. Agora, procurar a senha no histórico. O `-S` procura as alterações em que um texto apareceu ou desapareceu, e o `-p` mostra a alteração completa:

```
git log -p -S Tamal-Verde-2024 --oneline
```

**Como conferir:** a saída traz o patch completo de cada alteração; entre as linhas, devem aparecer as duas alterações, a que adicionou a linha (`+DB_PASSWORD=...`) e a que a removeu (`-DB_PASSWORD=...`). Se alguém clonar o repositório, fica com as duas. Escrever numa frase o que seria preciso fazer com essa senha, além de apagá-la.

**Exercício 4 — Que o git nem a veja.** Na mesma pasta do exercício 3, criar de novo um `.env` com outra senha e ver o que o git diz:

```
echo "DB_PASSWORD=Pozole-Rojo-2025" > .env
git status --short
```

Agora, fazer o git ignorá-lo. Criar um arquivo `.gitignore` com uma única linha, `.env`, e rodar de novo `git status --short`.

**Como conferir:** antes de criar o `.gitignore`, o git mostra `?? .env` (arquivo novo que poderia ser enviado). Depois, o `.env` não aparece mais; só `?? .gitignore`. Para ter certeza de qual regra o está ignorando, rodar `git check-ignore -v .env`; deve responder com o nome do arquivo e a linha da regra.

**Exercício 5 — Explique para dona Clara.** Escrever um parágrafo de no máximo 90 palavras, sem termos técnicos sem explicação, que responda: o que é o Vault? Qual problema da Canasta Morada ele resolveria primeiro? É a mesma coisa que um HSM? É software livre?

**Como conferir:** primeiro, autoavaliar-se: o parágrafo deve dizer (1) que o Vault guarda os segredos em um só lugar e controla quem os pede; (2) qual problema da Canasta Morada seria atacado primeiro; (3) que não é um HSM; e (4) que as versões atuais do Vault usam a licença BSL 1.1, que pode ser usada sem custo, mas não é software livre, e que o OpenBao usa a MPL 2.0. Depois, passar o texto a alguém que não estude sistemas: se a pessoa conseguir responder às quatro perguntas com as próprias palavras, está bom.

---

## Erros comuns (e como perceber)

| Erro | Como aparece | Como perceber | O que fazer |
|---|---|---|---|
| Achar que apagar o arquivo resolve o vazamento | «Já tirei do repo, pronto» | `git log -p -S <texto>` ainda o encontra | Considerar a senha queimada: **trocá-la**. Limpar o histórico ajuda, mas as cópias que já foram baixadas não se apagam |
| Adicionar o `.env` ao `.gitignore` depois de tê-lo enviado | O `git status` já não o mostra, mas ele continua no repositório | O `git ls-files` ainda o lista | O `.gitignore` só afeta arquivos novos. Tirá-lo do índice com `git rm --cached .env` e trocar a senha |
| Confiar que o `grep` encontrou tudo | A contagem fecha… para os nomes que vieram à cabeça | O exercício 1: o `clave_sms` escapa | Usar o `grep` para uma checagem rápida, não como garantia. Existem ferramentas feitas para isso, que procuram centenas de formatos |
| Achar que um repo privado é seguro | «Ninguém vê, é privado» | O caso Uber: o repo era privado | Privado reduz o risco, não o elimina. Segredos não vão no código, ponto |
| Compartilhar o `.env` por chat «só desta vez» | O arquivo aparece em três celulares e na nuvem | Procurar no chat a palavra `PASSWORD` | Cada cópia é mais uma porta. A partir da sessão 2, cada um pede o que lhe cabe ao Vault |

---

## Revisão para a próxima sessão

A sessão 2 começa com estas três perguntas. Responder sem olhar a lição:

1. Nomear quatro das seis formas pelas quais um segredo vaza.
2. Por que trocar a senha depois de um vazamento é obrigatório, mesmo que ela já tenha sido apagada do git?
3. Em que o motor Transit do Vault se parece com um HSM e em que se diferencia?

🔁 **Na próxima semana:** Iván decide construir o cofre. Sobe-se o Vault com Docker Compose, abre-se com três das cinco chaves, guardam-se os primeiros segredos com `curl` e vê-se como o Vault diz não a quem pede o que não lhe cabe. E no log de auditoria aparece algo que ninguém esperava.

---

## Soluções (não olhe antes de tentar)

**Exercício 1.** Com o padrão original, a saída é:

```
8:  password: Tamal-Verde-2024
11:  api_key: pk_prueba_51HcXyZ-esto-es-inventado
14:  conexion: smtp://avisos:Churro99@smtp.ejemplo.local:587
16:  llave_aes: MDEyMzQ1Njc4OUFCQ0RFRg==
```

a) Quatro linhas. Se a olho foram contadas cinco, estava certo: há cinco segredos.

b) Escapa o `clave_sms: Elote-2023`, porque «clave» não estava no padrão. Acrescentá-lo:

```
grep -niE 'pass|key|llave|clave|secret|token|://[^/ ]+:[^@ ]+@' config-tienda.yaml
```

Agora aparece também a linha `19:  clave_sms: Elote-2023`. A lição não é «adicione mais palavras»; é que uma busca de texto só encontra o que se lembrou de procurar.

**Exercício 2.**

a) Problema 5 (quem saiu ainda a sabe). Evitam-no o R4 (credenciais que expiram) e o R6 (revogar de uma vez). O R2 ajuda porque, com credenciais por pessoa, sabe-se qual cancelar.

b) Problema 6 (a chave junto dos dados). Evita-o o R7 (cifragem como serviço): o programa pede para cifrar e decifrar, mas nunca tem a chave.

c) Problemas 3 e 4 (a mesma para todos; ninguém sabe quem). Evitam-nos o R2 (identidade própria para cada um) e o R3 (log).

d) Problema 2 (o segredo que circula por chat). Evitam-no o R1 (um só lugar) e o R2 (cada um pede o que lhe cabe). E, como já vazou, entra o R5: trocá-la.

**Exercício 3.** A saída completa inclui, para cada alteração, os cabeçalhos do patch (`diff --git ...`, `index ...`). As linhas que importam são estas:

```
cbe77a9 quito el .env
-DB_PASSWORD=Tamal-Verde-2024
250264c primera version
+DB_PASSWORD=Tamal-Verde-2024
```

Os identificadores de alteração (os sete caracteres do começo) serão outros; isso é normal. A frase que se buscava: **é preciso trocar a senha no banco de dados**, porque qualquer pessoa que tenha clonado o repositório a tem.

**Exercício 4.** Antes do `.gitignore`:

```
?? .env
```

Depois:

```
?? .gitignore
```

E o `git check-ignore -v .env` responde:

```
.gitignore:1:.env	.env
```

Quer dizer: «ignoro pela linha 1 do arquivo `.gitignore`, que diz `.env`». Na sessão 2 aparece um script de inicialização que se recusa a criar senhas se essa regra não existir.

**Exercício 5.** Uma resposta possível: «O Vault é um cofre com guichê para as senhas e chaves dos sistemas. Cada programa e cada pessoa tem a própria identificação e só recebe o que lhe cabe, e tudo fica anotado. O que eu resolveria primeiro na Canasta Morada é o fato de quatro programas e quatro pessoas compartilharem a mesma senha. Não é um HSM: um HSM é um aparelho físico; o Vault é um programa, embora possa cifrar sem entregar a chave. Pode ser usado de graça, com uma licença que impõe limites a quem quiser competir com o fabricante; existe uma versão irmã com licença livre, chamada OpenBao.»

---

## O que vem a seguir

Na sessão 2 usa-se o Docker Compose. Antes de chegar lá, conferir se as ferramentas estão instaladas com `docker compose version`, `curl --version`, `jq --version` e `openssl version`. Se faltar o `jq`, que serve para ler as respostas em formato JSON, instalá-lo assim: no Debian ou no Ubuntu, `sudo apt-get install jq`; no Fedora, `sudo dnf install jq`; no Arch, `sudo pacman -S jq`; no macOS com o Homebrew instalado, `brew install jq`. É necessário o `jq` 1.6 ou mais recente.

---

*Escrevo a partir do que vemos todos os dias na Hábil, onde construímos sistemas para bancos, seguradoras e empresas no México. Se no trabalho ou no negócio da família de quem lê surgir um problema assim, vamos conversar: [habil.mx](https://www.habil.mx/pt/)*
