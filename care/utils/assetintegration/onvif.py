import json
from urllib import request
from assetintegration import BaseAssetIntegration

class OnvifAsset(BaseAssetIntegration):
    asset_type='onvif'
    def __init__(self, meta):
        self.meta = meta
        self.name = meta['camera_type']
        self.host = meta['camera_address']
        self.port = meta['camera_port'] or 80
        self.username = meta['camera_access_key'].split(':')[0]
        self.password = meta['access_credentials'].split(':')[1]
        self.middleware_hostname = meta['middleware_hostname']

    def validate_camera(self):
        # self.host not null
        if not self.host:
            return False
        # self.username not null
        if not self.username:
            return False
        # self.password not null
        if not self.password:
            return False
        # self.middleware_hostname not null
        if not self.middleware_hostname:
            return False
        return True

    def handle_action(self, action):
        self.validate_camera(self)
        if action.type == 'move_absolute':
            # Make API Call for action
            request_data = {
                'x': action.data['x'],
                'y': action.data['y'],
                'z': action.data['z'],
                'speed': action.data['speed'],
                'meta': self.meta
            }
            self.move_absolute(request_data)
            self.api_call('POST', 'onvif/PTZ/{}/absoluteMove'.format(self.name), data=request_data)

        elif action == 'goto_preset':
            action.data['preset']
        else:
            raise Exception('Invalid action')
    def api_call(self, method, endpoint, data=None):
        headers = {'content-type': 'application/xml'}
        url = 'https://{}/{}'.format(self.middleware_hostname,endpoint)
        if data:
            if method == 'GET':
                querystring = '&'.join(['{}={}'.format(k,v) for k,v in data.items()])
                url += '?' + querystring
            else:
                data = json.dumps(data)
                headers['content-type'] = 'application/json'

        # Make the HTTP request
        req = request.Request(url, data=data, headers=headers)
    