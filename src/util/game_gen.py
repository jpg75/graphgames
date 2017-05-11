from collections import deque
from itertools import permutations
from json import dumps
from copy import deepcopy

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
    'elements': {
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
    # VERIFICARE CHE LAMBDA GENERI DEGLI OGGETTI NUOVI TOTALEMNET: NON SOLO L'ESTERNO
    return new_state


def _process_next(rule, state, struct):
    if state is None:
        return None

    result = deepcopy(state)

    args = rule.split()
    print  "args: ", args
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


AVAILABLE_STATEMENTS = {'lambda': _process_lambda,
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
    for key_item in status:
        elem = dict()
        for k, v in key_item.items():  # earning : dict must have just a single entry k,v
            elem['value'] = v
            elem['key'] = k

        # enrich with features stated in the game struct:
        if elem['value'] in game_struct['elements'].keys():
            for k in game_struct['elements'][elem['value']].keys():
                elem[k] = game_struct['elements'][elem['value']][k]

        d.append(elem)

    return d


def game_states_from2(start_state, game_struct):
    status = _enrich_status(start_state, game_struct)
    # print status
    state_map = {}  # maps a state (values) to an index, keeps track of discovered states
    edges = []  # maps a state to a pair (state, rule)

    state_map[' '.join([item['value'] for item in status])] = 1  # add the start state

    for rule_op in game_struct['rules']:
        print "Rule operation: ", rule_op
        for rule_seq in game_struct['rules'][rule_op]:

            next_state = None
            inter_state = deepcopy(status)
            for rule in rule_seq:
                splt = rule.split()
                print "rule: ", rule
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

            print "next state: ", next_state
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
                    print "Setting state: %s with id %d and edge: %d, %d, %s" % (s, next_state_id,
                                                                                 state_map[
                                                                                     old_s],
                                                                                 state_map[s], \
                                                                                 rule_op)
                else:
                    old_s = ' '.join([item['value'] for item in status])
                    edges.append((state_map[old_s],
                                  state_map[s], rule_op))
                    print "Setting edge: %d, %d, %s" % (state_map[old_s],
                                                        state_map[s], \
                                                        rule_op)

    return state_map, edges


def game_states_from(start_state, game_struct, howmany=None):
    """
    Generate the graph/tree of possible game states from a starting one.

    :param start_state: a list of dictionaries key/value of the game state of interest
    :param game_struct: a structure defining the game in terms of states, values, rules and
    constraints
    :param howmany: howmany states iteration to descend
    :return: a pair (dictionary, list) respectively mapping state values to unique index and
    listing triplets as (state_i, state_j, rule)
    """
    lstatus = _enrich_status(start_state, game_struct)
    state_map = {}  # maps a state (values) to an index, keeps track of discovered states
    edges = []  # maps a state to a pair (state, rule)

    state_map[' '.join([x['value'] for x in lstatus])] = 1  # add the start state

    for rule_op in game_struct['rules']:  # this is a dict with operations
        print "Rule operation: ", rule_op
        print "LSTATUS: ", lstatus
        for rule_seq in game_struct['rules'][rule_op]:  # rule seq for op
            result = None

            for rule in rule_seq:  # rule
                print "Rule: ", rule
                print "LSTATUS: ", lstatus
                if rule.startswith('lambda'):
                    f = eval(rule)
                    # execute the python string
                    result = f(*lstatus)

                elif rule.startswith('next'):
                    if not result:
                        result = deepcopy(lstatus)

                    args = rule.split()
                    for arg in args[1:]:  # from the second string element
                        index = game_struct['status_keys'].index(arg)
                        var_values = game_struct['elements'].get(arg, None)
                        if not var_values:
                            print "Warning: position %s has no corresponding entry in 'elements' " \
                                  "structure." % arg
                        else:
                            next_value = deque(game_struct['elements'][arg]['values'])
                            next_value.rotate(-1)
                            result[index]['value'] = next_value[0]
                            # print "set to: ", next_value[0]

                else:
                    print("Waring: unrecognized operation or statement: "), rule

                # no result means rule set invalid: skip this set
                if not result:
                    print "OP Result is None"
                    break

            if not result:
                print "Skip the entire set for rule: ", rule_op
                break
            else:
                # log valid state
                s = ' '.join([x['value'] for x in result])
                # print "s: ", s
                if not state_map.get(s):  # when not present, add
                    new_state_id = len(state_map.keys()) + 1
                    state_map[s] = new_state_id
                    old_s = ' '.join([x['value'] for x in lstatus])
                    # print "old_s: ", old_s
                    # print lstatus
                    edges.append((state_map[old_s], state_map[s], rule_op))
                    print "Setting state: %s with id %d and edge: %d, %d, %s" % (s, new_state_id,
                                                                                 state_map[
                                                                                     old_s],
                                                                                 state_map[s], \
                                                                                 rule_op)
                else:
                    old_s = ' '.join([x['value'] for x in lstatus])
                    edges.append((state_map[old_s],
                                  state_map[s], rule_op))
                    print "Setting edge: %d, %d, %s" % (state_map[old_s],
                                                        state_map[s], \
                                                        rule_op)

    return state_map, edges


# a list of dictionaries stating card position and card value in the TTT case.
# the order is given by the game structure 'status_keys' list.
# each dictionary is then enriched by the features in the game structure.
st = [{x: k} for x, k in zip(g_struct['status_keys'], ['2C', '2H', '3C', '3H', '4C', '4H', 'CK'])]
if __name__ == '__main__':
    # s, e = game_states_from(st, g_struct)
    s, e = game_states_from2(st, g_struct)
    print "States found: ", s
    print "edges found: ", e
    # print "JSON of the structure: ", dumps(struct)

# print list(permutations(['2C','2H','3C','3H','4C','4H']))
