# Vault desde cero

**Por Dorian Chávez, fundador de Hábil y arquitecto de integración.**

Contraseñas que no viven en el código, llaves que nadie tiene y credenciales que caducan solas.

**Para quién es:** estudiantes de Sistemas y gente que ya programa o administra servidores y quiere dejar de guardar
contraseñas en archivos; y gente de Administración que quiere entender qué preguntar cuando se audita quién tiene acceso
a qué. Es un curso de nivel intermedio: no explica qué es una terminal ni un contenedor, pero cada palabra nueva se
explica cuando aparece. Cada sesión trae un recuadro «Si eres de Administración» con la misma idea llevada al control
interno de una empresa.

**Qué vas a terminar sabiendo:**

- Encontrar contraseñas escritas en archivos y demostrar con `git` que borrarlas no las quita del historial.
- Levantar Vault en modo servidor, abrirlo con 3 de 5 llaves y guardar secretos con permisos y bitácora.
- Cifrar y descifrar datos con el motor Transit sin que la llave llegue a tu programa, y rotar esa llave sin perder nada.
- Pedir usuarios de PostgreSQL y MariaDB que nacen cuando los pides y caducan solos, y conectar un programa de Python
  sin escribir ninguna contraseña.

**Lo que necesitas antes de empezar:** usar la terminal, `git` básico (`add`, `commit`, `status`) y Docker básico (qué
es una imagen y un contenedor). Para la sesión 1 basta una terminal y `git` 2.28 o más nuevo. Desde la sesión 2: Docker
con Compose, `curl`, `jq` 1.6 o más nuevo y `openssl`. Probado en Linux Mint 22.3 con la imagen oficial
`hashicorp/vault:2.2.0`, y en macOS; en Windows no se ha probado.

## Las cuatro sesiones

Cuatro sesiones de unas 2 horas cada una: más o menos una para leer y seguir el ejemplo, y otra para practicar. Todas
siguen la misma historia: una tienda, una contraseña que se subió a GitHub un viernes a las 6:04 p.m. y alguien que
entró a la base de datos a las 3:17 de la mañana.

| Sesión | | Qué aprendes |
|---|---|---|
| 1 | [El problema de los secretos](01-el-problema-de-los-secretos.md) | las seis formas en que se escapa un secreto; buscarlas con `grep` y `git`; qué es Vault y qué no es |
| 2 | [Levantar Vault y guardar secretos](02-levantar-vault-y-guardar-secretos.md) | Docker Compose, el sello y las llaves de Shamir, secretos con `curl`, políticas y bitácora |
| 3 | [Cifrar sin tener la llave](03-cifrar-sin-tener-la-llave.md) | el motor Transit: cifrar, descifrar, rotar, ligar el cifrado a su dueño y borrar destruyendo la llave |
| 4 | [Contraseñas que se cambian solas](04-contrasenas-que-se-cambian-solas.md) | credenciales dinámicas en PostgreSQL y MariaDB, rotación automática, el botón de pánico y Python sin contraseñas |

## El laboratorio

Todo lo que se usa desde la sesión 2 está en la raíz de este repositorio: `compose.yaml`, el guion `iniciar.sh`, las
políticas, los roles y el programa de Python. No trae ninguna contraseña: el laboratorio las genera al arrancar. Cómo
arrancarlo está en el [README principal](../README.md).

## Dónde se publica

Una sesión por semana en «En construcción», el Substack de Hábil, los sábados a las 8:00, del 7 al 28 de noviembre de
2026: https://enconstruccionmx.substack.com
