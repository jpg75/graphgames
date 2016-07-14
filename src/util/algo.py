__author__ = 'Gian Paolo Jesi'

from graph_tool import Graph, GraphView
from graph_tool.topology import min_spanning_tree, all_paths
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

    for path in all_paths(gr, 0, 4):
        print "Lenght: %d : %s" % (len(path), path)

    # g2 = spanning(gr, [gr.vertex(0), gr.vertex(4)])
    emap = spanning(gr, [gr.vertex(0), gr.vertex(4)], verbose=True)
    # emap = spanningTree(gr, [gr.vertex(0)], verbose=True)

    # tmap = min_spanning_tree(gr, root=gr.vertex(0))
    # u = GraphView(gr, efilt=tmap)
    u = GraphView(gr, efilt=emap)

    print gr

    pos = sfdp_layout(u, gamma=1.5)
    graph_draw(gr, pos, output_size=(1000, 1000), vertex_text=gr.vertex_index, edge_text_size=8)
    graph_draw(u, pos, output_size=(1000, 1000), vertex_text=u.vertex_index, edge_text_size=8)
