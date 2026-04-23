import demistomock as demisto
from CommonServerPython import *
import uuid

API_VERSION = 'v1.0'

ALL_EVENT_TYPES = [
    'av', 'avc', 'hd', 'aph', 'fw', 'dp', 'uc',
    'antiexploit', 'ransomware-mitigation', 'network-sandboxing', 'network-monitor',
    'exchange-malware', 'new-incident', 'new-extended-incident',
    'modules', 'sva', 'sva-load', 'registration', 'supa-update-status',
    'task-status', 'install', 'uninstall', 'hwid-change',
    'endpoint-moved-in', 'endpoint-moved-out', 'adcloud',
    'exchange-user-credentials', 'exchange-organization-info',
    'troubleshooting-activity', 'partner-changed', 'integrations-hub-status',
]


class GravityZoneClient(BaseClient):
    def __init__(self, base_url: str, api_key: str, verify: bool, proxy: bool, company_id: str | None = None):
        # Normalize: strip trailing slash and any trailing /api suffix so we always add it ourselves
        normalized = base_url.rstrip('/')
        if normalized.endswith('/api'):
            normalized = normalized[:-4]
        super().__init__(
            base_url=normalized,
            verify=verify,
            proxy=proxy,
            auth=(api_key, ''),
        )
        self.company_id = company_id or None

    def _with_company(self, params: dict) -> dict:
        if self.company_id:
            params = dict(params)
            params['companyId'] = self.company_id
        return params

    def _call(self, namespace: str, method: str, params: dict | None = None) -> Any:
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'id': str(uuid.uuid4()),
            'params': params or {},
        }
        response = self._http_request('POST', f'/api/{API_VERSION}/jsonrpc/{namespace}', json_data=payload)
        if 'error' in response:
            err = response['error']
            msg = err.get('message', str(err))
            data = err.get('data')
            detail = f' — {data}' if data else ''
            raise DemistoException(f'GravityZone API error [{err.get("code")}]: {msg}{detail}')
        return response.get('result')

    # ── Network ─────────────────────────────────────────────────────────────

    def get_endpoints_list(self, parent_id=None, is_managed=None, page=1, per_page=30, name_filter=None):
        params: dict = {'page': page, 'perPage': per_page}
        if parent_id:
            params['parentId'] = parent_id
        if is_managed is not None:
            params['isManaged'] = is_managed
        if name_filter:
            params['filters'] = {'name': name_filter}
        return self._call('network', 'getEndpointsList', params)

    def get_endpoint_details(self, endpoint_id: str):
        return self._call('network', 'getManagedEndpointDetails', {'endpointId': endpoint_id})

    def isolate_endpoint(self, endpoint_id: str):
        return self._call('network', 'createIsolateEndpointTask', {'endpointId': endpoint_id})

    def deisolate_endpoint(self, endpoint_id: str):
        return self._call('network', 'createRestoreEndpointFromIsolationTask', {'endpointId': endpoint_id})

    def create_scan_task(self, target_ids: list, scan_type: int, name=None, scan_depth=None, scan_paths=None):
        params: dict = {'targetIds': target_ids, 'type': scan_type}
        if name:
            params['name'] = name
        custom: dict = {}
        if scan_depth is not None:
            custom['scanDepth'] = scan_depth
        if scan_paths:
            custom['scanPath'] = scan_paths
        if custom:
            params['customScanSettings'] = custom
        return self._call('network', 'createScanTask', params)

    def get_task_status(self, task_id: str, return_subtasks: bool = False):
        params = {'filters': {'taskId': task_id}, 'returnSubtasks': return_subtasks}
        result = self._call('network', 'getTasksList', params)
        items = (result or {}).get('items', [])
        return items[0] if items else None

    def delete_scan_task(self, task_id: str):
        return self._call('network', 'deleteScanTask', {'taskId': task_id})

    # ── Incidents / ExtendedIncidents ────────────────────────────────────────

    def update_incident_note(self, namespace: str, incident_id: str, note: str):
        return self._call(namespace, 'addNote', {'incidentId': incident_id, 'note': note})

    def change_incident_status(self, namespace: str, incident_id: str, status: int):
        return self._call(namespace, 'changeStatus', {'incidentId': incident_id, 'status': status})

    # ── Blocklist (integrations namespace) ──────────────────────────────────

    def add_to_blocklist(self, rule_type: str, hash_value=None, hash_algorithm=None,
                         path_value=None, note=None):
        rule: dict = {'type': rule_type}
        if rule_type == 'hash':
            rule['hashType'] = hash_algorithm
            rule['hashValue'] = hash_value
        elif rule_type == 'path':
            rule['pathValue'] = path_value
        if note:
            rule['note'] = note
        return self._call('integrations', 'addToBlocklist', self._with_company({'rules': [rule]}))

    def get_blocklist(self, page=1, per_page=30):
        return self._call('integrations', 'getBlocklistItems', self._with_company({'page': page, 'perPage': per_page}))

    def remove_from_blocklist(self, item_ids: list):
        return self._call('integrations', 'removeFromBlocklist', self._with_company({'itemIds': item_ids}))

    # ── Quarantine ──────────────────────────────────────────────────────────

    def get_quarantine_items(self, service: str, endpoint_id=None, page=1, per_page=30, threat_name=None):
        params: dict = {'page': page, 'perPage': per_page}
        if endpoint_id:
            params['endpointId'] = endpoint_id
        if threat_name:
            params['filters'] = {'threatName': threat_name}
        return self._call(f'quarantine/{service}', 'getQuarantineItemsList', self._with_company(params))

    def remove_quarantine_items(self, service: str, item_ids: list):
        return self._call(f'quarantine/{service}', 'createRemoveQuarantineItemTask',
                          self._with_company({'quarantineItemsIds': item_ids}))

    def restore_quarantine_items(self, service: str, item_ids: list, location=None, add_exclusion=False):
        params: dict = {'quarantineItemsIds': item_ids}
        if location:
            params['locationToRestore'] = location
        if add_exclusion:
            params['addExclusionInPolicy'] = True
        return self._call(f'quarantine/{service}', 'createRestoreQuarantineItemTask', self._with_company(params))

    # ── Accounts (partner/reseller only) ────────────────────────────────────

    def get_license_info(self):
        return self._call('accounts', 'getLicenseInfo', self._with_company({}))

    # ── Push notifications ───────────────────────────────────────────────────

    def get_push_settings(self):
        return self._call('push', 'getPushEventSettings', {})

    def set_push_settings(self, status: int, service_type: str, url: str,
                          authorization=None, require_valid_ssl=None, subscribe_all=False):
        settings: dict = {'url': url}
        if authorization:
            settings['authorization'] = authorization
        if require_valid_ssl is not None:
            settings['requireValidSslCertificate'] = require_valid_ssl
        params: dict = {
            'status': status,
            'serviceType': service_type,
            'serviceSettings': settings,
        }
        if subscribe_all:
            params['subscribeToEventTypes'] = {t: True for t in ALL_EVENT_TYPES}
        if self.company_id:
            params['subscribeToCompanies'] = [self.company_id]
        return self._call('push', 'setPushEventSettings', params)

    def send_test_push(self, event_type: str):
        return self._call('push', 'sendTestPushEvent', {'eventType': event_type})


