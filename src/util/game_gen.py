from collections import deque
from itertools import permutations
from json import dumps
from copy import deepcopy
from sys import maxsize

__author__ = 'Gian Paolo Jesi'

g_struct = {
    'status_keys': ['CK', 'NK', 'U', 'C', 'N', 'T', 'PL'],
    'moves': ['U', 'P', 'C', 'N', 'T'],
    'rules': {
        'U': [
            [
                "lambda CK,NK,U,C,N,T,PL: (U,NK,CK,C,N,T,PL) if PL['value']=='CK' else (CK,U,NK,C,N,T,PL)",
                "next PL"]
        ],
        'C': [
            [
                "lambda CK,NK,U,C,N,T,PL: (C,NK,U,CK,N,T,PL) if PL['value']=='CK' else (CK,C,U,NK,N,T,PL)",
                "next PL"],
        ],
        'N': [
            [
                "lambda CK,NK,U,C,N,T,PL: (N,NK,U,C,CK,T,PL) if PL['value']=='CK' else (CK,N,U,C,NK,T,PL)",
                "next PL"],
        ],
        'P': [
            ["next PL"]
        ],
        'T': [
            [
                "lambda CK,NK,U,C,N,T,PL: (T,NK,U,C,N,CK,PL) if PL['value']=='CK' and CK['color']==T['color'] else None",
                "next PL"],
            [
                "lambda CK,NK,U,C,N,T,PL: (CK,T,U,C,N,NK,PL) if PL['value']=='NK' and NK['number']==T['number'] else None",
                "next PL"],
        ]
    },
    'elements': {  # 'features' might be a better name!
        # standard features: belong to possible values of status_keys
        '2C': {
            'color': 'black',
            'number': 2
        },
        '2H': {
            'color': 'red',
            'number': 2
        },
        '3C': {
            'color': 'black',
            'number': 3
        },
        '3H': {
            'color': 'red',
            'number': 3
        },
        '4C': {
            'color': 'black',
            'number': 4
        },
        '4H': {
            'color': 'red',
            'number': 4
        },
        # extra feature: belongs to one of the status_keys; express the corresponding  key value
        # domain
        'PL': {
            'values': ['CK', 'NK']
        }
    }
}


def _process_lambda(rule, state, struct):
    f = eval(rule)
    new_state = f(*state)
    return new_state


def _process_next(rule, state, struct):
    if state is None:
        return None

    result = deepcopy(state)

    args = rule.split()
    # print  "args: ", args
    for arg in args[1:]:  # from the second string element
        index = struct['status_keys'].index(arg)
        var_values = struct['elements'].get(arg, None)
        if var_values is None:
            print "Warning: position %s has no corresponding entry in 'elements' " \
                  "structure." % arg
        else:
            next_value = deque(struct['elements'][arg]['values'])
            next_value.rotate(-1)
            result[index]['value'] = next_value[0]
            # print "set to: ", next_value[0]

    return result


AVAILABLE_STATEMENTS = {
    'lambda': _process_lambda,
    'next': _process_next
}


def _enrich_status(status, game_struct):
    """
    Enrich the basic game status with the features listed in the 'elements' section of the
    game_struct.

    :param status: basic status
    :param game_struct: game structure, a dictionary defining the game in abstract terms.
    :return:
    """
    # prepare an list with empty dictionaries:
    d = []
    for key_value in status:
        elem = dict()
        for k, v in key_value.items():  # earning : dict must have just a single entry k,v
            elem['value'] = v
            elem['key'] = k

        # enrich with features stated in the game struct:
        if elem['value'] in game_struct['elements'].keys():
            for k in game_struct['elements'][elem['value']].keys():
                elem[k] = game_struct['elements'][elem['value']][k]

        d.append(elem)

    return d


def _evaluate_rules(rule_op, rule_seq, status, game_struct):
    next_state = None
    inter_state = deepcopy(status)
    for rule in rule_seq:
        splt = rule.split()
        # print "rule: ", rule
        if splt[0] in AVAILABLE_STATEMENTS:
            next_state = AVAILABLE_STATEMENTS[splt[0]](rule, inter_state, game_struct)

            if next_state is None:
                print "Skip the entire set for rule: ", rule_op
                break
            else:
                # feed the new state as input to the next rule if any:
                inter_state = deepcopy(next_state)

        else:
            print "Waring: unrecognized operation or statement: ", rule

    return next_state


