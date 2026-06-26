# Super Insecure Bank

**Super Insecure Bank** es una aplicación web bancaria intencionalmente vulnerable, creada por **Fernando Conislla** con fines educativos.

El laboratorio está diseñado para practicar identificación, explotación y análisis de vulnerabilidades web modernas alineadas con **OWASP Top 10:2025**.

Simula funciones típicas de banca digital como autenticación, consulta de cuentas, transferencias, estados de cuenta, restablecimiento de contraseña, recibos, logs de seguridad y servicios internos expuestos.

> **Advertencia:** esta aplicación contiene vulnerabilidades intencionales. Debe ejecutarse únicamente en entornos controlados, locales o de laboratorio. No debe exponerse a Internet ni utilizarse como aplicación real.

---

## Requisitos

Se recomienda usar **Kali Linux** como máquina de trabajo.

Instalar Docker y Docker Compose:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable docker --now
```

---

## Instalación y despliegue

### 1. Descargar el proyecto

```bash
git clone https://github.com/seguridadcero/super-insecure-bank.git
cd super-insecure-bank
```

### 2. Construir el laboratorio

```bash
sudo docker compose build --no-cache
```

Este comando construye la imagen Docker. Úsalo la primera vez, después de actualizar el proyecto o cuando necesites reconstruir el entorno desde cero.

### 3. Levantar la aplicación

```bash
sudo docker compose up
```

Este comando inicia el laboratorio y muestra los logs en pantalla.

Apagar y eliminar volúmenes:

```bash
sudo docker compose down -v
```

---

## Cómo ingresar al laboratorio

Desde la misma máquina donde corre Docker:

```text
http://127.0.0.1:5080
https://127.0.0.1:5443
```

Desde otra máquina de la red, usa la **IP del dispositivo donde está corriendo Docker**.

Para obtener la IP del dispositivo:

```bash
ip -4 addr
```

Ejemplo:

```text
http://192.168.1.122:5080
https://192.168.1.122:5443
```

---

## Credenciales iniciales

```text
Usuario:  fernando.conislla
Password: password1
```

---

# Escenarios OWASP Top 10:2025

## A01:2025 — Broken Access Control

### Lab 1 — Acceso a información de otra cuenta

La aplicación permite a los usuarios del banco ver sus cuentas y transacciones.

¿Será posible consultar los movimientos de otros usuarios, como Alice en la cuenta 2002?

### Lab 2 — Funcionalidad de préstamos oculta

La sección de préstamos indica que este trámite debe realizarse de forma presencial.

¿Será posible solicitar un préstamo desde la aplicación?

### Lab 3 — Modificación de un dato sensible del perfil

La aplicación permite al usuario modificar algunos datos de su perfil.

¿Será posible modificar el teléfono usado para recibir OTP?

---

## A02:2025 — Security Misconfiguration

### Lab 4 — Información interna expuesta

La aplicación cuenta con una ruta para consultar el estado del sistema.

¿Será posible acceder a información interna del banco sin iniciar sesión?

### Lab 5 — Consola de diagnóstico expuesta

La aplicación fue desplegada conservando una pantalla de diagnóstico.

¿Será posible encontrar una consola interna accesible desde el navegador?

---

## A03:2025 — Software Supply Chain Failures

### Lab 6 — Componentes de terceros desactualizados

La aplicación utiliza componentes de terceros para funcionar.

¿Tendrá componentes de terceros desactualizados o vulnerables?

---

## A04:2025 — Cryptographic Failures

### Lab 7 — Almacenamiento inseguro de contraseñas

La aplicación almacena las contraseñas de los usuarios en una base de datos interna.

¿Será posible recuperar los valores originales de esas contraseñas?

### Lab 8 — Canal HTTPS con configuración débil

La aplicación ofrece acceso mediante HTTPS para proteger la comunicación entre el usuario y el banco.

¿Será posible identificar si el canal cifrado utiliza configuraciones criptográficas débiles?

### Lab 9 — Secreto débil para la generación de tokens

La aplicación usa tokens para mantener la sesión del usuario autenticado.

¿Será posible crear un token válido para otro usuario?

---

## A05:2025 — Injection

### Lab 10 — Inyección SQL en búsqueda de transacciones

La aplicación permite buscar movimientos dentro de una cuenta bancaria.

¿Será posible manipular la búsqueda para obtener más información de la esperada?

### Lab 11 — Command Injection en estados de cuenta

La aplicación permite al usuario consultar sus estados de cuenta.

¿Será posible manipular esta funcionalidad para ejecutar comandos en el servidor?

### Lab 12 — Cross-Site Scripting en recibos

La aplicación permite escribir una nota o referencia al realizar una transferencia.

¿Será posible contaminar este campo para ejecutar código JavaScript arbitrario cuando se visualice el recibo?

---

## A06:2025 — Insecure Design

### Lab 13 — Diseño inadecuado en el cobro de comisiones

La aplicación cobra una comisión por transferencias externas.

¿Será posible evitar el cobro de la comisión al ejecutar una transferencia externa?

---

## A07:2025 — Authentication Failures

### Lab 14 — Enumeración de usuarios

La aplicación permite interactuar con distintos flujos donde se procesan nombres de usuario.

¿Será posible descubrir y validar nombres de usuario válidos en la aplicación?

### Lab 15 — Restablecimiento de contraseña inseguro

La aplicación permite restablecer contraseñas mediante un enlace enviado al correo del usuario.

¿Será posible cambiar la contraseña de otro usuario del sistema, por ejemplo Alice?

### Lab 16 — Login con defensa insuficiente y contraseñas débiles

El formulario de login permite intentar diferentes combinaciones de usuario y contraseña.

¿Será posible identificar contraseñas válidas de los usuarios de la aplicación?

---

## A08:2025 — Software or Data Integrity Failures

### Lab 17 — Recibo con datos manipulados

La aplicación genera un recibo después de realizar una transferencia.

¿Será posible generar recibos inconsistentes respecto a las transacciones reales?

---

## A09:2025 — Security Logging and Alerting Failures

### Lab 18 — Logs de seguridad que exponen demasiada información

La aplicación registra eventos relacionados con autenticación y actividad sospechosa.

¿Será posible identificar información excesiva o sensible almacenada en los logs?

---

## A10:2025 — Mishandling of Exceptional Conditions

### Lab 19 — Manejo inadecuado de errores en consulta de transacciones

La aplicación recibe identificadores de cuenta para consultar transacciones.

¿Será posible provocar un error que revele detalles internos del sistema?

---

## Créditos

Super Insecure Bank is an intentionally vulnerable web application created by [Fernando Conislla](https://www.linkedin.com/in/fernando-conislla-murguia/) for educational purposes.<br>
Removing these credits may result in your bank account being mysteriously hacked.