# ── Command implementations ──────────────────────────────────────────────────

def _is_success(result) -> bool:
    return result is not False and result != 'false'


def _readable_bool_result(action: str, result) -> str:
    if _is_success(result):
        return f'{action} successfully.'
    return f'{action} failed.\n\nResponse: {result}'

def test_module(client: GravityZoneClient) -> str:
    client.get_endpoints_list(per_page=1)
    return 'ok'


def bd_endpoint_list_command(client: GravityZoneClient, args: dict) -> list:
    page = arg_to_number(args.get('page')) or 1
    per_page = arg_to_number(args.get('per_page')) or 1000
    is_managed_raw = args.get('is_managed')
    is_managed: bool | None = argToBoolean(is_managed_raw) if is_managed_raw is not None else True

    result = client.get_endpoints_list(
        parent_id=args.get('parent_id'),
        is_managed=is_managed,
        page=page,
        per_page=per_page,
        name_filter=args.get('name_filter'),
    )
    items = (result or {}).get('items', [])

    bd_outputs = [{
        'ID': e.get('id'),
        'Name': e.get('name'),
        'IP': e.get('ip'),
        'OS': e.get('operatingSystemVersion'),
        'IsManaged': e.get('isManaged'),
        'GroupID': e.get('groupId'),
        'CompanyID': e.get('companyId'),
    } for e in items]

    std_outputs = [{
        'ID': e.get('id'),
        'Hostname': e.get('name'),
        'IPAddress': e.get('ip'),
    } for e in items]

    readable = tableToMarkdown('GravityZone Endpoints', bd_outputs,
                               headers=['ID', 'Name', 'IP', 'OS', 'IsManaged'],
                               removeNull=True)
    return [
        CommandResults(
            outputs_prefix='Bitdefender.Endpoint',
            outputs_key_field='ID',
            outputs=bd_outputs,
            readable_output=readable,
            raw_response=result,
        ),
        CommandResults(
            outputs_prefix='Endpoint',
            outputs_key_field='ID',
            outputs=std_outputs,
        ),
    ]


