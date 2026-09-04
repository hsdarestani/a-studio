# A+ Studio iOS — Cloud App Builder execution boundary

Date: 2026-09-04
Bundle ID: `de.aplussolution.studio`

A+ Studio is an app builder. The iOS client intentionally keeps the core builder workflow while enforcing a strict execution boundary:

- Existing users can create a new app project from the iOS client.
- Project requirements are sent as ordinary JSON data to A+ Studio's backend.
- Generation and build work run only on A+ Studio cloud infrastructure.
- The iOS client may display project metadata, textual lifecycle status, and change-request status.
- Generated source code, IPA/APK binaries, repositories, deployment artifacts, `preview_url`, and `live_url` are not returned by the mobile API.
- The iOS client does not download, install, execute, embed, or launch generated application code.
- The iOS client does not expose generated-app WebView/iframe preview controls.
- The iOS client does not expose mobile publishing or App Store / Play Store submission controls.
- Account registration remains outside the iOS client.

## Mobile API capability contract

`/api/mobile/config/` identifies the product as `cloud_app_builder` and enables `project_creation` and `cloud_app_generation`, while explicitly disabling `code_download`, `local_code_execution`, `external_app_preview`, `mobile_publishing`, `store_status`, and `mobile_purchases`.

## Regression coverage

`core/test_mobile_api.py` verifies that cloud project creation works while executable/deployment fields are absent from all mobile project payloads. `scripts/store_positioning_check.py` prevents iOS UI or App Store copy from advertising generated-app execution, installation, download, preview-launch, or direct mobile store submission.

This boundary preserves A+ Studio's actual app-builder functionality without using the iOS app as a runtime or distribution mechanism for software created after App Review.