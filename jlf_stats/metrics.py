"""
Metrics
"""
from jlf_stats.fogbugz_wrapper import FogbugzWrapper
from jlf_stats.jira_wrapper import JiraWrapper

import pandas as pd
import numpy as np
import math

import exceptions
from bucket import bucket_labels
from index import fill_date_index_blanks, week_start_date
from history import arrivals, history_from_state_transitions


class Metrics(object):

    def __init__(self, config):

        self.source = None
        self.work_items = None
        self.states = []

        if config['source']['type'] == 'fogbugz':
            self.source = FogbugzWrapper(config)
        elif config['source']['type'] == 'jira':
            self.source = JiraWrapper(config)

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

    def work_item(self, id):
        """
        Get an individual work item.

        This is a case in FogBugz or an Issue in Jira.
        """
        if self.work_items is None:
            self.work_items = self.source.work_items()

        matches = [work_item for work_item in self.work_items if work_item.id == id]
        return matches[0]

    def details(self, fields=None):

        if self.work_items is None:
            self.work_items = self.source.work_items()

        details = []

        for work_item in self.work_items:
            details.append(work_item.detail())

        df = pd.DataFrame(details)

        if fields is None:
            return df
        else:
            return df.filter(fields)

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
                    history[work_item.id] = history_from_state_transitions(work_item.date_created.date(), work_item.history, until_date)
            else:
                for type_grouping in types:
                    if work_item.type in self.types[type_grouping]: 
                        if isinstance(self.source, JiraWrapper):
                            history[work_item.id] = work_item.history
                        else:
                            history[work_item.id] = history_from_state_transitions(work_item.date_created.date(), work_item.history, until_date)

        if history is not None:
            df = pd.DataFrame(history)
            return df

        return None

    def throughput(self,
                   from_date,
                   to_date,
                   cumulative=True,
                   category=None,
                   types=None):
        """
        Return throughput for all work_items in a state where they are considered
        to count towards throughput.

        Might want to add some additional conditions other than state but state
        allows us the most options as to where to place the 'finishing line'
        """

        work_item_history = self.history(from_date, to_date)

        work_item_rows = []

        for work_item_key in work_item_history:

            work_item = self.work_item(work_item_key)

            if category is not None:

                if category != work_item.category:
                    continue

            swimlane = work_item.category

            # Are we grouping by work type?

            if types is not None:
                for type_grouping in types:
                    if work_item.type in self.types[type_grouping]:
                        swimlane = swimlane + '-' + type_grouping
                    else:
                        continue
                        # print "Not counting " + f.work_itemtype.name
                if swimlane == work_item.category:
                    continue

            for day, state in work_item_history[work_item_key].iteritems():
                if day.weekday() == self.throughput_dow:

                    if state in self.counts_towards_throughput:

                        work_item_row = {'swimlane': swimlane,
                                         'id':       work_item_key,
                                         'week':     day,
                                         'count':    1}
                        work_item_rows.append(work_item_row)

        df = pd.DataFrame(work_item_rows)

        if len(df.index) > 0:

            table = pd.tools.pivot.pivot_table(df, rows=['week'], cols=['swimlane'], values='count', aggfunc=np.count_nonzero)

            if cumulative:
                return table

            else:

                def de_cumulative(x):
                    for i in range(x.size-1, 0, -1):
                        x[i] = x[i] - x[i-1]
                    return x

                table = table.apply(de_cumulative)

                return table

        else:

            return None

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

                    raise exceptions.MissingState(state, "Missing state:{0}".format(state))

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
                                                     detail['date_created'].isocalendar()[1]).strftime('%Y-%m-%d')

            include = True

            swimlane = work_item.category

            if types is not None and self.types is not None:
                include = False
                for type_grouping in types:
                    if work_item.type in self.types[type_grouping]:
                        swimlane = swimlane + '-' + type_grouping
                        include = True

            detail['swimlane'] = swimlane

            if include:
                details.append(detail)

        df = pd.DataFrame(details)

        table = pd.tools.pivot.pivot_table(df, rows=['week_created'], cols=['swimlane'], values='count', aggfunc=np.count_nonzero)

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
                print e

        df = pd.DataFrame.from_dict(arrivals_count, orient='index')
        df.index = pd.to_datetime(df.index)
        wf = df.resample('W-MON', how='sum')

        return wf
