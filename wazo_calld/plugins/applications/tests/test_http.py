# Copyright 2026 The Wazo Authors  (see the AUTHORS file)
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase
from unittest.mock import Mock, patch

from wazo_calld.plugins.applications.http import _BaseResource


class TestBaseApplicationResource(TestCase):
    @patch('wazo_calld.plugins.applications.http.Tenant')
    def test_application_lookup_is_scoped_to_request_tenant(self, Tenant):
        tenant_uuid = '038a676c-ae15-4a1f-9e1f-8d456635d15c'
        application_uuid = '6edbb9c3-3060-4aba-bf1a-1ba1d038136d'
        Tenant.autodetect.return_value.uuid = tenant_uuid
        service = Mock()
        resource = _BaseResource(service)

        resource._get_application(application_uuid)

        service.get_application.assert_called_once_with(
            application_uuid,
            tenant_uuid=tenant_uuid,
        )
