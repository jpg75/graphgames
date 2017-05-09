__author__ = 'Gian Paolo Jesi'

struct = {
    'status_keys': ['CK', 'NK', 'U', 'C', 'N', 'T', 'PL'],
    'moves': ['U', 'P', 'C', 'N', 'T'],
    'rules': {
        'U': [
            ["lambda CK,NK,U,C,N,T,PL: (U,NK,CK,C,N,T,PL) if PL=='CK' else (CK,U,NK,C,N,T,PL)",
             "! PL"]
        ],
        'C': [
            ["lambda CK,NK,U,C,N,T,PL: (C,NK,U,CK,N,T,PL) if PL=='CK' else (CK,C,U,NK,N,T,PL)",
             "! PL"],
        ],
        'N': [
            ["lambda CK,NK,U,C,N,T,PL: (N,NK,U,C,CK,T,PL) if PL=='CK' else (CK,N,U,C,NK,T,PL)",
             "! PL"],
        ],
        'P': [
            ["! PL"]
        ],
        'T': [
            [
                "lambda CK,NK,U,C,N,T,PL: (T,NK,U,C,N,CK,PL) if PL=='CK' and CK.color==T.color else None",
                "! PL"],
            [
                "lambda CK,NK,U,C,N,T,PL: (CK,T,U,C,N,NK,PL) if PL=='NK' and NK.number==T.number else None",
                "! PL"],
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
            'values': ['NC', 'CK']
        }
    }
}


def _enrich_status(status, game_struct):
    # prepare an list with empty dictionaries:
    d = dict([(x, None) for x in game_struct['status_keys']])
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

    print d


def game_states_from(start_state, game_struct, howmany=None):
    """
    Generate the graph/tree of possible game states from a starting one.

    :param start_state: a list of dictionaries key/value of the game state of interest
    :param game_struct: a structure defining the game in terms of states, values, rules and
    constraints
    :param howmany: howmany states iteration to descend
    :return:
    """
    l = _enrich_status(start_state, game_struct)

    for rule_op in game_struct['rules']:  # this is a dict with operations
        for rule_seq in game_struct['rules'][rule_op]:  # rule seq for op
            for rule in rule_seq:  # rule
                print rule
                result = True
                if rule.startswith('lambda'):
                    # prepare the arguments values
                    # execute the python string
                    pass
                elif rule.startswith('!'):
                    # prepare the argument values
                    # execute the string
                    pass
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
