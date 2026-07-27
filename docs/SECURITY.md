# Security decisions

1. AI output is treated as untrusted input.
2. The base platform does not execute model-generated shell commands or arbitrary source code.
3. OpenAI, Stripe and GitHub credentials are never sent to the browser or model context.
4. Every generated app is sanitized and written to its own project directory.
5. Preview and production are physically separate directories.
6. Production is updated only by an explicit publish action after a successful preview build.
7. On-demand TLS is restricted through a database-backed allow endpoint.
8. Django uses HTTPS-aware secure cookies, HSTS, CSRF protection and clickjacking protection.
9. Customer repository provisioning is off by default until dedicated credentials are supplied.
10. A future arbitrary-code agent must run inside ephemeral containers with no production credentials, constrained egress, CPU/RAM/disk limits and mandatory quality gates.
