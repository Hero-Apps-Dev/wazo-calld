# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from unittest.mock import Mock, patch

from wazo_calld.plugins.applications.exceptions import NoSuchApplication, NoSuchCall
from wazo_calld.plugins.applications.services import ApplicationService


class TestApplicationServiceSnoop(TestCase):
    application_uuid = '6edbb9c3-3060-4aba-bf1a-1ba1d038136d'
    tenant_uuid = '038a676c-ae15-4a1f-9e1f-8d456635d15c'
    supervisor_call_id = 'supervisor-call'
    target_call_id = 'target-call'

    def setUp(self):
        self.ari = Mock()
        self.bridge = self.ari.bridges.createWithId.return_value
        self.snoop_channel = self.ari.channels.snoopChannel.return_value
        self.snoop_channel.id = 'snoop-channel'
        self.confd_apps = Mock()
        self.application = {
            'uuid': self.application_uuid,
            'name': f'wazo-app-{self.application_uuid}',
            'tenant_uuid': self.tenant_uuid,
            'channel_ids': [self.supervisor_call_id],
        }
        self.service = ApplicationService(
            self.ari,
            Mock(),
            Mock(),
            Mock(),
            self.confd_apps,
            Mock(),
        )

    def test_snoop_accepts_same_tenant_target_outside_application(self):
        self._target_channel(self.tenant_uuid)

        snoop = self.service.snoop_create(
            self.application,
            self.target_call_id,
            self.supervisor_call_id,
            'none',
        )

        self.assertEqual(snoop.snooped_call_id, self.target_call_id)
        self.assertEqual(snoop.snooping_call_id, self.supervisor_call_id)
        self.ari.channels.snoopChannel.assert_called_once_with(
            channelId=self.target_call_id,
            spy='both',
            whisper='none',
            app=self.application['name'],
        )

    def test_snoop_rejects_target_owned_by_another_tenant(self):
        self._target_channel('54c68273-7876-42b9-a6d0-ef7241183740')

        with self.assertRaises(NoSuchCall):
            self.service.snoop_create(
                self.application,
                self.target_call_id,
                self.supervisor_call_id,
                'none',
            )

        self.ari.channels.snoopChannel.assert_not_called()

    def test_snoop_rejects_external_target_without_tenant_ownership(self):
        self._target_channel(None)

        with self.assertRaises(NoSuchCall):
            self.service.snoop_create(
                self.application,
                self.target_call_id,
                self.supervisor_call_id,
                'none',
            )

        self.ari.channels.snoopChannel.assert_not_called()

    def test_snoop_rejects_application_target_with_foreign_tenant_metadata(self):
        self.application['channel_ids'] = [
            *self.application['channel_ids'],
            self.target_call_id,
        ]
        self._target_channel('54c68273-7876-42b9-a6d0-ef7241183740')

        with self.assertRaises(NoSuchCall):
            self.service.snoop_create(
                self.application,
                self.target_call_id,
                self.supervisor_call_id,
                'none',
            )

        self.ari.channels.snoopChannel.assert_not_called()

    @patch('wazo_calld.plugins.applications.services.CallFormatter')
    def test_originate_sets_application_tenant_on_supervisor_leg(self, CallFormatter):
        self.service._amid.action.return_value = [
            {
                'Event': 'ListDialplan',
                'Priority': '1',
            }
        ]
        self.service._amid.command.return_value = {'response': []}
        self.ari.channels.originate.return_value.json = {
            'name': 'Local/1000@internal-00000001;1'
        }
        CallFormatter.return_value.from_channel.return_value = Mock()

        self.service.originate(
            self.application,
            None,
            '1000',
            'internal',
            True,
            'Sidekick Voice Listen',
            '1000',
            variables={'heronet_source': 'sidekick_voice_supervisor'},
        )

        originate_variables = self.ari.channels.originate.call_args.kwargs['variables'][
            'variables'
        ]
        self.assertEqual(
            originate_variables['WAZO_TENANT_UUID'],
            self.tenant_uuid,
        )
        self.assertEqual(
            originate_variables['heronet_source'],
            'sidekick_voice_supervisor',
        )

    def _target_channel(self, tenant_uuid):
        target_channel = Mock()
        target_channel.json = {
            'channelvars': {
                'WAZO_TENANT_UUID': tenant_uuid,
            }
        }
        self.ari.channels.get.return_value = target_channel


class TestApplicationServiceTenantOwnership(TestCase):
    application_uuid = '6edbb9c3-3060-4aba-bf1a-1ba1d038136d'
    tenant_uuid = '038a676c-ae15-4a1f-9e1f-8d456635d15c'

    def setUp(self):
        self.ari = Mock()
        self.ari.applications.get.return_value = {
            'name': f'wazo-app-{self.application_uuid}',
            'channel_ids': [],
        }
        self.confd_apps = Mock()
        self.confd_apps.get.return_value = {
            'destination': None,
            'tenant_uuid': self.tenant_uuid,
        }
        self.service = ApplicationService(
            self.ari,
            Mock(),
            Mock(),
            Mock(),
            self.confd_apps,
            Mock(),
        )

    def test_get_application_accepts_owning_tenant(self):
        application = self.service.get_application(
            self.application_uuid,
            tenant_uuid=self.tenant_uuid,
        )

        self.assertEqual(application['tenant_uuid'], self.tenant_uuid)

    def test_get_application_hides_resource_from_another_tenant(self):
        with self.assertRaises(NoSuchApplication):
            self.service.get_application(
                self.application_uuid,
                tenant_uuid='54c68273-7876-42b9-a6d0-ef7241183740',
            )
