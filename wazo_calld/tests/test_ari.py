# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from unittest.mock import Mock

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
