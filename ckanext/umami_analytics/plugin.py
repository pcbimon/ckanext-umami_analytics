from typing import Any,AnyStr
from ckan.common import CKANConfig
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import os
import logging
import requests

from ckan.types import CKANApp
log = logging.getLogger(__name__)
def authenTracking(username: AnyStr, password: AnyStr, umami_instance: AnyStr) -> AnyStr:
    login_data = {
        'username': username,
        'password': password
    }
    response = requests.post(f'{umami_instance}/api/auth/login', json=login_data)
    token = response.json().get('token')
    if not token:
        raise Exception('Failed to get token from Umami Analytics')
    return token

def verifyToken(token: AnyStr, umami_instance: AnyStr) -> bool:
    headers = {
        'Authorization': f'Bearer {token}'
    }
    response = requests.get(f'{umami_instance}/api/auth/verify', headers=headers)
    return response.status_code == 200
class DownloadTrackingMiddleware(object):
    def __init__(self, app, config): # type: ignore
        self.app = app
        self.config = config

    def __call__(self, environ: Any, start_response: Any) -> Any:
        path = environ.get('PATH_INFO', '')
        # Track download event
        if path.startswith('/dataset') and '/resource/' and '/download/' in path:
            self.track_download(environ)
        return self.app(environ, start_response)    
    def track_download(self, environ: Any):
        try:
            log.info(environ)
            headers = {
                'User-Agent': environ.get('HTTP_USER_AGENT', ''),
            }
            resource_id = environ.get('ckan.resource_id')
            user = environ.get('REMOTE_USER', 'anonymous')
            self.token = os.getenv('CKANEXT_UMAMI_ANALYTICS_TOKEN', '')
            self.umami_instance = os.getenv('CKANEXT_UMAMI_ANALYTICS_URL', '')
            self.username = os.getenv('CKANEXT_UMAMI_ANALYTICS_USERNAME', '')
            self.password = os.getenv('CKANEXT_UMAMI_ANALYTICS_PASSWORD', '')
            self.site_id = os.getenv('CKANEXT_UMAMI_ANALYTICS_SITE_ID', '')
            self.site_url = os.getenv('CKAN_SITE_URL', '').replace('http://', '').replace('https://', '')
            download_path = environ.get('PATH_INFO', '')
            # get dataset id,resource id from path /dataset/{dataset_id}/resource/{resource_id}/download/{filename}
            dataset_id = download_path.split('/')[2]
            resource_id = download_path.split('/')[4]
            data = {
                "payload": {
                    "hostname": self.site_url,
                    "language": "en-US",
                    "referrer": "",
                    "screen": "1920x1080",
                    "title": "resource-download",
                    "url": download_path,
                    "website": self.site_id,
                    "name": "resource-download",
                    "data": {
                        "dataset-id": dataset_id,
                        "resource-id": resource_id,
                    }
                },
                "type": "event"
            }
            log.info('Tracking download')
            log.info(data)
            # Make the API call
            response = requests.post(self.umami_instance+'/api/send',json=data, headers=headers)
            log.info(response.json())
            response.raise_for_status()
            log.info(f"Download tracked for resource: {resource_id} by user: {user}")
        except Exception as e:
            log.error(f"Failed to track download: {e}")

class UmamiAnalyticsPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IMiddleware, inherit=True)

    def make_middleware(self, app: CKANApp, config: 'CKANConfig') -> CKANApp:
        return DownloadTrackingMiddleware(app, config)
    # IConfigurer

    def update_config(self, config_: 'CKANConfig'):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "umami_analytics")
        self.umami_instance = os.getenv('CKANEXT_UMAMI_ANALYTICS_URL', '')
        self.site_id = os.getenv('CKANEXT_UMAMI_ANALYTICS_SITE_ID', '')
        self.username = os.getenv('CKANEXT_UMAMI_ANALYTICS_USERNAME', '')
        self.password = os.getenv('CKANEXT_UMAMI_ANALYTICS_PASSWORD', '')
        self.site_url = os.getenv('CKAN_SITE_URL', '').replace('http://', '').replace('https://', '')
        if not self.umami_instance or not self.site_id:
            raise Exception('CKANEXT_UMAMI_ANALYTICS_URL and CKANEXT_UMAMI_ANALYTICS_SITE_ID must be set in the environment')
        # if username and password are set, get the token
        if self.username and self.password:
            token = authenTracking(self.username, self.password, self.umami_instance)
            # set token to environment
            os.environ['CKANEXT_UMAMI_ANALYTICS_TOKEN'] = token
            log.info('Umami Analytics token is set')
        
        # Inject the script into the <head> section
        script_tag = f'<script defer src="{self.umami_instance}/script.js" data-website-id="{self.site_id}"></script>'
        config_['ckan.template_head_end'] = config_.get('ckan.template_head_end', '') + script_tag

    
