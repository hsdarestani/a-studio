# A+ Studio production architecture

## Control plane

Django is the product control plane. It owns users, organizations, projects, app specifications, conversations, feature requests, credit accounting, deployments, domains and store-submission requests.

## Build plane

Celery workers process initial builds and chat changes. The model returns a complete declarative specification. A strict sanitizer accepts only known section types and scalar/list content. The generator writes a dependency-free PWA, computes a checksum and exposes it under a preview URL.

## Release plane

Publishing copies the tested preview to a separate production directory. Existing production files are backed up before replacement. Caddy serves static customer PWAs directly and proxies Studio requests to Django.

## Repository plane

When runtime GitHub credentials are configured, every customer project can receive a private repository. The current adapter syncs the app specification and generated public files. A GitHub App should replace a long-lived token before broad commercial launch.

## Native store plane

Store publishing requests are tracked inside Studio but remain human-managed. A+ performs eligibility review, obtains access to the customer's developer accounts, prepares Capacitor/native packages, submits builds, and handles store feedback. Store automation credentials are intentionally not included in the base deployment.
