import os
import glob
import shutil
from django.conf import settings
from django.contrib.gis.db import models
from django.core.cache import cache
from django.template.defaultfilters import slugify
from django.utils.html import escape
from django.db.models.signals import post_delete
from django.dispatch.dispatcher import receiver
from madrona.features import register, alternate
from madrona.features.models import FeatureCollection
from madrona.unit_converter.models import area_in_display_units
from madrona.analysistools.models import Analysis
from madrona.common.utils import asKml
from madrona.async.ProcessHandler import process_is_running, process_is_complete, \
    process_is_pending, get_process_result, process_is_complete, check_status_or_begin
from madrona.common.utils import get_logger
from seak.tasks import marxan_start
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import simplejson as json
from madrona.common.models import KmlCache
from jenks import jenks as get_jenks_breaks
from collections import defaultdict
import redis

logger = get_logger()

# connection must match the cache set in scenario_tiles view
redisconn = redis.Redis(host='localhost', port=6379, db=settings.APP_REDIS_DB)

def cachemethod(cache_key, timeout=60*60*24*365):
    '''
    http://djangosnippets.org/snippets/1130/    
    Cacheable class method decorator
    from madrona.common.utils import cachemethod

    @property
    @cachemethod("SomeClass_get_some_result_%(id)s")
    '''
    def paramed_decorator(func):
        def decorated(self):
            key = cache_key % self.__dict__
            res = cache.get(key)
            if res == None:
                res = func(self)
                cache.set(key, res, timeout)
                #if cache.get(key) != res:
                #    logger.error("*** Cache GET was NOT successful, %s" % key)
            return res
        return decorated 
    return paramed_decorator


class JSONField(models.TextField):
    """JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly"""
    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""
        if value == "":
            return None
        # Actually we'll just return the string
        # need to explicitly call json.loads(X) in your code
        # reason: converting to dict then repr that dict in a form is invalid json
        # i.e. {"test": 0.5} becomes {u'test': 0.5} (not unicode and single quotes)
        return value

    def get_db_prep_save(self, value, *args, **kwargs):
        """Convert our JSON object to a string before we save"""
        if value == "":
            return None
        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)

        return super(JSONField, self).get_db_prep_save(value, *args, **kwargs)

# http://south.readthedocs.org/en/latest/customfields.html#extending-introspection
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^seak\.models\.JSONField"])

class ConservationFeature(models.Model):
    '''
    Django model representing Conservation Features (typically species)
    '''
    name = models.CharField(max_length=99)
    level1 = models.CharField(max_length=99)
    level2 = models.CharField(max_length=99, null=True, blank=True)
    dbf_fieldname = models.CharField(max_length=15, null=True, blank=True)
    units = models.CharField(max_length=90, null=True, blank=True)
    desc = models.TextField(null=True, blank=True)
    uid = models.IntegerField(primary_key=True)

    @property
    @cachemethod("seak_conservationfeature_%(uid)s_total_amount")
    def total_amount(self):
        return sum([x.amount for x in self.puvscf_set.all() if x.amount])

    @property
    def level_string(self):
        """ All levels concatenated with --- delim """
        levels = [self.level1, self.level2] #, self.level3, self.level4, self.level5]
        return '---'.join([slugify(x.lower()) for x in levels])

    @property
    def id_string(self):
        """ Relevant levels concatenated with --- delim """
        levels = [self.level1, self.level2] #, self.level3, self.level4, self.level5]
        return '---'.join([slugify(x.lower()) for x in levels if x not in ['', None]])

    def __unicode__(self):
        return u'%s' % self.name

class Aux(models.Model):
    '''
    Django model representing Auxillary data (typically planning unit metrics to be used in reports
    but *not* in the prioritization as costs or targets)
    '''
    name = models.CharField(max_length=99)
    uid = models.IntegerField(primary_key=True)
    dbf_fieldname = models.CharField(max_length=15, null=True, blank=True)
    units = models.CharField(max_length=16, null=True, blank=True)
    desc = models.TextField()

class Cost(models.Model):
    '''
    Django model representing Costs (typically planning unit metrics which are considered
    "costly")
    '''
    name = models.CharField(max_length=99)
    uid = models.IntegerField(primary_key=True)
    dbf_fieldname = models.CharField(max_length=15, null=True, blank=True)
    units = models.CharField(max_length=16, null=True, blank=True)
    desc = models.TextField(null=True, blank=True)

    @property
    @cachemethod("seak_cost_%(uid)s_ordered_puvscosts")
    def ordered_puvscosts(self):
        return list(self.puvscost_set.all().order_by('pu'))

    @property
    def slug(self):
        return slugify(self.name.lower())

    def __unicode__(self):
        return u'%s' % self.name

