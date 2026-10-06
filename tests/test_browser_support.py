"""The keyboard event must wait for browser-side chooser interception readiness."""
import asyncio
import importlib.util
from pathlib import Path
import types
import unittest
spec=importlib.util.spec_from_file_location('picker_support',Path(__file__).with_name('browser_support.py'))
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)

class PickerOrderingTests(unittest.TestCase):
    def test_native_key_waits_for_interception_ack_and_no_activation_is_granted(self):
        events=[]
        class Session:
            def send(self,method,params):
                self_params=params
                self_test.assertIs(self_params['userGesture'],False)
                return {'result':{'value':'{"active":"choose","focused":true,"disabled":false}'}}
            def detach(self):events.append('detached')
        class Channel:
            async def send(self,method,timeout,params):
                self_test.assertEqual((method,params),('updateSubscription',{'event':'fileChooser','enabled':True}))
                events.append('enable-sent');await asyncio.sleep(0);events.append('enable-acknowledged')
        class Waiter:
            value='native chooser'
            def __enter__(self):events.append('waiter-armed');return self
            def __exit__(self,*args):pass
        def press(key):
            self.assertEqual(key,'Enter');self.assertEqual(events[-2:],['enable-acknowledged','waiter-armed']);events.append('native-key')
        self_test=self
        page=types.SimpleNamespace(context=types.SimpleNamespace(new_cdp_session=lambda _:Session()),
            _impl_obj=types.SimpleNamespace(_channel=Channel()),_sync=asyncio.run,
            keyboard=types.SimpleNamespace(press=press),expect_file_chooser=Waiter)
        self.assertEqual(support.keyboard_picker(page,'choose',[]),'native chooser')
        self.assertEqual(events,['enable-sent','enable-acknowledged','waiter-armed','native-key','detached'])
