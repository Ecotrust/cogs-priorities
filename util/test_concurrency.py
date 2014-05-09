from django.core.management import setup_environ
import os
import sys
sys.path.append(os.path.dirname(os.path.join('..','priorities',__file__)))

import settings
setup_environ(settings)
#==================================#
from seak.models import Scenario, ConservationFeature, PlanningUnit, Cost, PuVsCf, PuVsCost
from django.contrib.auth.models import User
from django.utils import simplejson as json
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
import time
import random

def mean(alist):
    floatNums = [float(x) for x in alist]
    return sum(floatNums) / len(alist)

user, created = User.objects.get_or_create(username='mperry')

scalefactors = []
num_species = []
num_units = []

f = 5
n = 15
nc = 1
targets = [0.1, 0.2, 0.3]
penalties = [0.1, 0.2, 0.3]
COUNT = 0

def create_wp(target_dict, penalties_dict, costs_dict, geography_list, sf):
    global COUNT
    COUNT += 1
    print target_dict
    print penalties_dict
    print costs_dict
    print geography_list
    print sf

    with open(os.path.join(os.path.dirname(__file__), 'random_words.txt'),'r') as fh:
        name = ' '.join([x.strip() for x in random.sample(fh.readlines(), 2)])

    name += " - %s" % sf

    wp = Scenario(input_targets = json.dumps( 
           target_dict
        ), 
        input_penalties = json.dumps(
            penalties_dict
        ), 
        input_relativecosts=json.dumps(
            costs_dict
        ), 
        input_geography=json.dumps(
            geography_list 
        ),
        input_scalefactor=sf,
        name= name, user=user)

    return wp


if __name__ == '__main__':
    wp = Scenario.objects.filter(name__startswith="Auto Test Scale Factor")
    wp.delete()

    cfs =  ConservationFeature.objects.all()
    keys = []
    for c in cfs:
        a = c.level_string
        while a.endswith('---'):
            print a
            a = a[:-3]
        keys.append(a)

    fh = open("/tmp/results.csv", 'w+')
    fh.write('ncosts, nspecies, sumpenalties, meanpenalties, scalefactor, numspeciesmet, numplannningunits')
    fh.write('\n')
    fh.flush()

    for i in range(1):
        geography_list = [x.fid for x in PlanningUnit.objects.all()]

        try:
            n = int(n)
            target_dict = {}
            penalty_dict = {}
            # pick n random species
            selected_key = random.sample(keys, n) #'blah---blah'
            if random.choice([True,False]):
                t = random.choice(targets)
                p = random.choice(penalties)
            else:
                t = None
                p = None
            for key in selected_key:
                if t and p:
                    # Use the predetermined for ALL species
                    target_dict[key] = t 
                    penalty_dict[key] = p
                else:
                    # random for each species
                    target_dict[key] = random.choice(targets)
                    penalty_dict[key] = random.choice(penalties)
        except ValueError:
            # ALL species
            t = random.choice(targets)
            p = random.choice(penalties)
            t2 = random.choice(targets)
            p2 = random.choice(penalties)
            target_dict = { "coordinate":t, "uids":t2 } 
            penalty_dict = { "coordinate":p, "uids":p2 } 

        costs_dict = {} 
        for a in random.sample([c.slug for c in Cost.objects.all()], nc):
            costs_dict[a] = 1

        sf = f
        wp = create_wp(target_dict, penalty_dict, costs_dict, geography_list, sf)

        print "####################################"
        print 'targets', wp.input_targets
        print 'penalties', wp.input_penalties
        print 'costs', wp.input_relativecosts

        wp.save()
        #continue 
        while not wp.done:
            time.sleep(2)
            print wp.uid, "  ", wp.status_html

        print wp.uid, "    DONE!"
