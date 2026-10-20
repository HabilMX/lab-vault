# Vault desde cero (1): el problema de los secretos

*Un viernes a las 6:04 p.m. una practicante sube un archivo a GitHub. A las 3:17 a.m. alguien entra a la base de datos. Por qué pasa, por qué es tan común, y qué necesita una empresa para que no le pase.*

*Vault desde cero · sesión 1 de 4*

Esta serie tiene cuatro sesiones, una por semana. Aprendes a guardar contraseñas, llaves y otros secretos en HashiCorp Vault, a cifrar datos sin tener la llave en tu programa y a que las contraseñas de las bases de datos se cambien solas. Todo con la terminal: `curl`, `psql`, `mariadb` y Docker Compose. El único programa lo escribes al final, y tiene menos de 30 líneas.

| Sesión | Qué ves | Práctica |
|---|---|---|
| **1 — El problema de los secretos** | Qué sale mal cuando las contraseñas viven en archivos, qué se necesita para evitarlo y qué es Vault | Ejercicios 1 a 5, con `grep` y `git` |
| **2 — Levantar Vault y guardar secretos** | Vault con Docker Compose, el sello y sus llaves, guardar y leer secretos con `curl`, permisos y bitácora | Ejercicios 6 a 10 |
| **3 — Cifrar sin tener la llave** | El motor Transit: cifrar, descifrar y rotar llaves; guardar en PostgreSQL datos que nadie más puede leer | Ejercicios 11 a 15 |
| **4 — Contraseñas que se cambian solas** | Usuarios de base de datos que caducan, contraseñas que rotan solas y un script de Python que no guarda ninguna contraseña | Ejercicios 16 a 20, autoevaluación y repaso de la serie |

Cada sesión es de unas 2 horas: más o menos una para leer y seguir el ejemplo, y otra para practicar. Desde la sesión 2, cada una empieza con **3 preguntas de repaso** de la anterior, para contestar sin ver.

**Qué necesitas saber antes:** usar la terminal (moverte entre carpetas, crear archivos, correr comandos), `git` básico (`git add`, `git commit` y `git status`; saber que un archivo "nuevo" es uno que git todavía no conoce) y Docker básico (qué es una imagen y un contenedor, y `docker compose up`). **Qué necesitas tener hoy:** una terminal y `git` versión 2.28 o más nueva (compruébalo con `git --version`). Docker lo usas desde la sesión 2.

A lo largo de la serie vas a seguir una historia. Es un **escenario**: la empresa y las personas son inventadas. Los datos del mundo real que aparecen dentro de la historia sí son ciertos, y cada uno trae su fuente.

