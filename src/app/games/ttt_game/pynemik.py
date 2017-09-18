from argparse import ArgumentParser
from string import whitespace
from parser import RuleParser
from ttt import _SHOE_FILE_ORDER

__author__ = 'Gian Paolo Jesi'

"""
This module implements the basic services provided by the old "nemik" program written in OPascal
(Delphi).
The aim of this implementation is to provide nemik functionalities that can be exploited by
distinct interfaces: CLI, web, GUI,...
"""


class Nemik(object):
    def __init__(self, moves, ck_rules=None, nk_rules=None, iteration=0, gui=False):
        self.moves = self.load_moves(moves)  # dictionary of lists
        self.ck_rules = self.load_rules(ck_rules) if ck_rules is None else None
        self.nk_rules = self.load_rules(nk_rules) if nk_rules is None else None
        self.iteration = iteration
        self.gui = gui
        self.deck = dict([(x, '') for x in _SHOE_FILE_ORDER])

    def load_moves(self, moves_file):
        data = dict()
        current_hand = ''
        try:
            with open(moves_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line == '': continue

                    if any([c in line for c in whitespace]):  # a hand line
                        data[line] = []
                        current_hand = line

                    else:
                        data[current_hand].append[line]

        except Exception as e:
            print "Cannot open file: %s" % e

        print data
        return data

    def load_rules(self, rules_file):
        return RuleParser(file_name=rules_file)

    def init_deck(self, hand):
        """
        Initialize the internal deck representation with the provided hand.
        :param hand: string representing the hand
        """
        hand = hand.split()
        if len(hand) == 6:
            hand.extend(['2H', 'CK'])
        elif len(hand) == 7:
            hand.append('CK')

        hand_data = dict(zip(_SHOE_FILE_ORDER, hand))
        for item in hand_data:
            self.deck[item] = hand_data[item]

    def classify(self):
        """
        Classify the loaded moves in order to detect the game style (eg.: 422, 442).
        For each hand, it shows the content of the Target position over time.

        :return:
        """
        data = dict()
        for hand in self.moves:
            data[hand] = []
            # classify this hand for every player:
            for mseq in self.moves[hand]:
                tcardseq = ''
                self.init_deck(hand)
                for c in mseq:
                    self.play_move(c)
                    if c == 'T':
                        tcardseq += ' ' + self.deck['T']

                data[hand].append(tcardseq)

        print data

    def play_move(self, move):
        """
        Play or simulate a move over the deck.
        No checks are performed concerning the validity of the move.

        :param move: a move symbol (str)
        """

        def pass_turn():
            if self.deck['PL'] == 'NK':
                self.deck['PL'] = 'CK'
            elif self.deck['PL'] == 'CK':
                self.deck['PL'] = 'NK'

        def move_c():
            if self.deck['PL'] == 'NK':
                old = self.deck['NK']  # backup
                self.deck['NK'] = self.deck['C']
                self.deck['C'] = old
            elif self.deck['PL'] == 'CK':
                old = self.deck['CK']  # backup
                self.deck['CK'] = self.deck['C']
                self.deck['C'] = old

            pass_turn()

        def move_n():
            if self.deck['PL'] == 'NK':
                old = self.deck['NK']  # backup
                self.deck['NK'] = self.deck['N']
                self.deck['N'] = old
            elif self.deck['PL'] == 'CK':
                old = self.deck['CK']  # backup
                self.deck['CK'] = self.deck['N']
                self.deck['N'] = old

            pass_turn()

        def move_u():
            if self.deck['PL'] == 'NK':
                old = self.deck['NK']  # backup
                self.deck['NK'] = self.deck['U']
                self.deck['U'] = old
            elif self.deck['PL'] == 'CK':
                old = self.deck['CK']  # backup
                self.deck['CK'] = self.deck['U']
                self.deck['U'] = old

            pass_turn()

        def move_t():
            if self.deck['PL'] == 'NK':
                old = self.deck['NK']  # backup
                self.deck['NK'] = self.deck['T']
                self.deck['T'] = old
            elif self.deck['PL'] == 'CK':
                old = self.deck['CK']  # backup
                self.deck['CK'] = self.deck['T']
                self.deck['T'] = old

            pass_turn()

        options = {'P': pass_turn,
                   'C': move_c,
                   'N': move_n,
                   'U': move_u,
                   'T': move_t
                   }


def main(parser):
    args = vars(parser.parse_args())
    if args is None:
        print "None"

    if len(args) == 0:
        parser.print_help()
    else:
        print "Nemik running..."

        if not args['gui']:  # no GUI
            nemik = Nemik(moves=args['moves'],
                          ck_rules=args['ck_rules'],
                          nk_rules=args['nk_rules'],
                          iteration=args['iteration'])
            nemik.classify()

        else:  # generate GUI
            pass


if __name__ == '__main__':
    p = ArgumentParser(description="""Command Line Interface to Nemik python.""")

    p.add_argument("-m", "--moves", dest="moves",
                   help="specify the moves file to read from. Default is "
                        "'aggregated_output.txt' in project directory",
                   metavar="FILE", default='aggregated_output.txt')

    p.add_argument("-n", "--nk_rules", dest="nk_rules",
                   help="automata rules for NK role",
                   metavar="FILE",
                   default='')

    p.add_argument("-c", "--ck_rules", dest="ck_rules",
                   help="automata rules for CK role",
                   metavar="FILE",
                   default='')

    p.add_argument("-N", "--iterations", dest="iterations",
                   help="how many times the automata will play each hand",
                   default=0)

    p.add_argument("-G", "--gui", action="store_true", dest="gui",
                   help="toggle GUI generation")

    p.add_argument("-v", action="store_true", dest="verbose", help="toggle verbosity")

    main(p)
