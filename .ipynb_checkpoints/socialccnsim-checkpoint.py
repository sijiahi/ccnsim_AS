#####################################################################
#SocialCCNSim, a simulator of caches for Content Centric Networking.
#
#Developed by Cesar A. Bernardini Copyright (C) 2014.
# Copyright (C) 2021 Sijia Zhang <sijia.zhang@buaa.edu.cn>
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Library General Public
#License as published by the Free Software Foundation; either
#version 2 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#Library General Public License for more details.
#
#You should have received a copy of the GNU Library General Public
#License along with this library; if not, write to the
#Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
#Boston, MA  02110-1301, USA. 
#
#####################################################################

import random
from multiprocessing import Queue

import sys
import tempfile
import sqlite3
import sched, time
import re
import optparse
import logging

import threading

from user import User
from topology_manager import TopologyManager, Paths, SocialPaths

import numpy

import logging
logging.basicConfig(filename='example.log',
    level=logging.CRITICAL,
    format='%(asctime)-15s %(message)s'
)

class Executor(object):
    def __init__(self, social_graph, topology, cache_size, caching_strategy, cache_policy, sequence_filename = '', mobility_enabled = False, step_printing = [], topology_file = None):
        self.lock = threading.Lock()
        self.condition = threading.Condition()
        # Configuration
        self.conf = {}
        self.conf['caching_strategy'] = caching_strategy
        self.conf['cache_policy'] = cache_policy
        self.conf['sequence_from_file'] = sequence_filename != ''

        self.conf['step_printing'] = step_printing
        if self.conf['step_printing'] != None:
            self.steps = 0
        else:
            self.steps = None

        # The topology manager handles user connection to CCN nodes.
        logging.debug('Topology manager, connect users started')
        topology_coords = {}
        for node in topology.nodes():
            topology_coords[node] = (
                    random.randint(0, 100),
                    random.randint(0, 100)
            )
        self.topology_nodes = TopologyManager(topology, social_graph, topology_coords, mobility_enabled, topology_file = topology_file)
        self.topology_nodes.set_method('random')
        for user in social_graph.nodes():
            self.topology_nodes.update_user_position(
                user,
                (random.randint(0, 100), random.randint(0, 100))
            )
        self.topology_nodes.update_all_users_position()

        logging.debug('Topology manager, connect users finished')
        
        self.social_graph = social_graph
        self.topology = topology

        #
        self.users = {}
        for user in self.social_graph.nodes():
            self.users[user] = User(user)

        logging.debug('Start simulation')

        self.sched = sched.scheduler(time.time, time.sleep)

        # Generate Sequence
        #print "generate sequence"
        if sequence_filename == '':
            self.generate_sequence()
        else:
            self.initialize_scheduler_from_file(sequence_filename)

        # Initialize Caches
        self.lock.acquire()

        caching_strategy_upper = self.conf['caching_strategy'].upper()
        cm = getattr(getattr(__import__('cache_management.%s'%caching_strategy_upper), caching_strategy_upper), caching_strategy_upper)
        self.caches = cm(
                self.conf['cache_policy'],
                cache_size,
                self.social_graph,
                self.topology,
                self.topology_nodes,
                threshold = None
        )
        logging.debug('Loaded caching strategy')
        self.lock.release()
        self.f = tempfile.NamedTemporaryFile(delete=True, dir='/tmp/')
        self.conn = sqlite3.connect(self.f.name)

        self.c = self.conn.cursor()
        self.initialize_catalog()

        
    def initialize_scheduler(self):
        self.sched = sched.scheduler(time.time, time.sleep)

        self.extract_sequence()

        assert not self.sched.empty()

    #TODO: currently not being used
    def initialize_scheduler_from_file(self, filename):
        self.seq_file = open(filename, 'r')
        self.seq_n = 0
    def extract_sequence(self):
        
        line = self.seq_file.readline()
        while line != '': #Empty line, we reach the end of the sequence
            result = re.match ("(?P<timestamp>[0-9]*\.[0-9]+)\t(?P<activity>Retrieve|Publish|retrieve|publish|Retrievecontent|Publishcontent)\t(?P<user>[0-9]+)\t\((?P<dependent>.*)\)\t\((?P<mobility_x>[0-9\.]*), ?(?P<mobility_y>[0-9\.]*)\)", line)
            if result != None:

                #print step result
                if self.steps != None and self.steps < len(self.conf['step_printing']) and float(result.group('timestamp')) > self.conf['step_printing'][self.steps]:
                    self.sched.enter(self.seq_n * 0.01, 0, self.printStepSummary, (self.conf['step_printing'][self.steps],))
                    self.steps += 1
                
                pos = (float(result.group('mobility_x')), float(result.group('mobility_y')))
                if result.group('activity').lower() in ['publishcontent', 'publish']:
                    self.sched.enter(self.seq_n * 0.01, 0, self.producer2, (int(result.group('user')), pos, "/content/%s"%result.group('dependent').split(',')[0] ))
                    #
                elif result.group(2).lower() == 'retrieve':
                    self.sched.enter(self.seq_n * 0.01, 0, self.consumer, (int(result.group('user')), pos,))
                elif result.group(2).lower() == 'retrievecontent':
                    self.sched.enter(self.seq_n * 0.01, 0, self.consume_from_server, (int(result.group('user')), pos, "/content/%s"%result.group('dependent').split(',')[0]))
                    #
            else:
                print("repr line: %s"%repr(line))
                exit(-1)
            self.seq_n+=1
            line=self.seq_file.readline()

    
    def initialize_catalog(self):


        #c.execute('''DROP table catalog''')
        self.c.execute('''CREATE TABLE catalog
                     (content_name text, publisher int, date double, refer text, refered_level int, topic int)''')

    def generate_sequence(self, sequence = []):
        assert type(sequence) == list
        
        if sequence == []:
            self.sequence = [random.randint(0, len(self.social_graph.nodes())-1) \
                for i in range(0, len(self.social_graph)*40)]
            random.shuffle(self.sequence)
        else:
            self.sequence = sequence

    def run(self):
        #print "the process begins"
        self.initialize_scheduler()
        self.sched.run()
        time.sleep(2)

        
    def __del__(self):
        if self.conn:
            self.conn.close()

    def producer2(self, social_publisher, position, content, reference = '', topic = 0):
        self.topology_nodes.update_user_position(social_publisher, position)
        self.caches.incr_publish()

        #content_name = "/friend%i/%i"%(social_publisher, self.stats.increase_messages())
        content_name = "%s"%content
        _new_content_name = content_name
        if reference == '':
            _ref_level = 0
        else:
            #Select 
            _ref_level = 0
            for row in self.c.execute('SELECT * FROM catalog WHERE content_name=\"%s\" LIMIT 1'%reference):
                _ref_level = row[4]+1
                _new_content_name = row[0]
                topic = row[5]
            assert _ref_level == 1, _ref_level
        self.c.execute("INSERT INTO catalog VALUES (\"%s\",'%s', '%s', '%s', %d, %d);"%(content_name, social_publisher, time.time(), reference, _ref_level, topic))

        self.lock.acquire()
        self.caches.post_production(_new_content_name, social_publisher)
        self.lock.release()

    def producer(self, social_publisher, position, reference = '', topic = 0):
        logging.error("WARNING, this function is deprecated")
        exit(-1)
        self.topology_nodes.update_user_position(social_publisher, position)
        self.caches.incr_publish()

        content_name = "/friend%i/%i"%(social_publisher, self.stats.increase_messages())
        _new_content_name = content_name
        if reference == '':
            _ref_level = 0
            
            topic = self.users[social_publisher].decide_next_topic()
        else:
            #Select 
            _ref_level = 0
            for row in self.c.execute('SELECT * FROM catalog WHERE content_name=\"%s\" LIMIT 1'%reference):
                _ref_level = row[4]+1
                _new_content_name = row[0]
                topic = row[5]
            assert _ref_level == 1, _ref_level
        self.c.execute("INSERT INTO catalog VALUES (\"%s\",'%s', '%s', '%s', %d, %d);"%(content_name, social_publisher, time.time(), reference, _ref_level, topic))

        self.lock.acquire()
        self.caches.post_production(_new_content_name, social_publisher)
        self.lock.release()

    def consume_from_server(self, social_issuer, position, content_name):
        #print "consume_from_server %s"%content_name
        self.topology_nodes.update_user_position(social_issuer, position)

        content_retrieved = {}
        last = 0
        
        for row in self.c.execute('SELECT * FROM catalog WHERE content_name == \"%s\" LIMIT 1'%( content_name )):
            last = row[0]
            reference = row[3]
            referer_level = row[4]
            topic = row[5]
            
            interest = last

            path = self.topology_nodes.get_path(social_issuer, row[1])

            # Retrieve content and calculate statistics
            self.lock.acquire()
            self.caches._retrieve_from_caches(interest, path)
            self.lock.release()

    def consumer(self, social_issuer, position):
        self.topology_nodes.update_user_position(social_issuer, position)

        content_retrieved = {}
    
        for social_neighbour in self.social_graph.neighbors(social_issuer):
            topology_neighbour = self.topology_nodes[social_neighbour]
            last = 0
            
            for row in self.c.execute('SELECT * FROM catalog WHERE publisher=%s and date BETWEEN %2f AND %2f ORDER BY date DESC LIMIT 1'%(social_neighbour, time.time()-0.2, time.time())):
                last = row[0]
                reference = row[3]
                referer_level = row[4]
                topic = row[5]
                
                #detecting original consumer
                while referer_level > 0:
                    for row in self.c.execute('SELECT * FROM catalog WHERE content_name=\"%s\" ORDER BY date DESC LIMIT 1'%reference):
                        last = row[0]
                        reference = row[3]
                        referer_level = row[4]
                        topic = row[5]
                #print row
                interest = last

                path = self.topology_nodes.get_path(social_issuer, social_neighbour)

                self.lock.acquire()
                self.caches._retrieve_from_caches(interest, path)
                self.lock.release()

    def get_expired_elements(self):
        # get last element of each social user
        #TODO: refactoring URGENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        return 0
    def get_diversity(self):
        return self.stats.get_diversity(self.caches)
    def printStats(self):
        return self.caches.stats_summary()
    def printStepSummary(self, timestamp):
        print("=> {0} {1}".format(timestamp, self.caches.stats_summary()))
    def finishSimulation(self):
        self.lock.acquire()
        self.lock.release()
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()



