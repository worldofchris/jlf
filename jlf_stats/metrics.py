"""
Metrics
"""
from jlf_stats.fogbugz_wrapper import FogbugzWrapper
from jlf_stats.jira_wrapper import JiraWrapper
from jlf_stats.trello_wrapper import TrelloWrapper
from jlf_stats.local_wrapper import LocalWrapper

import pandas as pd
import numpy as np
import math

import jlf_stats.exceptions
from jlf_stats.bucket import bucket_labels
from jlf_stats.index import fill_date_index_blanks, week_start_date
from jlf_stats.history import arrivals, history_from_state_transitions

import re
import os
import json
import math
from datetime import datetime, timedelta, date

class Metrics(object):

    def __init__(self, config):

        self.source = None
        self.work_items = None
        self.states = []
        self.config = config

        if config['source']['type'] == 'fogbugz':
            self.source = FogbugzWrapper(self.config)
        elif config['source']['type'] == 'jira':

            m = re.match("^ENV\(([^\']+)\)", self.config['source']['authentication']['password'])
            if m is not None:
                self.config['source']['authentication']['password'] = os.environ.get(m.group(1), 'undefined')

            self.source = JiraWrapper(self.config)
        elif config['source']['type'] == 'trello':
            self.source = TrelloWrapper(self.config)

        elif config['source']['type'] == 'local':
            self.source = LocalWrapper(self.config)

        if 'throughput_dow' in config:
            self.throughput_dow = config['throughput_dow']
        else:
            self.throughput_dow = 4

        try:
            self.types = config['types']
            self.counts_towards_throughput = config['counts_towards_throughput']
        except KeyError as e:
            raise exceptions.MissingConfigItem(e.message, "Missing Config Item:{0}".format(e.message))

        # Optional

        try:
            self.states = config['states']
            self.states.append(None)
        except KeyError:
            pass

        # Normalise Types so they match with Trello types
        def normalise(item):
            return item.strip().lower()

        for type_grouping in self.types:
            self.types[type_grouping] = map(normalise, self.types[type_grouping])

    def work_item(self, id):
        """
        Get an individual work item.

        This is a case in FogBugz or an Issue in Jira.
        """
        if self.work_items is None:
            self.work_items = self.source.work_items()

        try:
            matches = [work_item for work_item in self.work_items if work_item.id == id]
            return matches[0]
        except(IndexError):
            return None

    def details(self, fields=None):

        if self.work_items is None:
            self.work_items = self.source.work_items()

        details = []

        for work_item in self.work_items:
            detail = work_item.detail()
            if detail['type'] is not None:
                detail['type_grouping'] = self.type_grouping(detail['type'])
            details.append(detail)

            if work_item.state in self.counts_towards_throughput:
                detail['counts_towards_throughput'] = True
            else:
                detail['counts_towards_throughput'] = False

        df = pd.DataFrame(details)

        if fields is None:
            return df
        else:
            return df.filter(fields)

    def type_grouping(self, work_item_type):

        for type_grouping in self.types:
            if work_item_type.lower().strip() in self.types[type_grouping]:
                return type_grouping
                

    def history(self, from_date=None, until_date=None, types=None):

        if self.work_items is None:
            self.work_items = self.source.work_items()

        history = {}

        for work_item in self.work_items:

            if types is None:
                # HACK HACK HACK
                # Also need some consistency around thing_date and date_thing
                if isinstance(self.source, JiraWrapper):
                    history[work_item.id] = work_item.history
                else:
                    history[work_item.id] = history_from_state_transitions(work_item.date_created, work_item.state_transitions, until_date)
            else:
                for type_grouping in types:
                    if work_item.type in self.types[type_grouping]:
                        if isinstance(self.source, JiraWrapper):
                            history[work_item.id] = work_item.history # TODO: This will need to be changed once we've got Trello working
                        else:
                            history[work_item.id] = history_from_state_transitions(work_item.date_created, work_item.state_transitions, until_date)

        if history is not None:
            df = pd.DataFrame(history)
            return df

        return None

    def throughput(self,
                   from_date,
                   to_date,
                   cumulative=True,
                   types=None):
        """
        Return throughput for all work_items in a state where they
        count towards throughput.
        """

        throughput_by_week = []

        if self.work_items is None:

            self.work_items = self.source.work_items()

        for work_item in self.work_items:

            if work_item.state in self.counts_towards_throughput:
                # Need to add a test for work items that are not in a throughput state

                # TODO: Reinstate Category

                swimlane = work_item.category

                if types is not None:
                    for type_grouping in types:
                        for work_type in self.types[type_grouping]:
                            if work_item.type is not None:
                                if work_item.type.lower().strip() == work_type.lower().strip():
                                    swimlane = swimlane + '-' + type_grouping

                    if swimlane == work_item.category:
                        # Item was not in one of the types we are measuring
                        continue


                # Work backwards through the item history...
                try:
                    for transition in reversed(work_item.state_transitions):
                        state = transition['from']
                        if not isinstance(state, basestring):
                            state = 'unknown' # Need to figure out why we're getting NaNs from JIRA here.

                        # ...and find the last transition from a state that doesn't count towards throughput
                        if state not in self.counts_towards_throughput:

                            # Figure out which week we're in
                            transition_date = transition['timestamp'].date()

                            work_item_row = {'swimlane': swimlane,
                                             'id':       work_item.id,
                                             'week':     transition_date - timedelta(days=transition_date.weekday()),
                                             'count':    1}
                            throughput_by_week.append(work_item_row)
                            break
                except AttributeError:
                    pass
        df = pd.DataFrame(throughput_by_week)

        if len(df.index) > 0:
            table = pd.tools.pivot.pivot_table(df, rows=['week'], cols=['swimlane'], values='count', aggfunc=np.count_nonzero)
            if not cumulative:
                return table
            else:
                reindexed = table.reindex(index=fill_date_index_blanks(table.index), fill_value=np.int64(0))
                reindexed.index.name = "week"
                return reindexed.fillna(0).cumsum()

    def cfd(self, from_date=None, until_date=None, types=None):
        """
        Cumulative Flow Diagram
        """

        cfd = self.history(from_date, until_date, types)

        days = {}

        for day in cfd.index:
            tickets = []
            for ticket in cfd.ix[day]:
                tickets.append(ticket)

            def state_order(state):

                try:
                    return self.states.index(state)
                except ValueError:
                    if type(state) == float:
                        if math.isnan(state):
                            return -1
                    if type(state) == np.float64:
                        if math.isnan(state):
                            return -1

                    print "Missing state:{0}".format(state)

            days[day] = sorted(tickets, key=state_order)

        return pd.DataFrame(days)

    def cycle_time_histogram(self,
                             cycle,
                             types=None,
                             buckets=None):
        """
        Time taken for work to complete one or more 'cycles' - i.e. transitions from a start state to an end state
        """

        if self.work_items is None:
            self.work_items = self.source.work_items()

        cycle_time_data = {}

        for work_item in self.work_items:

            if types is not None:

                include = False

                for type_grouping in types:

                    if work_item.type in self.types[type_grouping]:
                        include = True
                        key = "{0}-{1}".format(type_grouping, cycle)
                        break

                if not include:
                    continue

            else:
                key = cycle

            try:
                if work_item.cycles[cycle] is not None:
                    if key not in cycle_time_data:
                        cycle_time_data[key] = [work_item.cycles[cycle]]
                    else:
                        cycle_time_data[key].append(work_item.cycles[cycle])
            except KeyError:
                continue
            except TypeError:
                continue

        histogram = None

        for cycle in cycle_time_data:
            if buckets is not None:

                try:
                    li = buckets.index('max')
                    buckets[li] = max(cycle_time_data[cycle])

                except ValueError:
                    pass

                labels = bucket_labels(buckets)
                count, division = np.histogram(cycle_time_data[cycle], bins=buckets)
            else:

                count, division = np.histogram(cycle_time_data[cycle])
                labels = bucket_labels(division)

            cycle_histogram = pd.DataFrame(count, index=labels, columns=[cycle])
            cycle_histogram.index.name = 'bucket'

            if histogram is None:
                histogram = cycle_histogram.copy(deep=True)
            else:
                old_histogram = histogram.copy(deep=True)
                histogram = old_histogram.join(cycle_histogram, how='outer')

        return histogram

    def demand(self,
               from_date,
               to_date,
               types=None):
        """
        Return the number of issues created each week - i.e. the demand on the system
        """

        if self.work_items is None:
            self.work_items = self.source.work_items()

        details = []

        for work_item in self.work_items:
            detail = work_item.detail()
            detail['count'] = 1  # Need to figure out where to put this

            # resolution_date_str = f.resolutiondate

            # if resolution_date_str is not None:
            #     resolution_date = datetime.strptime(resolution_date_str[:10],
            #                                         '%Y-%m-%d')

            #     week = week_start_date(resolution_date.isocalendar()[0],
            #                            resolution_date.isocalendar()[1]).strftime('%Y-%m-%d')

            # else:

            #     week = None

            detail['week_created'] = week_start_date(detail['date_created'].isocalendar()[0],
                                                     detail['date_created'].isocalendar()[1])

            include = True

            swimlane = work_item.category

            if types is not None and self.types is not None:
                include = False
                for type_grouping in types:
                    if work_item.type is not None:
                        if work_item.type.strip().lower() in self.types[type_grouping]:
                            swimlane = swimlane + '-' + type_grouping
                            include = True

            detail['swimlane'] = swimlane

            if include:
                details.append(detail)

        df = pd.DataFrame(details)

        table = pd.tools.pivot.pivot_table(df, rows=['week_created'], cols=['swimlane'], values='count', aggfunc=np.count_nonzero).fillna(0)

        reindexed = table.reindex(index=fill_date_index_blanks(table.index), fill_value=np.int64(0))
        reindexed.index.name = "week"
        return reindexed

    def arrival_rate(self,
                     from_date,
                     to_date):
        """
        So that we can get an idea of the flow of work that has not been completed and so does not have a resolution date
        and so does not count towards throughput, what is the rate at which that work arrived at states further up the
        value chain?
        """

        if self.work_items is None:
            self.work_items = self.source.work_items()

        arrivals_count = {}

        for work_item in self.work_items:
            try:
                arrivals_count = arrivals(work_item.history, arrivals_count)
            except AttributeError as e:
                # TODO: Rethrow as domain specific error
                print e

        df = pd.DataFrame.from_dict(arrivals_count, orient='index')
        df.index = pd.to_datetime(df.index)
        wf = df.resample('W-MON', how='sum')

        return wf


    def save_work_items(self, filename=None):

        def json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""

            if isinstance(obj, date):
                serial = obj.isoformat()
                return serial
            raise TypeError (str(type(obj)) + " Type not serializable")

        if filename is None:
            if 'name' in self.config:
                filename = self.config['name'] + '.json'
            else:
                filename = 'local.json'

        if self.work_items is None:
            self.work_items = self.source.work_items()

        output = []

        for item in self.work_items:
            work_item = item.__dict__.copy()
            work_item.pop('history', None)
            output.append(work_item)

        with open(filename, 'w') as outfile:
            json.dump(output, outfile, indent=4, sort_keys=True, default=json_serial)
