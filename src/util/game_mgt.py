from game_gen import get_TTT_bforce_graph, g_struct, get_game_graph

__author__ = 'Gian Paolo Jesi'


class GameEngine(object):
    """
    Basic game engine class. Implements the interface defined by the GameManager.
    """

    def __init__(self, struct):
        self.struct = struct
        self.start_state = None

    def play_move(self, move, current_state=None):
        if current_state:
            self.start_state = current_state

        if self.start_state:
            rule_list = self.struct['rules'].get(move, None)
            if rule_list:
                pass
            else:
                raise Exception("Rule operation: '%s', not available." % move)
                pass
        else:
            return None

    def get_graph(self, start_state=None, how_many=None):
        return get_TTT_bforce_graph(self.struct)


class GameManager(object):
    """
    Factory class for game engines. At the manger level, the state is a list of strings.
    """

    def __init__(self, game_struct):
        self.struct = game_struct
        self.game = None

    def generate_game(self):
        self.game = GameEngine(self.struct)

    def get_graph(self, start_state=None):
        if self.game:
            # result = None
            if start_state:
                st = [{x: k} for x, k in
                      zip(self.struct['status_keys'], start_state)]
                result = self.game.get_graph(start_state=start_state)
            else:
                result = self.game.get_graph()
            return result
        else:
            return None

    def play_move(self, move):
        return self.game.play_move(move)


st = [{x: k} for x, k in zip(g_struct['status_keys'], ['2C', '2H', '3C', '3H', '4C', '4H', 'CK'])]
if __name__ == '__main__':
    pass
    # get_TTT_bforce_graph(g_struct)
