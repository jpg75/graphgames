import itertools
import random


class RuleParser(object):
    """
    Class for reading and parsing rules for the automatic player.
    Rules are in 'data/arules.txt' file by default.
    """
    
    # as in old 'REGOLE.TXT' file
    weights = [100, 100, 100, 15, 15, 15, 15, 5, 5, 5, 3, 3, 3, 1, 1, 1, 1]  

    def __init__(self, file_name='data/arules.txt'):
        self.filename = file_name
        self.rules = []
        self.rates = dict()  # maps score -> [rule1, rule2,...]

    def load_rules(self):
        with open(self.filename) as f:
            lines = [line.rstrip('\n') for line in f]

        for line in lines:
            if line.startswith('#') or line.startswith('//') or line == '' or line.isspace():
                continue
            else:
                self.rules.append(line.split())

        # check the basics for rule correctness: length
        counter = 1
        for rule in self.rules:
            if len(rule) not in [4, 7, 11, 14, 18]:
                print "Warning: rule -%s- has non standard size: %d" % (str(rule), len(rule))

            counter += 1

        print "Rules loaded: ", len(self.rules)

    def match(self, hand, up, target, ck_knowledge, nk_knowledge, history_record, auto_player='nk'):
        """Calculate the rule match and return the rule to apply.
        The rule to apply is selected according to the rate scored.
        If multiple rules scored the same, then a rule is selected at random
        """
        if not ck_knowledge:
            ckk = []
        else:
            ckk = [[i.get(k) for k in history_record.iterkeys() if k != 'hand'] for i in ck_knowledge]

        if not nk_knowledge:
            nkk = []
        else:
            nkk = [[i.get(k) for k in history_record.iterkeys()] for i in nk_knowledge]

        # since they are lists of 2 items they are multiplied for the inner elements:
        nksize = len(nkk) * 4
        cksize = len(ckk) * 3
        print "ckk: %s" % ckk
        print "nkk: %s" % nkk
        rl = [x for x in self.rules if len(x) - 1 <= cksize + nksize + 4]
        print "Size nk: %d , ck: %s" % (nksize, cksize)
        print "Avail rules:\n %s" % rl

        # makes a single list where alternatively puts ck_knowledge and
        # nk_knowledge elements 'hand' elements are removed from ck_knowledge
        iters = [iter(ckk), iter(nkk)]
        knowledge = [hand, up, target] 
        l = list(it.next() for it in itertools.cycle(iters))
        knowledge.extend([item for sublist in l for item in sublist])
        print "Knowledge: %s" % knowledge
        
        for rule in rl:
            score = 0
            comparison = zip(rule[1:], knowledge)
            index = 0
            # print "COMPARING: %s"%comparison
            for r, k in comparison:
                if r == k:
                    try:
                        score += 1 + RuleParser.weights[index]
                    except IndexError as ie:
                        score += 1
                        
                elif r == '#':
                    pass
                else:
                    score = -1
                    break  # goes to the next rule

            if score != -1:
                if self.rates.get(score):
                    self.rates[score].append(rule)
                else:
                    self.rates[score] = []
                    self.rates[score].append(rule)
              
                print "COMPARING: %s score %d" % (comparison, score)
        
        highest_score = max(self.rates.keys())
        result = self.rates[highest_score]
        print "Highest score: %d" % highest_score
        print "Result set is: %s" % result
        if len(result) == 1:
            return result[0]
        else:
            return random.choice(result)

    def show_rule_rates(self, how_many=5):
        txt = ''
        s = sorted(self.rates.iterkeys())
        for k in s[min(how_many, len(s))]:
            txt += self.rates[k] + '\n'

        return txt

# ===============================================================================
# Debugging from console with:
#
# rp.match('3C','2C','4C',[{'hand':'2C','move':'U','up':'2H','target':'4C'}],[])
# ===============================================================================
