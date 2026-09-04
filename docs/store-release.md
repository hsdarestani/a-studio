# A+ Studio — Store release profile

## Identity

- Product: **A+ Studio**
- Developer/business: **A+ Solution GmbH**
- Version: **1.0.0**
- Android package: `de.aplussolution.studio`
- iOS bundle ID: `de.aplussolution.studio`
- Mobile marketing URL: `https://studio.aplus-solution.de/mobile/`
- Mobile privacy policy: `https://studio.aplus-solution.de/mobile/privacy/`
- Mobile support URL: `https://studio.aplus-solution.de/mobile/support/`
- Mobile terms: `https://studio.aplus-solution.de/mobile/terms/`
- Account deletion URL: `https://studio.aplus-solution.de/account-deletion/`
- Category: Business / Productivity
- Native technology: Capacitor 8 with a local first-party UI. There is no remote `server.url` WebView wrapper.
- Mobile positioning: **customer project coordination** for already assigned A+ Solution customer projects.

## German store copy

**Title**  
A+ Studio

**Apple subtitle**  
Kundenprojekte mobil

**Google short description**  
Projektstatus und Abstimmung für bestehende A+ Solution Kundenprojekte.

**Apple description**  
A+ Studio ist der mobile Kundenbereich für bestehende A+ Solution Projekte.

Sehen Sie Projektfortschritt, Projektbeschreibung und offene Abstimmungspunkte und senden Sie Fragen oder Feedback an das Projektteam.

Der mobile Zugang ist ausschließlich für bereits zugeordnete Kundenprojekte gedacht. Konten und Projekte werden außerhalb der mobilen App durch das A+ Solution Projektteam eingerichtet. Für die unverbindliche Ansicht des mobilen Funktionsumfangs steht direkt auf der Anmeldeseite ein Demo-Modus bereit.

Die App enthält keine Käufe oder Abonnements.

**Google Play description**  
A+ Studio ist der mobile Kundenbereich für bestehende A+ Solution Projekte.

Sehen Sie Projektfortschritt, Projektbeschreibung und offene Abstimmungspunkte und senden Sie Fragen oder Feedback an das Projektteam.

Der mobile Zugang ist ausschließlich für bereits zugeordnete Kundenprojekte gedacht. Konten und Projekte werden außerhalb der mobilen App durch das A+ Solution Projektteam eingerichtet. Ein Demo-Modus ist direkt auf der Anmeldeseite verfügbar.

Die mobile App enthält keine Käufe oder Abonnements.

**Keywords (Apple)**  
projekt,kundenbereich,status,abstimmung,feedback,team,business,produktivität

**Promotional text**  
Bestehende Kundenprojekte mobil im Blick behalten und mit dem Projektteam abstimmen.

## App Review notes

### Guideline 2.5.2 remediation for Build 7

Build 7 has been deliberately reduced to an existing-customer project coordination client.

- App Review can tap **Demo ansehen** on the sign-in screen and evaluate the complete iOS feature set locally without an account.
- There is no account registration in the iOS app.
- There is no project creation in the iOS app.
- The mobile client displays only projects already assigned to an existing customer account.
- Project detail contains the project name, description, neutral progress state and customer coordination items.
- Sending a question or feedback item records a customer request for the human A+ Solution project team.
- The mobile API enforces the same boundaries server-side.
- The iOS client does not contain software creation, executable-content, external-app runtime, distribution or store-control functionality.
- Mobile-specific marketing, privacy, terms and support pages describe only this customer-project feature set.

### Review access

- App Review does **not** need credentials.
- Tap **Demo ansehen** on the sign-in screen.
- The demo is local and does not depend on backend account data.
- Existing A+ Solution customers may sign in with accounts provisioned by the project team outside the mobile app.
- Account deletion is available in-app under **Konto → Konto dauerhaft löschen** and externally at the account deletion URL.

### Business model

- The iOS app contains no purchases, subscriptions, credits, pricing, feature unlocks or external purchase calls to action.
- Existing customers may have a separate B2B services relationship with A+ Solution GmbH, but the mobile app is only a project coordination surface.
- No paid digital content is unlocked in the iOS app.

## Privacy / data disclosures

The store declarations must match the production behavior at submission time.

### Collected
- Contact info: email address and account name for authenticated customer access.
- User content: customer project descriptions and questions/feedback submitted to the project team.
- Identifiers: internal account/project identifiers.
- Diagnostics/security: server logs necessary for security, reliability and abuse prevention.

### Purposes
- Existing customer authentication.
- Displaying already assigned project information and progress.
- Customer/project-team coordination.
- Account management, support, security and service reliability.

### Mobile backend behavior
- Mobile account registration is disabled.
- Mobile project creation is disabled.
- The mobile API exposes only neutral customer project progress and coordination data.
- Customer messages are stored as requests for human project-team review.
- The mobile client has no advertising SDK, payment SDK or cross-app tracking.

### Tracking
- No advertising identifier.
- No advertising SDK.
- No cross-app tracking in mobile version 1.0.

## Account deletion behavior

- Single-user workspaces owned by the deleting account are removed with their projects.
- Shared company workspaces are transferred to another member when available; the deleting user's identifying foreign keys are removed.
- The user account is then deleted.
- The public deletion page lets a user who no longer has the app request deletion by email and informs support to verify identity.

## iOS release requirements

- Build on Publisher Cloud Mac using **Xcode 26+**.
- Publisher-managed Apple Distribution certificate and App Store provisioning profile.
- `ITSAppUsesNonExemptEncryption = NO`.
- A privacy manifest is created during the native build for the app target.
- Build 7 is the remediation binary for the rejected `1.0.0 (6)` submission.
