

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': '{{ dbname }}',
        'USER': '{{ dbname }}',
        'PASSWORD': '{{ dbname }}',
        'HOST':'localhost',
    }
}

# This should be a local folder created for use with the install_media command 
MEDIA_ROOT = '{{ project_path}}/mediaroot/'
MEDIA_URL = '/media/'
STATIC_URL = '/media/'

DEBUG = {{ debug }}
TEMPLATE_DEBUG = {{ debug }} 

ADMINS = (('Madrona', 'madrona@ecotrust.org'),)

import logging
logging.getLogger('django.db.backends').setLevel(logging.ERROR)
import os

LOG_FILE = os.path.join(os.path.dirname(__file__),'..','seak.log')
