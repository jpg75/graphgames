__author__ = 'Gian Paolo Jesi'

from numpy.random import random
from util.algo import split_check, spanning
from graph_tool.generation import geometric_graph, random_graph
from graph_tool.draw import graph_draw, sfdp_layout
from graph_tool import load_graph
from timeit import default_timer as timer

if __name__ == '__main__':
    # points = random((10000, 2)) * 4
    # g, pos = geometric_graph(points, 0.3, [(0, 4), (0, 4)])
    g = load_graph('data/bg2000.xml.gz')
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
