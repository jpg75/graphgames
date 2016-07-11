__author__ = 'Gian Paolo Jesi'

from graph_tool.all import *
from numpy.random import random
import matplotlib as pl
import ast

_MATLAB_CARD_LAYOUT = ("ck", "target", "nk", "dc", "up", "dn", "player")


class LeafVertexDetector(DFSVisitor):
    def __init__(self, leaf, target=None):
        self.leaf = leaf
        self.target = target

    def discover_vertex(self, u):
        # print "Check node %d: ind: %d, outd: %d" % (u, u.in_degree(), u.out_degree())
        if u.out_degree() == 0:
            self.leaf[u] = True
            print "detected leaf node: ", u

        # 2H is in target zone:
        if self.target and self.target[u] == '2H':
            self.leaf[u] = True
            print "detected leaf node: ", u


class GTLoader(object):
    def __init__(self):
        self.index = dict()  # maps lists (node states) to name index
        self.g = Graph()
        # making internal properties for vertex:
        for item in _MATLAB_CARD_LAYOUT:
            self.g.vertex_properties[item] = self.g.new_vertex_property("string")
        # internal property for edges:
        self.g.edge_properties['move'] = self.g.new_edge_property("string")

    def make_gt_line(self, line):
        line = line.replace('{', '[')
        line = line.replace('}', ']')

        a_data, b_data, m = ast.literal_eval(line)
        params_a = dict(zip(_MATLAB_CARD_LAYOUT, a_data))
        params_b = dict(zip(_MATLAB_CARD_LAYOUT, b_data))

        if a_data.__repr__() not in self.index.keys():
            self.index['counter'] += 1
            v = self.g.add_vertex()
            for key in params_a.keys():
                self.g.vertex_properties[key][v] = params_a[key]
            self.index[a_data.__repr__()] = v

            print "Inserting: %s with name: %d" % (a_data.__repr__(), self.g.vertex_index[v])
        else:
            print "data %s already in" % a_data.__repr__()
            pass

        if b_data.__repr__() not in self.index.keys():
            self.index['counter'] += 1
            v = self.g.add_vertex()
            for key in params_b.keys():
                self.g.vertex_properties[key][v] = params_b[key]
            self.index[b_data.__repr__()] = v
            print "Inserting: %s with name: %d" % (b_data.__repr__(), self.g.vertex_index[v])
        else:
            print "data %s already in" % b_data.__repr__()
            pass

        ab = self.g.add_edge(self.index[a_data.__repr__()], self.index[b_data.__repr__()])
        self.g.edge_properties['move'][ab] = m
        # rels[m] += 1

    def loadMatrix(self, filename="data/TTT-matrix.txt", limit=-1):
        counter = 1
        # reset the index to avoid conflicts
        self.index.clear()
        self.index['counter'] = 0
        self.g.clear()

        try:
            with open(filename, 'r') as f:
                for line in f:
                    if limit != -1 and counter >= limit: break

                    print "processing line %d: %s" % (counter, line)
                    counter += 1

                    self.make_gt_line(line)

        except IOError as ioe:
            print ioe

    def show_betweeness(self):
        assert self.g.num_vertices(ignore_filter=True) > 0

        gv = GraphView(self.g)
        pos = sfdp_layout(gv, gamma=1.5)
        bv, be = betweenness(gv)
        move = gv.edge_properties['move']
        vcmap = pl.cm.gist_heat
        graph_draw(gv, pos, vertex_size=prop_to_size(bv, mi=1, ma=15), output_size=(1000, 1000),
                   vertex_fill_color=bv, edge_text=move, edge_text_size=8,
                   edge_pen_width=prop_to_size(be, mi=0.5, ma=5), vcmap=vcmap)

    def show_min_span_tree(self, filter=False):
        assert self.g.num_vertices(ignore_filter=True) > 0

        gv = GraphView(self.g)
        pos = sfdp_layout(gv, gamma=1.5)
        tree = min_spanning_tree(gv)
        move = gv.edge_properties['move']
        if filter:
            gv.set_edge_filter(tree)

        graph_draw(gv, pos=pos, vertex_size=1.0, output_size=(1000, 1000),
                   edge_pen_width=1.0, edge_color=tree, edge_text=move)

    def show_start_end_path(self):
        assert self.g.num_vertices(ignore_filter=True) > 0

        gv = GraphView(self.g)
        # new properties:
        leaf = gv.new_vertex_property('bool')
        gv.edge_properties['asp'] = gv.new_edge_property('bool')  # internal prop

        target = gv.vertex_properties['target']
        move = gv.edge_properties['move']


        dfs_search(gv, gv.vertex(0), LeafVertexDetector(leaf, target))
        print "Available leaf nodes: %d" % sum([item for item in leaf.a if item == 1])
        print gv.edge_properties
        print gv.list_properties()

        # g1 = Graph()
        edge_list = []
        for path in all_shortest_paths(gv, gv.vertex(0), gv.vertex(1036)):
            print path
            for i in range(0, len(path) - 1):
                edge_list.append((path[i], path[i + 1]))
                e = gv.edge(gv.vertex(path[i]), gv.vertex(path[i + 1]))
                # print e
                gv.edge_properties.asp[e] = True

        print edge_list
        # g1.add_edge_list(edge_list, hashed=True)

        # Graph with all shortest paths:
        path = gv.edge_properties['asp']
        print path
        # gv.set_edge_filter(path)
        #pos = sfdp_layout(gv, gamma=2.5)
        #graph_draw(gv, pos=pos, vertex_size=5.0, vertex_text=gv.vertex_index, edge_text=move,
        #           output_size=(1000, 1000), vertex_color=leaf, edge_color=path,
        # edge_pen_width=1.0)

        # Graph with highlighted leafs:
        pos = sfdp_layout(gv, gamma=2.5)
        graph_draw(gv, pos=pos, vertex_size=8.0, vertex_shape=leaf, output_size=(1000, 1000),
                   edge_pen_width=1.0, vertex_color=leaf, edge_text=move)

    def show_shortest_path(self):
        assert self.g.num_vertices(ignore_filter=True) > 0
        gv = GraphView(self.g)
        pos = sfdp_layout(gv, gamma=1.5)
        move = gv.edge_properties['move']

        vl, el = shortest_path(gv, gv.vertex(0), gv.vertex(1000))

        graph_draw(gv, pos=pos, vertex_size=1.0, output_size=(1000, 1000),
                   edge_pen_width=1.0, edge_text=move)


if __name__ == '__main__':
    ldr = GTLoader()
    # ldr.loadMatrix()
    ldr.g.load('data/TTTg.xml.gz')
    #ldr.show_betweeness()
    #ldr.show_min_span_tree(filter=True)
    ldr.show_start_end_path()
    # print ldr.index