class PlanningUnit(models.Model):
    '''
    Django model representing polygon planning units
    '''
    fid = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    geometry = models.MultiPolygonField(srid=settings.GEOMETRY_DB_SRID, 
            null=True, blank=True, verbose_name="Planning Unit Geometry")
    calculated_area = models.FloatField(null=True, blank=True) # pre-calculated in GIS
    objects = models.GeoManager()
    date_modified = models.DateTimeField(auto_now=True)

    @property
    @cachemethod("PlanningUnit_%(fid)s_area")
    def area(self):
        if self.calculated_area:
            area = self.calculated_area
        else:
            # assume storing meters and returning acres
            area = self.geometry.area * 0.000247105
        return area

    @property
    @cachemethod("PlanningUnit_%(fid)s_centroid")
    def centroid(self):
        centroid = self.geometry.point_on_surface.coords
        return centroid

    def __unicode__(self):
        return u'%s' % self.name

    @property
    @cachemethod("PlanningUnit_%(fid)s_cffields")
    def conservation_feature_fields(self):
        cfs = PuVsCf.objects.filter(pu=self, amount__isnull=False).select_related()
        return [x.cf.dbf_fieldname for x in cfs]

    @property
    @cachemethod("PlanningUnit_%(fid)s_costfields")
    def cost_fields(self):
        cfs = PuVsCost.objects.filter(pu=self, amount__isnull=False).select_related()
        return [x.cost.dbf_fieldname for x in cfs]

class DefinedGeography(models.Model):
    '''
    A subset of planning units that can be refered to by name 
    '''
    name = models.CharField(max_length=99)
    planning_units = models.ManyToManyField(PlanningUnit)

    @property
    def planning_unit_fids(self):
        return json.dumps([x.fid for x in self.planning_units.all()])

    @property
    def slug(self):
        return slugify(self.name)

    def __unicode__(self):
        return self.name

class PuVsCf(models.Model):
    '''
    The conservation feature value per planning unit
    '''
    pu = models.ForeignKey(PlanningUnit)
    cf = models.ForeignKey(ConservationFeature)
    amount = models.FloatField(null=True, blank=True)
    class Meta:
        unique_together = ("pu", "cf")

class PuVsCost(models.Model):
    '''
    The cost feature value per planning unit
    '''
    pu = models.ForeignKey(PlanningUnit)
    cost = models.ForeignKey(Cost)
    amount = models.FloatField(null=True, blank=True)
    class Meta:
        unique_together = ("pu", "cost")

class PuVsAux(models.Model):
    '''
    Auxillary data values per planning unit
    i.e. data associated with planning units 
         useful for reports, data not used as a cost or a target.
    '''
    pu = models.ForeignKey(PlanningUnit)
    aux = models.ForeignKey(Aux)
    value = models.TextField(null=True, blank=True)
    class Meta:
        unique_together = ("pu", "aux")

    @property
    def amount(self):
        try:
            amt = float(self.value)
        except:
            amt = None
        return amt

def scale_list(vals, floor=None):
    """
    If floor is None, Scales a list of floats linearly between 100*min/max and 100 
    Otherwise, scales a list of floats linearly between floor and 100 
    """
    if len(vals) < 1:
        return []
    nonull_vals = []
    for v in vals:
        if v is not None:
            nonull_vals.append(v)
        else:
            logger.error("WARNING: null value enountered in a scaled list: assuming zero!")
            nonull_vals.append(0)
    minval = min(nonull_vals)
    maxval = max(nonull_vals)
    high = 100.0
    if floor is None:
        try:
            low = 100.0 * float(minval)/maxval
        except ZeroDivisionError:
            low = 0
    else:
        low = floor
    if maxval == minval: 
        return [0] * len(vals)
    scaled = [high - (z / float(maxval - minval)) for z in 
                [(high - low) * y for y in 
                    [maxval - x for x in nonull_vals]]] 
    return scaled

