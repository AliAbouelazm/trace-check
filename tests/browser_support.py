"""Browser identity and passive native-keyboard diagnostics for local/CI parity."""
import importlib.metadata
import json
import os


def launch_chromium(playwright):
    # CI uses the browser revision installed by the pinned Playwright package.
    # Local overrides must be explicit; silently picking a system binary masks drift.
    executable = os.environ.get('CHROMIUM_PATH')
    browser = playwright.chromium.launch(headless=True, executable_path=executable)
    print(json.dumps({'playwright': importlib.metadata.version('playwright'),
                      'browser_version': browser.version, 'headless': True,
                      'executable': executable or 'Playwright bundled chromium-headless-shell'}), flush=True)
    return browser


PICKER_EVENTS = """(() => {
  window.__pickerEvents = [];
  for (const type of ['keydown', 'keyup', 'click', 'focusin', 'focusout']) {
    document.addEventListener(type, event => {
      window.__pickerEvents.push({type, key: event.key || null,
        target: event.target.id || event.target.tagName, trusted: event.isTrusted,
        active: document.activeElement?.id, focused: document.hasFocus(),
        activation: navigator.userActivation.isActive,
        disabled: Boolean(event.target.disabled)});
      if (window.__pickerEvents.length > 30) window.__pickerEvents.shift();
    }, true);
  }
})();"""


def arm_file_chooser(page):
    # Playwright 1.62 sends first-listener updateSubscription without awaiting
    # Page.setInterceptFileChooserDialog. Input can overtake its acknowledgment.
    # Arm through the pinned driver protocol BEFORE adding the waiter, so the
    # subsequent fire-and-forget enable is idempotent. This changes only test
    # interception, not page activation, app handlers or native key events.
    page._sync(page._impl_obj._channel.send(
        'updateSubscription', None, {'event':'fileChooser','enabled':True}))


def keyboard_picker(page, button_id, console_messages):
    session = page.context.new_cdp_session(page)
    def snapshot():
        # Playwright page.evaluate normally sets userGesture=true. A diagnostic
        # must not grant activation and accidentally make a failing picker work.
        result = session.send('Runtime.evaluate', {
            'expression': """JSON.stringify({active:document.activeElement?.id,
              focused:document.hasFocus(),visibility:document.visibilityState,
              activation:navigator.userActivation.isActive,
              disabled:document.getElementById(%s).disabled,
              fileDisabled:document.getElementById('file').disabled,
              events:window.__pickerEvents || []})""" % json.dumps(button_id),
            'userGesture': False, 'returnByValue': True})
        return json.loads(result['result']['value'])
    before = snapshot()
    try:
        assert before['active'] == button_id and before['focused'] and not before['disabled'], before
        arm_file_chooser(page)
        with page.expect_file_chooser() as chooser:
            page.keyboard.press('Enter')
        return chooser.value
    except Exception as error:
        evidence = {'button':button_id,'before':before,'after':snapshot(),'console':console_messages[-10:]}
        raise AssertionError('Native keyboard file picker failed: ' + json.dumps(evidence)) from error
    finally:
        session.detach()
