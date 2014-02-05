__author__ = 'Leif'

from pygoap.actions import Ability, ActionContext
from pygoap.agent import GoapAgent
from pygoap.goals import *
from pygoap.precepts import *
from lib.english import make_english
import random


def coroutine(func):
    def start(*args, **kwargs):
        cr = func(*args, **kwargs)
        next(cr)
        return cr

    return start


@coroutine
def age_action(context, caller):
    """
    Makes the caller older
    """

    age = 0
    try:
        while 1:
            td = (yield)
            age += td
    except GeneratorExit:
        pass


class AgeAbility(Ability):
    def get_contexts(self, caller, memory=None):
        effects = []
        prereqs = []
        action = age_action(self, caller)
        context = ActionContext(self, caller, action, prereqs, effects)
        yield context


@coroutine
def give_birth_action(context, caller):
    """
    Make a new human child
    """

    try:
        td = (yield)
        p = ActionPrecept(caller, "birth", None)
        caller.environment.enqueue_precept(p)
    except GeneratorExit:
        pass


class GiveBirthAbility(Ability):
    """
    Make a new human child
    """

    def get_contexts(self, caller, memory=None):
        effects = [SimpleGoal(has_baby=True), SimpleGoal(ready_to_birth=False)]
        prereqs = [SimpleGoal(ready_to_birth=True)]
        action = give_birth_action(self, caller)
        context = ActionContext(self, caller, action, prereqs, effects)
        yield context


@coroutine
def create_life_action(context, caller):
    ttl = 3
    try:
        while 1:
            td = (yield)
            if ttl <= 0:
                break
            ttl -= td
    except GeneratorExit:
        pass


class CreateLifeAbility(Ability):
    def get_contexts(self, caller, memory=None):
        effects = [SimpleGoal(ready_to_birth=True)]
        prereqs = [SimpleGoal(had_sex=True)]
        action = create_life_action(self, caller)
        context = ActionContext(self, caller, action, prereqs, effects)
        yield context


@coroutine
def copulate_action(context, caller):
    try:
        td = (yield)
        p = ActionPrecept(caller, "sex", None)
        caller.environment.enqueue_precept(p)
    except GeneratorExit:
        pass


class CopulateAbility(Ability):
    def get_contexts(self, caller, memory=None):
        effects = [SimpleGoal(had_sex=True)]
        action = copulate_action(self, caller)
        context = ActionContext(self, caller, action, None, effects)
        yield context


@coroutine
def speak_action(context, caller, p):
    try:
        td = (yield)
        print('[{}]\t\t{}'.format(caller.name, make_english(caller, p)))
    except GeneratorExit:
        pass


class ConverseAbility(Ability):
    """
    examine caller's memory and create some things to say
    """
    def get_contexts(self, caller, memory=None):
        if memory is not None:
            p = random.choice(list(memory))
            effects = [SimpleGoal(chatter=True)]
            action = speak_action(self, caller, p)
            yield ActionContext(self, caller, action, None, effects)


class Trait:
    def __init__(self, name, kind):
        self.name = name
        self.value = kind()

    def __eq__(self, other):
        return self.value == other

    def __gt__(self, other):
        return self.value > other

    def __lt__(self, other):
        return self.value < other


class Traits:
    default = [
        "strength",
        "perception",
        "endurance",
        "charisma",
        "intelligence",
        "agility",
        "luck",
        "chatty",
        "morality",
        "tradition",
        "alignment",
        "touchy",
        "esteem",
        "karma",
        "report"
    ]

    def __init__(self):
        self.__traits = {}
        for name in Traits.default:
            self.__traits[name] = Trait(name, float)

    def __getattr__(self, item):
        try:
            return self.__traits[item]
        except KeyError:
            raise AttributeError

    @classmethod
    def random(cls):
        t = cls()
        for key, value in t.__traits.items():
            t.__traits[key].value = random.random()
        return t


class Human(GoapAgent):
    population = 0

    def __init__(self):
        super(Human, self).__init__()
        self.name = "Pathetic Human {}".format(Human.population)
        self.traits = Traits()
        self.sex = 0
        Human.population += 1

    def reset(self):
        self.sex = 0
        self.traits = Traits()
        self.goals = []
        self.abilities = []
        self.plan = []

    def model(self):
        self.model_abilities()
        self.model_goals()

    def model_abilities(self):
        """
        add abilities that are inherent to humans
        """
        if self.sex:
            self.add_ability(CreateLifeAbility())
            self.add_ability(GiveBirthAbility())

        #self.add_ability(AgeAbility())
        self.add_ability(ConverseAbility())
        self.add_ability(CopulateAbility())

    def model_goals(self):
        """
        add goals that are inherent to humans
        """

        if self.sex:
            baby_goal = SimpleGoal(has_baby=True)
            self.add_goal(baby_goal)

        if self.traits.chatty > 0:
            friendly_goal = SimpleGoal(chatter=True)
            self.add_goal(friendly_goal)

        #if self.traits.touchy > .50:
        #    copulate_goal = SimpleGoal(had_sex=True)
        #    self.add_goal(copulate_goal)

    def birth(self):
        pass


def random_human():
    h = Human()
    h.sex = bool(random.randint(0, 1))
    h.traits = Traits.random()
    h.model()
    return h