@register
class Scenario(Analysis):
    '''
    Madrona feature for prioritization scenario
    '''
    input_targets = JSONField(verbose_name='Target Percentage of Habitat')
    input_penalties = JSONField(verbose_name='Penalties for Missing Targets') 
    input_relativecosts = JSONField(verbose_name='Relative Costs')
    input_geography = JSONField(verbose_name='Input Geography fids', null=True, blank=True) 
    input_scalefactor = models.FloatField(default=0.0) 
    description = models.TextField(default="", null=True, blank=True, verbose_name="Description/Notes")

    # All output fields should be allowed to be Null/Blank
    output_best = JSONField(null=True, blank=True, verbose_name="Watersheds in Optimal Reserve")
    output_pu_count = JSONField(null=True, blank=True)

    @property
    def outdir(self):
        # make sure we only get 1000 scenarios per subdirectory 
        # some filesystems (ext2/3) have a 32000 limit on number of directories; this raises it to 32 mil
        subdir = str(int(self.id / 1000.0))
        return os.path.realpath(os.path.join(settings.MARXAN_OUTDIR, subdir, "%s_" % (self.uid,) ))
        # This is not asycn-safe! A new modificaiton will clobber the old. 
        # What happens if new and old are both still running - small chance of a corrupted mix of output files? 

    @property
    def expired(self):
        if self.date_modified < PlanningUnit.objects.latest('date_modified').date_modified:
            return True
        else:
            return False

    def copy(self, user):
        """ Override the copy method to make sure the marxan files get copied """
        orig = self.outdir
        copy = super(Scenario, self).copy(user)
        shutil.copytree(orig, copy.outdir, symlinks=True)
        copy.save(rerun=False)
        return copy

    def process_dict(self, d):
        """
        Use the levels in the ConservationFeature table to determine the 
        per-species value based on the specified levels.
        Input:
         {
             'widespread---trout': 0.5,
             'widespread---lamprey': 0.4,
             'widespread---salmon': 0.3,
             'widespread---steelhead': 0.2,
             'locally endemic': 0.1,
         }

        Return:
        species pk is the key
        { 1: 0.5, 2: 0.5, ......}
        """
        ndict = {}
        for cf in ConservationFeature.objects.all():
            # TODO don't assume fields are valid within the selected geography
            levels = cf.level_string
            val = 0
            for k, v in d.items():
                if levels.startswith(k.lower()):
                    val = v
                    break
            ndict[cf.pk] = val
        return ndict

    def invalidate_cache(self):
        '''
        Remove any cached values associated with this scenario.
        Warning: additional caches will need to be added to this method
        '''
        if not self.id:
            return True

        # depends on django-redis as the cache backend!!!
        # assumes that all caches associated with this scenario contain <uid>_*
        key_pattern = "%s_*" % self.uid
        cache.delete_pattern(key_pattern)

        # remove the xml file
        try:
            os.remove(self.mapnik_xml_path)
        except OSError:
            pass

        # delete the tiles directly (and any remaining )
        [redisconn.delete(x) for x in redisconn.keys(pattern="*%s*" % self.uid)]

        # remove the PlanningUnitShapes
        PlanningUnitShapes.objects.filter(stamp=self.id).delete()

        return True

    def run(self):
        '''
        Fire off the marxan analysis
        '''
        from seak.marxan import MarxanAnalysis
        self.invalidate_cache()

        # create the target and penalties
        targets = self.process_dict(json.loads(self.input_targets))
        penalties = self.process_dict(json.loads(self.input_penalties))
        cost_weights = json.loads(self.input_relativecosts)

        #geography_fids = json.loads(self.input_geography)
        geography_fids = []

        assert len(targets.keys()) == len(penalties.keys())
        assert max(targets.values()) <= 1.0
        assert min(targets.values()) >=  0.0

        nonzero_pks = [k for k, v in targets.items() if v > 0] 
        nonzero_targets = []
        nonzero_penalties = []
        for nz in nonzero_pks:
            nonzero_targets.append(targets[nz])
            nonzero_penalties.append(penalties[nz])
            
        maxtarget = max(nonzero_targets)
        avgtarget = float(sum(nonzero_targets))/float(len(nonzero_targets))

        # ignore input, choose a scalefactor automatically based on avg and max target
        self.input_scalefactor = 1 + (avgtarget * 2) + (maxtarget * 2) + settings.ADD_SCALEFACTOR_CONSTANT
        if self.input_scalefactor < 0.5: # min of 0.5
            self.input_scalefactor = 0.5

        # Apply the target and penalties
        logger.debug("Creating the MarxanAnalysis object")
        cfs = []

        if settings.VARIABLE_GEOGRAPHY:
            pus = PlanningUnit.objects.select_related().filter(fid__in=geography_fids).order_by('fid')
        else:
            puqs = PlanningUnit.objects.select_related().all().order_by('fid')

        cfs_qs = ConservationFeature.objects.all()
        for cf in cfs_qs:
            if settings.VARIABLE_GEOGRAPHY:
                # big performance bottleneck
                total = sum([x.amount for x in cf.puvscf_set.filter(pu__in=puqs) if x.amount])
            else:
                total = cf.total_amount
            target_prop = targets[cf.pk]
            # only take 99.9% at most to avoid rounding errors 
            # which lead Marxan to believe that the target is unreachable
            if target_prop >= 0.999:
                target_prop = 0.999 
            target = total * target_prop 
            penalty = penalties[cf.pk] * self.input_scalefactor
            # MUST include all species even if they are zero
            cfs.append((cf.pk, target, penalty, cf.name))

        final_cost_weights = {}
        for cost in Cost.objects.all():
            costkey = cost.slug
            try:
                final_cost_weights[costkey] = cost_weights[costkey]
            except KeyError:
                final_cost_weights[costkey] = 0

        raw_costs = defaultdict(list)

        for cost in Cost.objects.all():
            costkey = cost.slug
            if settings.VARIABLE_GEOGRAPHY:
                # big performance bottleneck
                puvscosts = PuVsCost.objects.filter(cost=cost, pu__in=puqs).order_by('pu')
            else:
                puvscosts = cost.ordered_puvscosts
            raw_costs[costkey] = [x.amount for x in puvscosts]

        pus = [pu.fid for pu in puqs] # assume this ordering matches the costs

        # make sure the lists are aligned
        len_pus = len(pus)
        for k, v in raw_costs.items():
            assert len_pus == len(v)

        # scale, weight and combine costs
        weighted_costs = {}
        for costkey, costs in raw_costs.iteritems():
            if None in costs:
                logger.debug("Warning: skipping ", costkey, "; contains nulls in this geography")
                continue
            weighted_costs[costkey] = [x * final_cost_weights[costkey] for x in scale_list(costs)]
        final_costs = [sum(x) for x in zip(*weighted_costs.values())] 
        final_costs = [1.0 if x < 1.0 else x for x in final_costs] # enforce a minimum cost of 1.0
        pucosts = zip(pus, final_costs)

        m = MarxanAnalysis(pucosts, cfs, self.outdir, self.id)

        logger.debug("Firing off the marxan process")
        check_status_or_begin(marxan_start, task_args=(m,), polling_url=self.get_absolute_url())
        return True

    @property
    def numreps(self):
        try:
            with open(os.path.join(self.outdir,"input.dat")) as fh:
                for line in fh.readlines():
                    if line.startswith('NUMREPS'):
                        return int(line.strip().replace("NUMREPS ",""))
        except IOError:
            # probably hasn't started processing yet
            return settings.MARXAN_NUMREPS

    @property
    def progress(self):
        path = os.path.join(self.outdir, "output", "seak_r*.csv")
        outputs = glob.glob(path)
        numreps = self.numreps
        repsdone = len(outputs)

        if repsdone == numreps:
            if not self.done:
                return (0, numreps)

        return (repsdone, numreps)

    def geojson(self, srid=None):
        # Note: no reprojection support here 
        rs = self.results

        if 'bbox' in rs: 
            bbox = rs['bbox']
        else:
            bbox = None
   
        fullname = self.user.get_full_name()
        if fullname == '':
            fullname = self.user.username

        error = False
        if self.status_code == 0:
            error = True

        serializable = {
            "type": "Feature",
            "bbox": bbox,
            "geometry": None,
            "properties": {
               'uid': self.uid, 
               'bbox': bbox,
               'name': self.name, 
               'done': self.done, 
               'error': error,
               'sharing_groups': [x.name for x in self.sharing_groups.all()],
               'expired': self.expired,
               'description': self.description,
               'date_modified': self.date_modified.strftime("%m/%d/%y %I:%M%P"),
               'user': self.user.username,
               'user_fullname': fullname,
               #'selected_fids': selected_fids,
               #'potential_fids': json.loads(self.input_geography)
            }
        }
        return json.dumps(serializable)

    @cachemethod("consfeat_dict")
    def consfeat_dict(self):
        #consfeats = dict([(x.pk, x.__dict__) for x in ConservationFeature.objects.prefetch_related('puvscf_set')])
        consfeats = []
        for cf in ConservationFeature.objects.prefetch_related('puvscf_set'):
            dd = cf.__dict__
            dd['amount'] = sum([x.amount for x in cf.puvscf_set.all() if x.amount])
            del dd['_prefetched_objects_cache']
            consfeats.append((cf.pk, dd))
        return dict(consfeats)
        
    @property
    @cachemethod("seak_scenario_%(id)s_results")
    def results(self):
        targets = json.loads(self.input_targets)
        penalties = json.loads(self.input_penalties)
        cost_weights = json.loads(self.input_relativecosts)

        targets_penalties = {}
        for k, v in targets.items():
            targets_penalties[k] = {'label': k.replace('---', ' > ').replace('-',' ').title(), 'target': v, 'penalty': None}
        for k, v in penalties.items():
            try:
                targets_penalties[k]['penalty'] = v
            except KeyError:
                # this should never happen but just in case
                targets_penalties[k] = {'label': k.replace('---', ' > ').title(), 'target': None, 'penalty': v}

        species_level_targets = self.process_dict(targets)
        if not self.done:
            return {'targets_penalties': targets_penalties, 'costs': cost_weights}

        logger.debug("Calculating results for %s" % self.uid)


        fh = open(os.path.join(self.outdir, "output", "seak_mvbest.csv"), 'r')
        lines = [x.strip().split(',') for x in fh.readlines()[1:]]
        fh.close()
        species = []
        num_target_species = 0
        num_met = 0
        consfeats = self.consfeat_dict()
        for line in lines:
            sid = int(line[0])
            try:
                consfeat = consfeats[sid]
            except ConservationFeature.DoesNotExist:
                logger.error("ConservationFeature %s doesn't exist; refers to an old scenario?" % sid)
                continue

            sname = consfeat["name"]
            sunits = consfeat["units"]
            slevel1 = consfeat["level1"]
            scode = consfeat["dbf_fieldname"]
            starget = float(line[2])
            try:
                starget_prop = species_level_targets[sid]
            except KeyError:
                continue
            sheld = float(line[3])
            stotal = consfeat['amount']
            try:
                spcttotal = sheld/stotal 
            except ZeroDivisionError:
                spcttotal = 0
            smpm = float(line[9])
            if starget == 0:
                smpm = 0.0
            smet = False
            if line[8] == 'yes' or smpm > 1.0:
                smet = True
                num_met += 1
            s = {'name': sname, 'id': sid, 'target': starget, 'units': sunits, 'code': scode, 
                    'held': sheld, 'met': smet, 'pct_target': smpm, 'level1': slevel1, 
                    'pcttotal': spcttotal, 'target_prop': starget_prop }
            species.append(s)      
            if starget > 0:
                num_target_species += 1

        species.sort(key=lambda k:k['name'].lower())

        costs = {}
        for k,v in cost_weights.iteritems():
            name = k.replace("-", " ").title()
            costs[name] = v

        res = {
            'costs': costs, #cost_weights
            'targets_penalties': targets_penalties,
            'num_met': num_met,
            'num_species': num_target_species, #len(species),
            'species': species, 
        }

        # trigger caching of hit maps
        logger.debug("Trigger caching of scenario maps")
        self.thunderstorm_sql()
        self.mapnik_xml()

        return res
        
    @property
    def status_html(self):
        return self.status[1]

    @property
    def status_code(self):
        return self.status[0]
    
    @property
    def status(self):
        url = self.get_absolute_url()
        if process_is_running(url):
            status = """Analysis is currently running."""
            if self.progress[0] == 0:
                status += " (Pre-processing)"
            code = 2
        elif process_is_complete(url):
            status = "Analysis completed. Compiling results..."
            code = 3
        elif process_is_pending(url):
            status = "Analysis is in the queue but not yet running."
            res = get_process_result(url)
            code = 1
            if res is not None:
                status += ".. "
                status += str(res)
        else:
            status = "An error occured while running this analysis."
            code = 0
            res = get_process_result(url)
            if res is not None:
                status += "..<br/> "
                status += str(res)
            status += "<br/>Please edit the scenario and try again. If the problem persists, please contact us."

        return (code, "<p>%s</p>" % status)

    def process_output(self):
        if process_is_complete(self.get_absolute_url()):
            chosen = get_process_result(self.get_absolute_url())
            wshds = PlanningUnit.objects.filter(pk__in=chosen)
            self.output_best = json.dumps({'best': [str(x.pk) for x in wshds]})
            ssoln = [x.strip().split(',') for x in 
                     open(os.path.join(self.outdir,"output","seak_ssoln.csv"),'r').readlines()][1:]
            selected = {}
            for s in ssoln:
                num = int(s[1])
                if num > 0:
                    selected[int(s[0])] = num
            self.output_pu_count = json.dumps(selected) 
            super(Analysis, self).save() # save without calling save()
            self.invalidate_cache()

    @property
    def done(self):
        """ Boolean; is MARXAN process complete? """
        done = True
        if self.output_best is None: 
            done = False
        if self.output_pu_count is None: 
            done = False

        if not done:
            done = True
            # only process async results if output fields are blank
            # this means we have to recheck after running
            self.process_output()
            if self.output_best is None: 
                done = False
            if self.output_pu_count is None: 
                done = False
        return done

    @classmethod
    def mapnik_geomfield(self):
        return "output_geometry"

    @property
    def color(self):
        # colors are ABGR
        colors = [
         'aa0000ff',
         'aaff0000',
         'aa00ffff',
         'aaff00ff',
        ]
        return colors[self.pk % len(colors)]

    @property 
    def kml_done(self):
        key = "watershed_kmldone_%s_%s" % (self.uid, slugify(self.date_modified))
        kmlcache, created = KmlCache.objects.get_or_create(key=key)
        kml = kmlcache.kml_text
        if not created and kml:
            logger.warn("%s ... kml cache found" % key)
            return kml
        logger.warn("%s ... NO kml cache found ... seeding" % key)

        ob = json.loads(self.output_best)
        wids = [int(x.strip()) for x in ob['best']]
        puc = json.loads(self.output_pu_count)
        method = "best" 
        #method = "all"
        if method == "best":
            wshds = PlanningUnit.objects.filter(pk__in=wids)
        elif method == "all":
            wshds = PlanningUnit.objects.all()

        kmls = []
        color = self.color
        #color = "cc%02X%02X%02X" % (random.randint(0,255),random.randint(0,255),random.randint(0,255))
        for ws in wshds:
            try:
                hits = puc[str(ws.pk)] 
            except KeyError:
                hits = 0

            if method == "all":
                numruns = settings.MARXAN_NUMREPS
                prop = float(hits)/numruns
                scale = (1.4 * prop * prop) 
                if scale > 0 and scale < 0.5: 
                    scale = 0.5
                desc = "<description>Included in %s out of %s runs.</description>" % (hits, numruns)
            else:
                prop = 1.0
                scale = 1.2
                desc = ""

            if prop > 0:
                kmls.append( """
            <Style id="style_%s">
                <IconStyle>
                    <color>%s</color>
                    <scale>%s</scale>
                    <Icon>
                        <href>http://maps.google.com/mapfiles/kml/shapes/shaded_dot.png</href>
                    </Icon>
                </IconStyle>
                <LabelStyle>
                    <color>0000ffaa</color>
                    <scale>0.1</scale>
                </LabelStyle>
            </Style>
            <Placemark id="huc_%s">
                <visibility>1</visibility>
                <name>%s</name>
                %s
                <styleUrl>style_%s</styleUrl>
                %s
            </Placemark>
            """ % (ws.fid, color, scale, ws.fid, ws.name, desc, ws.fid, asKml(ws.geometry.point_on_surface)))


        fullkml = """%s
          <Folder id='%s'>
            <name>%s</name>
            %s
          </Folder>""" % (self.kml_style, 
                          self.uid, 
                          escape(self.name), 
                          '\n'.join(kmls))

        kmlcache.kml_text = fullkml
        kmlcache.save()
        return fullkml
       
    @property 
    def kml_working(self):
        code = self.status_code
        if code == 3: 
            txt = "completed"
        elif code == 2: 
            txt = "in progress"
        elif code == 1: 
            txt = "in queue"
        elif code == 0: 
            txt = "error occured"
        else: 
            txt = "status unknown"

        return """
        <Placemark id="%s">
            <visibility>0</visibility>
            <name>%s (%s)</name>
        </Placemark>
        """ % (self.uid, escape(self.name), txt)

    @property
    def kml_style(self):
        return """
        <Style id="selected-watersheds">
            <IconStyle>
                <color>ffffffff</color>
                <colorMode>normal</colorMode>
                <scale>0.9</scale> 
                <Icon> <href>http://maps.google.com/mapfiles/kml/paddle/wht-blank.png</href> </Icon>
            </IconStyle>
            <LabelStyle>
                <color>ffffffff</color>
                <scale>0.8</scale>
            </LabelStyle>
            <PolyStyle>
                <color>7766ffff</color>
            </PolyStyle>
        </Style>
        """

    def thunderstorm_sql(self):
        """
        Write planning units containing a `pucount`
        Effectively a join of the planning units and the marxan output
        Uses the PlanningUnitShapes mechanism with the scenario id as the stamp
        """
        from seak.models import PlanningUnitShapes

        stamp = int(self.id)
        sql = "(SELECT geometry, hits, bests FROM seak_planningunitshapes WHERE stamp = %s) as foo" % stamp 

        if PlanningUnitShapes.objects.filter(stamp=stamp).count() > 0:
            return sql

        pucount = json.loads(self.output_pu_count)
        bests = [int(x) for x in json.loads(self.output_best)['best']]
        pushapes = []

        for pu in PlanningUnit.objects.all():
            try:
                hits = pucount[str(pu.fid)] 
            except KeyError:
                hits = 0

            if pu.fid in bests:
                best = 1
            else:
                best = 0

            pushapes.append(PlanningUnitShapes(stamp=stamp, fid=pu.fid, pu=pu, name=pu.name,
                hits=hits, bests=best, geometry=pu.geometry))

        PlanningUnitShapes.objects.bulk_create(pushapes)
        return sql

    @property  
    def mapnik_xml_path(self):
        return os.path.join(self.outdir, "results.xml")

    def mapnik_xml(self):
        """
        Mapnik representation of the scenario results
        """
        path = self.mapnik_xml_path
        sql = self.thunderstorm_sql()

        if not os.path.exists(path):
            dbs = settings.DATABASES['default']
            context = dbs.copy()
            context['sql'] = sql
            context['a'] = settings.MARXAN_NUMREPS - 2
            context['b'] = round(settings.MARXAN_NUMREPS * 0.7)
            context['c'] = round(settings.MARXAN_NUMREPS * 0.5)
            context['d'] = round(settings.MARXAN_NUMREPS * 0.4)
            context['e'] = round(settings.MARXAN_NUMREPS * 0.3)
            context['f'] = round(settings.MARXAN_NUMREPS * 0.2)

            with open(path, 'w') as fh:
                xml = """<?xml version="1.0"?>
                <!DOCTYPE Map [
                <!ENTITY google_mercator "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs +over">
                ]>
                <Map srs="&google_mercator;">
                    <Style name="pu" filter-mode="first">
                        
                                <Rule>
                                    <Filter>([hits] &gt;= %(a)s)</Filter>
                                    <PolygonSymbolizer fill="#0c2c84" fill-opacity="1.0" gamma=".45" />
                                </Rule>
                                <Rule>
                                    <Filter>([hits] &gt;= %(b)s)</Filter>
                                    <PolygonSymbolizer fill="#225ea8" fill-opacity="1.0" gamma=".45" />
                                </Rule>
                                <Rule>
                                    <Filter>([hits] &gt;= %(c)s)</Filter>
                                    <PolygonSymbolizer fill="#1d91c0" fill-opacity="1.0" gamma=".45" />
                                </Rule>
                                <Rule>
                                    <Filter>([hits] &gt;= %(d)s)</Filter>
                                    <PolygonSymbolizer fill="#41b6c4" fill-opacity="1.0" gamma=".45" />
                                </Rule>
                                <Rule>
                                    <Filter>([hits] &gt;= %(e)s)</Filter>
                                    <PolygonSymbolizer fill="#7fcdbb" fill-opacity="1.0" gamma=".45" />
                                </Rule>
                                <Rule>
                                    <Filter>([hits] &gt;= %(f)s)</Filter>
                                    <PolygonSymbolizer fill="#c7e9b4" fill-opacity="1.0" gamma=".45" />
                                </Rule>
                                <Rule>
                                    <Filter>([hits] &gt;= 1)</Filter>
                                    <PolygonSymbolizer fill="#ffffcc" fill-opacity="1.0" gamma=".45" />
                                </Rule>
                                <Rule>
                                    <Filter>([hits] = 0)</Filter>
                                    <PolygonSymbolizer fill="#ffffff" fill-opacity="1.0" gamma=".45" />
                                </Rule>
                            
                    </Style>
                    <!--
                    <Style name="pu_best">
                        <Rule>
                            <Filter>([bests] &gt;= 1)</Filter>
                            <PointSymbolizer/> 
                            <PolygonSymbolizer fill="#081d58" fill-opacity="1.0" gamma=".45" />
                        </Rule>
                    </Style>
                    -->
                    <Layer name="layer" srs="&google_mercator;">
                        <StyleName>pu</StyleName>
                        <!--
                        <StyleName>pu_best</StyleName>
                        -->
                        <Datasource>
                            <Parameter name="type">postgis</Parameter>
                            <Parameter name="host">%(HOST)s</Parameter>
                            <Parameter name="dbname">%(NAME)s</Parameter>
                            <Parameter name="user">%(USER)s</Parameter>
                            <Parameter name="password">%(PASSWORD)s</Parameter>
                            <Parameter name="table">%(sql)s</Parameter>
                            <Parameter name="estimate_extent">false</Parameter>
                        </Datasource>
                    </Layer>
                </Map>""" % context

                fh.write(xml)

        return path


    class Options:
        form = 'seak.forms.ScenarioForm'
        verbose_name = 'Prioritization Scenario' 
        show_template = 'seak/show.html'
        form_template = 'seak/form.html'
        form_context = {
            'cfs': ConservationFeature.objects.all().order_by('level1', 'name'),
            'defined_geographies': DefinedGeography.objects.all(),
            'costs': Cost.objects.all().order_by('uid'),
            'slider_mode': settings.SLIDER_MODE,
            'slider_show_raw': settings.SLIDER_SHOW_RAW,
            'slider_show_proportion': settings.SLIDER_SHOW_PROPORTION,
            'slider_start_collapsed': settings.SLIDER_START_COLLAPSED,
            'variable_geography': settings.VARIABLE_GEOGRAPHY,
        }
        show_context = {
            'slider_mode': settings.SLIDER_MODE,
            'slider_show_raw': settings.SLIDER_SHOW_RAW,
            'slider_show_proportion': settings.SLIDER_SHOW_PROPORTION,
            'show_raw_costs': settings.SHOW_RAW_COSTS,
            'show_aux': settings.SHOW_AUX,
            'show_goal_met': settings.SHOW_GOAL_MET,
        }
        icon_url = 'common/images/watershed.png'
        links = (
            alternate('Shapefile',
                'seak.views.watershed_shapefile',
                select='single multiple',
                type='application/zip',
            ),
            alternate('Marxan Inputs',
                'seak.views.watershed_marxan',
                select='single',
                type='application/zip',
            ),
            alternate('Tile',
                'seak.views.scenario_tile',
                select='single',
                type='image/png',
            ),
        )

