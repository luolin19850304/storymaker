__author__ = 'Leif'

from pygoap.agent import GoapAgent
from pygoap.actions import Action
from pygoap.goals import *
from pygoap.precepts import *
from lib.english import make_english
from lib.traits import *
from collections import defaultdict
import random


# get all known entities at this point
# do this by checking for "name" DatumPrecepts
def get_known_agents(agent):
    for p in agent.memory:
        try:
            if p.entity is not agent:
                yield p.entity
        except AttributeError:
            continue


def opposite_sex(agent, others):
    for other in others:
        if not agent.sex == other.sex:
            yield other


class AgeAbility(Action):
    requires = [DatumPrecept]

    def get_actions(self, parent, memory=None):
        effects = []
        prereqs = []
        action = AgeAction()
        context = ActionContext(parent, action, prereqs, effects)
        yield context


class AgeAction(Action):
    """
    simulate human aging
    """
    def __init__(self, *arg, **kwarg):
        super(AgeAction, self).__init__(*arg, **kwarg)
        self.age = 0

    def update(self, dt):
        self.age += dt
        yield None


class GiveBirthAbility(Action):
    """
    simulate birth
    """
    requires = [DatumPrecept]

    def get_actions(self, parent, memory=None):
        effects = [PreceptGoal(DatumPrecept(parent, "has baby", True)),
                   PreceptGoal(DatumPrecept(parent, "ready to birth", False))]
        prereqs = [PreceptGoal(DatumPrecept(parent, "ready to birth", True))]
        yield GiveBirthAction(parent, prereqs, effects)


class GiveBirthAction(Action):
    def update(self, dt):
        yield SpeechPrecept(self.parent, "my baby is here!")
        yield ActionPrecept(self.parent, "birth", None)


class GestationAbility(Action):
    """
    simulate child gestation
    """
    requires = [DatumPrecept]

    def get_actions(self, parent, memory=None):
        effects = [PreceptGoal(DatumPrecept(parent, "ready to birth", True))]
        prereqs = [PreceptGoal(DatumPrecept(parent, "had sex", True))]
        yield GestationAction(parent, prereqs, effects)


class GestationAction(Action):
    default_duration = 5


class CopulateAbility(Action):
    """
    simulate sex
    """
    requires = [DatumPrecept]

    def get_actions(self, parent, memory=None):
        for other in opposite_sex(parent, get_known_agents(parent)):
            if not other.sex == parent.sex:
                effects = [PreceptGoal(ActionPrecept(parent, "sex", other)),
                           PreceptGoal(DatumPrecept(parent, "had sex", True))]
                yield CopulateAction(parent, None, effects, other=other)


class CopulateAction(Action):
    def __init__(self, *args, **kwargs):
        super(CopulateAction, self).__init__(*args, **kwargs)
        self.other = kwargs.get('other', None)
        assert(self.other is not None)

    def update(self, dt):
        yield ActionPrecept(self.parent, "sex", self.other)


class SpeakAbility(Action):
    """
    examine parent's memory and create some things to say
    """
    def __init__(self, *args, **kwargs):
        super(SpeakAbility, self).__init__(*args, **kwargs)
        self.perception_map = defaultdict(list)

    def get_actions(self, parent, memory=None):
        if memory is not None:
            if len(memory) == 0:
                raise StopIteration
            p = random.choice(list(memory))
            if p not in self.perception_map[parent]:
                if p is None:
                    print(memory, p)
                self.perception_map[parent].append(p)  # assume when speaking all actors will receive the message
                effects = [PreceptGoal(DatumPrecept(parent, "chatter", True))]
                yield SpeakAction(parent, None, effects, precept=p)


class SpeakAction(Action):
    def __init__(self, *args, **kwargs):
        super(SpeakAction, self).__init__(*args, **kwargs)
        self.p = kwargs.get('precept', None)
        assert(self.p is not None)

    def update(self, dt):
        msg = SpeechPrecept(self.parent, make_english(self.parent, self.p))
        yield msg     # return a speech precept
        yield self.p  # return a the original precept (simulates passing of information through speech)


class TeleSend(Action):
    """
    Telepathic Communication (a joke!)
    """
    def __init__(self, p, *arg, **kwarg):
        super(TeleSend, self).__init__(*arg, **kwarg)
        self.p = p

    def update(self, dt):
        yield self.p


class Preferences:
    """
    Preferences are a map that determines the effects actions have on behaviour
    """
    pass


# filters should modify the agent's traits or mood
def copulate_filter(agent, p):
    try:
        assert(isinstance(p, ActionPrecept))
        assert(p.entity is agent)
    except AssertionError:
        return [p]

    r = [p]

    value = 0

    to_remove = []
    for mp in agent.memory.of_class(MoodPrecept):
        if mp.entity is agent and mp.name == 'content':
            value += mp.value
            to_remove.append(mp)

    for mp in to_remove:
        agent.memory.remove(mp)

    if p.action == "sex":
        value += .01
        p = MoodPrecept(agent, 'content', value)
        r.append(p)

    return r


class Human(GoapAgent):
    mood_names = (
        "content",     # low values cause agent to seek another activity
        "hunger",      # negative requires food
        "rested",      # negative requires sleep
        "stressed",    # high values affect behaviour
    )

    population = 0

    def __init__(self, **kwarg):
        super(Human, self).__init__()
        self.traits = Traits()
        self.sex = kwarg.get("sex", 0)

        name = kwarg.get("name", None)
        if not name:
            name = "Pathetic Human {} ({})".format(Human.population, self.sex)
        self.name = name

        self.reset_moods()

        Human.population += 1

    def reset_moods(self):
        for name in Human.mood_names:
            p = MoodPrecept(self, name, float())
            self.process(p)

    def reset(self):
        super(Human, self).reset()
        self.traits = Traits()
        self.sex = 0
        self.reset_moods()
        self.model()

    def model(self):
        self.model_abilities()
        self.model_goals()

    def model_abilities(self):
        """
        add abilities that are inherent to humans
        """
        if self.sex:
            self.abilities.add(GestationAbility(self))
            self.abilities.add(GiveBirthAbility(self))

        #self.abilities.add(AgeAbility(self))
        self.abilities.add(SpeakAbility(self))
        self.abilities.add(CopulateAbility(self))

        #self.filters.append(copulate_filter)

    def model_goals(self):
        """
        add goals that are inherent to humans
        """
        if self.sex:
            baby_goal = PreceptGoal(DatumPrecept(self, "has baby", True), name="baby")
            self.goals.add(baby_goal)

        if self.traits.touchy > 0:
            copulate_goal = PreceptGoal(DatumPrecept(self, "had sex", True), name="sex")
            self.goals.add(copulate_goal)

        if self.traits.chatty > 0:
            chatter_goal = PreceptGoal(DatumPrecept(self, "chatter", True), name="chatty")
            self.goals.add(chatter_goal)

    def birth(self):
        pass


def random_human():
    h = Human()
    h.sex = random.randint(0, 1)
    h.traits = Traits.random()
    h.model()
    return h