"""
Wrapper around the JIRA API to allow us to categorize issues by
project/component/label etc and report on:

- Work in Progress
- Work completed - including Cycle Time
- Work history
- Cumulative Flow
- Throughput
- Rate at which types of work are created

Also abstracts away from batch searching and other implementation
details we don't want to present to the user.
"""

import jira.client
import sys

from datetime import date, datetime

from index import week_start_date
from history import time_in_states, cycle_time, history_from_jira_changelog
from exceptions import MissingConfigItem
from work import WorkItem
import dateutil.parser


class JiraWrapper(object):
    """
    Wrapper around our JIRA instance
    """

    def __init__(self, config):

        authentication = None

        try:
            source = config['source']
        except KeyError as e:
            raise MissingConfigItem(e, "Missing Config Item:{0}".format(e))

        self.jira = None

        authentication = source['authentication']

        if 'username' in authentication and 'password' in authentication:
            self.jira = jira.client.JIRA({'server': source['server']},
                                         basic_auth=(authentication['username'],
                                                     authentication['password']))
        elif ('access_token' in authentication and
              'access_token_secret' in authentication and
              'consumer_key' in authentication and
              'key_cert'):

            try:
                with open(authentication['key_cert'], 'r') as key_cert_file:
                    key_cert_data = key_cert_file.read()
            except IOError:
                raise MissingConfigItem('key_cert', "key_cert not found:{0}". format(authentication['key_cert']))

            self.jira = jira.client.JIRA({'server': source['server']},
                                         oauth={'access_token': authentication['access_token'],
                                                'access_token_secret': authentication['access_token_secret'],
                                                'consumer_key': authentication['consumer_key'],
                                                'key_cert': key_cert_data})
        else:
            raise MissingConfigItem('authentication', "Authentication misconfigured")

        self.categories = None
        self.cycles = None
        self.types = None
        self.until_date = None

        if 'until_date' in config:
            self.until_date = datetime.strptime(config['until_date'], '%Y-%m-%d').date()

        try:
            self.categories = config['categories']
            self.cycles = config['cycles']
        except KeyError as e:
            raise MissingConfigItem(e.message, "Missing Config Item:{0}".format(e.message))

        self.all_issues = None

    def work_items(self):
        """
        All issues
        """
        if self.all_issues is None:
            self.all_issues = self._issues_from_jira()

        return self.all_issues


    def totals(self):
        """
        What are current totals of work in our various states
        """

        # We can get this by doing a count of the last day of the CFD

        cfd = self.cfd()

        return None

