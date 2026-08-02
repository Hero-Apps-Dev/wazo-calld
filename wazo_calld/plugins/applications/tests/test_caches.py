# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from unittest.mock import Mock

import requests

from ..caches import ConfdApplicationsCache


class TestConfdApplicationsCache(TestCase):
    def setUp(self):
        self.confd = Mock()
        self.cache = ConfdApplicationsCache(self.confd)
        self.created = Mock()
        self.updated = Mock()
        self.deleted = Mock()
        self.cache.created_subscribe(self.created)
        self.cache.updated_subscribe(self.updated)
        self.cache.deleted_subscribe(self.deleted)

    def test_refresh_initializes_without_emitting_changes(self):
        application = {'uuid': 'application-1', 'name': 'initial'}
        self.confd.applications.list.return_value = {'items': [application]}

        result = self.cache.refresh()

        self.assertEqual(result, [application])
        self.created.assert_not_called()
        self.updated.assert_not_called()
        self.deleted.assert_not_called()

    def test_refresh_fetches_confd_on_every_call(self):
        self.confd.applications.list.side_effect = [
            {'items': [{'uuid': 'application-1'}]},
            {'items': [{'uuid': 'application-2'}]},
        ]

        self.cache.refresh()
        result = self.cache.refresh()

        self.assertEqual(result, [{'uuid': 'application-2'}])
        self.assertEqual(self.confd.applications.list.call_count, 2)

    def test_failed_refresh_preserves_last_known_applications(self):
        application = {'uuid': 'application-1'}
        self.confd.applications.list.side_effect = [
            {'items': [application]},
            requests.ConnectionError(),
        ]
        self.cache.refresh()

        with self.assertRaises(requests.ConnectionError):
            self.cache.refresh()

        self.assertEqual(self.cache.list(), [application])

    def test_refresh_emits_authoritative_changes(self):
        unchanged = {'uuid': 'application-1', 'name': 'unchanged'}
        old = {'uuid': 'application-2', 'name': 'old'}
        deleted = {'uuid': 'application-3', 'name': 'deleted'}
        new = {'uuid': 'application-2', 'name': 'new'}
        created = {'uuid': 'application-4', 'name': 'created'}
        self.cache._cache = {
            unchanged['uuid']: unchanged,
            old['uuid']: old,
            deleted['uuid']: deleted,
        }
        self.confd.applications.list.return_value = {'items': [unchanged, new, created]}

        result = self.cache.refresh()

        self.assertCountEqual(result, [unchanged, new, created])
        self.created.assert_called_once_with(created)
        self.updated.assert_called_once_with(old, new)
        self.deleted.assert_called_once_with(deleted)
