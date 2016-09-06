__author__ = 'Gian Paolo Jesi'

from graph_tool import Graph, GraphView
from graph_tool.topology import shortest_distance
from itertools import combinations
from collection import make_toy_graph
from graph_tool.draw import *
from graph_tool.util import find_vertex
from math import factorial
import numpy as np


def spanning_tree(g, multigoal=[], verbose=False):
    """
    Generate a spanning tree for the given graph g.

    :param g: Graph based object
    :param multigoal: list of goal vertexes (where the spanning starts)
    :param verbose: default disabled
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
    :param verbose: default disabled
    :return: an boolean edge property map, marking the edges of the spanning
    """
    assert len(multigoal) != 0

    gv = g.copy()

    gv.set_fast_edge_removal()  # a bit faster
    spanning_g = gv.new_edge_property('bool')
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
            spanning_g[e] = 1

        actual = frozenset([e.source() for e in predecessors])
        if verbose:
            print "actual: ", actual

    return spanning_g


def split_check(g, goals=[], verbose=False):
    """
    Check if the graph can be split according to the given vertexes in the goal list.
    Based on shortest distance matrix.

    :param g: graph
    :param goals: list of vertexes (goals)
    :param verbose: default disabled
    :return: a pair: (bool, NumPy Array) where the bool represents if we have any split in the graph
    and the string is the distance differences for every combination of goals.
    """
    assert len(goals) >= 2

    any_split = False
    distances = shortest_distance(g)

    mat = np.array([distances[v].a for v in g.vertices()])
    mat = mat.T

    ng = len(goals)
    rows = factorial(ng) / 2 / factorial(ng - 2)
    result = np.zeros(shape=(rows, g.num_vertices()))

    index = 0
    for subset in combinations(goals, 2):
        row = mat[g.vertex_index[subset[0]]] - mat[g.vertex_index[subset[1]]]
        if verbose:
            print row

        if not any_split:
            # print np.count_nonzero(row), g.num_vertices()
            if np.count_nonzero(row) == g.num_vertices():
                any_split = True  # found a split

        result[index] = row
        index += 1

    return any_split, result


def even_odd(g, goals=[], letters=False, verbose=False):
    """
    Generate the even/odd matrix. Essentially, it calculates the distance matrix and converts it
    into a 0/1 matrix just keeping the information about even (1) or odd (0) distances.

    :param g: the graph
    :param goals: list of vertexes (goals)
    :param letters: whether or not using letters ('E', 'O') into even-odd matrix. Default False.
    :param verbose: default disabled
    :return:
    """
    assert len(goals) >= 2

    distances = shortest_distance(g)
    eo = np.zeros(shape=(g.num_vertices(), g.num_vertices()))
    eo = eo.T
    for v in g.vertices():
        print distances[v].a

    index = 0
    for v in g.vertices():
        j = 0
        for value in distances[v].a:
            # print value
            if letters:
                eo[index][j] = 'E' if value % 2 == 0 else 'O'
            else:
                eo[index][j] = 1.0 if value % 2 == 0 else 0.0
            j += 1

        index += 1

    # transforming even-odd
    new_order = []
    for item in goals:
        new_order.append(g.vertex_index[item])
    for item in [x for x in g.vertices() if x not in goals]:
        new_order.append(g.vertex_index[item])
    if verbose:
        print "Reordering EO-matrix as follows: %s" % new_order

    eo_new = eo[:, new_order][new_order]
    return eo, eo_new


if __name__ == '__main__':
    as_undir_tuples = [('a', 'b'), ('a', 'c'), ('a', 'd'), ('b', 'd'), ('c', 'g'),
                       ('d', 'f'), ('d', 'g'), ('e', 'b'), ('e', 'd'), ('f', 'c'),
                       ('g', 'e')]
    # gr = make_toy_graph()
    gr = make_toy_graph(tuples=as_undir_tuples, as_undirected=True)

    goals = ['e', 'f', 'a']
    goals = [find_vertex(gr, gr.vp.name, item)[0] for item in goals]

    print split_check(gr, goals, verbose=True)
    print even_odd(gr, goals, verbose=True)

    emap = spanning(gr, goals, verbose=False)
    u = GraphView(gr, efilt=emap)

    pos_u = sfdp_layout(u, gamma=1.5)
    pos_gr = sfdp_layout(gr, gamma=1.5)
    graph_draw(gr, pos_gr, output_size=(1000, 1000), vertex_text=gr.vp.name,
               edge_text_size=8)
    graph_draw(u, pos_u, output_size=(1000, 1000), vertex_text=u.vp.name,
               edge_text_size=8)
