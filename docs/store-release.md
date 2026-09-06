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
A+ Studio ist der mobile Kundenbereich für bestehende A+ Solution Kundenprojekte.

Sehen Sie Projektstatus, Projektbeschreibung und offene Abstimmungspunkte. Senden Sie Fragen oder Feedback direkt an das zuständige Projektteam.

Der mobile Zugang ist ausschließlich für Projekte gedacht, die Ihrem bestehenden Kundenkonto bereits durch A+ Solution zugeordnet wurden. Konten und Projekte werden außerhalb der mobilen Anwendung eingerichtet.

Die App enthält keine Käufe oder Abonnements.

**Google Play description**  
A+ Studio ist der mobile Kundenbereich für bestehende A+ Solution Kundenprojekte.

Sehen Sie Projektstatus, Projektbeschreibung und offene Abstimmungspunkte. Senden Sie Fragen oder Feedback direkt an das zuständige Projektteam.

Der mobile Zugang ist ausschließlich für Projekte gedacht, die Ihrem bestehenden Kundenkonto bereits durch A+ Solution zugeordnet wurden. Konten und Projekte werden außerhalb der mobilen Anwendung eingerichtet.

Die mobile App enthält keine Käufe oder Abonnements.

**Keywords (Apple)**  
projekt,kundenbereich,status,abstimmung,feedback,team,business,produktivität

**Promotional text**  
Bestehende Kundenprojekte mobil im Blick behalten und mit dem Projektteam abstimmen.

## App Review notes

### Guideline 2.5.2 remediation — next submission target Build 11

The rejected version was 1.0.0 (10). The next submission is intended to use Build 11 with the App Store client deliberately limited to existing-customer project coordination.

- Project/application creation has been removed from the mobile UI.
- The local demo/review-demo flow has been removed from the mobile UI.
- The mobile client only lists projects that were created and assigned to the customer's account outside the app.
- Project detail shows neutral project progress, project information and existing coordination items.
- Users can submit a question, feedback item or coordination request to the human A+ Solution project team.
- The mobile backend enforces the same boundary: account registration and project creation are rejected, and no publishing/store-submission action is exposed.
- The App Store client does not contain an app-builder workflow, executable-content runtime, external-app preview, installation, download or distribution functionality.
- Mobile-specific marketing, privacy, terms and support pages describe only this existing-project customer feature set.

### Review access

- Provide the current reviewer username and password in **App Review Information** in App Store Connect.
- The reviewer account should contain at least one already assigned sample customer project.
- There is intentionally no demo or app-preview mode in the App Store binary.
- Existing A+ Solution customers sign in with accounts provisioned outside the mobile app.
- Account deletion is available in-app under **Konto → Konto dauerhaft löschen** and externally at the account deletion URL.

### Business model

- The iOS app contains no purchases, subscriptions, credits, pricing, feature unlocks or external purchase calls to action.
- Existing customers may have a separate B2B services relationship with A+ Solution GmbH, but the mobile app is only a project coordination surface.
- No paid digital content is unlocked in the iOS app.

## Privacy / data disclosures

The store declarations must match the production behavior at submission time.

### Collected
- Contact info: email address and account name for authenticated customer access.
- User content: existing customer project descriptions and questions/feedback submitted to the project team.
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
- The next App Store binary must be built only after the companion-only regression guard passes.
