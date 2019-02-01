import unittest
from fb_management import configuration
import time
import logging


class TestFB(unittest.TestCase):

    def setUp(self):
        # Configure the logging output
        logging.basicConfig(level=logging.INFO,
                            format='[%(asctime)s][%(levelname)s][%(threadName)-10s] %(message)s')

        self.conf = configuration.Configuration('config_1', 'EMB_RES')

    def test_fb_creation(self):
        self.conf.create_fb('E_SWITCH_1', 'E_SWITCH')

        self.assertEqual(2, len(self.conf.fb_dictionary))

        fb = self.conf.fb_dictionary['E_SWITCH_1']

        self.assertEqual(1, len(fb.input_events))
        self.assertEqual(2, len(fb.output_events))
        self.assertEqual(1, len(fb.input_vars))
        self.assertEqual(0, len(fb.output_vars))
        self.assertEqual(1, len(fb.input_events))

    def test_fb_connection(self):
        self.conf.create_fb('E_SWITCH_1', 'E_SWITCH')
        self.conf.create_fb('E_SWITCH_2', 'E_SWITCH')

        self.assertEqual(3, len(self.conf.fb_dictionary))

        self.conf.create_connection('E_SWITCH_1.EO0', 'E_SWITCH_2.EI')

        fb_1 = self.conf.fb_dictionary['E_SWITCH_1']
        self.assertEqual(1, len(fb_1.output_connections))

        fb_2 = self.conf.fb_dictionary['E_SWITCH_2']
        self.assertEqual(0, len(fb_2.output_connections))

        connection = fb_1.output_connections['EO0'][0]
        self.assertEqual('EI', connection.value_name)
        self.assertEqual(fb_2, connection.destination_fb)

    def test_fb_running(self):
        self.conf.create_fb('E_SWITCH_1', 'E_SWITCH')
        self.conf.start_work()

        fb = self.conf.fb_dictionary['E_SWITCH_1']
        fb.push_event('EI', True)

        time.sleep(0.01)

        # Validate the inputs
        event_type, value, is_watch = fb.input_events['EI']
        self.assertEqual(True, value)
        self.assertEqual('Event', event_type)
        var_type, value, is_watch = fb.input_vars['G']
        self.assertEqual(None, value)
        self.assertEqual('BOOL', var_type)

        # Validate the outputs
        event_type, value, is_watch = fb.output_events['EO0']
        self.assertEqual(True, value)
        self.assertEqual('Event', event_type)
        event_type, value, is_watch = fb.output_events['EO1']
        self.assertEqual(None, value)
        self.assertEqual('Event', event_type)

        self.conf.stop_work()

    def test_fb_flow(self):
        self.conf.create_fb('E_SWITCH_1', 'E_SWITCH')
        self.conf.create_fb('E_SWITCH_2', 'E_SWITCH')
        self.conf.create_connection('E_SWITCH_1.EO0', 'E_SWITCH_2.EI')
        self.conf.start_work()

        fb = self.conf.fb_dictionary['E_SWITCH_1']
        fb.push_event('EI', True)

        time.sleep(0.01)

        fb_2 = self.conf.fb_dictionary['E_SWITCH_2']

        # Validate the inputs
        event_type, value, is_watch = fb_2.input_events['EI']
        self.assertEqual(True, value)
        self.assertEqual('Event', event_type)
        var_type, value, is_watch = fb_2.input_vars['G']
        self.assertEqual(None, value)
        self.assertEqual('BOOL', var_type)

        # Validate the outputs
        event_type, value, is_watch = fb_2.output_events['EO0']
        self.assertEqual(True, value)
        self.assertEqual('Event', event_type)
        event_type, value, is_watch = fb_2.output_events['EO1']
        self.assertEqual(None, value)
        self.assertEqual('Event', event_type)

        self.conf.stop_work()