def bd_endpoint_get_command(client: GravityZoneClient, args: dict) -> list:
    endpoint_id = args['endpoint_id']
    result = client.get_endpoint_details(endpoint_id)
    if not result:
        return [CommandResults(readable_output=f'Endpoint `{endpoint_id}` not found.')]

    agent = result.get('agent', {})
    bd_output = {
        'ID': result.get('id'),
        'Name': result.get('name'),
        'IP': result.get('ip'),
        'OS': result.get('operatingSystemVersion'),
        'State': result.get('state'),
        'MachineType': result.get('machineType'),
        'CompanyID': result.get('companyId'),
        'LastSeen': result.get('lastSeen'),
        'Agent': {
            'ProductVersion': agent.get('productVersion'),
            'Licensed': agent.get('licensed'),
            'SignatureOutdated': agent.get('isSignatureOutdated'),
        },
    }
    std_output = {
        'ID': result.get('id'),
        'Hostname': result.get('name'),
        'IPAddress': result.get('ip'),
        'OS': result.get('operatingSystemVersion'),
        'Status': result.get('state'),
    }
    readable = tableToMarkdown('GravityZone Endpoint Details', [bd_output],
                               headers=['ID', 'Name', 'IP', 'OS', 'State', 'MachineType', 'LastSeen'],
                               removeNull=True)
    return [
        CommandResults(
            outputs_prefix='Bitdefender.Endpoint',
            outputs_key_field='ID',
            outputs=bd_output,
            readable_output=readable,
            raw_response=result,
        ),
        CommandResults(
            outputs_prefix='Endpoint',
            outputs_key_field='ID',
            outputs=std_output,
        ),
    ]


