#####################################################################
#SocialCCNSim, a simulator of caches for Content Centric Networking.
#
#Developed by Cesar A. Bernardini Copyright (C) 2014.
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
#This function creates a mapping between the users and the node where they are placed
import random

import numpy

import networkx
import os
import pickle

#import percache
#cache = percache.Cache("/tmp/my-cache")

#@cache
def get_path(topology, source, target):
        return networkx.shortest_path(
                    topology,
                    source=source,
                    target=target
                )

class Paths(object):
    def __init__(self, _graph):
        self._topology = _graph
    def calculate_path(self, _source, _target):
        return networkx.shortest_path(self._topology ,source=_source,target=_target)

class SocialPaths(Paths):
    def __init__(self, _topology):
        Paths.__init__(self, _topology)
        self._path = {}

        # All against all
        for source in self._topology.nodes():
            self._path[source] = {}
            for target in self._topology.nodes():
                self._path[source][target] = get_path(self._topology, source, target)

    

    def calculate_path(self, _source, _target):
        path =  self._path[_source][_target]
        if path == False:
            assert "The graph must be connected"
        return path

#cache.close()
class TopologyManager(object):
    def __init__(self, topology, social_graph, topology_nodes_position, enable_mobility = False, topology_file=None):
        assert type(topology_nodes_position) == dict
        self.topology = topology
        self.social_graph = social_graph
        self.enable_mobility = enable_mobility
        #Coordinates for the nodes and the users
        #First: filter nodes without caching capabilities
        tnp = {}
        for n in topology_nodes_position.keys():
            if self.has_request_capabilities(n):
                tnp[n] = topology_nodes_position[n]
        topology_nodes_position = None 
        self.coords = tnp
        self.coords_user = {}
        self.topology_nodes = {}
        self.method = None
        self.topology_file = topology_file
        self.initialize_paths()

    def initialize_paths(self):
        if os.path.exists('graphs/'+self.topology_file+'.routes'):
            self.paths = pickle.load(open('graphs/'+self.topology_file+'.routes', 'rb'))
        else:
            # 将拓扑图生成路由文件（通过前面定义的SocialPaths类）
            self.paths = SocialPaths(self.topology)
            # 将其保存为路由文件，便于下一步进行设置
            pickle.dump(self.paths, open('graphs/'+self.topology_file+'.routes', 'wb'))
    # 通过两个社交用户来确定其对应的网络节点，并进行路径寻找
    def get_path(self, social_src, social_dst):
        return self.paths.calculate_path(self.topology_nodes[social_src], self.topology_nodes[social_dst])

    def set_method(self, method):
        #Decide which method to use
        #Request Pattern of in
        assert method in ['random', 'geographical', 'onepublisher']
        self.method = method
    # 如果mobility——enabled:
    #      设置coords_user以及topology_nodes
    # 如果mobility——not-enabled:
    #       设置coords_user
    def update_user_position(self, user, position):
        # Assign new coords and then calculate user belonging to the topology_node.
        self.coords_user[user] = position
        if self.enable_mobility:
        #if random.randint(0, 2) == 0:
            self.topology_nodes[user] = self.closest_node(user)

    def update_user_node(self, user, node):
        self.topology_nodes[user] = node
    def get_user_node(self, user):
        return self.topology_nodes[user]

    def update_all_users_position(self):
        #TODO: add feature that users only can be putted in a node without the wr attribute as true
        # 随机将用户与拓扑节点之间建立关系
        if self.method == 'random':
            request_nodes = [n for n in self.topology.nodes() if self.has_request_capabilities(n)]
            res = []
            for user in self.social_graph.nodes():
                self.topology_nodes[user] = random.choice(request_nodes)

        elif self.method == 'geographical':
            for user in self.social_graph.nodes():
                self.topology_nodes[user] = self.closest_node(user)

        elif self.method == 'onepublisher':
            for user in self.social_graph.nodes():
                self.topology_nodes[user] = 1
            self.topology_nodes[0] = 0
        else:
            raise Exception('Not implemented method: %s'%self.method)
    
    #寻找最近的节点
    def closest_node(self, user):
        x, y = self.coords_user[user]
        d = 100*100 # max distance
        n = -2
        for k,v in self.coords.items():
            x1, y1 = v
            # 寻找二维数组中的最小差值项
            # Euclidean distance
            a = numpy.array((x,y))
            b = numpy.array((x1,y1))
            d1 = numpy.linalg.norm(a-b)
            #遍历所有的点，进行欧式距离计算并且替代
            if d1 < d:
                d = d1
                n = k
        assert n != -1, "Remember to set original coordinates for CCN nodes. User %s found closest node the -1"%user
        return n

    def has_caching_capabilities(self, node):
        n = self.topology.nodes[node]
        return not ('wc'in n.keys()  and n['wc'] == True)
    def has_request_capabilities(self, node):
        n = self.topology.nodes[node]
        return not ('wr' in n.keys() and n['wr'] == True)

    def __getitem__(self, key):
        return self.get_user_node(key)
    def __setitem__(self, key, value):
        return self.update_user_node(key, value)


if __name__ == '__main__':

    # Import Social Graph
    social_g = getattr(__import__('graphs.random'), 'random').G
    topology_g = getattr(__import__('graphs.random'), 'random').G

    topology_coords = {}
    for node in topology_g:
        topology_coords[node] = (random.randint(0, 100),
                                random.randint(0, 100)
                                )
    t = TopologyManager(topology_g, social_g, topology_coords)
    t.set_method('geographical')
    for user in social_g.nodes():
        t.update_user_position(user, (random.randint(0, 100),
                                random.randint(0, 100)
                                )
        )
    t.update_all_users_position()
    for user in social_g.nodes()[:10]:
        print(user, t[user])