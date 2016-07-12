__author__ = 'Gian Paolo Jesi'

from graph_tool.all import *
from numpy.random import random
import matplotlib as pl
import ast
from util.algo import spanning


class RubikLoader(object):
    def __init__(self, properties=('name',)):
        self.index = dict()  # maps lists (node states) to name index
        self.properties = properties
        self.g = Graph()
        # making internal properties for vertex:
        for item in properties:
            self.g.vertex_properties[item] = self.g.new_vertex_property("string")
        # internal property for edges:
        self.g.edge_properties['move'] = self.g.new_edge_property("string")

    def make_gt_line(self, line):
        line = line.replace('{', '[')
        line = line.replace('}', ']')

        a_data, b_data, m = ast.literal_eval(line)
        params_a = dict()
        params_b = dict()

        # when a and b are simple strings, convert them to a sequence of a
        # single element
        if type(a_data) is str:
            print "converting to seq"
            params_a = dict(zip(self.properties, (a_data,)))
        else:
            params_a = dict(zip(self.properties, a_data))

        if type(b_data) is str:
            params_b = dict(zip(self.properties, (b_data,)))
        else:
            params_b = dict(zip(self.properties, b_data))

        if a_data not in self.index.keys():
            self.index['counter'] += 1
            v = self.g.add_vertex()
            for key in params_a.keys():
                self.g.vertex_properties[key][v] = params_a[key]
            self.index[a_data] = v

            print "Inserting: %s with name: %d" % (a_data, self.g.vertex_index[v])
        else:
            print "data %s already in" % a_data
            pass

        if b_data not in self.index.keys():
            self.index['counter'] += 1
            v = self.g.add_vertex()
            for key in params_b.keys():
                self.g.vertex_properties[key][v] = params_b[key]
            self.index[b_data] = v
            print "Inserting: %s with name: %d" % (b_data, self.g.vertex_index[v])
        else:
            print "data %s already in" % b_data
            pass

        ab = self.g.add_edge(self.index[a_data], self.index[b_data])
        self.g.edge_properties['move'][ab] = m

    def loadMatrix(self, filename="data/MiniRubik.txt", limit=-1):
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

    def draw(self):
        assert self.g.num_vertices(ignore_filter=True) > 0

        gv = GraphView(self.g)
        pos = sfdp_layout(gv, gamma=1.5)
        move = gv.edge_properties['move']
        name = gv.vertex_properties['name']
        # print name
        # vcmap = pl.cm.gist_heat
        graph_draw(gv, pos, output_size=(1000, 1000),
                   edge_text=move, vertex_text=name, edge_text_size=8)

    def draw_intersect(self, v1='ABCD', v2='ABDC'):
        """Draw the result of the intersection of the spanning trees stemming from nodes v1 and v2.
        """
        assert self.g.num_vertices(ignore_filter=True) > 0

        gv = GraphView(self.g)
        pos = sfdp_layout(gv, gamma=1.5)
        # pos = radial_tree_layout(gv, root=v1)
        move = gv.edge_properties['move']
        name = gv.vertex_properties['name']

        v1 = gv.vertex_index[self.index[v1]]
        v2 = gv.vertex_index[self.index[v2]]

        spt1_map = min_spanning_tree(gv, root=v1)
        spt2_map = min_spanning_tree(gv, root=v2)

        # sub is the tree graph representing the min span tree from v1
        sub = GraphView(self.g)
        print "spt1map: ", spt1_map
        print get_vertices_from_eprop(spt1_map)
        vpresence_val_map = sub.new_vp("bool", vals=get_vertices_from_eprop(
            spt1_map))
        sub.set_edge_filter(spt1_map)
        sub.set_vertex_filter(vpresence_val_map)
        vm = subgraph_isomorphism(gv, sub, max_n=100)
        print(len(vm))

        graph_draw(sub, pos, output_size=(1000, 1000),
                   edge_text=move, vertex_text=name)

        map_values = intersect_maps(spt1_map, spt2_map)
        filter_map_values = [bool(x) for x in map_values]
        intersection_map = gv.new_ep("int", vals=map_values)
        filter_map = gv.new_ep("bool", vals=map_values)

        # NOTE: marca il sottografo, poi filtra nodi e link

        gv.set_edge_filter(filter_map)
        graph_draw(gv, pos, output_size=(1000, 1000),
                   edge_text=move, vertex_text=name, edge_color=intersection_map)

    def draw_spanning(self, multigoal=[]):
        """
        Draw the graph generated by the spanning function.

        :param multigoal: list of vertex labels as strings. Correspond to 'name' vertex property.
        :return:
        """
        if not multigoal:
            multigoal = [self.g.vertex(0)]
        else:
            multigoal = [self.index[x] for x in multigoal]

        move = self.g.edge_properties['move']
        name = self.g.vertex_properties['name']
        sg = spanning(self.g, multigoal)
        pos = sfdp_layout(sg, gamma=1.5)
        graph_draw(sg, pos, output_size=(1000, 1000),
                   edge_text=move, vertex_text=name, edge_text_size=8)


def get_vertices_from_eprop(eprop):
    assert eprop.key_type() == 'e'

    data = eprop.fa
    print "properties values: ", data
    g = eprop.get_graph()

    # print g
    values = []
    for i in range(0, g.num_vertices()):
        values.append(False)

    index = 0
    for e in g.edges():
        # print data[index]
        if data[index] == 1:
            a = g.vertex_index[e.source()]
            b = g.vertex_index[e.target()]
            values[a] = True
            values[b] = True
            # print "Node indexes %d and %d are in a relation" % (a, b)
        index += 1

    return values


def intersect_maps(map_a, map_b):
    """
    Compute the intersection over the values on the given property maps. The intersection in
    returned as a new collection of values.
    It works only over simple maps representing boolean scalar values (0 or 1).

    :param map_a: a PropertyMap obj
    :param map_b: a PropertyMap obj
    :return: a list of values (0 or 1)
    """
    intersect_map_values = []
    zipped_tuple = zip(map_a.a, map_b.a)
    for (x, y) in zipped_tuple:
        if x == 1 and y == 1:
            intersect_map_values.append(1)
        else:
            intersect_map_values.append(0)

    return intersect_map_values


if __name__ == '__main__':
    ldr = RubikLoader()
    # ldr.g.load('data/MRubikg.xml.gz')
    ldr.loadMatrix('data/MiniRubik.txt')
    print ldr.g
    ldr.draw()
    ldr.draw_spanning(multigoal=['ABCD', 'ABDC'])
    # ldr.draw_intersect(v1='ABCD', v2='ABDC')
