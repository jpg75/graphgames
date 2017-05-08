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


def game_states_from(start_state, game_struct, howmany=None):
    """
    Generate the graph/tree of possible game states from a starting one.

    :param start_state: a key value dictionary of the game state of interest
    :param game_struct: a structure defining the game in terms of states, values, rules and
    constraints
    :param howmany: howmany states iteration to descend
    :return:
    """
    pass