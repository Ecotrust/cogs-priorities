

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

MARXAN_BIN =  os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'marxan_bin', 'MarOpt_v243_Linux32')) # or 64 bit?
MARXAN_OUTDIR =  '{{ project_path }}/marxan_output'  # for vagrant boxes, put this outside the shared dir so we can symlink
MARXAN_TEMPLATEDIR = os.path.join(MARXAN_OUTDIR, 'template')
