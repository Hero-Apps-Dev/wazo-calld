# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from unittest.mock import Mock, patch

from ari.exceptions import ARINotFound

from wazo_calld.ari_ import ARIClientProxy, CoreARI


class TestARIClientProxy(TestCase):
    @patch('wazo_calld.ari_.swaggerpy.http_client.SynchronousHttpClient')
    @patch('wazo_calld.ari_.ari.client.Client.__init__')
    def test_init_retries_until_all_required_repositories_are_available(
        self, client_init, http_client_class
    ):
        client = ARIClientProxy('http://asterisk:5039/ari', 'username', 'password')
        rejected_swagger = Mock()

        def initialize_repositories(*_args):
            if client_init.call_count == 1:
                client.swagger = rejected_swagger
                client.repositories = {
                    'applications': Mock(),
                    'channels': Mock(),
                }
            else:
                client.swagger = Mock()
                client.repositories = {
                    'amqp': Mock(),
                    'applications': Mock(),
                    'channels': Mock(),
                }

        client_init.side_effect = initialize_repositories
        client.on_channel_event = Mock()

        self.assertFalse(client.init())
        self.assertFalse(client._initialized)
        rejected_swagger.close.assert_called_once_with()

        self.assertTrue(client.init())
        self.assertTrue(client.init())
        self.assertTrue(client._initialized)
        self.assertEqual(client_init.call_count, 2)
        client.on_channel_event.assert_called_once_with(
            'ChannelDestroyed', client.repositories['channels'].on_hang_up
        )
        http_client_class.return_value.set_basic_auth.assert_called_with(
            'asterisk', 'username', 'password'
        )


class TestCoreARIApplicationRegistration(TestCase):
    def test_failed_subscription_does_not_block_retry(self):
        core_ari = CoreARI.__new__(CoreARI)
        core_ari._apps = []
        core_ari.client = Mock()
        core_ari.client.amqp.stasisSubscribe.side_effect = [
            RuntimeError('transient failure'),
            None,
        ]

        with self.assertRaises(RuntimeError):
            core_ari.register_application('wazo-app-test')

        self.assertEqual(core_ari._apps, [])

        core_ari.register_application('wazo-app-test')

        self.assertEqual(core_ari._apps, ['wazo-app-test'])
        self.assertEqual(core_ari.client.amqp.stasisSubscribe.call_count, 2)

    def test_cached_application_missing_from_asterisk_is_registered_again(self):
        core_ari = CoreARI.__new__(CoreARI)
        core_ari._apps = ['wazo-app-test']
        core_ari.client = Mock()
        core_ari.client.applications.get.side_effect = ARINotFound(Mock(), Mock())

        core_ari.register_application('wazo-app-test')

        core_ari.client.applications.get.assert_called_once_with(
            applicationName='wazo-app-test'
        )
        core_ari.client.amqp.stasisSubscribe.assert_called_once_with(
            applicationName='wazo-app-test'
        )
        core_ari.client.execute_app_registered_callbacks.assert_called_once_with(
            ['wazo-app-test']
        )
        self.assertEqual(core_ari._apps, ['wazo-app-test'])

    def test_cached_application_still_in_asterisk_is_not_registered_again(self):
        core_ari = CoreARI.__new__(CoreARI)
        core_ari._apps = ['wazo-app-test']
        core_ari.client = Mock()

        core_ari.register_application('wazo-app-test')

        core_ari.client.applications.get.assert_called_once_with(
            applicationName='wazo-app-test'
        )
        core_ari.client.amqp.stasisSubscribe.assert_not_called()
        core_ari.client.execute_app_registered_callbacks.assert_not_called()
