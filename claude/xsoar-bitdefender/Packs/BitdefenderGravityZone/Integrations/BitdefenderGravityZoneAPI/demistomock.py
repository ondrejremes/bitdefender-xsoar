"""Minimal demistomock for local unit testing."""

_params: dict = {}
_args: dict = {}
_command: str = 'test-module'
_results: list = []

callingContext: dict = {'context': {'IntegrationBrand': 'BitdefenderGravityZoneAPI', 'IntegrationInstance': 'test'}}


def params():
    return _params


def args():
    return _args


def command():
    return _command


def results(data):
    _results.append(data)


def debug(msg):
    pass


def error(msg):
    pass


def info(msg):
    pass


def log(msg):
    pass


def getLastRun():
    return {}


def setLastRun(data):
    pass


def incidents(data):
    pass


def getFilePath(id):
    return {'name': '', 'path': ''}


def investigation():
    return {'id': '1'}


def context():
    return {}


def getIntegrationContext():
    return {}


def setIntegrationContext(data):
    pass


def getIntegrationContextVersioned(sync=True):
    return {'context': {}, 'version': 0}


def setIntegrationContextVersioned(context, version=0, sync=False):
    pass


def uniqueFile():
    return 'tmpfile'


def getenv(key, default=None):
    import os
    return os.getenv(key, default)


def getLicenseID():
    return 'test-license'


def demistoVersion():
    return {'version': '6.14.0', 'buildNumber': '1234', 'isCloud': False}


def executeCommand(command, args):
    return [{'Type': 1, 'Contents': {}, 'ContentsFormat': 'json'}]


def get(obj, field, defaultParam=None):
    parts = field.split('.')
    val = obj
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part, defaultParam)
        else:
            return defaultParam
    return val


def dt(obj, trnsfrm):
    return None


def addEntry(id, entry):
    pass


def mirrorInvestigation(id, mirrorType, autoClose=False):
    pass
