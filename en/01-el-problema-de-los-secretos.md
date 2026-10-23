# Vault from Scratch (1): The Problem of Secrets

*On a Friday at 6:04 p.m., an intern pushes a file to GitHub. At 3:17 a.m., someone accesses the database. Why it happens, why it is so common, and what a company needs to prevent it.*

*Vault from Scratch · Session 1 of 4*

This series has four sessions, one per week. You learn how to store passwords, keys, and other secrets in HashiCorp Vault, encrypt data without holding the key in your program, and make database passwords rotate automatically. Everything from the terminal: `curl`, `psql`, `mariadb`, and Docker Compose. You write the only program at the very end, and it is under 30 lines.

| Session | What you cover | Hands-on |
|---|---|---|
| **1 — The Problem of Secrets** | What goes wrong when passwords live in files, what is needed to prevent it, and what Vault is | Exercises 1 to 5, with `grep` and `git` |
| **2 — Spinning Up Vault and Storing Secrets** | Vault with Docker Compose, the seal and its unseal keys, storing and reading secrets with `curl`, permissions, and audit logs | Exercises 6 to 10 |
| **3 — Encrypting Without the Key** | The Transit engine: encrypting, decrypting, and rotating keys; storing data in PostgreSQL that no one else can read | Exercises 11 to 15 |
| **4 — Passwords That Change Themselves** | Database users that expire, passwords that rotate automatically, and a Python script that stores zero passwords | Exercises 16 to 20, self-assessment, and series review |

Each session takes about 2 hours: roughly one to read and follow the example, and another to practice. Starting in Session 2, each one begins with **3 review questions** from the previous session, to answer without looking.

**What you need to know beforehand:** using the terminal (navigating directories, creating files, running commands), basic `git` (`git add`, `git commit`, and `git status`; knowing that an "untracked" file is one git does not yet track), and basic Docker (what an image and a container are, and `docker compose up`). **What you need to have today:** a terminal and `git` version 2.28 or newer (check it with `git --version`). You use Docker starting in Session 2.

Throughout the series, you will follow a story. It is a **scenario**: the company and the characters are fictional. The real-world data points that appear within the story are real, and each includes its source.

> **The course lab** is in the public repository [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). You do not need it yet in this session: in Session 2 you build it yourself, file by file, and the repository serves as a reference to compare against. It contains no passwords; the lab generates them upon startup.

## Objectives for this session

By the end, you will be able to do these five things. Next to each is the exercise that demonstrates it.

| # | By the end you will be able to… | Demonstrated by |
|---|---|---|
| 1 | **Find** passwords and keys written in a configuration file using `grep` | Exercise 1 |
| 2 | **Name** the six most common ways secrets leak, and **match** each with what prevents it | Exercise 2 |
| 3 | **Demonstrate** with `git` that deleting a file does not remove the password from history | Exercise 3 |
| 4 | **Protect** a `.env` file so `git` does not push it, and **verify** it | Exercise 4 |
| 5 | **Explain** what Vault does, what it does not do, and under what license it is used | Exercise 5 |

---

## Scenario (fiction) — Chapter 1: Friday, 6:04 p.m.

Guadalajara. The offices of **Canasta Morada**, an online grocery store: fourteen people, two vans, and an app where you order tortillas, eggs, and soap and they arrive within an hour.

Valeria is 21 years old and has been an intern for three months. Today she finished her first real screen: "My Orders." It works. It took her two weeks. She is proud of it.

It's 6:04. She has tickets to a concert at 8:00. She opens the terminal and types what she has typed a hundred times:

```
git add .
git commit -m "pantalla de mis pedidos"
git push
```

The dot after `add` means "everything." Everything in the directory. Including a file named `.env`, where the app stores its configuration. And inside that file, a single line:

```
DB_PASSWORD=Tamal-Verde-2024
```

That is the database password for Canasta Morada. The database with the orders, the customers, the addresses.

One more detail: Valeria didn't push the code to the company's private repository. She pushed it to a copy she made on her personal GitHub account, to show it in her portfolio. And her account is **public**.

She shuts her laptop. Heads to the concert.

Nobody notices.

