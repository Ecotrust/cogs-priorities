# Django settings for omm project.
from madrona.common.default_settings import *

APP_NAME = "COGS-Priorities"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'wp',
        'USER': 'postgres', }
}

GEOMETRY_DB_SRID = 3857

TIME_ZONE = 'America/Vancouver'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = ( os.path.realpath(os.path.join(os.path.dirname(__file__), 'templates').replace('\\','/')), )

INSTALLED_APPS += ( 'seak', 
                    'djkombu',
                    'madrona.analysistools',
                    'madrona.layer_manager',
                    'django.contrib.humanize',) 


COMPRESS_CSS['application']['source_filenames'] = (
    'common/css/jquery-ui.css',
    'common/css/ui.theme.css',
    'seak/css/seak.css',
    'theme/default/style.css',
)

COMPRESS_JS['application']['source_filenames'] = (
    'common/js/json2.js',
    'features/js/workspace.js',
    'seak/js/seak.js',
    'seak/js/scenario.js',
    'seak/js/form_targetvalues.js',
)

# The following is used to assign a name to the default folder under My Shapes 
KML_UNATTACHED_NAME = 'Areas of Inquiry'

KML_ALTITUDEMODE_DEFAULT = 'clampToGround'

#These two variables are used to determine the extent of the zoomed in image in madrona.staticmap
#If one or both are set to None or deleted entirely than zoom will default to a dynamic zoom generator
STATICMAP_WIDTH_BUFFER = None
STATICMAP_HEIGHT_BUFFER = None

CELERY_IMPORT = ('seak.tasks',)

MARXAN_BIN =  os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'marxan_bin','MarOpt_v243_Linux64')) 
MARXAN_OUTDIR =  os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'marxan_output'))
MARXAN_TEMPLATEDIR = os.path.join(MARXAN_OUTDIR, 'template')
MARXAN_NUMREPS = 20
MARXAN_NUMITNS = 2250000

N_BULK_CREATE = 2000  # How many items do we store in memory while importing before hitting the DB

LOG_FILE = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'logs', 'seak.log'))
MEDIA_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'mediaroot'))
TILE_CONFIG_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'tile_config'))

ENFORCE_SUPPORTED_BROWSER = False

# ecotrust.org
GOOGLE_API_KEY = 'ABQIAAAAIcPbR_l4h09mCMF_dnut8RQbjMqOReB17GfUbkEwiTsW0KzXeRQ-3JgvCcGix8CM65XAjBAn6I0bAQ'

TEMPLATE_DEBUG = False
LOGIN_REDIRECT_URL = '/'
HELP_EMAIL = 'ksdev@ecotrust.org'

#######################################
# IMPORTANT
# One redis database for everything, unique to this app
# Must NOT conflict with other apps on this server
#######################################
APP_REDIS_DB = 2

# Use redis_sessions 
SESSION_ENGINE = 'redis_sessions.session'
SESSION_REDIS_HOST = 'localhost'
SESSION_REDIS_PORT = 6379
SESSION_REDIS_DB = APP_REDIS_DB
SESSION_REDIS_PREFIX = 'priorities-session'

# Redis for caching
CACHES = {
    "default": {
        "BACKEND": "redis_cache.cache.RedisCache",
        "LOCATION": "localhost:6379:%d" % APP_REDIS_DB,
        "OPTIONS": {
            "CLIENT_CLASS": "redis_cache.client.DefaultClient",
        }
    }
}

# Redis for celery
BROKER_URL = 'redis://localhost:6379/%d' % APP_REDIS_DB
BROKER_TRANSPORT_OPTIONS = {'visibility_timeout': 43200}  # 12 hours
CELERY_RESULT_BACKEND = 'redis://localhost:6379/%d' % APP_REDIS_DB
CELERY_ALWAYS_EAGER = False
CELERY_DISABLE_RATE_LIMITS = True
CELERY_TIMEZONE = 'UTC'
CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']
import djcelery
djcelery.setup_loader()

import logging
logging.getLogger('django.db.backends').setLevel(logging.INFO)
logging.getLogger('django.db.backends').setLevel(logging.ERROR)

# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'rotatefile': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': LOG_FILE,
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'standard',
        }, 
    },
    'loggers': {
        'django.db.backends': {
            'handlers':['rotatefile'],
            'propagate': False,
            'level':'INFO',
        },
        'madrona.models': {
            'handlers':['rotatefile'],
            'propagate': False,
            'level':'INFO',
        },
        'seak.models': {
            'handlers':['rotatefile'],
            'propagate': False,
            'level':'DEBUG',
        },
        '': {
            'handlers': ['rotatefile'],
            'level': 'WARNING',
        },
    }
}

SLIDER_MODE = "single" # 'dual' OR 'single'
SLIDER_SHOW_RAW = False
SLIDER_SHOW_PROPORTION = True
SLIDER_START_COLLAPSED = True
VARIABLE_GEOGRAPHY = False # do we allow variable geographies (True) or just use all planning units (False)?
SHOW_RAW_COSTS = False # in report
SHOW_ALL_COSTS = True # in report
SHOW_AUX = False # in report
SHOW_GOAL_MET = True # in report
USE_BLM = True  # Use boundary length modifier?

JS_OPTS = {
    'start_zoom': 3,  
    'num_levels': 9,  
    'center': {'lon': -96, 'lat': 39},
    'extent': [-127.1, 25.0, -62.0, 51.0],
    'name_field': 'NAME',
    'sigfigs': 3,
    'zoom_on_select': False,
}

ADD_SCALEFACTOR_CONSTANT = 5 # 0==moderately weight costs, 5==meet targets at (almost) any cost

CACHE_TIMEOUT = 60 * 60 * 24 * 365

#############################################################
try:
    from settings_local import *
except ImportError:
    pass

# makes djcelery and djkombu happy?
DATABASE_ENGINE = DATABASES['default']['ENGINE']
DATABASE_NAME = DATABASES['default']['NAME']
DATABASE_USER = DATABASES['default']['USER']



if not os.path.exists(MEDIA_ROOT):
    os.makedirs(MEDIA_ROOT)

if not os.path.exists(MARXAN_TEMPLATEDIR):
    os.makedirs(MARXAN_TEMPLATEDIR)

def get_tile_config():
    import TileStache as tilestache
    pth = os.path.join(TILE_CONFIG_DIR, 'tiles.cfg')
    try:
        cfg = tilestache.parseConfigfile(pth)
    except (IOError, ValueError):
        cfg = None
    return cfg

TILE_CONFIG = get_tile_config()

if DEBUG:
    try:
        import gunicorn
        INSTALLED_APPS += ('gunicorn',)
    except ImportError:
        pass
