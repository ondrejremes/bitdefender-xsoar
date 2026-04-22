import pytest
from unittest.mock import MagicMock, patch
from BitdefenderGravityZoneAPI import (
    GravityZoneClient,
    test_module as _test_module,
    bd_endpoint_list_command,
    bd_endpoint_get_command,
    bd_endpoint_isolate_command,
    bd_endpoint_deisolate_command,
    bd_scan_create_command,
    bd_task_status_command,
    bd_task_delete_command,
    bd_incident_note_update_command,
    bd_incident_status_change_command,
    bd_blocklist_add_command,
    bd_blocklist_get_command,
    bd_blocklist_remove_command,
    bd_quarantine_list_command,
    bd_quarantine_item_remove_command,
    bd_quarantine_item_restore_command,
    bd_license_info_command,
    bd_push_settings_get_command,
    bd_push_settings_set_command,
    bd_push_test_command,
)

BASE_URL = 'https://cloud.gravityzone.bitdefender.com'
API_KEY = 'test-api-key'

MOCK_ENDPOINT = {
    'id': 'ep-001',
    'name': 'WIN-TESTPC',
    'ip': '192.168.1.10',
    'operatingSystemVersion': 'Windows 10',
    'isManaged': True,
    'groupId': 'grp-001',
    'companyId': 'cmp-001',
}

MOCK_ENDPOINT_DETAIL = {
    **MOCK_ENDPOINT,
    'state': 1,
    'machineType': 1,
    'lastSeen': '2024-01-15T10:00:00Z',
    'agent': {
        'productVersion': '7.9.9',
        'licensed': 1,
        'isSignatureOutdated': False,
    },
}


@pytest.fixture
def client():
    return GravityZoneClient(BASE_URL, API_KEY, verify=False, proxy=False)


def mock_call(client: GravityZoneClient, response):
    client._call = MagicMock(return_value=response)
    return client


class TestTestModule:
    def test_ok(self, client):
        mock_call(client, {'subscriptionType': 2, 'expiryDate': '2025-12-31', 'usedSlots': 10, 'totalSlots': 50})
        assert _test_module(client) == 'ok'

    def test_api_error_propagates(self, client):
        client._call = MagicMock(side_effect=Exception('Auth failed'))
        with pytest.raises(Exception, match='Auth failed'):
            _test_module(client)


class TestEndpointList:
    def test_returns_endpoints(self, client):
        mock_call(client, {'items': [MOCK_ENDPOINT], 'total': 1})
        results = bd_endpoint_list_command(client, {})
        assert len(results) == 2  # Bitdefender.Endpoint + Endpoint
        bd_result = results[0]
        assert bd_result.outputs[0]['ID'] == 'ep-001'
        assert bd_result.outputs[0]['Name'] == 'WIN-TESTPC'

    def test_empty_result(self, client):
        mock_call(client, {'items': [], 'total': 0})
        results = bd_endpoint_list_command(client, {})
        assert results[0].outputs == []

    def test_passes_filters_to_client(self, client):
        mock_call(client, {'items': [], 'total': 0})
        client.get_endpoints_list = MagicMock(return_value={'items': [], 'total': 0})
        bd_endpoint_list_command(client, {'parent_id': 'p1', 'name_filter': 'WIN*', 'page': '2', 'per_page': '10'})
        client.get_endpoints_list.assert_called_once_with(
            parent_id='p1', is_managed=None, page=2, per_page=10, name_filter='WIN*'
        )


class TestEndpointGet:
    def test_returns_details(self, client):
        mock_call(client, MOCK_ENDPOINT_DETAIL)
        results = bd_endpoint_get_command(client, {'endpoint_id': 'ep-001'})
        bd_result = results[0]
        assert bd_result.outputs['ID'] == 'ep-001'
        assert bd_result.outputs['State'] == 1
        assert bd_result.outputs['Agent']['ProductVersion'] == '7.9.9'

    def test_not_found(self, client):
        mock_call(client, None)
        results = bd_endpoint_get_command(client, {'endpoint_id': 'missing'})
        assert 'not found' in results[0].readable_output


