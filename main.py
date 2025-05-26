import requests
import io
import logging
import json
from datetime import datetime

import firebase_admin
from firebase_admin import credentials
from firebase_admin import remote_config, _utils
from firebase_admin.remote_config import (
    _REMOTE_CONFIG_ATTRIBUTE,
    _RemoteConfigService)

logger = logging.getLogger(__name__)


class ManagedRemoteConfigService():

    def __init__(self):
        self.PROJECT_ID = 'my-test-1181b'
        self.BASE_URL = 'https://firebaseremoteconfig.googleapis.com'
        self.REMOTE_CONFIG_ENDPOINT = 'v1/projects/' + self.PROJECT_ID + '/remoteConfig'
        self.REMOTE_CONFIG_URL = self.BASE_URL + '/' + self.REMOTE_CONFIG_ENDPOINT
        self.SCOPES = ['https://www.googleapis.com/auth/firebase.remoteconfig']

    def _get_access_token(self):
        """Retrieve a valid access token that can be used to authorize requests.

        :return: Access token.
        """
        cred = credentials.Certificate("serviceAccountKey.json")

        access_token_info = cred.get_access_token()

        return access_token_info.access_token

    def _save_remote_config(self, response: requests.Response):
        """Save the Remote Config template to a local file.

        :param template: The Remote Config template to save.
        """

        timestamp = datetime.now().strftime('%Y%m%d%H%M')
        remote_file_name = f'config_{timestamp}.json'

        with io.open(remote_file_name, 'wb') as f:
            f.write(response.text.encode('utf-8'))

        logger.info(
            f'Retrieved template has been written to {remote_file_name}')
        logger.info('ETag from server: {}'.format(response.headers['ETag']))

        return remote_file_name

    def get_remote_config(self):
        """Retrieve the current Firebase Remote Config template from server.

        Retrieve the current Firebase Remote Config template from server and store it
        locally.
        """
        headers = {
            'Authorization': 'Bearer ' + self._get_access_token()
        }
        resp = requests.get(self.REMOTE_CONFIG_URL, headers=headers)

        if resp.status_code == 200:
            return self._save_remote_config(resp)
        else:
            logger.error(
                'Error retrieving template: {}'.format(resp.status_code))
            logger.error('Response: {}'.format(resp.text))

    def update_remote_config(self, remote_config_file: str):
        """Update the Firebase Remote Config template on server.

        Update the Firebase Remote Config template on server.
        """
        headers = {
            'Authorization': 'Bearer ' + self._get_access_token()
        }

        with open(remote_config_file, 'rb') as f:

            data = json.load(f)
            resp = requests.put(self.REMOTE_CONFIG_URL,
                                headers=headers, data=json.dumps(data))

        if resp.status_code == 200:
            logger.info('Updated template successfully')
            logger.info('ETag from server: {}'.format(resp.headers['ETag']))
        else:
            logger.error(
                'Error updating template: {}'.format(resp.status_code))
            logger.error('Response: {}'.format(resp.text))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    remote_config_service = ManagedRemoteConfigService()
    config_file = remote_config_service.get_remote_config()
    remote_config_service.update_remote_config(config_file)
