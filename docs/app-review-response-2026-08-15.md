# App Review response — 2026-08-15

Submission: `6b4c9437-b7fb-4151-99e7-dec41d4c4934`
Rejected build: `1.0.0 (3)`
Replacement build: `1.0.0 (4)` or later

## Important product distinction

A+ Studio has two deliberately different surfaces:

- **A+ Studio Web** (`studio.aplus-solution.de`) is the full browser-based software project platform. Existing business customers may use web-only functionality such as the AI builder workflow, previews, project credits, and managed publishing services there.
- **A+ Studio for iOS** is a **free project-companion app only**. It does not expose the web builder, previews, credits, billing, code generation, build execution, publishing controls, or purchase calls-to-action.

The existence of the separate web product must not be hidden from App Review. The iOS app is positioned under the free stand-alone companion model described in App Review Guideline 3.1.3(f): there is no purchase in the iOS app and no call to action in the iOS app to purchase outside the app.

## Reply to App Review

Hello App Review Team,

Thank you for the detailed feedback. We have substantially revised the iOS application in response to Guideline 2.5.2.

A+ Studio for iOS is now a free project-companion application only. It does not generate, download, install, preview, publish, or execute application code or other apps. Creating a project in the iOS app creates only a project briefing/workspace. Change requests are recorded for the A+ Solution project team and do not trigger AI code generation or build tasks. Publishing and store-submission actions are disabled at the mobile API level as well as removed from the iOS user interface.

For clarity, A+ Studio also has a separate browser-based web product at studio.aplus-solution.de. The web product may provide existing business customers with web-only project-development functionality such as AI-assisted development workflows, previews, project credits, and managed publishing services. Those web-only functions are not exposed, unlocked, previewed, or purchasable in the iOS app, and the iOS app contains no link or call to action directing users to purchase them.

Regarding the business-model questions:

1. **Who are the users that will use the paid services in the app?**
   No paid service is sold or unlocked in the iOS app. Users are A+ Solution business customers and authorized project contacts who use the free iOS app to coordinate an existing software project.

2. **Where can users purchase the services that can be accessed in the app?**
   There is no purchase flow in the iOS app. A+ Solution may have a separate B2B commercial relationship with customers outside the app. The iOS app does not direct users to any external purchase flow.

3. **What specific types of previously purchased services can a user access in the app?**
   The iOS app provides project-companion functionality only: project status, project briefings, change/support requests, and read-only distribution status. It does not expose the web AI builder, executable previews, code repositories, build downloads, project credits, or publishing controls.

4. **What paid content, subscriptions, or features are unlocked within the app that do not use In-App Purchase?**
   None. There are no paid content items, subscriptions, premium mobile features, or paid feature unlocks in the iOS app.

5. **How can users purchase credits and what do they unlock?**
   Credits cannot be purchased, displayed, granted, consumed, or used in the iOS app. Credits are part of the separate web product only and do not unlock functionality in the iOS app.

The iOS app contains no pricing, subscriptions, payment links, purchase buttons, external purchase calls-to-action, or links to the web builder/billing flow.

We also updated the App Store metadata and the local review demo so that they accurately describe and demonstrate only the companion functionality.

Please review replacement build 1.0.0 (4) or later.

Thank you.

## Resubmission checklist

- Use a new build number (`4` or later).
- App Store screenshots must show only the companion UI.
- App Store description/subtitle/keywords must use the companion positioning.
- Do not include any screenshot showing Builder, Preview, Credits, Billing, Build, Publish, or Store Submission controls.
- Confirm the iOS binary contains no web-builder URL, billing URL, or external purchase CTA.
- Keep the web platform operational; do not disguise or remove it solely for review.
- Be transparent in Review Notes that the web platform and iOS companion have different feature sets.
