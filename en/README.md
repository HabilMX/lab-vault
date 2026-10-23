# Vault from scratch

**By Dorian Chávez, founder of Hábil and integration architect.**

Passwords that do not live in code, keys that no one has, and credentials that expire on their own.

**Who it is for:** Computer Science students and people who already program or manage servers and want to stop storing
passwords in files; and people in Management who want to understand what to ask when auditing who has access to
what. It is an intermediate-level course: it does not explain what a terminal or a container is, but every new term is
explained as it comes up. Each session includes an “If you are in Management” box with the same idea applied to a
company's internal controls.

**What you will know by the end:**

- Find passwords written in files and prove with `git` that deleting them does not remove them from history.
- Start Vault in server mode, unseal it with 3 of 5 keys, and store secrets with permissions and an audit log.
- Encrypt and decrypt data with the Transit engine without the key reaching your program, and rotate that key without losing anything.
- Request PostgreSQL and MariaDB users that are created when you ask for them and expire on their own, and connect a Python program
  without writing any passwords.

**What you need before you start:** comfort with the terminal, basic `git` (`add`, `commit`, `status`), and basic Docker (what
an image and a container are). For session 1, a terminal and `git` 2.28 or newer are enough. From session 2 on: Docker
with Compose, `curl`, `jq` 1.6 or newer, and `openssl`. Tested on Linux Mint 22.3 with the official
`hashicorp/vault:2.2.0` image, and on macOS; it has not been tested on Windows.

## The four sessions

Four sessions of about 2 hours each: roughly one to read and follow along with the example, and another to practice. All of them
follow the same story: a store, a password pushed to GitHub on a Friday at 6:04 p.m., and someone who
accessed the database at 3:17 in the morning.

| Session | | What you learn |
|---|---|---|
| 1 | [The problem with secrets](01-el-problema-de-los-secretos.md) | the six ways a secret leaks; searching for them with `grep` and `git`; what Vault is and what it is not |
| 2 | [Starting Vault and storing secrets](02-levantar-vault-y-guardar-secretos.md) | Docker Compose, the seal and Shamir keys, secrets with `curl`, policies, and the audit log |
| 3 | [Encrypting without having the key](03-cifrar-sin-tener-la-llave.md) | the Transit engine: encrypting, decrypting, rotating, binding encryption to its owner, and deleting by destroying the key |
| 4 | [Passwords that change on their own](04-contrasenas-que-se-cambian-solas.md) | dynamic credentials in PostgreSQL and MariaDB, automatic rotation, the panic button, and Python without passwords |

## The lab

Everything used from session 2 on is in the root of this repository: `compose.yaml`, the `iniciar.sh` script, the
policies, the roles, and the Python program. It does not include any passwords: the lab generates them on startup. How
to start it is in the [main README](../README.md).

## Where it is published

One session per week in “En construcción”, Hábil's Substack, on Saturdays at 8:00 a.m., from November 7 to 28,
2026: https://enconstruccionmx.substack.com
