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
import networkx
import numpy
import random
import re

import externmodules.community

from statistics import Stats, GeneralStats

import logging
def setup_logger1(logger_name, log_file, level=logging.INFO, format_style = '%(asctime)-15s %(message)s'):
    l = logging.getLogger(logger_name)
    formatter = logging.Formatter(format_style)
    fileHandler = logging.FileHandler(log_file, mode='w')
    fileHandler.setFormatter(formatter)
    l.addHandler(fileHandler)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    l.addHandler(streamHandler)
    l.setLevel(level)
    return l
logger = logging.getLogger('logger')
cache_info = logging.getLogger('cache_info')
#setup_logger('cache_info','cache_info.log', level = logging.INFO, format_style = '%(message)s')

class CacheManager(object):
    def _init_strategy(self):
        pass
    def __init__(self, cache_policy, cache_size, social_graph, topology, topology_manager, threshold = None):
        self.cache_policy = cache_policy
        res = re.match('((?P<name>[a-zA-Z0-9_]*)(\((?P<params>([0-9]*\.?[0-9]*,? ?)*)\))?)', cache_policy)
        assert res != None
        self.cache_policy = res.group('name')
        try:
            self.cache_policy_params = [float(r) for r in res.group('params').split(',')]
        except AttributeError:
            self.cache_policy_params = []
        
        self.social_graph = social_graph
        self.CACHE_SIZE = cache_size

        self.topology_manager = topology_manager
        self.topology = topology

        self.stats = Stats()
        self.caches = {}
        self.prepare_caches(cache_size)

        ## INItIALIZE PRODUCER POLICY
        self._init_strategy()

    def prepare_caches(self, cache_size):
        ### REPLACEMENT POLICIES ##############################################
        #if cache_policy in ['subset_influentials', 'subset_noninfluentials']:
        #    #recorremos todos los nodos, nos fijamos cuales caen y extramos los amigos del subgrafo social
        #    if cache_policy == 'subset_influentials':
        #        n_ = [n for n in social_graph.nodes() if pagerank[n] > threshold]
        #    elif cache_policy == 'subset_noninfluentials':
        #        n_ = [n for n in social_graph.nodes() if pagerank[n] <= threshold]

        #    nodes_ = {}
        #    for n in n_:
        #        nodes_[str(n)] = n

        #    for node in self.topology.nodes():
        #        self.caches[node] = SubsetCache(cache_size, subset = nodes_)

        #elif cache_policy in ['subset_community2']:
        #    partition = externmodules.community.best_partition(self.social_graph)
            
        #    for node in topology.nodes():
        #        users_in_node = [n for n in social_graph.nodes() if topology_manager[n] == node]
        #        for vecino in networkx.neighbors(topology, node):
        #            users_in_node += [n for n in social_graph.nodes() if topology_manager[n] == vecino]
                
        #        self.caches[node] = CommunitySubsetCache(
        #            cache_size,
        #            users = users_in_node,
        #            node_in_the_topology = node,
        #            partition = partition
        #        )

        #elif cache_policy in ['specialsemantic2']:
        #    for node in topology.nodes():
        #        self.caches[node] = SemanticCache2(cache_size, [0.5, 20, 100000])
        #    self.caches[node] = SemanticCache3(cache_size, [0.5, 20, 100000])
        ### END REPLACEMENT POLICIES ##########################################
        rp = getattr(getattr(__import__('replacement_policies.%s'%self.cache_policy), self.cache_policy), self.cache_policy)
        # 只有在拓扑图中的节点才可以缓存
        for node in self.topology.nodes():
            if self.topology_manager.has_caching_capabilities(node):
                self.caches[node] = rp(cache_size)#, self.cache_policy_params)

    def post_production(self, content_name, social_publisher):
        self._post_production(content_name, social_publisher)

    def _post_production(self, content_name, social_publisher):
        """Function to be overloaded"""
        pass

    def __getitem__(self, key):
        return self.caches[key]
    def values(self):
        return self.caches.values()

    #TODO: change function name
    def _retrieve_from_caches(self, interest, path):
        self.stats.incr_interest()
        res = self.retrieve_from_caches(interest, path)
        # Move to _retrieve_from_caches
        if res[0]:
            self.stats.incr_w()
            logger.info("Resolved interest(%s) with %s, path(%s): hit request into node %s of the topology"%(self.__class__.__name__, interest, path, path[res[1]]))
        else:
            logger.info("Resolved interest(%s) with %s,  path(%s): miss request"%(self.__class__.__name__, interest, path))
        self.stats.hops_walked(res[1], len(path)-1)
        

    def lookup_cache(self, node, interest):
        """Wrapper to lookup in the caches
        """
        if self.topology_manager.has_caching_capabilities(node):
            res = self.caches[node].lookup(interest)
            if res:
                self.stats.hit()
            else:
                self.stats.miss()
        else:
            res = False
        return res
    def store_cache(self, node, interest):
        if self.topology_manager.has_caching_capabilities(node):
            self.stats.incr_accepted(self.caches[node].store(interest))

    def print_caches(self):
        logger.debug('Inspection of the caches')
        for k in self.caches.keys():
            logger.debug("Cache in Node(%s): %s"%(k, [k for k in self.caches[k].keys()]))
            cache_info.info("Cache in Node(%s): %s"%(k, [k for k in self.caches[k].keys()]))
            #logger.critical("Cache in Node(%s): %s"%(k, [k for k in self.caches[k].keys()]))

    #REFACTORING OF THIS!
    def incr_publish(self):
        return self.stats.incr_publish()
    def stats_summary(self):
        self.print_caches()
        return self.stats.summary(self.caches)