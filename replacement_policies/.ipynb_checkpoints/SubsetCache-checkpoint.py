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
from replacement_policies.Cache import Cache
import re
import externmodules.pylru as pylru

class SubsetCache(Cache):
    def __init__(self, size, **args):
        #It only caches content from certain users
        Cache.__init__(self, size)
        assert size > 0
        self._store = pylru.lrucache(size)
        self.max_size = size
        self.subset = args['subset']
        self.prog = re.compile('\/friend([0-9]*)\/')
    def accept(self, content_name):
        res = self.prog.match(content_name)
        return res != None and self.subset.has_key(res.group(1))
