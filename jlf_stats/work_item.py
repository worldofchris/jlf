import json
from datetime import datetime
import pandas as pd

from jlf_stats.history import cycle_time, history_from_state_transitions

class WorkItem(object):

    def __init__(self,
                 id,
                 title,
                 state,
                 type,
                 date_created,
                 history=None,
                 state_transitions=None,
                 category=None,
                 cycles=None,
                 cycle_config=None,
                 until_date=datetime.today().date()):

        self.id = id
        self.title = title
        self.state = state
        self.type = type
        self.history = history
        self.date_created = date_created
        self.category = category
        self.cycles = cycles
        self.state_transitions = state_transitions

        if self.history is None:
            self.set_history(until_date)

        if self.cycles is None:
            self.cycles = {}
            if cycle_config is not None:

                self.set_cycles(cycle_config)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return "{0}:{1}:{2}".format(self.id, self.state, self.history)

    def set_history(self, until_date):

        self.history = history_from_state_transitions(self.date_created,
                                                      self.state_transitions,
                                                      until_date)

    def set_cycles(self, cycle_config):

        for cycle in cycle_config:
            reopened_state = None
            after_state = None
            start_state = None
            exit_state = None
            end_state = None
            include_states = None
            exclude_states = None

            if 'ignore' in cycle_config[cycle]:
                reopened_state = cycle_config[cycle]['ignore']

            if 'after' in cycle_config[cycle]:
                after_state = cycle_config[cycle]['after']

            if 'start' in cycle_config[cycle]:
                start_state = cycle_config[cycle]['start']

            if 'exit' in cycle_config[cycle]:
                exit_state = cycle_config[cycle]['exit']

            if 'include' in cycle_config[cycle]:
                include_states = cycle_config[cycle]['include']

            if 'exclude' in cycle_config[cycle]:
                exclude_states = cycle_config[cycle]['exclude']

            # if str(self.id) == "56558dda8d27a0775ab70ab0":
            #     import pdb; pdb.set_trace()

            if 'end' in cycle_config[cycle]:
                end_state = cycle_config[cycle]['end']

                self.cycles[cycle] = cycle_time(self.history,
                                                start_state=start_state,
                                                after_state=after_state,
                                                include_states=include_states,
                                                exclude_states=exclude_states,
                                                end_state=end_state,
                                                reopened_state=reopened_state)

            else:

                self.cycles[cycle] = cycle_time(self.history,
                                                start_state=start_state,
                                                after_state=after_state,
                                                include_states=include_states,
                                                exclude_states=exclude_states,
                                                exit_state=exit_state,
                                                reopened_state=reopened_state)

    def detail(self):

        detail = {'id': self.id,
                  'title': self.title,
                  'state': self.state,
                  'type': self.type,
                  'date_created': self.date_created} # .replace(tzinfo=None)}  # HACK HACK HACK - for excel's benefit

        if self.cycles is not None:
            for cycle in self.cycles:
                detail[cycle] = self.cycles[cycle]

        return detail