def game_states_from2(start_state, game_struct, state_map, edges):
    """
    Generate the graph/tree of possible game states from a starting one.

    :param start_state: a list of dictionaries key/value of the game state of interest
    :param game_struct: a structure defining the game in terms of states, values, rules and
        constraints
    :param state_map: maps a state value to an index
    :param edges: a list of triplets: (node_a, node_b, op)
    :return: a pair (dictionary, list) respectively mapping state values to unique index and
    listing triplets as (state_i, state_j, rule)
    """
    status = _enrich_status(start_state, game_struct)
    # print status
    # state_map = {}  # maps a state (values) to an index, keeps track of discovered states
    # edges = []  # maps a state to a pair (state, rule)

    state_str = ' '.join([item['value'] for item in status])
    if state_map.get(state_str, None) is None:
        state_map[state_str] = len(state_map) + 1  # add the start state

    for rule_op in game_struct['rules']:
        # print "Rule operation: ", rule_op
        for rule_seq in game_struct['rules'][rule_op]:

            next_state = None
            inter_state = deepcopy(status)
            for rule in rule_seq:
                splt = rule.split()
                # print "rule: ", rule
                if splt[0] in AVAILABLE_STATEMENTS:
                    next_state = AVAILABLE_STATEMENTS[splt[0]](rule, inter_state, game_struct)

                    if next_state is None:
                        print "Skip the entire set for rule: ", rule_op
                        break
                    else:
                        # feed the new state as input to the next rule if any:
                        inter_state = deepcopy(next_state)

                else:
                    print "Waring: unrecognized operation or statement: ", rule

            # print "next state: ", next_state
            if next_state is not None:
                # collect the new state:
                s = ' '.join([item['value'] for item in next_state])
                if state_map.get(s) is None:  # when not present, add
                    next_state_id = len(state_map.keys()) + 1
                    state_map[s] = next_state_id
                    old_s = ' '.join([item['value'] for item in status])
                    # print "old_s: ", old_s
                    # print status
                    edges.append((state_map[old_s], state_map[s], rule_op))
                    # print "Setting state: %s with id %d and edge: %d, %d, %s" % (s, next_state_id,
                    #                                                              state_map[
                    #                                                                  old_s],
                    #                                                              state_map[s], \
                    #                                                              rule_op)
                else:
                    old_s = ' '.join([item['value'] for item in status])
                    edges.append((state_map[old_s],
                                  state_map[s], rule_op))
                    # print "Setting edge: %d, %d, %s" % (state_map[old_s],
                    #                                     state_map[s], \
                    #                                     rule_op)

    return state_map, edges


def get_game_graph(start_state, game_struct, state_map, edges, how_many=None):
    """
    Generate a game graph starting from a specific game state.

    :param start_state:
    :param game_struct:
    :param state_map: maps a state value to an index
    :param edges: a list of triplets: (node_a, node_b, op)
    :param how_many: howmany states iteration to descend
    :return:  a pair (dictionary, list) respectively mapping state values to unique index and
    listing triplets as (state_i, state_j, rule)
    """
    if not how_many:
        how_many = maxsize

    # state_map = dict()  # maps string state into list of edges
    print "start state: ", start_state
    # for x in start_state:
    #     print x.items()
    # s = ' '.join([x.items()[0][0] for x in start_state])
    # state_map[s] = []  # add 1st state

    # Algo:
    #######
    new_states, new_edges = game_states_from2(start_state, game_struct, state_map, edges)
    temp = []
    for item in new_states.keys():  # takes the string
        print "item: ", item
        if item not in state_map:
            state_map[item] = len(state_map) + 1
            # states[item]
            temp.append(item)

    print "temp ", temp
    while temp:  # while not empty...
        item = temp.pop(0)
        print "temp item: ", item

        st = [{x: k} for x, k in zip(g_struct['status_keys'], item.split(' '))]
        print "st: ", st
        new_states, new_edges = game_states_from2(st, game_struct, state_map, edges)
        for item in new_states.keys():  # takes the string
            if item not in state_map and item not in state_map:  # if not existent, mark it and go
                # through it
                state_map[item] = len(state_map) + 1
                # states[item]
                temp.append(item)

        print "temp ", temp
        print "temp len: ", len(temp)

    print "states: ", state_map
    print len(state_map)
    return state_map


def get_bforce_graph(all_permutations, game_struct):
    """
    Generate the game graph from the state permutations.

    :param all_permutations: state permutations of a game
    :param game_struct: a structure defining the game in terms of states, values, rules and
        constraints
    :return:  a pair (dictionary, list) respectively mapping state values to unique index and
    listing triplets as (state_i, state_j, rule)
    """
    state_map = {}
    edges = []

    for item in all_permutations:
        st = [{x: k} for x, k in zip(g_struct['status_keys'], item)]
        n, e = game_states_from2(st, game_struct, state_map, edges)

    print "state_map: ", state_map
    print "edges: ", edges
    return state_map, edges


def get_TTT_bforce_graph(game_struct):
    """
    Genrate a TTT game graph using all state permutations.

    :param game_struct: a structure defining the game in terms of states, values, rules and
        constraints
    :return:  a pair (dictionary, list) respectively mapping state values to unique index and
    listing triplets as (state_i, state_j, rule)
    """
    l = list(permutations(['2C', '2H', '3C', '3H', '4C', '4H']))
    l1 = [item + ('NK',) for item in l]
    l2 = [item + ('CK',) for item in l]
    l3 = l1 + l2

    n, e = get_bforce_graph(all_permutations=l3, game_struct=game_struct)
    return n, e


# a list of dictionaries stating card position and card value in the TTT case.
# the order is given by the game structure 'status_keys' list.
# each dictionary is then enriched by the features in the game structure.
st = [{x: k} for x, k in zip(g_struct['status_keys'], ['2C', '2H', '3C', '3H', '4C', '4H', 'CK'])]
if __name__ == '__main__':
    # s, e = game_states_from2(st, g_struct)
    # print "States found: ", s
    # print "edges found: ", e
    # print "JSON of the structure: ", dumps(struct)

    print "generating graph"
    state_map = {}
    edges = []
    get_game_graph(st, g_struct, state_map, edges)
    # print list(permutations(['2C','2H','3C','3H','4C','4H']))

    print "generating brute force graph"
    # get_TTT_bforce_graph(g_struct)


# automi azione reazione è una macchina di Turing?