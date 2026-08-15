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
- Category: Business / Productivity
- Native technology: Capacitor 8 with a local first-party UI. There is no remote `server.url` WebView wrapper.
- Mobile positioning: **free project-companion app** for coordinating A+ Solution software projects.

## German store copy

**Title**  
A+ Studio

**Apple subtitle**  
Projekte mobil begleiten

**Google short description**  
Projektstatus, Briefings und Änderungswünsche mit A+ Solution mobil verwalten.

**Apple description**  
A+ Studio ist die mobile Begleit-App für Softwareprojekte mit A+ Solution.

Behalten Sie laufende Projekte im Blick, erfassen Sie Projektbriefings und senden Sie Änderungswünsche oder Fragen an das Projektteam. Bestehende Veröffentlichungsprozesse können als Status eingesehen werden.

Die mobile App dient ausschließlich der Projektkoordination. Sie erstellt, lädt, installiert oder führt keinen Programmcode und keine anderen Apps aus. App-Builds, ausführbare Previews und Store-Einreichungen werden nicht innerhalb der mobilen App erzeugt oder gestartet.

In A+ Studio für iOS gibt es keine Käufe, Abonnements, Credits, Preisangaben oder Freischaltungen.

**Google Play description**  
A+ Studio ist die mobile Begleit-App für Softwareprojekte mit A+ Solution.

Behalten Sie laufende Projekte im Blick, erfassen Sie Projektbriefings und senden Sie Änderungswünsche oder Fragen an das Projektteam. Bestehende Veröffentlichungsprozesse können als Status eingesehen werden.

Die mobile App dient ausschließlich der Projektkoordination. Sie erstellt, lädt, installiert oder führt keinen Programmcode und keine anderen Apps aus. App-Builds, ausführbare Previews und Store-Einreichungen werden nicht innerhalb der mobilen App erzeugt oder gestartet.

In der mobilen App gibt es keine Käufe, Abonnements, Credits, Preisangaben oder Freischaltungen.

**Keywords (Apple)**  
projekt,projektmanagement,software,status,briefing,anforderungen,team,business,produktivität

**Promotional text**  
Softwareprojekte mit A+ Solution mobil begleiten: Status, Briefings und Änderungswünsche an einem Ort.

## App Review notes

### What changed after the Guideline 2.5.2 rejection

The iOS client has been changed from a builder/preview workflow to a project-companion workflow.

- The app does **not** generate, download, install, preview, publish, or execute application code.
- Preview URLs, live app URLs, repository URLs, deployment URLs, and build controls are not exposed by the mobile API.
- Creating a project in iOS only creates a project briefing/workspace; it does not start code generation or provisioning.
- Sending a project change request only records a request for the A+ Solution project team; it does not invoke an AI builder or any code-generation task.
- Mobile publish and store-submission actions are disabled at the API level, not merely hidden in the UI.
- Existing distribution/submission information, when present, is displayed read-only as project status.
- The local **Demo ansehen** flow is fully reviewable without an account and demonstrates the same companion-only feature set.

### Review access

- A pre-existing paid account is **not required** to review the app.
- The login screen contains a local **Demo ansehen** flow, which works without credentials or backend data.
- Reviewers may also create a free companion account in-app.
- Account deletion is available in-app under **Konto → Konto dauerhaft löschen** and externally at the deletion URL above.
- Backend services used by authenticated project-companion functionality are available over HTTPS.

### Business model — answers to App Review Guideline 2.1(b)

1. **Who are the users that will use paid services?**  
   A+ Solution business customers and their authorized project contacts may have a separate commercial software/project-services relationship with A+ Solution GmbH. The iOS app itself is free and can also be reviewed or used as a project companion without purchasing anything in the app.

2. **Where can users purchase the services that can be accessed in the app?**  
   There is no purchase flow in the iOS app. Any separate commercial B2B project/service agreement with A+ Solution GmbH is handled outside the App Store and outside the iOS app.

3. **What specific types of previously purchased services can a user access in the app?**  
   The iOS app does not unlock paid digital content. It provides project-companion functionality: project status, project briefings, change/support requests, and read-only distribution status for a user's A+ Solution project.

4. **What paid content, subscriptions, or features are unlocked within the app that do not use In-App Purchase?**  
   None. There are no paid content items, subscriptions, premium mobile features, or feature unlocks in the iOS app.

5. **How can users purchase credits and what do they unlock?**  
   They cannot. Credits are not shown, sold, granted, consumed, or usable in the iOS app. The iOS mobile API does not return plan or credit entitlements.

### Payments / entitlements

- No In-App Purchase is implemented because the iOS app does not sell or unlock digital content or functionality.
- No Stripe/payment flow, pricing page, upgrade button, subscription CTA, credit balance, or external purchase CTA is exposed in the mobile app.
- Any separate web/business systems are not linked from the iOS app as a purchase mechanism.

## Privacy / data disclosures

The store declarations must match the production behavior at submission time.

### Collected
- Contact info: email address, account name, company/workspace name.
- User content: project descriptions, requirements, change requests and support/project notes.
- Identifiers: internal account/project identifiers.
- Diagnostics/security: server logs necessary for security, reliability and abuse prevention.

### Purposes
- Project coordination and account management.
- Processing project briefings and change/support requests.
- Security, fraud/abuse prevention, support and service reliability.
- Displaying existing project/distribution status when applicable.

### Mobile backend behavior
- Mobile project creation stores a project briefing only; it does not trigger AI generation or provisioning.
- Mobile change requests are stored for project-team review; they do not invoke code generation.
- The mobile API does not expose generated preview/live/repository URLs.
- The mobile API blocks publish and store-submission actions.
- The mobile client has no advertising SDK, payment SDK, or cross-app tracking.

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
- `ITSAppUsesNonExemptEncryption = NO`.
- A privacy manifest is created during the native build for the app target; SDK manifests supplied by dependencies remain part of their packages.
- Before resubmission, increment the App Store build number from rejected build **3** to a new build number (for example **4**).

## Monetization decision for mobile 1.0

The mobile 1.0 product is a free project-companion app. It has no billing, prices, payment links, subscriptions, credits, premium mobile features, or purchase CTAs. Any commercial B2B relationship with A+ Solution GmbH is separate from the mobile app. If paid digital functionality is ever introduced into the iOS app, the applicable App Store payment rules must be implemented before that functionality is enabled.
