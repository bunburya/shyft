import unittest
from datetime import datetime

from shyft.message import MessageBus, Message, CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET


class MessagingTestCase(unittest.TestCase):


    def test_01_add_get_messages(self):
        """Test basic adding and fetching of messages."""
        mbus1 = MessageBus()
        msg1 = mbus1.add_message(
            'Test message 1 (defaults).'
        )
        self.assertEqual(msg1.text, 'Test message 1 (defaults).')
        self.assertEqual(msg1.severity, INFO)
        self.assertIsNone(msg1.views)

        msg2 = mbus1.add_message(
            'Test message 2 (error).',
            severity=ERROR,
            timestamp=datetime(2020, 1, 1, 12, 43, 42)
        )
        self.assertEqual(msg2.text, 'Test message 2 (error).')
        self.assertEqual(msg2.severity, ERROR)
        self.assertIsNone(msg2.views)
        self.assertEqual(msg2.timestamp, datetime(2020, 1, 1, 12, 43, 42))

        msg3 = mbus1.add_message(
            'Test message 3 (debug, test_view, test_view2).',
            severity=DEBUG,
            views={'test_view', 'test_view2'}
        )
        self.assertEqual(msg3.text, 'Test message 3 (debug, test_view, test_view2).')
        self.assertEqual(msg3.severity, DEBUG)
        self.assertSetEqual(msg3.views, {'test_view', 'test_view2'})

        mbus2 = mbus1.copy()
        self.assertEqual(mbus1, mbus2)

        # Get with defaults
        messages = mbus1.get_messages(discard=False)
        self.assertListEqual(messages, [msg1, msg2])

        # Get only ERROR and above
        messages = mbus1.get_messages(severity=ERROR, discard=False)
        self.assertListEqual(messages, [msg2])

        # Get only exactly INFO
        messages = mbus1.get_messages(exact_severity=True, discard=False)
        self.assertListEqual(messages, [msg1])

        # Get all severities
        messages = mbus1.get_messages(severity=NOTSET, discard=False)
        self.assertListEqual(messages, [msg1, msg2, msg3])

        # Get DEBUG and higher but only for 'test_view3' (ie, exclude msg3)
        messages = mbus1.get_messages(severity=DEBUG, view='test_view3', discard=False)
        self.assertListEqual(messages, [msg1, msg2])

        # Get DEBUG and higher for 'test_view2' (ie, everything).
        messages = mbus1.get_messages(severity=DEBUG, view='test_view2', discard=False)
        self.assertListEqual(messages, [msg1, msg2, msg3])

        # Get only exactly INFO and discard it
        mbus1.get_messages(exact_severity=True, discard_less_severe=False)
        self.assertListEqual(mbus1._messages, [msg2, msg3])

        mbus2.get_messages(discard_less_severe=True)
        self.assertListEqual(mbus2._messages, [])




if __name__ == '__main__':
    unittest.main()