> **El laboratorio del curso** está en el repositorio público [github.com/HabilMX/lab-vault](https://github.com/HabilMX/lab-vault). En esta sesión todavía no lo necesitas: en la sesión 2 lo armas tú, archivo por archivo, y el repositorio te sirve para comparar. No trae ninguna contraseña; el laboratorio las genera al arrancar.

## Objetivos de esta sesión

Al terminar, vas a poder hacer estas cinco cosas. Al lado de cada una está el ejercicio que la demuestra.

| # | Al terminar puedes… | Lo demuestra |
|---|---|---|
| 1 | **Encontrar** contraseñas y llaves escritas en un archivo de configuración, con `grep` | Ejercicio 1 |
| 2 | **Nombrar** las seis formas más comunes en que los secretos se escapan, y **relacionar** cada una con lo que la evita | Ejercicio 2 |
| 3 | **Demostrar** con `git` que borrar un archivo no borra la contraseña del historial | Ejercicio 3 |
| 4 | **Proteger** un archivo `.env` para que `git` no lo suba, y **comprobarlo** | Ejercicio 4 |
| 5 | **Explicar** qué hace Vault, qué no hace, y bajo qué licencia se usa | Ejercicio 5 |

---

## Escenario (ficción) — Capítulo 1: Viernes, 6:04 p.m.

Guadalajara. Oficinas de **Canasta Morada**, una tienda de mandado en línea: catorce personas, dos camionetas y una app donde pides tortillas, huevo y jabón y te llegan en una hora.

Valeria tiene 21 años y lleva tres meses de practicante. Hoy terminó su primera pantalla de verdad: la de «mis pedidos». Funciona. Le tomó dos semanas. Está orgullosa.

Son las 6:04. Tiene boletos para un concierto a las 8. Abre la terminal y escribe lo que ha escrito cien veces:

```
git add .
git commit -m "pantalla de mis pedidos"
git push
```

El punto después de `add` significa «todo». Todo lo que hay en la carpeta. Incluido un archivo que se llama `.env`, donde la app guarda su configuración. Y dentro de ese archivo, una línea:

```
DB_PASSWORD=Tamal-Verde-2024
```

Esa es la contraseña de la base de datos de Canasta Morada. La de los pedidos, los clientes, las direcciones.

Un detalle más: Valeria no subió el código al repositorio privado de la empresa. Lo subió a una copia que hizo en su cuenta personal de GitHub, para enseñarla en su portafolio. Y su cuenta es **pública**.

Cierra la laptop. Se va al concierto.

Nadie se da cuenta.

---

## Capítulo 2: Sábado, 3:17 a.m.

El celular de Iván vibra en el buró. Iván es el único desarrollador con experiencia en Canasta Morada; lleva cinco años ahí. La alerta dice: **«Servidor de base de datos: uso de procesador al 98%»**.

Iván piensa en un pedido grande. Un sábado a las tres de la mañana nadie pide mandado, pero quién sabe. Se vuelve a dormir.

A las 7:40 abre la laptop con el café en la mano. La bitácora de la base de datos dice esto:

```
03:17:02  conexión autorizada: usuario=app_tienda  origen=185.xx.xx.xx
03:17:05  SELECT * FROM clientes
03:21:40  SELECT * FROM pedidos
```

El usuario es `app_tienda`. Es el usuario de la app. La contraseña es la correcta. Para la base de datos, todo está en orden: alguien llegó con la llave buena y abrió la puerta.

Pero esa dirección de origen no es de ningún servidor de Canasta Morada.

---

## Capítulo 3: Sábado, 9:00 a.m. La junta

Doña Clara, la dueña, llega en pants. Están Iván, Valeria —que no durmió casi nada y todavía no sabe que fue ella— y una laptop en la mesa.

—¿Quién entró? —pregunta doña Clara.

Iván no sabe contestar. Y las razones por las que no sabe son el tema de esta sesión.

**Primera pista.** `app_tienda` no es una persona. Es la contraseña que comparten la app, la página web, el programa que manda los pedidos a las camionetas y la macro de Excel con la que contabilidad saca el reporte del mes. Cuatro programas. Además, la saben tres personas. Y Toño.

—¿Quién es Toño?

—El que estaba antes que yo. Se fue hace ocho meses.

—¿Y la sigue sabiendo?

—Nunca la cambiamos.

**Segunda pista.** —Pues cámbienla ya —dice doña Clara.

Iván explica: si cambia la contraseña ahorita, se caen los cuatro programas al mismo tiempo. Hay que entrar a cada uno, editar su archivo, reiniciarlo. Es sábado y hay pedidos. Y la macro de Excel nadie sabe dónde la tiene escrita.

**Tercera pista.** Valeria, en voz baja, pregunta por las CURP. La app guarda la CURP de los clientes que pagan con vales, y se supone que van cifradas.

—Sí van cifradas —dice Iván—. La llave está en el servidor, en un archivo que se llama `llave.txt`.

—¿En el mismo servidor donde están los respaldos?

Silencio.

---

## Capítulo 4: Sábado, 9:26 a.m.

Iván abre la carpeta de respaldos. Cada noche, a las 2:00, el servidor guarda una copia completa de la base de datos.

El respaldo de anoche se descargó a las **3:21 a.m.**

Y la carpeta de al lado, la que tiene `llave.txt`, también.

En ese respaldo están los nombres, las direcciones y las CURP de ocho mil clientes.

*(Continúa en la sesión 2.)*

---

## Por qué importa: esto no es exagerado

La historia de Canasta Morada es inventada. Lo que le pasa, no. Estos casos y cifras son reales y públicos:

- **Cada año aparecen millones de secretos en GitHub público.** La empresa GitGuardian revisa los cambios que se suben a GitHub público y cuenta las contraseñas y llaves que encuentra. En su informe de 2026 contó **28.65 millones de secretos nuevos** subidos durante 2025, un 34% más que el año anterior. Y lo peor: de las credenciales que encontraron válidas en 2022, **más del 64% seguían funcionando** cuando las volvieron a probar en enero de 2026. Es decir, según GitGuardian, esas credenciales nunca se remediaron: la contraseña filtrada seguía abriendo la puerta años después. Fuente: [GitGuardian, *The State of Secrets Sprawl 2026*](https://blog.gitguardian.com/the-state-of-secrets-sprawl-2026/).
- **Un repositorio privado no te salva.** En 2016 unos intrusos entraron a la cuenta de GitHub de ingenieros de Uber usando contraseñas reutilizadas de otras filtraciones. En un repositorio **privado** encontraron una llave de acceso a Amazon Web Services. Con ella descargaron datos de unos 25.6 millones de nombres y correos y de unas 607,000 licencias de conducir. Lo documentó la Comisión Federal de Comercio de Estados Unidos (FTC): [análisis del caso Uber, 2018](https://www.ftc.gov/system/files/documents/cases/1523054_uber_technologies_revised_analysis.pdf).
- **Una sola liga puede abrir todo.** En 2023, la empresa de seguridad Wiz encontró en un repositorio público de investigadores de Microsoft una liga con un permiso de acceso a una cuenta de almacenamiento. El permiso no era de lectura: era de **control total**, vencía en 2051 y dejaba ver 38 terabytes, incluidos respaldos de computadoras y más de 30,000 mensajes internos de Teams. Fuente: [Wiz, 18 de septiembre de 2023](https://www.wiz.io/blog/38-terabytes-of-private-data-accidentally-exposed-by-microsoft-ai-researchers).

GitGuardian también reporta que cerca de 28% de los incidentes que detecta no nacen en el código, sino en herramientas como Slack, Jira o Confluence. La contraseña pegada en el chat «nada más para que la copies» también cuenta.

---

## Las seis formas en que se escapa un secreto

Antes de ver soluciones, ponle nombre a cada problema. Un **secreto** es cualquier dato que da acceso a algo: una contraseña, una llave de cifrado, un token de una API. Piensa en la llave de tu casa: no es valiosa por sí misma, es valiosa por la puerta que abre.

### 1. La contraseña escrita en el código o en un archivo que se sube

Es lo que hizo Valeria. El archivo `.env` es una costumbre muy útil: separa la configuración del código. Pero si el archivo viaja con el código, la separación no sirve de nada. Es como pegar la llave de la casa con cinta a la puerta, por dentro, y luego mandar fotos de la puerta.

Y hay una trampa extra: **en git, borrar no es borrar.** Git guarda la historia de cada cambio. Si subiste la contraseña y en el siguiente cambio la quitas, sigue en el cambio anterior. Lo compruebas en el ejercicio 3.

### 2. El `.env` que se pasa por WhatsApp

—Oye, ¿me pasas el `.env`? —Va. Y ahí queda: en el chat, en el respaldo del celular y en la computadora del que abrió WhatsApp Web en un café. Cada copia es una puerta más que nadie vigila.

### 3. La misma contraseña para todos y para siempre

En Canasta Morada, cuatro programas y cuatro personas usan `app_tienda`. Es como el candado de la bodega de una escuela cuya combinación saben todos los maestros desde 2019. Si un día falta algo, no hay forma de saber quién abrió.

Y como cambiarla rompe todo al mismo tiempo, nadie la cambia. «Para siempre» no es una decisión: es lo que pasa cuando cambiar duele.

### 4. Nadie sabe quién la usó

La base de datos registró «entró `app_tienda`». No registró «entró la app», ni «entró Toño», ni «entró alguien desde otro país con la contraseña robada». Cuando todos usan la misma identidad, la bitácora sirve de poco.

### 5. El que se fue todavía la sabe

Toño se fue hace ocho meses, en buenos términos. Pero se llevó en la cabeza la contraseña de la base de datos, la del servidor de correo y la de la cuenta de pagos. No hizo nada malo. Tampoco nadie puede garantizarlo. Y si su laptop vieja la vendió por Marketplace con un archivo de configuración adentro, ya no depende ni de él.

### 6. La llave de cifrado junto a los datos

Cifrar, en corto, es revolver un dato con una llave para que solo quien tenga la llave pueda leerlo. Canasta Morada sí cifraba las CURP. Pero guardó la llave en `llave.txt`, en el mismo servidor que los respaldos. Es como tener una caja fuerte y dejar la combinación en un post-it pegado arriba. El ladrón se llevó las dos cosas en el mismo viaje.

---

## Lo que se requiere

Si fueras Iván y tuvieras que diseñar cómo debería funcionar Canasta Morada el lunes, ¿qué pedirías? Esta es la lista que hace casi cualquier equipo de seguridad. Cada punto ataca uno o varios de los seis problemas.

| # | Requisito | Ataca el problema | En palabras de doña Clara |
|---|---|---|---|
| R1 | **Guardar los secretos en un solo lugar, cifrados**, no regados en archivos | 1, 2 | «Que las llaves vivan en una caja fuerte, no en los cajones» |
| R2 | **Dar acceso por identidad y por permiso**: cada programa y cada persona tiene su propia credencial, y solo puede leer lo que le toca | 3, 4 | «Que cada quien tenga su llave, y que la de la cocina no abra la caja» |
| R3 | **Bitácora de auditoría**: quién pidió qué secreto, cuándo y si se lo dieron | 4 | «Que quede anotado quién abrió» |
| R4 | **Credenciales que caducan solas** | 3, 5 | «Que las llaves se derritan después de un rato» |
| R5 | **Rotación automática**: cambiar contraseñas sin que nadie tenga que editar archivos | 3, 5 | «Que cambiar la chapa no obligue a cerrar la tienda» |
| R6 | **Revocar de golpe**: si algo se filtra, cancelar todas las credenciales afectadas con una sola orden | 5 | «Un botón de pánico» |
| R7 | **Cifrado como servicio**: los programas piden «cíframe esto» y reciben el dato cifrado, pero nunca tienen la llave | 6 | «Que la llave de la caja nunca salga del banco» |

Fíjate en una cosa: ninguno de estos requisitos dice «que la gente tenga más cuidado». Valeria no es descuidada; es una persona cansada un viernes a las seis. Un buen diseño no depende de que nadie se equivoque nunca. Depende de que, cuando alguien se equivoque, el daño sea chico.

---

## Qué es Vault

**HashiCorp Vault** es un programa que hace exactamente esa lista. Corre como un servidor; los programas y las personas le hablan por HTTP (con `curl`, por ejemplo) o con su comando `vault`.

Piensa en Vault como la **bóveda de un banco con ventanilla**:

- Tú no entras a la bóveda. Te formas en la ventanilla y pides.
- La cajera revisa tu identificación (tu **token**) y lo que tienes permitido (tu **política**).
- Si te toca, te da lo que pediste. Si no, te dice que no: un **403**.
- Si el banco tiene la bitácora encendida —en Vault la enciendes tú—, todo queda anotado.
- Y algunas cosas ni siquiera te las entrega: le das tu documento, la cajera lo sella en la bóveda y te lo regresa sellado. El sello nunca sale del banco. Eso es el cifrado como servicio.

| Requisito | Cómo lo cubre Vault | Lo practicas en |
|---|---|---|
| R1 Guardar centralizado y cifrado | Motor **KV** (de *key-value*, llave-valor): guarda secretos cifrados; con **KV v2**, además conserva versiones | Sesión 2 |
| R2 Acceso por identidad y política | **Tokens** y **políticas**: cada token solo hace lo que su política permite; todo lo demás está negado | Sesión 2 |
| R3 Auditoría | **Dispositivos de auditoría**: una vez que los activas, casi cada petición y cada respuesta quedan en una bitácora, con los valores sensibles protegidos | Sesión 2 |
| R4 Credenciales que caducan | **Arrendamientos** (*leases*) con tiempo de vida (**TTL**); motor **Database** con usuarios dinámicos | Sesión 4 |
| R5 Rotación automática | Roles estáticos del motor Database con `rotation_period` (rotan solos cada cierto tiempo); y `rotate-root` para cambiar de inmediato la contraseña administrativa con la que Vault se conecta a la base | Sesión 4 |
| R6 Revocar de golpe | Revocación de un arrendamiento o de todos los que empiezan con un prefijo | Sesión 4 |
| R7 Cifrado como servicio | Motor **Transit**: cifra y descifra, rota llaves y no guarda tus datos | Sesión 3 |

Un **motor** (*secrets engine*) es una parte de Vault especializada en un tipo de secreto, como las ventanillas del banco: una para depósitos, otra para cheques. Activas los que necesites.

---

## Lo que Vault no es (y una nota de licencia)

**Vault no es un HSM.** Un **HSM** (*hardware security module*) es un aparato físico que guarda llaves y hace operaciones de cifrado adentro, con protecciones contra manipulación. Según el modelo y su configuración, las llaves pueden ser imposibles de sacar y el aparato puede borrar su material si alguien intenta abrirlo a la fuerza. Los bancos los usan, por ejemplo, para los PIN de las tarjetas.

El motor Transit de Vault se parece en la forma de trabajar: tú mandas datos y recibes datos cifrados, y la llave se queda en Vault. La documentación oficial lo describe como «cifrado como servicio» y aclara que Vault no guarda los datos que le mandas ([Transit, documentación de Vault](https://developer.hashicorp.com/vault/docs/secrets/transit)). Pero Vault es software corriendo en un servidor, no hardware. Y Transit permite, si lo configuras así, crear llaves exportables o importar llaves tuyas; por defecto no deja exportarlas (lo vas a comprobar en la sesión 3).

Lo que sí existe: **Vault Enterprise**, la versión de pago, puede usar un HSM real para proteger su propia llave maestra y para abrirse solo al arrancar, con equipos compatibles con el estándar PKCS#11 ([Vault HSM support](https://developer.hashicorp.com/vault/docs/enterprise/hsm)). En esta serie usamos la versión comunitaria, que no lo trae.

**Sobre la licencia.** Vault fue software libre con licencia MPL 2.0 durante años. El 10 de agosto de 2023, HashiCorp anunció que sus versiones nuevas pasaban a la **Business Source License (BSL) 1.1** ([anuncio de HashiCorp](https://www.hashicorp.com/blog/hashicorp-adopts-business-source-license)). En corto: puedes usar Vault gratis en tu empresa, pero hay límites si quieres ofrecer un producto que compita con HashiCorp. En febrero de 2025, IBM terminó de comprar HashiCorp ([comunicado de IBM](https://newsroom.ibm.com/2025-02-27-ibm-completes-acquisition-of-hashicorp,-creates-comprehensive,-end-to-end-hybrid-cloud-platform)).

Como respuesta al cambio de licencia, una parte de la comunidad tomó el último código abierto y siguió por su lado: **OpenBao**, que hoy es un proyecto de la OpenSSF, dentro de la Linux Foundation, con licencia MPL 2.0 ([openbao.org](https://openbao.org/)). A eso se le llama un *fork*, una bifurcación: como cuando una receta familiar se divide y cada rama de la familia la sigue haciendo a su modo. Casi todo lo que aprendas en esta serie te sirve también en OpenBao, pero en esta serie no lo probamos.

---

👉 **Si eres de Administración:** los seis problemas de esta sesión son problemas de control interno, no de programación. «La misma contraseña para todos» es lo mismo que «todos firman con el mismo sello»: si sale un cheque raro, no hay a quién preguntarle. «El que se fue todavía la sabe» es una baja de personal que no terminó: le quitaste la credencial del edificio pero no la llave de la caja chica. Cuando auditen sistemas en tu empresa, las preguntas de la tabla de requisitos (¿quién tiene acceso?, ¿queda registrado?, ¿caduca?, ¿se puede cancelar de golpe?) son las mismas que harías sobre las firmas de una cuenta de banco.

---

## Ejercicios de la sesión 1

Las soluciones están al final de esta entrega. Cada ejercicio te dice cómo comprobar solo si te salió.

**Ejercicio 1 — Caza de secretos con `grep`.** Crea un archivo `config-tienda.yaml` con este contenido (todos los valores son inventados):

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

Primero, a ojo: ¿cuántos secretos ves? Escríbelo en papel. Después corre esta búsqueda. `grep` busca texto en archivos; `-n` muestra el número de línea, `-i` ignora mayúsculas y `-E` permite usar `|` para decir «esto o esto otro»:

```
grep -niE 'pass|key|llave|secret|token|://[^/ ]+:[^@ ]+@' config-tienda.yaml
```

El último pedazo, `://[^/ ]+:[^@ ]+@`, busca direcciones que llevan usuario y contraseña adentro, como `smtp://usuario:contraseña@servidor`.

a) ¿Cuántas líneas encontró `grep`? ¿Coincide con tu conteo a ojo?
b) Hay un secreto que `grep` no encontró. ¿Cuál? Modifica el patrón para que también lo encuentre.

**Cómo compruebas:** con el patrón original, `grep -c` (que cuenta líneas en lugar de mostrarlas) debe dar `4`. Con tu patrón corregido, debe dar `5`.

**Ejercicio 2 — Relaciona.** Para cada situación, escribe cuál de los seis problemas es y qué requisito (R1 a R7) lo evita. Puede haber más de un requisito.

a) Un practicante termina su servicio social. Tres meses después, su usuario de la base de datos sigue funcionando.
b) La llave para descifrar las tarjetas de los clientes está en una variable del mismo programa que las guarda.
c) Alguien borró una tabla. La bitácora dice que fue `admin`, y el usuario `admin` lo usan cinco personas.
d) Para «hacerlo rápido», el líder pega la contraseña del servidor en el canal general de Slack.

**Cómo compruebas:** compara con las soluciones. Si en alguna pusiste otro requisito, revisa si de verdad lo evita o solo lo hace menos grave.

**Ejercicio 3 — En git, borrar no es borrar.** En una carpeta nueva y vacía, corre esto línea por línea. Las dos líneas de `git config` le dicen a git quién eres; sin ellas, en una computadora recién estrenada `git commit` se niega a funcionar. Solo valen para esta carpeta:

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

El archivo ya no está en la carpeta. Ahora busca la contraseña en la historia. `-S` busca los cambios donde apareció o desapareció un texto, y `-p` muestra el cambio completo:

```
git log -p -S Tamal-Verde-2024 --oneline
```

**Cómo compruebas:** la salida trae el parche completo de cada cambio; entre sus líneas debes ver los dos cambios, el que agregó la línea (`+DB_PASSWORD=...`) y el que la quitó (`-DB_PASSWORD=...`). Si alguien clona tu repositorio, tiene los dos. Escribe en una frase qué tendrías que hacer con esa contraseña, además de borrarla.

**Ejercicio 4 — Que git ni la vea.** En la misma carpeta del ejercicio 3, vuelve a crear un `.env` con otra contraseña y mira qué dice git:

```
echo "DB_PASSWORD=Pozole-Rojo-2025" > .env
git status --short
```

Ahora haz que git lo ignore. Crea un archivo `.gitignore` con una sola línea, `.env`, y vuelve a correr `git status --short`.

**Cómo compruebas:** antes de crear `.gitignore`, git muestra `?? .env` (archivo nuevo que podría subirse). Después, ya no aparece `.env`; solo `?? .gitignore`. Para estar seguro de qué regla lo está ignorando, corre `git check-ignore -v .env`; debe contestar con el nombre del archivo y la línea de la regla.

**Ejercicio 5 — Explícaselo a doña Clara.** Escribe un párrafo de máximo 90 palabras, sin palabras técnicas sin explicar, que conteste: ¿qué es Vault?, ¿qué problema de Canasta Morada resolvería primero?, ¿es lo mismo que un HSM?, ¿es software libre?

**Cómo compruebas:** primero, autoevalúate: tu párrafo debe decir (1) que Vault guarda los secretos en un solo lugar y controla quién los pide; (2) qué problema de Canasta Morada atacarías primero; (3) que no es un HSM; y (4) que las versiones actuales de Vault usan la licencia BSL 1.1, que se puede usar sin costo pero no es software libre, y que OpenBao usa MPL 2.0. Después pásaselo a alguien que no estudie sistemas: si puede contestarte las cuatro preguntas con sus palabras, está bien.

---

## Errores comunes (y cómo darte cuenta)

| Error | Cómo se ve | Cómo darte cuenta | Qué hacer |
|---|---|---|---|
| Creer que borrar el archivo arregla la filtración | «Ya lo quité del repo, listo» | `git log -p -S <texto>` todavía lo encuentra | Considera la contraseña quemada: **cámbiala**. Limpiar la historia ayuda, pero las copias que ya se bajaron no se borran |
| Agregar `.env` al `.gitignore` después de haberlo subido | `git status` ya no lo muestra, pero sigue en el repositorio | `git ls-files` lo sigue listando | `.gitignore` solo afecta archivos nuevos. Quítalo del índice con `git rm --cached .env` y cambia la contraseña |
| Confiar en que `grep` encontró todo | El conteo sale bien… para los nombres que se te ocurrieron | El ejercicio 1: `clave_sms` se escapa | Usa `grep` para una revisión rápida, no como garantía. Existen herramientas hechas para esto que buscan cientos de formatos |
| Pensar que un repo privado es seguro | «Nadie lo ve, es privado» | El caso Uber: el repo era privado | Privado reduce el riesgo, no lo quita. Los secretos no van en el código, punto |
| Compartir el `.env` por chat «solo esta vez» | El archivo aparece en tres celulares y en la nube | Busca en tu chat la palabra `PASSWORD` | Cada copia es una puerta más. A partir de la sesión 2, cada quien pide lo suyo a Vault |

---

## Repaso para la próxima sesión

La sesión 2 empieza con estas tres preguntas. Contéstalas sin ver la lección:

1. Nombra cuatro de las seis formas en que se escapa un secreto.
2. ¿Por qué cambiar la contraseña después de una filtración es obligatorio, aunque ya la hayas borrado de git?
3. ¿En qué se parece y en qué se diferencia el motor Transit de Vault de un HSM?

🔁 **La próxima semana:** Iván decide construir la caja fuerte. Levantas Vault con Docker Compose, lo abres con tres de cinco llaves, guardas tus primeros secretos con `curl` y ves cómo Vault le dice que no a quien pide lo que no le toca. Y en la bitácora aparece algo que nadie esperaba.

---

## Soluciones (no las veas antes de intentarlo)

**Ejercicio 1.** Con el patrón original, la salida es:

```
8:  password: Tamal-Verde-2024
11:  api_key: pk_prueba_51HcXyZ-esto-es-inventado
14:  conexion: smtp://avisos:Churro99@smtp.ejemplo.local:587
16:  llave_aes: MDEyMzQ1Njc4OUFCQ0RFRg==
```

a) Cuatro líneas. Si a ojo contaste cinco, tenías razón: hay cinco secretos.

b) Se escapa `clave_sms: Elote-2023`, porque «clave» no estaba en el patrón. Agrégalo:

```
grep -niE 'pass|key|llave|clave|secret|token|://[^/ ]+:[^@ ]+@' config-tienda.yaml
```

Ahora aparece también la línea `19:  clave_sms: Elote-2023`. La lección no es «agrega más palabras»; es que una búsqueda de texto solo encuentra lo que se te ocurrió buscar.

**Ejercicio 2.**

a) Problema 5 (el que se fue todavía la sabe). Lo evitan R4 (credenciales que caducan) y R6 (revocar de golpe). R2 ayuda porque, con credenciales por persona, sabes cuál cancelar.

b) Problema 6 (la llave junto a los datos). Lo evita R7 (cifrado como servicio): el programa pide cifrar y descifrar, pero nunca tiene la llave.

