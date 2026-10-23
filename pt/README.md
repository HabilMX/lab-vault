# Vault do zero

**Por Dorian Chávez, fundador da Hábil e arquiteto de integração.**

Senhas que não vivem no código, chaves que ninguém tem e credenciais que expiram sozinhas.

**Para quem é:** estudantes de Sistemas e pessoas que já programam ou administram servidores e querem parar de guardar
senhas em arquivos; e pessoas de Administração que querem entender o que perguntar quando se audita quem tem acesso
a quê. É um curso de nível intermediário: não explica o que é um terminal nem um contêiner, mas cada palavra nova é
explicada quando aparece. Cada sessão traz um quadro «Para quem é de Administração» com a mesma ideia levada ao controle
interno de uma empresa.

**O que se vai saber ao terminar:**

- Encontrar senhas escritas em arquivos e demonstrar com `git` que apagá-las não as tira do histórico.
- Subir o Vault em modo servidor, abri-lo com 3 de 5 chaves e guardar segredos com permissões e log de auditoria.
- Cifrar e decifrar dados com o motor Transit sem que a chave chegue ao programa, e rotacionar essa chave sem perder nada.
- Pedir usuários do PostgreSQL e do MariaDB que nascem no momento do pedido e expiram sozinhos, e conectar um programa em Python
  sem escrever nenhuma senha.

**O que é preciso antes de começar:** usar o terminal, `git` básico (`add`, `commit`, `status`) e Docker básico (o que
é uma imagem e um contêiner). Para a sessão 1 bastam um terminal e o `git` 2.28 ou mais recente. A partir da sessão 2: Docker
com Compose, `curl`, `jq` 1.6 ou mais recente e `openssl`. Testado no Linux Mint 22.3 com a imagem oficial
`hashicorp/vault:2.2.0`, e no macOS; no Windows não foi testado.

## As quatro sessões

Quatro sessões de umas 2 horas cada: mais ou menos uma para ler e acompanhar o exemplo, e outra para praticar. Todas
seguem a mesma história: uma loja, uma senha que foi parar no GitHub numa sexta-feira às 18:04 e alguém que
entrou no banco de dados às 3:17 da madrugada.

| Sessão | | O que se aprende |
|---|---|---|
| 1 | [O problema dos segredos](01-el-problema-de-los-secretos.md) | as seis formas pelas quais um segredo vaza; procurá-las com `grep` e `git`; o que o Vault é e o que não é |
| 2 | [Subir o Vault e guardar segredos](02-levantar-vault-y-guardar-secretos.md) | Docker Compose, o selo e as chaves de Shamir, segredos com `curl`, políticas e log de auditoria |
| 3 | [Cifrar sem ter a chave](03-cifrar-sin-tener-la-llave.md) | o motor Transit: cifrar, decifrar, rotacionar, vincular a cifragem ao dono dos dados e apagar destruindo a chave |
| 4 | [Senhas que mudam sozinhas](04-contrasenas-que-se-cambian-solas.md) | credenciais dinâmicas no PostgreSQL e no MariaDB, rotação automática, o botão de pânico e Python sem senhas |

## O laboratório

Tudo o que se usa a partir da sessão 2 está na raiz deste repositório: `compose.yaml`, o script `iniciar.sh`, as
políticas, os papéis (roles) e o programa em Python. Não traz nenhuma senha: o laboratório as gera ao iniciar. Como
iniciá-lo está no [README principal](../README.md).

## Onde é publicado

Uma sessão por semana no «En construcción», o Substack da Hábil, aos sábados às 8:00, de 7 a 28 de novembro de
2026: https://enconstruccionmx.substack.com
