#
from cache_manager import CacheManager
from trend_forecast import predict
class POP(CacheManager):
    POP_THRESHOLD = 10
    RESET_VALUE = 0
    
    def _init_strategy(self):
        self.pop = {}
        for node in self.topology.nodes():
            self.pop[node] = {}
            # 写一下这个模块
            
    def retrieve_content(self, interest, target, path_to_target, server, target_to_server):
        retrieved_content = False
        retrieved_content = self.retrieve_from_target(interest, target, path_to_target)
        # TODO: 从Server中获取
        if not retrieved_content:
            self.retrieve_from_server(interest, target_to_server)
            if self.cache_decision(target, interest) == True:
                if self.topology_manager.has_caching_capabilities(target):
                    self.store_cache(target, interest)
        
    def retrieve_from_target(self, interest, target,path_to_target):
        content_found_caches = False
        r = self.stats.round
        try:
            # 本轮中访问过，直接加
            self.pop[target][interest][r] += 1
        except:
            try:
                # 过去访问过，可以直接对当前时间加
                self.pop[target][interest][r] = 1
            except:
                # 过去没有访问过，对这个文件进行初始化
                self.pop[target][interest] = {}
                self.pop[target][interest][r] = 1
        if self.caches[target].lookup(interest):
            content_found_caches = True
            self.stats.internal_hit()
        else:
            self.stats.internal_miss()
            self.stats.stretch_hop(len(path_to_target)-1)
        return content_found_caches
    
    def retrieve_from_server(self,interest, target_to_server):
        return 0
    # TODO:
    # Update cache_target and pre-match
    def cache_decision(self,target, interest):
        if self.stats.round < 3:
            return True
        else:
            if interest in self.cache_target[target]:
                return True
            else:
                return False
                
        
    def retrieve_from_caches(self, interest, path):
        content_found_caches = False
        for i in range(0, len(path)):
            p = path[i]
            try:
                self.pop[p][interest]+=1
            except:
                self.pop[p][interest] = 1

            if self.caches[p].lookup(interest):
                content_found_caches = True
                self.stats.hit()
                break
            else:
                self.stats.miss()
        if not content_found_caches:
            self.store_cache(path[len(path)-1], interest)
        if content_found_caches and self.pop[p][interest] >= self.POP_THRESHOLD:
            neighbors = self.topology_manager.topology.neighbors(p)
            for n in neighbors:
                if self.topology_manager.has_caching_capabilities(n):
                    self.store_cache(n, interest)
            self.pop[p][interest] = self.RESET_VALUE
                
        return (content_found_caches, i)
    def update_predict_result(self):
        p = predict()
        prediction_ranking = p.get_prediction_result(self.pop,2)
        cache_target = {}
        for node in prediction_ranking.keys():
            size = self.CACHE_SIZE
            try:
                cache_target[node] = list(prediction_ranking[node].keys())[:size]
            except:
                cache_target[node] = list(prediction_ranking[node].keys())
        #print("Target", cache_target)
        self.cache_target = cache_target
        
