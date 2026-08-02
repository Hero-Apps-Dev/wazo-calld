# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from unittest.mock import Mock

from ari.exceptions import ARINotFound

from wazo_calld.ari_ import CoreARI


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