# Post-delete hooks to remove the marxan files
@receiver(post_delete, sender=Scenario)
def _scenario_delete(sender, instance, **kwargs):
    if os.path.exists(instance.outdir):
        try:
            shutil.rmtree(instance.outdir)
            logger.debug("Deleting %s at %s" % (instance.uid, instance.outdir))
        except OSError:
            logger.debug("Can't delete %s; forging ahead anyway..." % (instance.uid,))

@register
class Folder(FeatureCollection):
    description = models.TextField(default="", null=True, blank=True)
        
    class Options:
        verbose_name = 'Folder'
        valid_children = ( 
                'seak.models.Folder',
                'seak.models.Scenario',
                )
        form = 'seak.forms.FolderForm'
        show_template = 'folder/show.html'
        icon_url = 'common/images/folder.png'

class PlanningUnitShapes(models.Model):
    pu = models.ForeignKey(PlanningUnit)
    stamp = models.FloatField(db_index=True)
    bests = models.IntegerField(default=0) 
    hits = models.IntegerField(default=0) 
    fid = models.IntegerField(null=True)
    name = models.CharField(max_length=255, null=True)
    geometry = models.MultiPolygonField(srid=settings.GEOMETRY_DB_SRID, 
            null=True, blank=True, verbose_name="Planning Unit Geometry")
