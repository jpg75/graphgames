__author__ = 'Gian Paolo Jesi'

from util.algo import split_check, spanning
from graph_tool.generation import geometric_graph, random_graph
from numpy import random
from graph_tool.draw import graph_draw, sfdp_layout
from graph_tool import load_graph
from timeit import default_timer as timer


def _corr(a, b):
    if a == b:
        return 0.999
    else:
        return 0.001


def graph_gen():
    # points = random((10000, 2)) * 4
    # g, pos = geometric_graph(points, 0.3, [(0, 4), (0, 4)])
    g, bm = random_graph(20000, lambda: random.poisson(10), directed=False,
                         model="blockmodel-traditional",
                         block_membership=lambda: random.randint(10),
                         vertex_corr=_corr)
    return g, bm


if __name__ == '__main__':
    g = load_graph('data/bg20000.xml.gz')
    print "Graph loaded: ", g

    print "Calculating distance matrix..."
    start = timer()
    split_check(g, [g.vertex(0), g.vertex(1000)])
    end = timer()
    print "time spent: ", end - start

    # print "Calculating layout generation..."
    # start = timer()
    # pos = sfdp_layout(g, gamma=1.5)
    # end = timer()
    # print "time spent: ", end - start

    # pos2 = graph_draw(g, pos, output_size=(1200, 800))

    print "Calculating spanning..."
    start = timer()
    span_map = spanning(g, [g.vertex(0), g.vertex(1000)])
    end = timer()
    print "time spent: ", end - start

    g.set_edge_filter(span_map)

    # print "Calculating layout generation..."
    # start = timer()
    # pos = sfdp_layout(g, gamma=1.5)
    # end = timer()
    # print "time spent: ", end - start

    # graph_draw(g, pos, output_size=(1200, 800))
