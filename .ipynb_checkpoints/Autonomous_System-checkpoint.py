#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from uhashring import HashRing


# In[4]:


class AS:
    def __init__(self, nodes = [],enable_Ketama = True):
        self.nodes = nodes
        if enable_Ketama:
            self.hash_ring = HashRing(nodes, hash_fn='ketama')
        else:
            self.hash_ring = HashRing(nodes)
    def add_node(self,node: str):
        self.nodes.append(node)
        self.hash_ring.add_node(node)
    def remove_node(self,node:str):
        if node in self.nodes:
            self.nodes.remove(node)
            self.hash_ring.add_node(node)
            
    def print_nodes():
        return self.nodes()
    def get_nodes(self):
        return self.nodes
    def get_node(self,content_name: str):
        if len(self.nodes)!= 0:
            return self.hash_ring.get_node(content_name)
        else:
            return None
# get the node name for the 'coconut' key
#target_node = hr.get_node('coconut')


# In[5]:


#target_node


# In[ ]:




