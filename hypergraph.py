from collections import MappingView, Mapping, Set, KeysView, MutableMapping

class Edge(Set):
    __slots__ = ["_nodes", "_edgekey", "data"]
    def __init__(self, nbunch, edgekey=None, **kwds):
        # to force undirected use frozenset(nbunch)
        self._nodes = nbunch
        self._edgekey = edgekey
        self.data = EdgeData(**kwds)
    def __iter__(self):
        return iter(self._nodes)
    def __contains__(self, node):
        return node in self._nodes
    def __len__(self):
        return len(self._nodes)
    def __repr__(self):
        if self._edgekey is None:
            return "Edge({})".format(self._nodes)
        return "Edge({}, edgekey={})".format(self._nodes, self._edgekey)
    def __hash__(self):
        if isinstance(self._nodes, Set):
            nodes = frozenset(self._nodes)
        else:
            nodes = self._nodes
        return hash((nodes, self._edgekey))
    def __eq__(self, other):
        return (self._nodes == other._nodes) and \
               (self._edgekey == other._edgekey)
    def __ne__(self, other):
        return not self == other
    @property
    def nodes(self):
        return self._nodes
    @property
    def edgekey(self):
        return self._edgekey

class EdgeData(MutableMapping):
    __slots__ = ["_data"]
    def __init__(self, **kwds):
        if len(kwds) == 0:
            self._data = None
        else:
            self._data = kwds
    def __getitem__(self, key):
        if self._data is None:
            raise KeyError(key)
        return self._data[key]
    def __setitem__(self, key, value):
        if self._data is None:
            self._data = {}
        self._data[key] = value
    def __delitem__(self, key):
        if self._data is None:
            raise KeyError(key)
        del self._data[key]
    def __iter__(self):
        if self._data is None:
            return iter({})
        return iter(self._data)
    def __len__(self):
        if self._data is None:
            return 0
        return len(self._data)
    def __repr__(self):
        return "EdgeData({})".format(self._data)


class HyperGraph(object):
    def __init__(self):
        self.node_data = {}
        self.node_incidence = {}
        self.edge_data = {}
    # Mutating Methods
    def add_node(self, node, **kwds):
        if node in self.node_data:
            self.node_data[node].update(kwds)
            return False
        self.node_data[node] = kwds  # Note: kwds is a copy of the input **dict
        self.node_incidence[node] = set()
        return True
    def add_edge(self, nbunch, **kwds):
        if isinstance(nbunch, Edge):
            e = nbunch
            e.data.update(kwds)
        else:
            edgekey = kwds.pop("edgekey", None)
            e = Edge(nbunch, edgekey, **kwds)
        if e in self.edge_data:
            data = self.edge_data[e]
            data.update(kwds)
            return False  # existing edge
        # new edge
        self.edge_data[e] = e.data
        for n in e:
            if n not in self.node_data:
                self.node_data[n] = {}
                self.node_incidence[n] = {e}
            else:
                self.node_incidence[n].add(e)
        return e
    def remove_edge(self, nbunch):
        if isinstance(nbunch, Edge):
            e = nbunch
        else:
            e = Edge(nbunch, None)
        del self.edge_data[e]
        for n in e:
            self.node_incidence[n].remove(e)
    def remove_node(self, node):
        del self.node_data[node]
        for e in list(self.node_incidence[node]):
            del self.edge_data[e]
            nbunch = (n for n in e if n != node)
            if isinstance(e.nodes, Set):
                newe = Edge(set(nbunch), e.edgekey, **(e.data))
            else:
                newe = Edge(tuple(nbunch), e.edgekey, **(e.data))
            if len(newe) > 1:
                self.edge_data[newe] = newe.data
                for nbr in newe:
                    self.node_incidence[nbr].add(newe)
            for nbr in newe:
                self.node_incidence[nbr].remove(e)
        del self.node_incidence[node]
    # Reporting Methods
    def edges(self, data=None):
        if data is None:
            return self.edge_data.keys()
        if data is True:
            return self.edge_data.items()
        return ((e, data(edata)) for e, edata in self.edges_data.items())
    def nodes(self, data=False):
        if data is True:
            return self.node_data.items()
        return self.node_data.keys()
    def has_edge(self, nbunch):
        if isinstance(nbunch, Edge):
            e = nbunch
        else:
            e = Edge(nbunch, None)
        return e in self.edge_data
    # report on adjacencies
    def adjacency(self):
        return NeighborAtlas(self)
    def neighbors(self, node):
        for e in self.node_incidence[node]:
            if len(e) == 1:
                yield node
            else:
                for n in e:
                    if n != node:
                        yield n
    def __getitem__(self, node):
        return NeighborMap(self, node)
    # extras
    def __iter__(self):
        return iter(self.node_data)
    def __contains(self, node):
        return node in self.node_data
    def __len__(self):
        return len(self.node_data)
    # others
    def clear(self):
        self.node_data.clear()
        self.edge_data.clear()
        self.node_incidence.clear()
        self.graph.clear()
    def copy(self):
        G = self.__class__()
        for n,ndata in self.nodes(data=True):
            G.add_node(n, **ndata)
        for e, edata in self.edges(data=True):
            G.add_edge(e, **edata)
        return G
    def order(self):
        return len(self.node_data)
    def size(self):
        return len(self.edge_data)
    def __repr__(self):
        return "HyperGraph({}, {})".format(self.node_data, self.edge_data)