class TestEndpointIsolate:
    def test_v10_boolean_response(self, client):
        mock_call(client, True)
        result = bd_endpoint_isolate_command(client, {'endpoint_id': 'ep-001'})
        assert result.outputs['Type'] == 'Isolate'
        assert result.outputs['EndpointID'] == 'ep-001'

    def test_v11_task_array_response(self, client):
        mock_call(client, [{'taskId': 'task-123', 'endpointId': 'ep-001'}])
        result = bd_endpoint_isolate_command(client, {'endpoint_id': 'ep-001'})
        assert result.outputs['ID'] == 'task-123'
        assert result.outputs['Type'] == 'Isolate'


class TestEndpointDeisolate:
    def test_creates_task(self, client):
        mock_call(client, True)
        result = bd_endpoint_deisolate_command(client, {'endpoint_id': 'ep-001'})
        assert result.outputs['Type'] == 'Deisolate'


class TestScanCreate:
    def test_returns_task_id(self, client):
        mock_call(client, {'taskId': 'scan-456'})
        result = bd_scan_create_command(client, {'target_ids': 'ep-001,ep-002', 'scan_type': '1'})
        assert result.outputs['ID'] == 'scan-456'
        assert result.outputs['Type'] == 'Scan'

    def test_custom_scan_params(self, client):
        mock_call(client, {'taskId': 'scan-789'})
        client.create_scan_task = MagicMock(return_value={'taskId': 'scan-789'})
        bd_scan_create_command(client, {
            'target_ids': 'ep-001',
            'scan_type': '4',
            'name': 'Custom Scan',
            'scan_depth': '2',
            'scan_path': 'LocalDrives',
        })
        client.create_scan_task.assert_called_once_with(
            target_ids=['ep-001'],
            scan_type=4,
            name='Custom Scan',
            scan_depth=2,
            scan_paths=['LocalDrives'],
        )


class TestTaskStatus:
    def test_returns_status(self, client):
        mock_call(client, {'items': [{'taskId': 't1', 'name': 'Scan', 'status': 3, 'type': 2, 'startDate': '2024-01-15'}]})
        result = bd_task_status_command(client, {'task_id': 't1'})
        assert result.outputs['ID'] == 't1'
        assert result.outputs['Status'] == 3

    def test_not_found(self, client):
        mock_call(client, {'items': []})
        result = bd_task_status_command(client, {'task_id': 'missing'})
        assert 'No task found' in result.readable_output


class TestTaskDelete:
    def test_deleted(self, client):
        mock_call(client, True)
        result = bd_task_delete_command(client, {'task_id': 't1'})
        assert result.outputs['Deleted'] is True


class TestIncidentNote:
    def test_note_updated(self, client):
        mock_call(client, True)
        result = bd_incident_note_update_command(client, {
            'incident_type': 'incidents',
            'incident_id': 'inc-001',
            'note': 'Investigated and confirmed.',
        })
        assert result.outputs['NoteUpdated'] is True


class TestIncidentStatus:
    def test_status_changed(self, client):
        mock_call(client, True)
        result = bd_incident_status_change_command(client, {
            'incident_type': 'incidents',
            'incident_id': 'inc-001',
            'status': '2',
        })
        assert result.outputs['StatusChanged'] is True


class TestBlocklist:
    def test_add_hash(self, client):
        mock_call(client, True)
        result = bd_blocklist_add_command(client, {
            'type': 'hash',
            'hash_value': 'abc123',
            'hash_algorithm': 'sha256',
        })
        assert result.outputs['Added'] is True

    def test_get_items(self, client):
        mock_call(client, {'items': [{'id': 'bl-1', 'type': 'hash', 'createdAt': '2024-01-01'}], 'total': 1})
        result = bd_blocklist_get_command(client, {})
        assert result.outputs['Total'] == 1
        assert result.outputs['Items'][0]['ID'] == 'bl-1'

    def test_remove_items(self, client):
        mock_call(client, True)
        result = bd_blocklist_remove_command(client, {'item_ids': 'bl-1,bl-2'})
        assert result.outputs['Removed'] is True