###############################################################################
# Internal methods
###############################################################################

    def _issues_from_jira(self, filter=None):
        """
        Get the actual issues from Jira itself via the Jira REST API
        """

        batch_size = 100
        work_items = []

        for category in self.categories:

            n = 0
            while 1:

                jql = self.categories[category]
                if filter is not None:
                    jql = jql + filter

                issue_batch = self.jira.search_issues(jql,
                                                      startAt=n,
                                                      maxResults=batch_size,
                                                      expand='changelog')

                if issue_batch is None:
                    #TODO: Fix mocking so we can get rid of this.
                    # 'expand' seems to have some magic meaning in Mockito...
                    issue_batch = self.jira.search_issues(jql,
                                                          startAt=n,
                                                          maxResults=batch_size)

                for issue in issue_batch:

                    issue.category = category
                    issue_history = None
                    cycles = {}

                    date_created = datetime.strptime(issue.fields.created[:10], '%Y-%m-%d')

                    if issue.changelog is not None:

                        issue_history = history_from_jira_changelog(issue.changelog, date_created, self.until_date)

                        try:

                            for cycle in self.cycles:
                                reopened_state = None
                                after_state = None
                                start_state = None
                                exit_state = None
                                end_state = None
                                include_states = None
                                exclude_states = None

                                if 'ignore' in self.cycles[cycle]:
                                    reopened_state = self.cycles[cycle]['ignore']

                                if 'after' in self.cycles[cycle]:
                                    after_state = self.cycles[cycle]['after']

                                if 'start' in self.cycles[cycle]:
                                    start_state = self.cycles[cycle]['start']

                                if 'exit' in self.cycles[cycle]:
                                    exit_state = self.cycles[cycle]['exit']

                                if 'include' in self.cycles[cycle]:
                                    include_states = self.cycles[cycle]['include']

                                if 'exclude' in self.cycles[cycle]:
                                    exclude_states = self.cycles[cycle]['exclude']

                                if 'end' in self.cycles[cycle]:
                                    end_state = self.cycles[cycle]['end']

                                    cycles[cycle] = cycle_time(issue_history,
                                                               start_state=start_state,
                                                               after_state=after_state,
                                                               include_states=include_states,
                                                               exclude_states=exclude_states,
                                                               end_state=end_state,
                                                               reopened_state=reopened_state)

                                else:

                                    cycles[cycle] = cycle_time(issue_history,
                                                               start_state=start_state,
                                                               after_state=after_state,
                                                               include_states=include_states,
                                                               exclude_states=exclude_states,
                                                               exit_state=exit_state,
                                                               reopened_state=reopened_state)

                        except AttributeError:

                            pass

                    state_transitions = []
                    if issue.changelog is not None:
                        for change in issue.changelog.histories:
                            st = self.state_transition(change)
                            state_transitions.append(st)

                    work_items.append(WorkItem(id=issue.key,
                                               title=issue.fields.summary,
                                               state=issue.fields.status.name,
                                               type=issue.fields.issuetype.name,
                                               history=issue_history,
                                               state_transitions=state_transitions,
                                               date_created=date_created,
                                               cycles=cycles,
                                               category=category))

                if len(issue_batch) < batch_size:
                    break
                n += batch_size
                sys.stdout.write('.')
                sys.stdout.flush()

        return work_items

    def state_transition(self, history):

        timestamp = dateutil.parser.parse(history.created)

        for item in history.items:
            if item.field == 'status':
                from_state = item.fromString
                to_state = item.toString

                return {'from': from_state,
                        'to': to_state,
                        'timestamp': timestamp}

        return None

    # This is on its way out

    def _issues_as_rows(self, issues, types=None):

        """
        Get issues into a state where we can stick them into a Pandas dataframe
        """

        # TODO: Decide if this should be a class / helper method?
        # TODO: See if has any overlap with throughput function

        issue_rows = []

        for issue in issues:
            f = issue.fields

            resolution_date_str = f.resolutiondate

            if resolution_date_str is not None:
                resolution_date = datetime.strptime(resolution_date_str[:10],
                                                    '%Y-%m-%d')

                week = week_start_date(resolution_date.isocalendar()[0],
                                       resolution_date.isocalendar()[1]).strftime('%Y-%m-%d')

            else:

                week = None

            date_created = datetime.strptime(f.created[:10], '%Y-%m-%d')
            week_created = week_start_date(date_created.isocalendar()[0],
                                           date_created.isocalendar()[1]).strftime('%Y-%m-%d')

            if issue.changelog is not None:
                tis = time_in_states(issue.changelog.histories,
                                     datetime.strptime(f.created[:10],
                                                       '%Y-%m-%d'),
                                     date.today())

                since = tis[-1]['days']

            else:

                since = None

            include = True

            # TODO: This looks like a bit of a hack.
            # Can we do without iterating over loop, seeing as we
            # only ever want one swimlane/category combination?

            swimlane = issue.category

            if types is not None and self.types is not None:
                include = False
                for type_grouping in types:
                    if f.issuetype.name in self.types[type_grouping]:
                        swimlane = swimlane + '-' + type_grouping
                        include = True

            if include:

                try:
                    story_points = f.customfield_10002
                except AttributeError:
                    story_points = None

                try:
                    epic_link = f.customfield_10200
                except AttributeError:
                    epic_link = None

                # TODO: Fields need to come out of config too.

                issue_row = {'swimlane':     swimlane,
                             'type':         f.issuetype.name,
                             'id':           issue.key,
                             'name':         f.summary,
                             'status':       f.status.name,
                             'project':      f.project.name,
                             'components':   None,
                             'week':         week,
                             'since':        since,
                             'created':      f.created,
                             'week_created': week_created,
                             'story_points': story_points,
                             'epic_link':    epic_link,
                             'count':        1}

                for cycle in self.cycles:
                    try:
                        issue_row[cycle] = getattr(issue, cycle)
                    except AttributeError:
                        pass

                components = []

                for component in f.components:
                    components.append(component.name)

                issue_row['components'] = ",".join(components)

                issue_rows.append(issue_row)

        return issue_rows
