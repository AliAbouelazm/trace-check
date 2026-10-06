# Native keyboard picker: interception acknowledgment race

CI run `37538695406`, job `112526083105`, failed at the first `keyboard_picker(page, 'choose')`. Playwright 1.62.0 used bundled Chromium headless shell 151.0.7922.34. The button remained focused, visible and enabled. Trusted Enter and button-click events had active user activation; the forwarding input click occurred; no console error was recorded. Focus, disabled controls and missing activation did not explain the failure.

A local protocol probe reproduced the failure in full Chromium 151.0.7922.173 with both the existing proxy button and a native input. With passive `Page.fileChooserOpened` reporting enabled on a diagnostic CDP session, all 20 interactions emitted a real chooser event. Three timed out in Playwright (one proxy, two native). The raw events had valid frame and backend node IDs. Merely switching headless shell or changing button markup would not address the observed mechanism.

The failing proxy interaction's protocol sequence was:

1. 22:17:47.652: Playwright sent `Page.setInterceptFileChooserDialog(enabled=true)`.
2. 22:17:47.652: it sent trusted Enter key-down before the interception response.
3. 22:17:47.653: Chromium processed Enter and emitted `Page.fileChooserOpened` to the passive observer. Playwright's interception session missed that event.
4. 22:17:47.654: interception was acknowledged, too late for that interaction.
5. Playwright's waiter timed out; increasing its timeout could not recover a lost event.

The installed Playwright Python `_connection.py` implements first-listener subscription updates with `send_no_reply`. Its driver `updateSubscription` handler awaits the underlying browser interception change, but the caller does not await that handler before sending the next keyboard operation. The protocol trace demonstrates the resulting race in this environment.

`tests/browser_support.py` now explicitly awaits the pinned Playwright driver's `updateSubscription(fileChooser, enabled=true)` before adding the waiter and pressing Enter. The subsequent implicit enable is idempotent. This uses a documented-in-project private protocol hook tied to Playwright 1.62.0; a future dependency upgrade must revalidate it. It alters only test interception. It does not grant user activation, synthesize chooser events, change app controls, bypass a native picker, retry failed actions or increase timeouts.

The controlled post-fix probe exercised 20 proxy and 20 native interactions after a sample download. All 40 opened a chooser, and the protocol trace showed no Enter dispatch preceding the interception acknowledgment. The full browser suite retains real native keyboard chooser assertions. Exact-head CI still needs to verify the bundled shell. No raw benchmark or user-log content is used in this diagnostic.

The attempt to obtain the exact CI browser build locally was refused by the environment proxy for `cdn.playwright.dev`. No alternate host, browser download route or access-policy change was used. The local reproduction used the already-installed full Chromium and the same Playwright version.
