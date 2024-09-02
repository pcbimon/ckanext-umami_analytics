from ckan.common import CKANConfig
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import os


class UmamiAnalyticsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    

    # IConfigurer

    def update_config(self, config_: 'CKANConfig'):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "umami_analytics")
        umami_instance = os.getenv('CKAN_UMAMI_ANALYTICS_URL', '')
        site_id = os.getenv('CKAN_UMAMI_ANALYTICS_SITE_ID', '')
        
        # Inject the script into the <head> section
        script_tag = f'<script defer src="{umami_instance}/script.js" data-website-id="{site_id}"></script>'
        config_['ckan.template_head_end'] = config_.get('ckan.template_head_end', '') + script_tag

    
