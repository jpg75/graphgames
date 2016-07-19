__author__ = 'Gian Paolo Jesi'

from graph_tool import Graph, GraphView
from graph_tool.topology import min_spanning_tree, all_paths, shortest_distance
from graph_tool.draw import *


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

    gv = g.copy()
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

    #print result


if __name__ == '__main__':
    gr = Graph()
    a = gr.add_vertex()
    b = gr.add_vertex()
    c = gr.add_vertex()
    d = gr.add_vertex()
    e = gr.add_vertex()
    f = gr.add_vertex()
    g = gr.add_vertex()
    gr.add_edge(a, b)
    gr.add_edge(a, d)
    gr.add_edge(a, c)
    gr.add_edge(b, a)
    gr.add_edge(b, d)
    gr.add_edge(c, g)
    gr.add_edge(d, a)
    gr.add_edge(d, f)
    gr.add_edge(d, g)
    gr.add_edge(e, b)
    gr.add_edge(e, d)
    gr.add_edge(f, c)
    gr.add_edge(g, e)

    goals = [a, e]

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

    posu = sfdp_layout(u, gamma=1.5)
    posgr = sfdp_layout(gr, gamma=1.5)
    graph_draw(gr, posgr, output_size=(1000, 1000), vertex_text=gr.vertex_index, edge_text_size=8)
    graph_draw(u, posu, output_size=(1000, 1000), vertex_text=u.vertex_index, edge_text_size=8)