if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-c", "--cache-size-per-node",
                  dest="cache_size_per_node",
                  help="space of cache allocated for every node in the topology",
                  type=int,
                  )
    parser.add_option("-s", "--strategy",
                  dest="caching_strategy",
                  help="caching Strategy used for evaluating the trace"
                  )
    parser.add_option("-u", "--social-connections",
                  dest="social_graph",
                  help='social connections between users of the trace. Every trace includes users that executes actions.'
    )
    parser.add_option("-t", "--topology",
                  dest="network_topology",
                  help='network topology used for executing the trace.'
    )
    parser.add_option("-f", "--trace-file",
                  dest="trace",
                  default="",
                  help='the trace to be executed',
    )
    parser.add_option("-p", "--replacement-policy",
                  dest="replacement_policy",
                  help='replacement policy used at every network node.',
    )
    parser.add_option("-m", "--mobility-enabled",
                  dest="mobility_enabled",
                  default=False,
                  action="store_true",
                  help="Enable mobility of users"
    )
    parser.add_option("-d", "--debug",
                  dest="debug",
                  default=False,
                  action="store_true",
                  help="Enable debugging options"
    )
    parser.add_option("-r", "--step-printing",
                  dest="step_printing",
                  default="",
                  help = ""
    )

    (options, args) = parser.parse_args()


    if options.debug:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        root.addHandler(ch)
        logging.info('Enable Debugging')

    CACHE_SIZE = options.cache_size_per_node
    CACHING_STRATEGY = options.caching_strategy
    RUNS = 1
    SOCIAL_GRAPH = options.social_graph
    TOPOLOGY_GRAPH = options.network_topology
    CACHE_STRUCTURE = options.replacement_policy

    SEQUENCE_FILE = options.trace
    if SEQUENCE_FILE == "":
        logging.error("no trace file, using random generation of messages.")
        exit()

    MOBILITY_ENABLED = options.mobility_enabled
    if MOBILITY_ENABLED:
        logging.debug("Mobility enabled")
    else:
        logging.debug("Mobility disabled")

    try:
        STEP_PRINTING = [float(x) for x in options.step_printing.split(",") if x != '']
        logging.debug("Step printing activated")
    except IndexError:
        STEP_PRINTING = []
        logging.debug("Step printing not activated")


    CACHE_STRUCTURE = re.match('([a-zA-Z0-9_]*(\((?P<params>([0-9]*\.?[0-9]*,? ?)*)\))?)', CACHE_STRUCTURE)
    assert CACHE_STRUCTURE != None
    CACHE_STRUCTURE = CACHE_STRUCTURE.group(1)

    # Import Social Graph
    #Social Graph is connection between nodes
    G = getattr(__import__('graphs.%s'%SOCIAL_GRAPH), SOCIAL_GRAPH).G
    logging.debug('Social Graph loaded')

    #random.seed(10442)

    for iteration in range(0, RUNS):
        # Import Topology Graph
        petersen = getattr(__import__('graphs.%s'%TOPOLOGY_GRAPH), TOPOLOGY_GRAPH).G
        #social_graph, topology, cache_size, caching_strategy, cache_policy, sequence_filename = '', mobility_enabled = False, step_printing = [], topology_file = None
        executor = Executor(G, petersen, CACHE_SIZE, CACHING_STRATEGY, CACHE_STRUCTURE, SEQUENCE_FILE, MOBILITY_ENABLED, STEP_PRINTING, topology_file=TOPOLOGY_GRAPH)
        executor.run()
        print(executor.printStats())