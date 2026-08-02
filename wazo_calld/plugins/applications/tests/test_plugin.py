# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from ..plugin import ApplicationRegistrationReconciler


class TestApplicationRegistrationReconciler(TestCase):
    def test_retries_after_a_transient_failure(self):
        attempts = []
        reconciler = None

        def callback():
            attempts.append(None)
            if len(attempts) == 1:
                raise RuntimeError('transient failure')
            reconciler._should_stop.set()

        reconciler = ApplicationRegistrationReconciler(callback, interval=0)

        reconciler._run()

        self.assertEqual(len(attempts), 2)

    def test_stop_before_start_is_safe(self):
        reconciler = ApplicationRegistrationReconciler(lambda: None)

        reconciler.stop()

        self.assertTrue(reconciler._should_stop.is_set())