def bd_endpoint_isolate_command(client: GravityZoneClient, args: dict) -> CommandResults:
    endpoint_id = args['endpoint_id']
    result = client.isolate_endpoint(endpoint_id)
    # v1.0 returns True; v1.1 returns [{"taskId": ..., "endpointId": ...}]
    if isinstance(result, list) and result:
        entry = result[0]
        output = {
            'ID': entry.get('taskId'),
            'EndpointID': entry.get('endpointId', endpoint_id),
            'Type': 'Isolate',
        }
    else:
        output = {'EndpointID': endpoint_id, 'Type': 'Isolate'}
    readable = f'Endpoint `{endpoint_id}` isolation task created successfully.'
    return CommandResults(
        outputs_prefix='Bitdefender.Task',
        outputs_key_field='ID',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_endpoint_deisolate_command(client: GravityZoneClient, args: dict) -> CommandResults:
    endpoint_id = args['endpoint_id']
    result = client.deisolate_endpoint(endpoint_id)
    if isinstance(result, list) and result:
        entry = result[0]
        output = {
            'ID': entry.get('taskId'),
            'EndpointID': entry.get('endpointId', endpoint_id),
            'Type': 'Deisolate',
        }
    else:
        output = {'EndpointID': endpoint_id, 'Type': 'Deisolate'}
    readable = f'Endpoint `{endpoint_id}` de-isolation task created successfully.'
    return CommandResults(
        outputs_prefix='Bitdefender.Task',
        outputs_key_field='ID',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_scan_create_command(client: GravityZoneClient, args: dict) -> CommandResults:
    target_ids = argToList(args['target_ids'])
    scan_type = arg_to_number(args['scan_type'])
    scan_depth = arg_to_number(args.get('scan_depth')) if args.get('scan_depth') else None
    scan_paths = argToList(args['scan_path']) if args.get('scan_path') else None

    result = client.create_scan_task(
        target_ids=target_ids,
        scan_type=scan_type,
        name=args.get('name'),
        scan_depth=scan_depth,
        scan_paths=scan_paths,
    )
    task_id = (result or {}).get('taskId')
    output = {'ID': task_id, 'Type': 'Scan'}
    readable = tableToMarkdown('Scan Task Created', [output], removeNull=True)
    return CommandResults(
        outputs_prefix='Bitdefender.Task',
        outputs_key_field='ID',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_task_status_command(client: GravityZoneClient, args: dict) -> CommandResults:
    task_id = args['task_id']
    return_subtasks = argToBoolean(args.get('return_subtasks', 'false'))
    task = client.get_task_status(task_id, return_subtasks)
    if not task:
        return CommandResults(readable_output=f'No task found with ID `{task_id}`.')
    output = {
        'ID': task.get('taskId') or task.get('id'),
        'Name': task.get('name'),
        'Status': task.get('status'),
        'Type': task.get('type'),
        'StartDate': task.get('startDate'),
    }
    readable = tableToMarkdown('Task Status', [output], removeNull=True)
    return CommandResults(
        outputs_prefix='Bitdefender.Task',
        outputs_key_field='ID',
        outputs=output,
        readable_output=readable,
        raw_response=task,
    )


def bd_task_delete_command(client: GravityZoneClient, args: dict) -> CommandResults:
    task_id = args['task_id']
    result = client.delete_scan_task(task_id)
    deleted = _is_success(result)
    output = {'Deleted': deleted}
    readable = _readable_bool_result(f'Task `{task_id}` deletion', result)
    return CommandResults(
        outputs_prefix='Bitdefender.Task',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_incident_note_update_command(client: GravityZoneClient, args: dict) -> CommandResults:
    incident_type = args['incident_type']
    incident_id = args['incident_id']
    note = args['note']
    result = client.update_incident_note(incident_type, incident_id, note)
    updated = _is_success(result)
    output = {'NoteUpdated': updated}
    readable = _readable_bool_result(f'Note update for incident `{incident_id}`', result)
    return CommandResults(
        outputs_prefix='Bitdefender.Incident',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_incident_status_change_command(client: GravityZoneClient, args: dict) -> CommandResults:
    incident_type = args['incident_type']
    incident_id = args['incident_id']
    status = arg_to_number(args['status'])
    result = client.change_incident_status(incident_type, incident_id, status)
    changed = _is_success(result)
    output = {'StatusChanged': changed}
    readable = _readable_bool_result(f'Status change for incident `{incident_id}`', result)
    return CommandResults(
        outputs_prefix='Bitdefender.Incident',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_blocklist_add_command(client: GravityZoneClient, args: dict) -> CommandResults:
    rule_type = args['type']
    result = client.add_to_blocklist(
        rule_type=rule_type,
        hash_value=args.get('hash_value'),
        hash_algorithm=args.get('hash_algorithm'),
        path_value=args.get('path_value'),
        note=args.get('note'),
    )
    added = _is_success(result)
    output = {'Added': added}
    readable = _readable_bool_result(f'Blocklist rule `{rule_type}` addition', result)
    return CommandResults(
        outputs_prefix='Bitdefender.Blocklist',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_blocklist_get_command(client: GravityZoneClient, args: dict) -> CommandResults:
    page = arg_to_number(args.get('page')) or 1
    per_page = arg_to_number(args.get('per_page')) or 30
    result = client.get_blocklist(page=page, per_page=per_page)
    items = (result or {}).get('items', [])
    total = (result or {}).get('total', 0)

    outputs_items = [{
        'ID': item.get('id'),
        'Type': item.get('type'),
        'Created': item.get('createdAt'),
    } for item in items]
    output = {'Total': total, 'Items': outputs_items}
    readable = tableToMarkdown('Blocklist Items', outputs_items,
                               headers=['ID', 'Type', 'Created'], removeNull=True)
    return CommandResults(
        outputs_prefix='Bitdefender.Blocklist',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_blocklist_remove_command(client: GravityZoneClient, args: dict) -> CommandResults:
    item_ids = argToList(args['item_ids'])
    result = client.remove_from_blocklist(item_ids)
    removed = _is_success(result)
    output = {'Removed': removed}
    readable = _readable_bool_result(f'{len(item_ids)} blocklist item(s) removal', result)
    return CommandResults(
        outputs_prefix='Bitdefender.Blocklist',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_quarantine_list_command(client: GravityZoneClient, args: dict) -> CommandResults:
    service = args['service']
    page = arg_to_number(args.get('page')) or 1
    per_page = arg_to_number(args.get('per_page')) or 30
    result = client.get_quarantine_items(
        service=service,
        endpoint_id=args.get('endpoint_id'),
        page=page,
        per_page=per_page,
        threat_name=args.get('threat_name'),
    )
    items = (result or {}).get('items', [])
    total = (result or {}).get('total', 0)

    outputs_items = [{
        'ID': item.get('id'),
        'ThreatName': item.get('threatName'),
        'FilePath': item.get('filePath'),
        'ActionStatus': item.get('actionStatus'),
    } for item in items]
    output = {'Total': total, 'Items': outputs_items}
    readable = tableToMarkdown('Quarantine Items', outputs_items,
                               headers=['ID', 'ThreatName', 'FilePath', 'ActionStatus'],
                               removeNull=True)
    return CommandResults(
        outputs_prefix='Bitdefender.Quarantine',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_quarantine_item_remove_command(client: GravityZoneClient, args: dict) -> CommandResults:
    service = args['service']
    item_ids = argToList(args['quarantine_item_ids'])
    result = client.remove_quarantine_items(service=service, item_ids=item_ids)
    task_id = (result or {}).get('taskId')
    output = {'ID': task_id}
    readable = f'Quarantine removal task created: `{task_id}`.'
    return CommandResults(
        outputs_prefix='Bitdefender.Task',
        outputs_key_field='ID',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_quarantine_item_restore_command(client: GravityZoneClient, args: dict) -> CommandResults:
    item_ids = argToList(args['quarantine_item_ids'])
    add_exclusion = argToBoolean(args.get('add_exclusion_in_policy', 'false'))
    result = client.restore_quarantine_items(
        service=args['service'],
        item_ids=item_ids,
        location=args.get('location_to_restore'),
        add_exclusion=add_exclusion,
    )
    task_id = (result or {}).get('taskId')
    output = {'ID': task_id}
    readable = f'Quarantine restore task created: `{task_id}`.'
    return CommandResults(
        outputs_prefix='Bitdefender.Task',
        outputs_key_field='ID',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_license_info_command(client: GravityZoneClient) -> CommandResults:
    try:
        result = client.get_license_info()
    except DemistoException as e:
        if '[-32601]' in str(e):
            raise DemistoException(
                f'{e}\n\nNote: getLicenseInfo is only available for partner/reseller API keys, '
                'not for standard company API keys.'
            )
        raise
    output = {
        'SubscriptionType': (result or {}).get('subscriptionType'),
        'ExpiryDate': (result or {}).get('expiryDate'),
        'UsedSlots': (result or {}).get('usedSlots'),
        'TotalSlots': (result or {}).get('totalSlots'),
    }
    readable = tableToMarkdown('GravityZone License', [output], removeNull=True)
    return CommandResults(
        outputs_prefix='Bitdefender.License',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


PUSH_NOT_AVAILABLE = (
    'Push Notification Service is not available on this account. '
    'Enable it in GravityZone Control Center under My Company → Integrations.'
)


def _wrap_push_call(fn):
    try:
        return fn()
    except DemistoException as e:
        msg = str(e)
        if '[-32000]' in msg and 'Event template not found' in msg:
            raise DemistoException(
                f'{e}\n\nNote: This event type is not available on this GravityZone account.'
            )
        if '[-32000]' in msg:
            raise DemistoException(f'{e}\n\nNote: {PUSH_NOT_AVAILABLE}')
        raise


def bd_push_settings_get_command(client: GravityZoneClient) -> CommandResults:
    result = _wrap_push_call(client.get_push_settings)
    settings = (result or {}).get('serviceSettings', {})
    output = {
        'Status': (result or {}).get('status'),
        'ServiceType': (result or {}).get('serviceType'),
        'ServiceSettings': {
            'URL': settings.get('url'),
        },
        'SubscribedEventTypes': (result or {}).get('subscribedEventTypes', []),
    }
    readable = tableToMarkdown('GravityZone Push Settings', [output],
                               headers=['Status', 'ServiceType', 'ServiceSettings', 'SubscribedEventTypes'],
                               removeNull=True)
    return CommandResults(
        outputs_prefix='Bitdefender.PushSettings',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_push_settings_set_command(client: GravityZoneClient, args: dict) -> CommandResults:
    webhook_url = args['url']
    if not webhook_url.lower().startswith('https://'):
        raise DemistoException(
            'GravityZone requires the webhook URL to use HTTPS (TLS 1.2+). '
            f'Provided URL uses plain HTTP: {webhook_url}\n'
            'Configure a reverse proxy (e.g. Traefik/nginx) with a valid TLS certificate in front of your XSOAR instance.'
        )
    require_ssl: bool | None = None
    if args.get('require_valid_ssl') is not None:
        require_ssl = argToBoolean(args['require_valid_ssl'])
    subscribe_all = argToBoolean(args.get('subscribe_all', 'false'))

    result = _wrap_push_call(lambda: client.set_push_settings(
        status=arg_to_number(args['status']),
        service_type=args['service_type'],
        url=webhook_url,
        authorization=args.get('authorization'),
        require_valid_ssl=require_ssl,
        subscribe_all=subscribe_all,
    ))
    updated = _is_success(result)
    output = {'Updated': updated}
    readable = _readable_bool_result('Push notification settings update', result)
    return CommandResults(
        outputs_prefix='Bitdefender.PushSettings',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


def bd_push_test_command(client: GravityZoneClient, args: dict) -> CommandResults:
    event_type = args['event_type']
    result = _wrap_push_call(lambda: client.send_test_push(event_type))
    success = _is_success(result)
    readable = _readable_bool_result(f'Test push event `{event_type}`', result)
    output = {'Success': success, 'Detail': result}
    return CommandResults(
        outputs_prefix='Bitdefender.PushTest',
        outputs=output,
        readable_output=readable,
        raw_response=result,
    )


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    params = demisto.params()
    args = demisto.args()
    command = demisto.command()

    base_url = params.get('url', '').rstrip('/')
    api_key = params.get('credentials', {}).get('password', '')
    verify = not params.get('insecure', False)
    proxy = params.get('proxy', False)
    company_id = params.get('company_id') or None

    client = GravityZoneClient(base_url, api_key, verify, proxy, company_id=company_id)

    try:
        if command == 'test-module':
            return_results(test_module(client))
        elif command == 'bd-endpoint-list':
            return_results(bd_endpoint_list_command(client, args))
        elif command == 'bd-endpoint-get':
            return_results(bd_endpoint_get_command(client, args))
        elif command == 'bd-endpoint-isolate':
            return_results(bd_endpoint_isolate_command(client, args))
        elif command == 'bd-endpoint-deisolate':
            return_results(bd_endpoint_deisolate_command(client, args))
        elif command == 'bd-scan-create':
            return_results(bd_scan_create_command(client, args))
        elif command == 'bd-task-status':
            return_results(bd_task_status_command(client, args))
        elif command == 'bd-task-delete':
            return_results(bd_task_delete_command(client, args))
        elif command == 'bd-incident-note-update':
            return_results(bd_incident_note_update_command(client, args))
        elif command == 'bd-incident-status-change':
            return_results(bd_incident_status_change_command(client, args))
        elif command == 'bd-blocklist-add':
            return_results(bd_blocklist_add_command(client, args))
        elif command == 'bd-blocklist-get':
            return_results(bd_blocklist_get_command(client, args))
        elif command == 'bd-blocklist-remove':
            return_results(bd_blocklist_remove_command(client, args))
        elif command == 'bd-quarantine-list':
            return_results(bd_quarantine_list_command(client, args))
        elif command == 'bd-quarantine-item-remove':
            return_results(bd_quarantine_item_remove_command(client, args))
        elif command == 'bd-quarantine-item-restore':
            return_results(bd_quarantine_item_restore_command(client, args))
        elif command == 'bd-license-info':
            return_results(bd_license_info_command(client))
        elif command == 'bd-push-settings-get':
            return_results(bd_push_settings_get_command(client))
        elif command == 'bd-push-settings-set':
            return_results(bd_push_settings_set_command(client, args))
        elif command == 'bd-push-test':
            return_results(bd_push_test_command(client, args))
        else:
            raise NotImplementedError(f'Command "{command}" is not implemented.')
    except Exception as e:
        return_error(f'Failed to execute {command}. Error: {str(e)}')


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
