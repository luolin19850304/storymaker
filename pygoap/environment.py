"""
Since a pyGOAP agent relies on cues from the environment when planning, having
a stable and efficient virtual environment is paramount.

When coding your game or simulation, you can think of the environment as the
conduit that connects your actors on screen to their simulated thoughts.  This
environment simply provides enough basic information to the agents to work.  It
is up to you to make it useful.
"""

from pygoap.precepts import *
from itertools import chain
import logging
import queue
import collections

debug = logging.debug


class ObjectBase(object):
    """
    class for objects that agents can interact with
    """
    name = 'noname'

    def __init__(self):
        self._condition = {}

    def get_actions(self, other):
        """
        generate a list of actions that could be used with this object
        """
        return []

    def condition(self, name):
        try:
            return self._condition[name]
        except KeyError:
            return False

    def set_condition(self, name, value):
        self._condition[name] = value

    def __repr__(self):
        return "<Object: {}>".format(self.name)


class Environment(object):
    """
    Abstract class representing an Environment.
    'Real' Environment classes inherit from this
    """

    def __init__(self):
        self.time = 0
        self._agents = []
        self._entities = []
        self._positions = {}
        self._context_queue = queue.Queue()
        self._precept_queue = queue.Queue()

    @property
    def agents(self):
        return iter(self._agents)

    @property
    def entities(self):
        return chain(self._entities, self._agents)

    def get_position(self, entity):
        raise NotImplementedError

    def add(self, entity, position=None):
        """
        Add an entity to the environment
        """
        from pygoap.agent import GoapAgent

        debug("[env] adding %s", entity)

        # hackish way to force agents to re-evaluate their environment
        for a in self._agents:
            for i in [p for p in a.memory.of_class(DatumPrecept) if p.name == 'aware']:
                a.memory.remove(i)

        # add the agent
        if isinstance(entity, GoapAgent):
            self._agents.append(entity)
            entity.environment = self
            self._positions[entity] = (None, (0, 0))

            # hack to let the planner know who the memory belongs to
            entity.process(DatumPrecept(entity, 'name', entity.name))
        else:
            self._entities.append(entity)

    def update(self, dt):
        """
        ***  Time is expected to be in milliseconds   ***

        ***  All actions must have same unit of time  ***

        - Update our time
        - Let agents know time has passed
        - Update actions that may be running
        - Add new actions to the queue
        """
        # update time in the simulation
        self.time += dt

        # let all the agents know that time has passed
        self._precept_queue.put(TimePrecept(self.time))

        self.handle_precepts()

        context_put = self._context_queue.put
        for agent in self.agents:
            agent.plan_if_needed()
            for context in agent.running_contexts:
                context_put(context)

        self.handle_contexts(dt)

    def handle_precepts(self):
        """
        process all of the precepts in the queue
        """
        l = set()
        get_precept = self._precept_queue.get
        while 1:
            try:
                l.add(get_precept(False))
            except queue.Empty:
                self.broadcast_precepts(l)
                break

    def broadcast_precepts(self, precepts):
        """
        broadcast and model a list of precepts
        """
        model_precepts = self.model_precepts

        for p in precepts:
            self.broadcast_hook(p)

        for agent in self._agents:
            agent.process_list(model_precepts(precepts, agent))

    def handle_contexts(self, dt):
        """
        process all of the actions in the queue
        """
        next_queue = queue.Queue()
        touched = set()

        # deref for speed
        context_get = self._context_queue.get
        context_put = self._context_queue.put
        precept_put = self._precept_queue.put
        while 1:
            try:
                context = context_get(False)

            except queue.Empty:
                self._context_queue = next_queue
                break

            else:
                if context.action in touched:
                    continue

                touched.add(context.action)

                #print("{} doing {}".format(context.caller, context))
                for precept in context.action.step(dt):
                    precept_put(precept)

                if context.action.finished:
                    #print("{} {} finished".format(context.caller, context))
                    context.touch()
                    context.caller.next_context()
                    for _context in context.caller.running_contexts:
                        context_put(_context)

                else:
                    next_queue.put(context)

    def model_context(self, context):
        """
        Used to model how an action interacts with the environment.
        Environment can ability to silence actions if they are not able to run.
        """
        return context

    def broadcast_hook(self, p):
        if isinstance(p, SpeechPrecept):
            msg = '{:>12} {}'.format('{}:'.format(p.entity.name), p.message)
            print(msg)

    def model_precepts(self, precepts, other):
        """
        override this to model the way that precept objects move in the
        simulation.  by default, all precept objects will be distributed
        indiscriminately to all agents.
        """
        return precepts