class NeighborMap(Mapping):
    __slots__ = ["_graph", "_node"]
    def __init__(self, graph, node):
        self._graph = graph
        self._node = node
    def __iter__(self):
        node = self._node
        graph = self._graph
        for e in graph.node_incidence[node]:
            if len(e) == 1:
                yield node
            else:
                for nbr in e:
                    if nbr != node:
                        yield nbr
    def __getitem__(self, nbr):
        node = self._node
        graph = self._graph
        ei = {e: e.data for e in graph.node_incidence[node] if nbr in e}
        if len(ei)==0:
            raise KeyError(nbr)
        return ei
    def __len__(self):
        return sum(len(e)-1 if len(e)>1 else 1
                   for e in self._graph.node_incidence[self._node])

class NeighborAtlas(MappingView):
    __slots__ = ["_mapping"]
    def __getitem__(self, node):
        if node in self._mapping.node_incidence:
            return NeighborMap(self._mapping, node)
        raise KeyError(node)
    def __contains__(self, node):
        return node in self._mapping.node_incidence
    def __iter__(self):
        for n in self._mapping.node_incidence:
            yield n, NeighborMap(self._mapping, n)


if __name__ == "__main__":
    G = HyperGraph()
    G.add_edge((1,2))
    G.add_edge({1,2})
    G.add_node(0, color=0)
    G.add_edge((2,3))
    assert len(G) == 4
    assert G.nodes() - {0,1,2,3} == set()
    assert G.edges() - {Edge((1,2)), Edge({1,2}), Edge((2,3))} == set()
    assert set(G[2]) == {1, 3}
    try:
        G.remove_edge((4,3))
        raise Exception("failed to raise KeyError on edge removal",(4,3))
    except KeyError:
        pass
    G.remove_edge((2,3))
    assert set(G[2]) == {1}
    assert G.edges() == {Edge((1,2)), Edge({1,2})}
    assert set(G.neighbors(1)) == {2}
    G.add_edge({2,3})
    G.remove_node(2)
    assert len(G.edges())==0
    assert len(G) == 3
    G.add_edge({1,2})
    G.add_edge({2,3})
    assert not G.has_edge((1,2))
    assert G.has_edge({1,2})
    assert G.has_edge({2,1})
    adj = dict(G.adjacency())
    assert set(adj[1].keys()) - {2} == set()
    # python3 only
    #assert repr(list(adj[1].items())) == "[(2, {Edge({1, 2})})]"
    assert set(G) == {0,1,2,3}
    assert 3 in G and 0 in G and 5 not in G
    assert G.size() == 2
    assert G.order() == 4
    # python3 only
    #assert repr(G) == ("HyperGraph("
    #               "{0: {'color': 0}, 1: {}, 2: {}, 3: {}}, "
    #               "{Edge({1, 2}), Edge({2, 3})})")

    # Test some hypergraph featuers too. :)
    G.add_edge((11,12,13,14,15,16))
    G.add_edge((14,15,16,17,18))
    assert set(G.neighbors(14)) == set([11, 12, 13, 15, 16, 17, 18, 15, 16])
    assert sorted(G.neighbors(14)) == [11, 12, 13, 15, 15, 16, 16, 17, 18]
    assert sorted(G[14]) == [11, 12, 13, 15, 15, 16, 16, 17, 18]
    assert G.size() == 4
    #print(G.edges())
    #print(G.nodes())