c) Problemas 3 y 4 (la misma para todos; nadie sabe quién). Lo evitan R2 (identidad propia para cada quien) y R3 (bitácora).

d) Problema 2 (el secreto que viaja por chat). Lo evitan R1 (un solo lugar) y R2 (cada quien pide lo suyo). Y como ya se filtró, toca R5: cambiarla.

**Ejercicio 3.** La salida completa incluye, por cada cambio, encabezados del parche (`diff --git ...`, `index ...`). Las líneas que importan son estas:

```
cbe77a9 quito el .env
-DB_PASSWORD=Tamal-Verde-2024
250264c primera version
+DB_PASSWORD=Tamal-Verde-2024
```

Tus identificadores de cambio (los siete caracteres del principio) van a ser otros; eso es normal. La frase que buscábamos: **hay que cambiar la contraseña en la base de datos**, porque cualquiera que haya clonado el repositorio la tiene.

**Ejercicio 4.** Antes del `.gitignore`:

```
?? .env
```

Después:

```
?? .gitignore
```

Y `git check-ignore -v .env` contesta:

```
.gitignore:1:.env	.env
```

Quiere decir: «lo ignoro por la línea 1 del archivo `.gitignore`, que dice `.env`». En la sesión 2 vas a ver un guion de arranque que se niega a crear contraseñas si esa regla no existe.

**Ejercicio 5.** Una respuesta posible: «Vault es una caja fuerte con ventanilla para las contraseñas y llaves de los sistemas. Cada programa y cada persona tiene su propia identificación y solo recibe lo que le toca, y todo queda anotado. Lo primero que resolvería en Canasta Morada es que cuatro programas y cuatro personas compartan la misma contraseña. No es un HSM: un HSM es un aparato físico; Vault es un programa, aunque puede cifrar sin entregar la llave. Se puede usar gratis, con una licencia que tiene límites para quien quiera competir con su fabricante; existe una versión hermana con licencia libre que se llama OpenBao.»

---

## Lo que sigue

En la sesión 2 usas Docker Compose. Antes de llegar, comprueba que tienes estas herramientas con `docker compose version`, `curl --version`, `jq --version` y `openssl version`. Si te falta `jq`, que sirve para leer las respuestas en formato JSON, instálalo así: en Debian o Ubuntu, `sudo apt-get install jq`; en Fedora, `sudo dnf install jq`; en Arch, `sudo pacman -S jq`; en macOS con Homebrew instalado, `brew install jq`. Necesitas `jq` 1.6 o más nuevo.

---

*Escribo desde lo que vemos todos los días en Hábil, donde construimos sistemas para banca, seguros y empresas en México. Si en tu trabajo o en el negocio de tu familia se topan con un problema así, platiquemos: [habil.mx](https://habil.mx)*
