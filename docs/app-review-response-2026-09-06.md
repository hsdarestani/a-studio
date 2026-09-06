# App Review response — Guideline 2.5.2

Submission: `a207293e-b0fa-4e0e-b49b-b222be31a229`  
Rejected build: `1.0.0 (10)`  
Review date: `2026-09-06`  
Next submission target: `1.0.0 (11)`

## Reply to App Review

Hello App Review Team,

Thank you for the clarification regarding Guideline 2.5.2.

We have changed the iOS app so that it is no longer an app builder, app-preview environment, or a client for testing builds of other apps.

For the next submission, the App Store client is limited to an existing-customer project companion:

- users can sign in only with an existing account provisioned outside the app;
- the app only displays customer projects that were already created and assigned outside the app;
- users can view project status, project information, and existing coordination items;
- users can send questions or feedback to the human A+ Solution project team;
- project/application creation has been removed from the iOS UI and is rejected by the mobile backend;
- the previous local demo/review-preview flow has been removed;
- the app does not download, install, launch, preview, execute, generate, publish, or distribute other applications or executable builds;
- there are no app-store submission controls in the mobile client.

We have also updated the mobile marketing, privacy, terms, support, and App Store metadata so they describe only this existing-project customer-companion functionality.

Reviewer credentials for an existing account with an already assigned sample project will be provided in the App Review Information section in App Store Connect.

We respectfully request review of the new binary with these changes.

Best regards,
A+ Solution GmbH

## Internal verification checklist

- Mobile config mode: `customer_project_companion`
- Mobile account registration: disabled
- Mobile project creation: disabled server-side
- App-builder/new-app UI: absent
- Demo/review-preview UI: absent
- Generated-app preview/runtime: absent
- Publish/store-submission actions: unavailable
- Existing-project status and customer-team coordination: available
- In-app account deletion: available
- Legal/support pages: companion-only wording
- Store-positioning regression guard: fails on builder/preview terminology