class TestQuarantine:
    def test_list_items(self, client):
        mock_call(client, {
            'items': [{'id': 'q1', 'threatName': 'Trojan.Test', 'filePath': 'C:\\bad.exe', 'actionStatus': 0}],
            'total': 1,
        })
        result = bd_quarantine_list_command(client, {'service': 'computers'})
        assert result.outputs['Total'] == 1
        assert result.outputs['Items'][0]['ThreatName'] == 'Trojan.Test'

    def test_remove_returns_task(self, client):
        mock_call(client, {'taskId': 'qtask-1'})
        result = bd_quarantine_item_remove_command(client, {'service': 'computers', 'quarantine_item_ids': 'q1'})
        assert result.outputs['ID'] == 'qtask-1'

    def test_restore_returns_task(self, client):
        mock_call(client, {'taskId': 'qtask-2'})
        result = bd_quarantine_item_restore_command(client, {'quarantine_item_ids': 'q1'})
        assert result.outputs['ID'] == 'qtask-2'


class TestLicenseInfo:
    def test_returns_license(self, client):
        mock_call(client, {'subscriptionType': 2, 'expiryDate': '2025-12-31', 'usedSlots': 10, 'totalSlots': 50})
        result = bd_license_info_command(client)
        assert result.outputs['SubscriptionType'] == 2
        assert result.outputs['TotalSlots'] == 50


class TestPushSettings:
    def test_get_settings(self, client):
        mock_call(client, {
            'status': 1,
            'serviceType': 'jsonRPC',
            'serviceSettings': {'url': 'https://xsoar.example.com/webhook'},
            'subscribedEventTypes': ['av', 'aph'],
        })
        result = bd_push_settings_get_command(client)
        assert result.outputs['Status'] == 1
        assert result.outputs['ServiceSettings']['URL'] == 'https://xsoar.example.com/webhook'

    def test_set_settings(self, client):
        mock_call(client, True)
        result = bd_push_settings_set_command(client, {
            'status': '1',
            'service_type': 'jsonRPC',
            'url': 'https://xsoar.example.com/webhook',
        })
        assert result.outputs['Updated'] is True

    def test_send_test_event(self, client):
        mock_call(client, True)
        result = bd_push_test_command(client, {'event_type': 'av'})
        assert result.outputs['Success'] is True


class TestGravityZoneClientCall:
    def test_raises_on_api_error(self, client):
        client._http_request = MagicMock(return_value={
            'jsonrpc': '2.0',
            'id': 'x',
            'error': {'code': -32602, 'message': 'Invalid params'},
        })
        with pytest.raises(Exception, match='Invalid params'):
            client._call('network', 'getEndpointsList', {})

    def test_returns_result(self, client):
        client._http_request = MagicMock(return_value={
            'jsonrpc': '2.0',
            'id': 'x',
            'result': {'items': [], 'total': 0},
        })
        result = client._call('network', 'getEndpointsList', {})
        assert result == {'items': [], 'total': 0}

    def test_request_format(self, client):
        client._http_request = MagicMock(return_value={'jsonrpc': '2.0', 'id': 'x', 'result': {}})
        client._call('network', 'getEndpointsList', {'page': 1})
        call_args = client._http_request.call_args
        assert call_args[0][0] == 'POST'
        assert 'jsonrpc' in call_args[1]['json_data']
        assert call_args[1]['json_data']['method'] == 'getEndpointsList'
        assert call_args[1]['json_data']['params'] == {'page': 1}
