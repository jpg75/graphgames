__author__ = 'Gian Paolo Jesi'

from graph_tool import Graph, GraphView
from graph_tool.topology import min_spanning_tree, all_paths, shortest_distance
from graph_tool.draw import *
from graph_tool.util import find_vertex
import string


def spanningTree(g, multigoal=[], verbose=True):
    """
    Generate a spanning tree for the given graph g.

    :param g: Graph based object
    :param multigoal: list of goal vertexes (where the spanning starts)
    :return: an boolean edge property map, marking the edges of the spanning tree
    """
    assert len(multigoal) != 0

    gv = g.copy()
    stree = gv.new_edge_property('bool')
    actual = multigoal

    while len(actual) != 0:
        # kills outgoing edges from current actual nodes
        temp = [item for item in gv.edges() if item.source() in actual]
        for e in temp:
            gv.remove_edge(e)

        predecessors = [item for item in gv.edges() if item.target() in actual]
        # EXPERIMENTAL! Keeps just one edge having the same source
        seen = set()
        keep = []
        for item in predecessors:
            if item.source() in seen:
                pass  # discard
            else:
                seen.add(item.source())
                keep.append(item)

        predecessors = keep

        # attaches the predecessor to the spanning tree:
        for e in predecessors:
            stree[e] = 1

        actual = frozenset([e.source() for e in predecessors])

    return stree


def spanning(g, multigoal=[], verbose=False):
    """
    Generate a spanning for the given graph g.
    Multiple starting nodes can be expressed in the multigoal parameter list.

    :param g: Graph based object
    :param multigoal: list of goal vertexes (where the spanning starts)
    :return: an boolean edge property map, marking the edges of the spanning
    """
    assert len(multigoal) != 0

    # from timeit import default_timer as timer
    # start = timer()
    gv = g.copy()
    # end = timer()
    # print "time for copy: ", end - start

    gv.set_fast_edge_removal()  # a bit faster
    spanningG = gv.new_edge_property('bool')
    actual = multigoal

    while len(actual) != 0:
        temp = [item for item in gv.edges() if item.source() in actual]
        for e in temp:
            if verbose:
                print("removing: ", e)
            gv.remove_edge(e)

        predecessors = [item for item in gv.edges() if item.target() in actual]
        if verbose:
            print "pred: ", predecessors

        # attaches the predecessor to the spanning:
        for e in predecessors:
            spanningG[e] = 1

        actual = frozenset([e.source() for e in predecessors])
        if verbose:
            print "actual: ", actual

    return spanningG


def split_check(g, goals=[]):
    """
    Check if the graph can be split according to the given vertexes in the goal list.
    EXPERIMENTAL!
    Based on shortest distance matrix. Works with just 2 goals for now.

    :param g: graph
    :param goals: list of vertexes
    :return:
    """
    assert len(goals) >= 2

    # print "Found %d distinct paths between node %s and node %s" % (len(paths), source, target)
    # for path in all_paths(g, goals[0], goals[1], cutoff=6):
    #    print "Lenght: %d : %s" % (len(path), path)
    # With big graphs we cannot afford to calculate the dist matrix, just vectors
    distances = {}
    for v in goals:
        distances[v] = shortest_distance(g, v)  # all distances

    print distances
    for v in distances:
        print distances[v].a

        # av1 = dist[ldr.index['ABCD']].a
        # av2 = dist[ldr.index['ADBC']].a
        # print ldr.index['ABDC']
        # print(av1)
        # print(av2)
        # result = [x[0] - x[1] for x in zip(distances[goals[0]].a, distances[goals[1]].a)]

        # print result[1000]
        # print

        # print result


def make_toy_graph(n=7,
                   tuples=[('a', 'b'), ('a', 'c'), ('a', 'd'), ('b', 'a'), ('b', 'd'), ('c', 'g'),
                           ('d', 'a'), ('d', 'f'), ('d', 'g'), ('e', 'b'), ('e', 'd'), ('f', 'c'),
                           ('g', 'e')], as_undirected=False):
    """
    Generate a toy graph for experimenting algorithms. By default the graph has 7 vertexes linked
    by 13 edges. Each vertex is represented by a lowercase letter.

    :param n: number of vertexes; default 7
    :param tuples: list of pairs representing the edges. It is the toy graph in my notebook :-)
    :param as_undirected: makes the graph undirected, but keeping an explicit directional
    representation. Essentially, the graph is still directed and each edge is reproduced in the
    opposite direction.
    :return:
    """
    assert n <= 26

    if as_undirected:
        tuples.extend([(item[1], item[0]) for item in tuples])
        print tuples

    g = Graph()
    vertex_it = g.add_vertex(n=n)
    g.vertex_properties['name'] = g.new_vertex_property('string')
    alphabet = list(string.ascii_lowercase)
    d = dict()
    i = 0
    for v in vertex_it:
        d[alphabet[i]] = v
        g.vp.name[v] = alphabet[i]
        i += 1

    vt = [(d[item[0]], d[item[1]]) for item in tuples]
    g.add_edge_list(vt)

    return g


if __name__ == '__main__':
    as_undir_tuples = [('a', 'b'), ('a', 'c'), ('a', 'd'), ('b', 'd'), ('c', 'g'),
                       ('d', 'f'), ('d', 'g'), ('e', 'b'), ('e', 'd'), ('f', 'c'), ('g', 'e')]
    # gr = make_toy_graph()
    gr = make_toy_graph(tuples=as_undir_tuples, as_undirected=True)

    print gr
    goals = ['a', 'e']
    goals = [find_vertex(gr, gr.vp.name, item)[0] for item in goals]

    # x,y:
    for path in all_paths(gr, goals[0], goals[1]):
        print "Lenght: %d : %s" % (len(path), path)
    # y,x:
    for path in all_paths(gr, goals[1], goals[0]):
        print "Lenght: %d : %s" % (len(path), path)

    dist = shortest_distance(gr)
    for v in gr.vertices():
        print(dist[v].a)

    print [x[0] - x[1] for x in zip(dist[goals[0]].a, dist[goals[1]].a)]

    emap = spanning(gr, goals, verbose=False)
    u = GraphView(gr, efilt=emap)

    pos_u = sfdp_layout(u, gamma=1.5)
    pos_gr = sfdp_layout(gr, gamma=1.5)
    graph_draw(gr, pos_gr, output_size=(1000, 1000), vertex_text=gr.vp.name,
               edge_text_size=8)
    graph_draw(u, pos_u, output_size=(1000, 1000), vertex_text=u.vp.name,
               edge_text_size=8)
