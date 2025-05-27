import os
import requests
import io
import logging
import json
from datetime import datetime

from firebase_admin import credentials

logger = logging.getLogger(__name__)


class ManagedRemoteConfigService():

    def __init__(self):
        self.PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', 'my-test-1181b')
        self.BASE_URL = 'https://firebaseremoteconfig.googleapis.com'
        self.REMOTE_CONFIG_ENDPOINT = 'v1/projects/' + self.PROJECT_ID + '/remoteConfig'
        self.REMOTE_CONFIG_URL = self.BASE_URL + '/' + self.REMOTE_CONFIG_ENDPOINT
        self.SCOPES = ['https://www.googleapis.com/auth/firebase.remoteconfig']

    def _rollback(self, version):
        """Roll back to an available version of Firebase Remote Config template.

        :param version: The version of the template to roll back to.
        """
        headers = {
            'Authorization': 'Bearer ' + self._get_access_token()
        }

        json = {
            "versionNumber": version
        }

        rollback_url = f"{self.REMOTE_CONFIG_URL}:rollback"
        resp = requests.post(rollback_url, headers=headers, json=json)

        if resp.status_code == 200:
            print('Rolled back to version: ' + version)
            print(resp.text)
            print('ETag from server: {}'.format(resp.headers['ETag']))
        else:
            print('Request to roll back to version ' + version + ' failed.')
            print(resp.text)

    def _get_access_token(self):
        """Retrieve a valid access token that can be used to authorize requests.

        :return: Access token.
        """
        cred = credentials.Certificate("serviceAccountKey.json")

        access_token_info = cred.get_access_token()

        return access_token_info.access_token

    def update_parameter_group(self, remote_config_current: dict, scenario: str, banner_option: str) -> str:
        """Update the Remote Config template with the specified banner option.

        :param remote_config_current: The current Remote Config template.
        :param scenario: The scenario for which the banner option is to be retrieved.
        :param banner_option: The banner option to be set, either 'enable' or 'disable'.
        :return: The updated Remote Config template with the banner option set.
        """

        if banner_option is None:
            raise ValueError("banner_type must be provided")

        if banner_option == "disable":
            config_file = f'{scenario}_disabled.json'
        elif banner_option == "enable":
            config_file = f'{scenario}_enabled.json'
        else:
            raise ValueError(
                "Invalid banner_type. Must be 'disable' or 'enable'.")

        with open(config_file, 'r') as f:
            data = json.load(f)

            for group, group_data in data.get('parameterGroups', {}).items():
                # update remote config current with the new values
                remote_config_current['parameterGroups'][group] = group_data

            return remote_config_current

    def _save_remote_config(self, response: dict):
        """Save the Remote Config template to a local file.

        :param response: The response from the Remote Config API containing the template.
        :return: The name of the file where the template is saved.
        """

        timestamp = datetime.now().strftime('%Y%m%d%H%M')
        remote_file_name = f'config_{timestamp}.json'

        with io.open(remote_file_name, 'wb') as f:
            f.write(response)

        logger.info(
            f'Retrieved template has been written to {remote_file_name}')

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

        # remove version key from response
        new_resp = json.loads(resp.content)

        etag = resp.headers.get('ETag', None)
        if etag is None:
            logger.error('ETag not found in response headers.')
            return None, None

        file_response = json.dumps(new_resp).encode('utf-8')
        if resp.status_code == 200:
            return etag, self._save_remote_config(file_response)
        else:
            logger.error(
                'Error retrieving template: {}'.format(resp.status_code))
            logger.error('Response: {}'.format(resp.text))

    def update_remote_config(self, remote_config_file: str, etag: str, scenario: str, banner_option: str):
        """Update the Firebase Remote Config template on server.

        :param remote_config_file: The local file containing the Remote Config template.
        :param etag: The ETag of the current Remote Config template.
        :param scenario: The scenario for which the banner option is to be updated.
        :param banner_option: The banner option to be set, either 'enable' or 'disable'.
        """
        headers = {
            'Authorization': 'Bearer ' + self._get_access_token(),
            'Content-Type': 'application/json',
            'If-Match': etag
        }

        with open(remote_config_file, 'rb') as file:

            remote_config_file = json.load(file)
            data = self.update_parameter_group(
                remote_config_current=remote_config_file, scenario=scenario, banner_option=banner_option)
            if data is None:
                logger.error(
                    'No data found for the given scenario and banner option.')
                raise ValueError(
                    'No data found for the given scenario and banner option.')
            

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

    rollback = False
    if rollback is True:
        # Example rollback to version 1
        version_to_rollback = "21"
        remote_config_service._rollback(version_to_rollback)
    else:
        etag, config_file = remote_config_service.get_remote_config()
        scenario = 'scenario1'
        banner_option = 'disable'  # or 'enable'
        remote_config_service.update_remote_config(
            config_file, etag=etag, scenario=scenario, banner_option=banner_option)
        logger.info('Remote config update process completed.')