---

## Chapter 2: Saturday, 3:17 a.m.

Iván's phone buzzes on the nightstand. Iván is the only experienced developer at Canasta Morada; he has been there for five years. The alert reads: **"Database server: CPU usage at 98%"**.

Iván assumes it's a large order. Nobody orders groceries at three in the morning on a Saturday, but who knows. He goes back to sleep.

At 7:40, he opens his laptop, coffee in hand. The database log shows this:

```
03:17:02  conexión autorizada: usuario=app_tienda  origen=185.xx.xx.xx
03:17:05  SELECT * FROM clientes
03:21:40  SELECT * FROM pedidos
```

The user is `app_tienda`. It's the app's user. The password is correct. As far as the database is concerned, everything is in order: someone showed up with the right key and opened the door.

Except that source IP address does not belong to any server at Canasta Morada.

---

## Chapter 3: Saturday, 9:00 a.m. The meeting

Doña Clara, the owner, shows up in sweatpants. Present are Iván, Valeria—who barely slept and still doesn't know it was her—and a laptop sitting on the table.

“Who got in?” asks Doña Clara.

Iván doesn't know how to answer. And the reasons why he doesn't know are the subject of this session.

**First clue.** `app_tienda` is not a person. It is the password shared by the app, the website, the service that dispatches orders to the delivery vans, and the Excel macro accounting uses to pull the monthly report. Four programs. On top of that, three people know it. And Toño.

“Who is Toño?”

“The guy who was here before me. He left eight months ago.”

“And he still knows it?”

“We never changed it.”

**Second clue.** “Well, change it right now,” says Doña Clara.

Iván explains: if he changes the password right now, all four programs go down at once. Someone has to log into each one, edit its configuration file, and restart it. It's Saturday and orders are coming in. And as for the Excel macro, nobody even knows where the password is hardcoded.

**Third clue.** Valeria, in a low voice, asks about the CURP records. The app stores the CURP of customers who pay with grocery vouchers, and they are supposed to be encrypted.

“They are encrypted,” says Iván. “The key is on the server, in a file called `llave.txt`.”

“On the same server where the backups are?”

Silence.

---

## Chapter 4: Saturday, 9:26 a.m.

Iván opens the backup directory. Every night at 2:00, the server saves a full dump of the database.

Last night's backup was downloaded at **3:21 a.m.**

And the adjacent folder, the one containing `llave.txt`, was too.

Inside that backup are the names, addresses, and CURP numbers of eight thousand customers.

*(To be continued in Session 2.)*

---

## Why it matters: this is not an exaggeration

The story of Canasta Morada is fictional. What happened to them is not. These cases and figures are real and public:

- **Millions of secrets appear on public GitHub every year.** The company GitGuardian scans commits pushed to public GitHub and tallies the passwords and keys it finds. In its 2026 report, it counted **28.65 million new secrets** pushed during 2025, a 34% increase over the previous year. And worse: of the credentials found to be valid in 2022, **more than 64% were still working** when retested in January 2026. In other words, according to GitGuardian, those credentials were never remediated: the leaked password was still unlocking the door years later. Source: [GitGuardian, *The State of Secrets Sprawl 2026*](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/).
- **A private repository will not save you.** In 2016, attackers gained access to the GitHub account of Uber engineers using credentials reused from other breaches. Inside a **private** repository, they found an access key for Amazon Web Services. With it, they downloaded data belonging to approximately 25.6 million names and email addresses and roughly 607,000 driver's license numbers. Documented by the U.S. Federal Trade Commission (FTC): [Uber case analysis, 2018](https://www.ftc.gov/system/files/documents/cases/1523054_uber_technologies_revised_analysis.pdf).
- **A single link can expose everything.** In 2023, security firm Wiz discovered a link in a public repository belonging to Microsoft researchers granting access permissions to a storage account. The permission was not read-only: it was **full control**, was set to expire in 2051, and exposed 38 terabytes of data, including workstation backups and more than 30,000 internal Teams messages. Source: [Wiz, September 18, 2023](https://www.wiz.io/blog/38-terabytes-of-private-data-accidentally-exposed-by-microsoft-ai-researchers).

GitGuardian also reports that roughly 28% of the incidents it detects do not originate in source code, but in tools like Slack, Jira, or Confluence. The password pasted into chat "just so you have it" counts too.

---

## The six ways a secret leaks

Before looking at solutions, give each problem a name. A **secret** is any piece of data that grants access to something: a password, an encryption key, an API token. Think of your house key: it isn't valuable in itself; it is valuable because of the door it unlocks.

### 1. Hardcoding the password or committing a configuration file

This is what Valeria did. The `.env` file is a very useful convention: it separates configuration from code. But if the file travels with the code, that separation is useless. It's like taping your house key to the inside of the door and then sending photos of the door.

And there is an added trap: **in git, deleting is not erasing.** Git retains the history of every commit. If you committed the password and removed it in the next commit, it remains in the previous one. You will prove this in Exercise 3.

### 2. Passing the `.env` file over WhatsApp

“Hey, can you send me the `.env`?” “Sure.” And there it stays: in the chat history, in the phone's backup, and on the laptop of someone who opened WhatsApp Web at a coffee shop. Every copy is another unmonitored door.

### 3. One shared password for everyone, forever

At Canasta Morada, four services and four people share `app_tienda`. It's like a school supply closet padlock whose combination every teacher has known since 2019. If something goes missing one day, there's no way to know who opened it.

And because changing it breaks everything at once, nobody changes it. "Forever" isn't a deliberate decision: it's what happens when changing things is painful.

### 4. Nobody knows who used it

The database logged "user `app_tienda` connected." It didn't log "the app connected," or "Toño connected," or "someone from another country connected using stolen credentials." When everyone shares the same identity, audit logs are practically useless.

### 5. Former employees still have access

Toño left eight months ago on good terms. But he walked away with the database password, the mail server credentials, and the payment gateway account memorized in his head. He didn't do anything malicious. But nobody can guarantee that either. And if he sold his old laptop on Marketplace with a leftover configuration file on it, it's out of his hands entirely.

### 6. Storing the encryption key next to the encrypted data

Encryption, in simple terms, scrambles data using a key so that only whoever holds the key can read it. Canasta Morada did encrypt its CURP data. But it stored the key in `llave.txt`, on the very same server as the backups. It's like having a safe and leaving the combination on a sticky note stuck on top of it. The intruder walked away with both in a single trip.

---

## What is required

If you were Iván and had to design how Canasta Morada should operate starting Monday, what would you ask for? This is the checklist virtually every security team drafts. Each item tackles one or more of the six problems.

| # | Requirement | Addresses problem | In Doña Clara's words |
|---|---|---|---|
| R1 | **Store secrets in a single place, encrypted**, not scattered across files | 1, 2 | "Keep keys inside a safe, not lying in desk drawers" |
| R2 | **Enforce access by identity and permission**: every service and person has unique credentials, and can only read what they are authorized to | 3, 4 | "Give everyone their own key, and make sure the kitchen key doesn't open the safe" |
| R3 | **Audit logging**: who requested which secret, when, and whether it was granted | 4 | "Keep a record of who opened it" |
| R4 | **Self-expiring credentials** | 3, 5 | "Make keys melt away after a while" |
| R5 | **Automated rotation**: changing passwords without anyone having to edit configuration files | 3, 5 | "Change the lock without having to close down the store" |
| R6 | **Instant revocation**: if a leak occurs, invalidate all affected credentials with a single command | 5 | "A panic button" |
| R7 | **Encryption as a service**: applications request "encrypt this for me" and receive the ciphertext, but never touch the key | 6 | "Make sure the vault key never leaves the bank" |

Notice one thing: none of these requirements says "tell people to be more careful." Valeria isn't careless; she's a tired person at six on a Friday. A good design does not depend on nobody ever making a mistake. It depends on the damage being small when someone does.

---

## What Vault is

**HashiCorp Vault** is a program that does exactly that list. It runs as a server; programs and people talk to it over HTTP (using `curl`, for example) or via its CLI command `vault`.

Think of Vault as a **bank vault with a teller window**:

- You don't walk into the vault yourself. You line up at the teller window and make a request.
- The teller verifies your identity (your **token**) and what you are authorized to access (your **policy**).
- If you're authorized, you receive what you asked for. If not, the teller denies the request: a **403**.
- If the bank has audit logging enabled—in Vault, you turn it on yourself—everything is recorded.
- And some things the teller doesn't even hand you: you hand over your document, the teller stamps it inside the vault, and hands it back stamped. The stamp never leaves the bank. That is encryption as a service.

| Requirement | How Vault addresses it | Practiced in |
|---|---|---|
| R1 Centralized and encrypted storage | **KV** engine (*key-value*): stores encrypted secrets; with **KV v2**, it also preserves version history | Session 2 |
| R2 Identity- and policy-based access | **Tokens** and **policies**: each token can only perform what its policy permits; everything else is denied | Session 2 |
| R3 Audit logging | **Audit devices**: once enabled, virtually every request and response is logged, with sensitive values protected | Session 2 |
| R4 Expiring credentials | **Leases** with a time-to-live (**TTL**); **Database** secrets engine with dynamic users | Session 4 |
| R5 Automated rotation | Static roles in the Database secrets engine with a `rotation_period` (rotating automatically on a schedule); and `rotate-root` to immediately rotate the administrative password Vault uses to connect to the database | Session 4 |
| R6 Instant revocation | Revoking a single lease or all leases matching a prefix | Session 4 |
| R7 Encryption as a service | **Transit** secrets engine: encrypts and decrypts, rotates keys, and does not store your data | Session 3 |

A **secrets engine** is a component within Vault specialized in handling a particular kind of secret, like teller windows in a bank: one for deposits, another for checks. You enable the ones you need.

---

## What Vault is not (and a note on licensing)

**Vault is not an HSM.** An **HSM** (*hardware security module*) is a physical device that stores keys and performs encryption operations inside it, with protections against tampering. Depending on the model and its configuration, keys can be impossible to extract, and the device can erase its material if someone tries to force it open. Banks use them, for example, for card PINs.

Vault's Transit secrets engine follows a similar operating model: you send data and receive encrypted data, and the key stays in Vault. Official documentation describes this as "encryption as a service" and clarifies that Vault does not store the data sent to it ([Transit, Vault documentation](https://developer.hashicorp.com/vault/docs/secrets/transit)). But Vault is software running on a server, not hardware. And Transit lets you, if you configure it that way, create exportable keys or import your own keys; by default, it does not allow exporting them (you will verify this in Session 3).

What does exist: **Vault Enterprise**, the paid commercial tier, can use a real HSM to protect its master key and automatically unseal upon boot via devices supporting the PKCS#11 standard ([Vault HSM support](https://developer.hashicorp.com/vault/docs/enterprise/hsm)). In this series, we use the community edition, which does not include that capability.

**A note on licensing.** Vault was open-source software under the MPL 2.0 license for years. On August 10, 2023, HashiCorp announced that future releases would transition to the **Business Source License (BSL) 1.1** ([HashiCorp announcement](https://www.hashicorp.com/blog/hashicorp-adopts-business-source-license)). In short: you can use Vault for free inside your company, but there are limits if you want to offer a product that competes with HashiCorp. In February 2025, IBM completed its acquisition of HashiCorp ([IBM press release](https://newsroom.ibm.com/2025-02-27-ibm-completes-acquisition-of-hashicorp,-creates-comprehensive,-end-to-end-hybrid-cloud-platform)).

In response to the license change, part of the community took the last open-source code and went its own way: **OpenBao**, currently an OpenSSF project under the Linux Foundation, licensed under MPL 2.0 ([openbao.org](https://openbao.org/)). That is called a *fork*: like when a family recipe splits in two directions and each branch continues making it their own way. Almost everything you learn in this series also applies to OpenBao; the callout below details what differs.

> **Vault and OpenBao: the same safe, two owners**
>
> OpenBao branched from the last open-source Vault release, version 1.14: the BSL applies to "Vault Version 1.15.0 or later" ([Vault license](https://github.com/hashicorp/vault/blob/main/LICENSE)). From that point onward, each follows its own path:
>
> | | HashiCorp Vault | OpenBao |
> |---|---|---|
> | License | BSL 1.1: permits internal and production use; restricts offering it as a commercial product competing with IBM's paid offerings | MPL 2.0, open source ([OpenBao license](https://github.com/openbao/openbao/blob/main/LICENSE)) |
> | Maintained by | IBM, parent company of HashiCorp | The community, as an OpenSSF project under the Linux Foundation ([openbao.org](https://openbao.org/)) |
> | CLI command | `vault` | `bao` |
> | Environment variables | `VAULT_ADDR`, `VAULT_TOKEN` | `BAO_ADDR`, `BAO_TOKEN`; falls back to `VAULT_` if unset ([commands](https://openbao.org/docs/commands/)) |
> | Container image | `hashicorp/vault` | `openbao/openbao`, on Docker Hub, Quay, and the GitHub container registry ([installation](https://openbao.org/docs/install/)); as of October 20, 2026, the latest release is 2.7.1, from October 1 ([releases](https://github.com/openbao/openbao/releases)) |
> | Tenant namespaces (*namespaces*) | Paid tier only ([Vault](https://developer.hashicorp.com/vault/docs/enterprise/namespaces)) | Included since version 2.3, released in 2025 ([OpenBao](https://openbao.org/docs/concepts/namespaces/)) |
>
> At Hábil, we chose OpenBao, the open-source version, to encrypt documents across our systems: a compatible API, an open license, and no dependence on a single vendor.
>
> This series uses the official HashiCorp Vault 2.2.0 container image, which is the version each command was tested with. In OpenBao, calls made with `curl` are identical: endpoints begin with `/v1/` and the token is passed in the exact same `X-Vault-Token` header ([OpenBao API](https://openbao.org/docs/api/)). CLI commands swap `vault` for `bao`. However, simply changing command names is not enough, due to three specific details:
>
> - The course lab persists data using `storage "file"`, and OpenBao 2.7 removed that storage backend ([2.7.0 release notes](https://github.com/openbao/openbao/blob/main/CHANGELOG.md)); there, an alternative such as integrated `raft` storage is used instead ([storage](https://openbao.org/docs/configuration/storage/)).
> - Inside the container, paths are `/openbao/config`, `/openbao/file`, and `/openbao/logs`, rather than `/vault/...` ([OpenBao Dockerfile](https://github.com/openbao/openbao/blob/main/Dockerfile)).
> - Currently, OpenBao tokens begin with `s.`, `b.`, or `r.`, not with `hvs.`; OpenBao notes that this token format may change, so avoid writing logic that relies on the prefix ([tokens](https://openbao.org/docs/concepts/tokens/)): grepping for `hvs.` later in the course would not match them.
>
> We did not run this lab environment against OpenBao.

---

👉 **If you are in Management:** the six problems in this session are internal control problems, not programming problems. "One shared password for everyone" is the same as "everyone signs with the same stamp": if an odd check goes out, there is no one to ask. "Former employees still have access" is an offboarding that was never finished: you took away their building badge but not the key to the petty cash box. When systems are audited at your company, the questions in the requirements table (who has access? is it logged? does it expire? can it be revoked all at once?) are the same ones you would ask about the signatures on a bank account.

---

## Exercises for Session 1

Solutions are at the end of this installment. Each exercise explains how to verify on your own whether you got it right.

**Exercise 1 — Secrets hunting with `grep`.** Create a file named `config-tienda.yaml` with the following content (all values are fictional):

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

First, by eye: how many secrets do you spot? Write the count down on paper. Then run this search. `grep` searches for text within files; `-n` prints line numbers, `-i` ignores case, and `-E` enables extended regex so you can use `|` to match "this or that":

```
grep -niE 'pass|key|llave|secret|token|://[^/ ]+:[^@ ]+@' config-tienda.yaml
```

The last pattern fragment, `://[^/ ]+:[^@ ]+@`, looks for URI formats that embed usernames and passwords, such as `smtp://user:password@server`.

a) How many lines did `grep` find? Does it match your visual count?
b) There is one secret that `grep` missed. Which one? Modify the regex pattern so that it catches it as well.

**How to verify:** With the original pattern, `grep -c` (which counts matching lines instead of displaying them) should return `4`. With your corrected pattern, it should return `5`.

**Exercise 2 — Matching.** For each scenario, state which of the six problems it represents and which requirement (R1 through R7) prevents it. There may be more than one requirement.

a) An intern completes their internship. Three months later, their database credentials remain active.
b) The decryption key used to decrypt customer credit card numbers is stored inside a variable in the same application that stores the cards.
c) Someone dropped a table. The audit log shows user `admin`, but five different team members share that `admin` login.
d) To "save time," a tech lead pastes the server password into the general Slack channel.

**How to verify:** Compare your answers against the solutions. If you listed an alternative requirement, check whether it truly prevents the issue or merely mitigates its severity.

**Exercise 3 — In git, deleting is not erasing.** Inside a fresh, empty directory, run these commands line by line. The two `git config` lines configure your identity for git; without them, on a freshly set up machine `git commit` will refuse to run. These settings apply only to this local folder:

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

The file is no longer present in the directory. Now search for the password in git history. `-S` searches for commits where a given string was added or removed, and `-p` prints the full patch diff:

```
git log -p -S Tamal-Verde-2024 --oneline
```

**How to verify:** The output displays the complete patch diff for each matching commit; across those lines you should see both changes: the commit that added the line (`+DB_PASSWORD=...`) and the commit that removed it (`-DB_PASSWORD=...`). Anyone who clones your repository has access to both. In a single sentence, state what must be done with that password in addition to removing it from the file.

**Exercise 4 — Making git blind to secrets.** In the same folder from Exercise 3, recreate a `.env` file with a new password and check what git reports:

```
echo "DB_PASSWORD=Pozole-Rojo-2025" > .env
git status --short
```

Now configure git to ignore it. Create a `.gitignore` file with a single line, `.env`, and rerun `git status --short`.

**How to verify:** Before creating `.gitignore`, git displays `?? .env` (an untracked file that could be staged and pushed). Afterwards, `.env` no longer appears; only `?? .gitignore` is shown. To verify exactly which rule is causing git to ignore it, run `git check-ignore -v .env`; it should return the filename and line number of the matching rule.

**Exercise 5 — Explain it to Doña Clara.** Write a paragraph of no more than 90 words, without unexplained technical jargon, answering: What is Vault? Which Canasta Morada problem would it solve first? Is it the same as an HSM? Is it open-source software?

**How to verify:** First, self-assess: your paragraph must state (1) that Vault stores secrets in a single place and controls who requests them; (2) which problem at Canasta Morada you would tackle first; (3) that it is not an HSM; and (4) that current versions of Vault use the BSL 1.1 license, which is free to use but not open source, while OpenBao uses MPL 2.0. Then share it with someone who does not work in tech: if they can answer the four questions in their own words, it's good.

---

## Common mistakes (and how to spot them)

| Mistake | What it looks like | How to catch it | What to do |
|---|---|---|---|
| Believing that deleting the file fixes the leak | "I removed it from the repo, all done" | `git log -p -S <text>` still finds it | Consider the password compromised: **rotate it**. Cleaning history helps, but copies that were already downloaded are not erased |
| Adding `.env` to `.gitignore` after having already committed it | `git status` no longer shows it, but it remains tracked in the repository | `git ls-files` still lists it | `.gitignore` only applies to untracked files. Untrack it with `git rm --cached .env` and rotate the password |
| Trusting that `grep` caught everything | The count looks clean… for the keywords you thought of | Exercise 1: `clave_sms` slipped through | Use `grep` for a quick sanity check, never as a guarantee. Dedicated secret-scanning tools exist that inspect hundreds of patterns |
| Assuming a private repository is secure | "Nobody can see it, it's private" | The Uber breach: the repo was private | Private lowers exposure, but does not eliminate risk. Secrets do not belong in source code, period |
| Sharing `.env` over chat "just this once" | The file ends up on three mobile phones and in cloud backups | Search your chat history for `PASSWORD` | Every copy is another unmonitored door. Starting in Session 2, everyone requests their own from Vault |

---

## Review for the next session

Session 2 begins with these three questions. Answer them without looking back at the lesson:

1. Name four of the six ways secrets leak.
2. Why is rotating a password after a leak mandatory, even if you already erased it from git history?
3. How is Vault's Transit secrets engine similar to an HSM, and how does it differ?

🔁 **Next week:** Iván decides to build the vault. You spin up Vault with Docker Compose, unseal it using three out of five unseal keys, store your first secrets with `curl`, and see how Vault turns down unauthorized requests. And in the audit log, something appears that nobody expected.

---

## Solutions (don't look before trying them)

**Exercise 1.** With the original pattern, the output is:

```
8:  password: Tamal-Verde-2024
11:  api_key: pk_prueba_51HcXyZ-esto-es-inventado
14:  conexion: smtp://avisos:Churro99@smtp.ejemplo.local:587
16:  llave_aes: MDEyMzQ1Njc4OUFCQ0RFRg==
```

a) Four lines. If you visually counted five, you were right: there are five secrets.

b) `clave_sms: Elote-2023` escapes, because "clave" was not in the pattern. Add it:

```
grep -niE 'pass|key|llave|clave|secret|token|://[^/ ]+:[^@ ]+@' config-tienda.yaml
```

Now line `19:  clave_sms: Elote-2023` appears as well. The lesson is not "just add more words"; it is that a plain text pattern match only finds what you remembered to look for.

**Exercise 2.**

a) Problem 5 (former employees still have access). Prevented by R4 (self-expiring credentials) and R6 (instant revocation). R2 helps because, with individual credentials per person, you know exactly which one to revoke.

b) Problem 6 (storing the encryption key next to the data). Prevented by R7 (encryption as a service): the application requests encryption and decryption, but never holds the key.

c) Problems 3 and 4 (one shared password for everyone; nobody knows who used it). Prevented by R2 (an identity of their own for everyone) and R3 (audit logging).

d) Problem 2 (secrets leaked via chat). Prevented by R1 (centralized storage) and R2 (everyone requests their own credentials). And since it has already leaked, R5 applies: rotate it.

**Exercise 3.** The full output includes patch headers for each commit (`diff --git ...`, `index ...`). The relevant lines are:

```
cbe77a9 quito el .env
-DB_PASSWORD=Tamal-Verde-2024
250264c primera version
+DB_PASSWORD=Tamal-Verde-2024
```

Your commit hashes (the seven characters at the start) will differ; that is normal. The sentence we were looking for: **the password must be rotated in the database**, because anyone who cloned the repository has it.

**Exercise 4.** Before `.gitignore`:

```
?? .env
```

Afterwards:

```
?? .gitignore
```

And `git check-ignore -v .env` outputs:

```
.gitignore:1:.env	.env
```

Meaning: "I am ignoring this due to line 1 of `.gitignore`, which specifies `.env`." In Session 2, you will encounter a startup script that refuses to generate any passwords if that rule is not in place.

**Exercise 5.** One possible answer: "Vault is a secure vault with a teller window for system passwords and keys. Every program and every person has their own identity and only receives what they are authorized for, with every action logged. The first issue it would solve at Canasta Morada is four services and four people sharing the exact same password. It is not an HSM: an HSM is a physical device; Vault is a program, though it can encrypt without exposing the key. It is free to use, with a license that has limits for anyone who wants to compete with its maker; there is a sibling version with an open license called OpenBao."

---

## What's next

In Session 2 you will use Docker Compose. Before you get there, verify that you have these tools installed using `docker compose version`, `curl --version`, `jq --version`, and `openssl version`. If you are missing `jq`, which is used to parse JSON responses, install it as follows: on Debian or Ubuntu, `sudo apt-get install jq`; on Fedora, `sudo dnf install jq`; on Arch, `sudo pacman -S jq`; on macOS with Homebrew installed, `brew install jq`. You need `jq` version 1.6 or newer.

---

*I write from what we encounter every day at Hábil, where we build systems for banking, insurance, and businesses in Mexico. If you run into a problem like this at work or in your family business, let's talk: [habil.mx](https://www.habil.mx/en/)*
