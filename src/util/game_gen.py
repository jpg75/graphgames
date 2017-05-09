from collections import deque
from itertools import permutations
from json import dumps

__author__ = 'Gian Paolo Jesi'

struct = {
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
        'PL': {
            'values': ['CK', 'NK']
        }
    }
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


def game_states_from(start_state, game_struct, howmany=None):
    """
    Generate the graph/tree of possible game states from a starting one.

    :param start_state: a list of dictionaries key/value of the game state of interest
    :param game_struct: a structure defining the game in terms of states, values, rules and
    constraints
    :param howmany: howmany states iteration to descend
    :return:
    """
    lstatus = _enrich_status(start_state, game_struct)

    print lstatus

    for rule_op in game_struct['rules']:  # this is a dict with operations
        print "Rule operation: ", rule_op
        for rule_seq in game_struct['rules'][rule_op]:  # rule seq for op
            for rule in rule_seq:  # rule
                print "Rule: ", rule
                result = None
                if rule.startswith('lambda'):
                    f = eval(rule)
                    # execute the python string
                    result = f(*lstatus)
                    print "result: ", result

                elif rule.startswith('next'):
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
                            lstatus[index]['value'] = next_value[0]
                            result = lstatus
                    print "result: ", result

                else:
                    print("Waring: unrecognized operation or statement: "), rule

                # no result means rule set invalid: skip this set
                if not result:
                    break
                else:
                    # result = convert_kv(result)
                    # result = _enrich_status(result)
                    pass

                    # print d


# a list of dictionaries stating card position and card value in the TTT case.
# the order is given by the game structure 'status_keys' list.
# each dictionary is then enriched by the features in the game structure.
st = [{x: k} for x, k in zip(struct['status_keys'], ['2C', '2H', '3C', '3H', '4C', '4H', 'CK'])]
if __name__ == '__main__':
    game_states_from(st, struct)

    # print dumps(struct)

# print list(permutations(['2C','2H','3C','3H','4C','4H']))
