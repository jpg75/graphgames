from argparse import ArgumentParser
from string import whitespace
from parser import RuleParser
from itertools import cycle

__author__ = 'Gian Paolo Jesi'

"""
This module implements the basic services provided by the old "nemik" program written in OPascal
(Delphi).
The aim of this implementation is to provide nemik features that can be exploited by
distinct interfaces: CLI, web, GUI,...
"""

_SHOE_FILE_ORDER = ['NK', 'N', 'U', 'C', 'CK', 'T', 'GC', 'PL']


class pyNemik(object):
    def __init__(self, moves, ck_rules=None, nk_rules=None, iterations=10, gui=False,
                 verbose=False):
        self.ordered_hands = []  # list of hands in order (as they appear in the file
        self.moves = self.load_moves(moves)  # dictionary of lists
        self.ck_rules = self.load_rules(ck_rules) if ck_rules is None else None
        self.nk_rules = self.load_rules(nk_rules) if nk_rules is None else None
        self.iterations = iterations
        self.gui = gui
        self.deck = dict([(x, '') for x in _SHOE_FILE_ORDER])
        self.classification = None
        self.verbose = verbose

    def load_moves(self, moves_file):
        data = dict()
        current_hand = ''
        with open(moves_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line == '': continue

                if any([c in line for c in whitespace]):  # a hand line
                    self.ordered_hands.append(line)
                    data[line] = []
                    current_hand = line

                else:
                    data[current_hand].append(line)

        print "Loaded %d distinct hands from file %s" % (len(self.ordered_hands), moves_file)
        return data

    def load_rules(self, rules_file):
        return RuleParser(file_name=rules_file)

    def init_deck(self, hand, turn='CK'):
        """
        Initialize the internal deck representation with the provided hand.
        :param hand: string representing the hand
        :param turn: the player turn. It is used only when the hand does not hold the turn info,
                        as in the old Nemik data format
        """
        hand = hand.split()
        l = len(hand)
        if l < 6 or l > 7:
            print "Error: %d elements in hand string. Must be: >=6 x <=8."
            return

        if l == 6:
            hand.extend(['2H', 'CK'])
        elif l == 7:
            hand.append(turn)

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
        itr = cycle(['CK', 'NK'])
        for hand in self.ordered_hands:
            hand_turn = itr.next()
            if self.verbose: print "hand: %s" % hand
            data[hand] = []
            # classify this hand for every player:
            for mseq in self.moves[hand]:
                if self.verbose: print "sequence: %s" % mseq

                self.init_deck(hand, turn=hand_turn)
                tcardseq = self.deck['T']

                for c in mseq:
                    if self.verbose:
                        print "playing %s" % c
                        print "deck before: %s" % self.deck
                    self.play_move(c)
                    if self.verbose:
                        print "deck after: %s" % self.deck

                    if c == 'T':
                        tcardseq += ' ' + self.deck['T']

                data[hand].append(tcardseq)

        self.classification = data

    def show_classification(self):
        for item in self.ordered_hands:
            print "%s -> %r" % (item, self.classification[item])

    def play_move(self, move):
        """
        Play or simulate a move over the deck.
        No checks are performed concerning the validity of the move.

        :param move: a move symbol (str)
        """

        def pass_turn(deck):
            if deck['PL'] == 'NK':
                deck['PL'] = 'CK'
            elif deck['PL'] == 'CK':
                deck['PL'] = 'NK'

        def move_c(deck):
            if deck['PL'] == 'NK':
                old = deck['NK']  # backup
                deck['NK'] = deck['C']
                deck['C'] = old
            elif deck['PL'] == 'CK':
                old = deck['CK']  # backup
                deck['CK'] = deck['C']
                deck['C'] = old

            pass_turn(deck)

        def move_n(deck):
            if deck['PL'] == 'NK':
                old = deck['NK']  # backup
                deck['NK'] = deck['N']
                deck['N'] = old
            elif deck['PL'] == 'CK':
                old = deck['CK']  # backup
                deck['CK'] = deck['N']
                deck['N'] = old

            pass_turn(deck)

        def move_u(deck):
            if deck['PL'] == 'NK':
                old = deck['NK']  # backup
                deck['NK'] = deck['U']
                deck['U'] = old
            elif deck['PL'] == 'CK':
                old = deck['CK']  # backup
                deck['CK'] = deck['U']
                deck['U'] = old

            pass_turn(deck)

        def move_t(deck):
            if deck['PL'] == 'NK':
                old = deck['NK']  # backup
                deck['NK'] = deck['T']
                deck['T'] = old
            elif deck['PL'] == 'CK':
                old = deck['CK']  # backup
                deck['CK'] = deck['T']
                deck['T'] = old

            pass_turn(deck)

        options = {'P': pass_turn,
                   'C': move_c,
                   'N': move_n,
                   'U': move_u,
                   'T': move_t
                   }

        options[move](self.deck)  # play


def main(parser):
    args = vars(parser.parse_args())

    if args['moves'] is None:
        parser.print_help()
    else:
        print "Nemik running..."

        if not args['gui']:  # no GUI
            nemik = pyNemik(moves=args['moves'],
                            ck_rules=args['ck_rules'],
                            nk_rules=args['nk_rules'],
                            iterations=args['iterations'],
                            verbose=args['verbose'])
            nemik.classify()
            nemik.show_classification()

        else:  # generate GUI
            pass


if __name__ == '__main__':
    p = ArgumentParser(description="""Command Line Interface to Nemik python.""")

    p.add_argument("-m", "--moves", dest="moves",
                   help="specify the moves file to read from. Default is "
                        "'aggregated_output.txt' in project directory",
                   metavar="FILE")

    p.add_argument("-n", "--nk_rules", dest="nk_rules",
                   help="automata rules for NK role",
                   metavar="FILE")

    p.add_argument("-c", "--ck_rules", dest="ck_rules",
                   help="automata rules for CK role",
                   metavar="FILE")

    p.add_argument("-N", "--iterations", dest="iterations",
                   help="how many times the automata will play each hand")

    p.add_argument("-G", "--gui", action="store_true", dest="gui",
                   help="toggle GUI generation")

    p.add_argument("-v", action="store_true", dest="verbose", help="toggle verbosity")

    main(p)
