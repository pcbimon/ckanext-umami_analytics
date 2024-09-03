from typing import Any,AnyStr
from ckan.common import CKANConfig
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import os
import logging
import requests
log = logging.getLogger(__name__)

class UmamiAnalyticsPlugin(plugins.SingletonPlugin):

    plugins.implements(plugins.IConfigurer)
    def __call__(self, environ: Any, start_response: Any) -> Any:
        path = environ.get('PATH_INFO', '')
        if path.startswith('/dataset') and '/resource/' and '/download/' in path:
            self.track_download(environ)
        return self.app(environ, start_response)    
    def track_download(self, environ: Any):
        try:
            resource_id = environ.get('ckan.resource_id')
            user = environ.get('REMOTE_USER', 'anonymous')
            # Check self.token is set
            if not self.token:
                # check if username and password are set
                if not self.username or not self.password:
                    raise Exception('CKAN_UMAMI_ANALYTICS_USERNAME and CKAN_UMAMI_ANALYTICS_PASSWORD must be set in the environment')
                # Get the token
                self.token = self.authenTracking(self.username,self.password)
            else:
                # verify token
                if not self.verifyToken(self.token):
                    # get the token again
                    self.token = self.authenTracking(self.username,self.password)

            # get token
            token = self.token
            # add token to headers Authorization
            headers = {
                'Authorization': f'Bearer {token}'
            }
            download_path = environ.get('PATH_INFO', '')
            # get dataset id,resource id from path /dataset/{dataset_id}/resource/{resource_id}/download/{filename}
            dataset_id = download_path.split('/')[2]
            resource_id = download_path.split('/')[4]
            data = {
                "payload": {
                    "hostname": self.site_url,
                    "title": "download",
                    "url": download_path,
                    "website": self.site_id,
                    "name": "download-resource",
                    "data": {
                        "dataset-id": dataset_id,
                        "resource-id": resource_id,
                    }
                },
                "type": "event"
            }
            # Make the API call
            response = requests.post(self.umami_instance+'/api/send',headers=headers, json=data)
            response.raise_for_status()
            log.info(f"Download tracked for resource: {resource_id} by user: {user}")
        except Exception as e:
            log.error(f"Failed to track download: {e}")
    def authenTracking(self,username:AnyStr,password:AnyStr)->AnyStr:
        login_data = {
                'username': self.username,
                'password': self.password
            }
        response = requests.post(f'{self.umami_instance}/api/auth/login', json=login_data)
        token = response.json().get('token')
        if not token:
            raise Exception('Failed to get token from Umami Analytics')
        # Add the token to the config
        return token
    def verifyToken(self,token:AnyStr)->bool:
        # /api/auth/verify
        headers = {
            'Authorization': f'Bearer {token}'
        }
        response = requests.get(f'{self.umami_instance}/api/auth/verify',headers=headers)
        if response.status_code == 200:
            return True
        else:    
            return False
    # IConfigurer

    def update_config(self, config_: 'CKANConfig'):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "umami_analytics")
        self.umami_instance = os.getenv('CKAN_UMAMI_ANALYTICS_URL', '')
        self.site_id = os.getenv('CKAN_UMAMI_ANALYTICS_SITE_ID', '')
        self.username = os.getenv('CKAN_UMAMI_ANALYTICS_USERNAME', '')
        self.password = os.getenv('CKAN_UMAMI_ANALYTICS_PASSWORD', '')
        self.site_url = os.getenv('CKAN_SITE_URL', '')
        if not self.umami_instance or not self.site_id:
            raise Exception('CKAN_UMAMI_ANALYTICS_URL and CKAN_UMAMI_ANALYTICS_SITE_ID must be set in the environment')
        # if username and password are set, get the token
        if self.username and self.password:
            token = self.authenTracking(self.username,self.password)
            self.token = token
        
        # Inject the script into the <head> section
        script_tag = f'<script defer src="{self.umami_instance}/script.js" data-website-id="{self.site_id}"></script>'
        config_['ckan.template_head_end'] = config_.get('ckan.template_head_end', '') + script_tag

    
