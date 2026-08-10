# A+ Studio — Store release profile

## Identity

- Product: **A+ Studio**
- Developer/business: **A+ Solution GmbH**
- Version: **1.0.0**
- Android package: `de.aplussolution.studio`
- iOS bundle ID: `de.aplussolution.studio`
- Production API / marketing URL: `https://studio.aplus-solution.de`
- Privacy policy: `https://studio.aplus-solution.de/privacy/`
- Support URL: `https://studio.aplus-solution.de/support/`
- Account deletion URL: `https://studio.aplus-solution.de/account-deletion/`
- Category: Business / Developer productivity
- Native technology: Capacitor 8 with a local first-party UI. There is no remote `server.url` WebView wrapper.

## German store copy

**Title**  
A+ Studio

**Apple subtitle**  
Apps mit AI bauen

**Google short description**  
Apps mit AI planen, als Preview testen und mit A+ professionell veröffentlichen.

**Apple description**  
A+ Studio ist die mobile AI Software Factory von A+ Solution. Beschreiben Sie Ihre App-Idee, erstellen Sie einen ersten Preview-Build und verbessern Sie das Produkt direkt im AI Builder.

Verwalten Sie Projekte, verfolgen Sie Build-Status und Versionen, öffnen Sie Previews und starten Sie nach Ihrer Freigabe die Veröffentlichung. Wenn Sie Ihre App im App Store veröffentlichen möchten, können Sie den A+ Store-Publishing-Prozess direkt aus dem Projekt anstoßen.

Die mobile App konzentriert sich auf den produktiven Builder-Workflow: Konto, Projekte, AI-Änderungen, Preview, Publishing und Store-Anfragen. Digitale Käufe oder externe Zahlungslinks sind in Version 1.0 bewusst nicht Bestandteil der mobilen App.

**Google Play description**  
A+ Studio ist die mobile AI Software Factory von A+ Solution. Beschreiben Sie Ihre App-Idee, erstellen Sie einen ersten Preview-Build und verbessern Sie das Produkt direkt im AI Builder.

Verwalten Sie Projekte, verfolgen Sie Build-Status und Versionen, öffnen Sie Previews und starten Sie nach Ihrer Freigabe die Veröffentlichung. Wenn Sie Ihre App bei Google Play veröffentlichen möchten, können Sie den A+ Store-Publishing-Prozess direkt aus dem Projekt anstoßen.

Die mobile App konzentriert sich auf den produktiven Builder-Workflow: Konto, Projekte, AI-Änderungen, Preview, Publishing und Store-Anfragen. Digitale Käufe oder externe Zahlungslinks sind in Version 1.0 bewusst nicht Bestandteil der mobilen App.

**Keywords (Apple)**  
app builder,ai,ki,software,pwa,prototyp,entwicklung,digitalisierung,preview,business

**Promotional text**  
Von der Idee zum Preview: Apps mit AI planen, iterieren und mit A+ strukturiert veröffentlichen.

## Review notes

- A pre-existing paid account is **not required**.
- The login screen contains a local **Demo ansehen** flow so the interface can be reviewed without credentials.
- Reviewers can also create a free account in-app; the account receives welcome credits and does not require a purchase.
- The native app contains no digital purchase flow, Stripe link, advertising SDK or cross-app tracking.
- Account deletion is available in-app under **Konto → Konto dauerhaft löschen** and externally at the deletion URL above.
- The app communicates only with the first-party A+ Studio API over HTTPS for authenticated product functions.

## Privacy / data disclosures

The store declarations must match the production behavior at submission time.

### Collected
- Contact info: email address, account name, company/workspace name.
- User content: business descriptions, builder prompts, project requirements and generated project specifications.
- Identifiers: internal account/project identifiers.
- Diagnostics/security: server logs necessary for security, reliability and abuse prevention.

### Purposes
- App functionality and account management.
- AI app generation and requested product changes.
- Security, fraud/abuse prevention, support and service reliability.
- Store publishing only when the user explicitly requests it.

### Third-party processors used by the backend
- OpenAI for AI builder requests.
- GitHub only for repository functionality explicitly enabled for a project.
- Hosting/infrastructure providers for operation of the service.
- Apple/Google only when a store publishing operation is requested.
- Stripe applies to the separate web billing flow; **no Stripe/payment flow is exposed in mobile version 1.0**.

### Tracking
- No advertising identifier.
- No advertising SDK.
- No cross-app tracking in mobile version 1.0.

## Account deletion behavior

- Single-user workspaces owned by the deleting account are removed with their projects.
- Shared company workspaces are transferred to another member when available; the deleting user's identifying foreign keys are removed.
- The user account is then deleted.
- The public web deletion page lets a user who no longer has the app request deletion by email and informs support to verify identity.

## Android release requirements

- Build an Android App Bundle (`.aab`).
- Publisher-managed upload key; no keystore is committed to this repository.
- `compileSdkVersion` and `targetSdkVersion` are explicitly enforced at **36**.
- HTTPS API only; mixed content and WebView debugging are disabled in release configuration.

## iOS release requirements

- Build on Publisher Cloud Mac using **Xcode 26+**.
- Publisher-managed Apple Distribution certificate and App Store provisioning profile.
- iPhone-only target in version 1.0 to avoid claiming an untested iPad layout.
- `ITSAppUsesNonExemptEncryption = NO`.
- A privacy manifest is created during the native build for the app target; SDK manifests supplied by dependencies remain part of their packages.

## Monetization decision for 1.0

A+ Studio sells digital/cloud functionality on the web. To keep the first store release unambiguous under Apple and Google payment rules, the mobile 1.0 client does not expose billing, prices, Stripe checkout, subscription upgrade buttons or calls-to-action to external payment methods. If mobile purchasing is added later, implement the applicable store billing/IAP program before enabling that UI.
