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
- Mobile positioning: **cloud app creation and project management** for existing A+ Studio accounts.

## German store copy

**Title**  
A+ Studio

**Apple subtitle**  
Apps in der Cloud erstellen

**Google short description**  
App-Projekte mobil starten und serverseitige Cloud-Erstellung verfolgen.

**Apple description**  
A+ Studio ist ein Cloud App Builder für bestehende A+ Studio Nutzer.

Starten Sie neue App-Projekte mobil, beschreiben Sie Zielgruppe und gewünschte Funktionen und verfolgen Sie den Status der serverseitigen Erstellung. Änderungswünsche können direkt einem bestehenden App-Projekt zugeordnet werden.

Die technische Generierung und Verarbeitung der App-Projekte findet auf der A+ Studio Cloud-Infrastruktur statt. Die mobile Anwendung lädt, installiert oder führt den generierten App-Code nicht aus und startet erzeugte Anwendungen nicht als ausführbare Preview innerhalb der App.

Konten werden außerhalb der mobilen Anwendung eingerichtet. Ein lokaler Demo-Modus auf der Anmeldeseite erklärt den vollständigen mobilen Workflow ohne Anmeldung. Die mobile App enthält keine Käufe oder Abonnements.

**Google Play description**  
A+ Studio ist ein Cloud App Builder für bestehende A+ Studio Nutzer.

Starten Sie neue App-Projekte mobil, beschreiben Sie Zielgruppe und gewünschte Funktionen und verfolgen Sie den Status der serverseitigen Erstellung. Änderungswünsche können direkt einem bestehenden App-Projekt zugeordnet werden.

Die technische Generierung und Verarbeitung der App-Projekte findet serverseitig in der A+ Studio Cloud statt. Die mobile Anwendung lädt oder installiert keine erzeugten App-Builds.

Konten werden außerhalb der mobilen Anwendung eingerichtet. Ein lokaler Demo-Modus erklärt den mobilen Workflow ohne Anmeldung. Die mobile App enthält keine Käufe oder Abonnements.

**Keywords (Apple)**  
app-projekte,cloud,builder,software,projekt,status,produkt,workflow,business

**Promotional text**  
Neue App-Projekte mobil starten und ihre serverseitige Erstellung in A+ Studio Cloud verfolgen.

## App Review notes

### Guideline 2.5.2 remediation for Build 8

Build 8 presents the product accurately as a cloud-based app creation service while keeping the iOS execution boundary explicit and enforced.

- A+ Studio is used to create app projects.
- Existing authenticated users can create a new app project in iOS by entering an app name, business type, language and functional requirements.
- Creating a project sends those inputs to A+ Studio's remote infrastructure and starts server-side generation there.
- The generated application's code and build artifacts remain on the remote service.
- The iOS client does **not** download, install or execute generated application code.
- The iOS client does **not** launch a generated customer application inside A+ Studio as an executable app preview/runtime.
- The mobile API deliberately omits generated-app `preview_url`, `live_url`, repository URLs, deployment artifacts and downloadable build files.
- The iOS app contains no controls for installing generated apps, downloading IPA/APK files, publishing a generated app, or submitting a generated app to an app store.
- Project change requests can be recorded from iOS for the remote project workflow/team; they do not execute downloaded code in the iOS process.
- Account registration is not offered in iOS. Existing A+ Studio accounts sign in.
- App Review can tap **Demo ansehen** on the sign-in screen to inspect the complete iOS product concept without credentials.
- The demo is bundled/local; it does not execute generated code and does not depend on a reviewer account.

This design keeps the iOS app self-contained while using ordinary HTTPS requests to control a remote cloud service. Generated software is never introduced into the A+ Studio iOS runtime.

### App-generation / distribution clarification

A+ Studio is itself a tool for creating customized app projects. Build 8 does not act as a software store or distribution channel. It does not install generated apps and it does not submit generated apps to a store from the iOS client. Any generated app intended for public distribution remains a separate product and must independently satisfy the applicable store rules and content-provider/developer-account requirements.

### Review access

- App Review does **not** need credentials to understand the complete iOS workflow.
- Tap **Demo ansehen** on the sign-in screen.
- The local demo shows: project creation input → remote/cloud generation → project status and change-request workflow.
- Existing users can sign in with accounts provisioned outside the iOS app.
- Account deletion is available in-app under **Konto → Konto dauerhaft löschen** and externally at the account deletion URL.

### Business model

- The iOS app contains no purchases, subscriptions, pricing, paid feature unlocks or external purchase calls to action.
- Account provisioning and any separate B2B commercial relationship are outside the iOS app.
- No paid digital content is sold or unlocked inside Build 8.

## Privacy / data disclosures

The store declarations must match the production behavior at submission time.

### Collected
- Contact info: email address and account name for authenticated access.
- User content: app-project names, business context, functional requirements and change requests.
- Identifiers: internal account/project identifiers.
- Diagnostics/security: server logs necessary for security, reliability and abuse prevention.

### Purposes
- Existing-account authentication.
- Creating and managing app projects on remote A+ Studio infrastructure.
- Displaying remote project-generation lifecycle state.
- Recording project change requests.
- Account management, support, security and service reliability.

### Mobile backend behavior
- Mobile account registration is disabled.
- Mobile app-project creation is enabled.
- App generation is started remotely on A+ Studio infrastructure.
- The mobile API does not expose executable generated-app previews, generated source repositories, deployment URLs, downloadable build artifacts or store-submission controls.
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
- Build 8 supersedes Build 7 so App Store metadata and the binary accurately describe A+ Studio as a cloud app-creation service while preserving the Guideline 2.5.2 local execution boundary.
