from datetime import date, datetime, timedelta
import pandas as pd

"""States between which we consider an issue to be being worked on
   for the purposes of calculating cycle time"""

CREATED_STATE = 'Open'
START_STATE = 'In Progress'
END_STATE = 'Customer Approval'
REOPENED_STATE = 'Reopened'


def cycle_time(history,
               start_state=START_STATE,
               after_state=None,
               end_state=END_STATE,
               exit_state=None,
               reopened_state=REOPENED_STATE,
               include_states=None,
               exclude_states=None):

    """Calculate how long it has taken an issue to get from START_STATE
       to END_STATE.  If we want to count from the date an issue was created
       we need to specify the date the issue was created and the CREATED_STATE
       if different from the default."""

    if include_states is not None:

        count = 0
        for day in history:
            if day in include_states:
                count += 1

        return count

    if exclude_states is not None:

        count = 0
        for day in history:
            if day not in exclude_states:
                count += 1

        return count

    start_date = None
    end_date = None

    for i, day in enumerate(history):

        new_start_date = None

        if after_state:

            if day == after_state:
                if i == len(history.index) - 1:
                    new_start_date = history.index[i]
                else:
                    new_start_date = history.index[i+1]

        else:

            if day == start_state:

                new_start_date = history.index[i]

            if day == start_state:

                new_start_date = history.index[i]

        if new_start_date is not None:

            if start_date is None:
                start_date = new_start_date
            else:
                if new_start_date < start_date:
                    start_date = new_start_date

        if exit_state is not None:

            if day == exit_state:
                if i == len(history.index) - 1:
                    end_date = history.index[i]
                else:
                    end_date = history.index[i+1]
        else:
            if day == end_state:

                # We ignore transitions to end_state if
                # they are from reopened.
                # This is because we sometime have to re-open
                # tickets just to fix
                # details of ownership, component, type or resolution.
                if day != reopened_state:
                    end_date = history.index[i]

    if start_date is None:
        # Round up if we only ever saw the end state.
        # This means that the start state was on the same day.
        if end_date is not None:
            return 1

    if end_date is None:
        return None

    offset = 0
    if exit_state is None:
        offset = 1

    return ((end_date - start_date).days) + offset


def extract_date(created):
    return datetime.strptime(created[:10], '%Y-%m-%d').date()


def time_in_states(histories, from_date=None, until_date=None):
    """
    How long did an issue spend in each state in its history.

    For the first state it was in count 'from' the start of the period we
    are interested in, typically when the issue was created

    For the last state it was in count from the time the state was entered
    until the date specified in 'until' - typically today's date
    """

    time_in_states = []

    current_state = 'Open'

    if from_date is None:
        from_date = date(1970, 01, 01)

    if hasattr(from_date, 'date'):
        prev_state_change_date = from_date.date()
    else:
        prev_state_change_date = from_date

    for history in histories:
        for item in history.items:
            if item.field == 'status':

                state_change_date = extract_date(history.created)

                days_in_state = state_change_date - prev_state_change_date

                if current_state is None:
                    current_state = item.fromString

                time_in_states.append({'state': current_state,
                                       'days': days_in_state.days})

                current_state = item.toString
                prev_state_change_date = state_change_date

    if until_date is not None:
        final_state_days = until_date - prev_state_change_date

        time_in_states.append({'state': current_state,
                               'days':  final_state_days.days})
    else:
        time_in_states.append({'state': current_state,
                               'days':  1})

    return time_in_states


def history_from_jira_changelog(changelog, created_date, until_date=None):

    issue_history = time_in_states(changelog.histories, from_date=created_date, until_date=until_date)

    issue_day_history = []
    history = None
    total_days = 0

    for state_days in issue_history:

        state = state_days['state']
        days = state_days['days']

        days_in_state = [state] * days

        issue_day_history += days_in_state
        total_days += days

    dates = [created_date + timedelta(days=x) for x in range(0, total_days)]

    try:
        history = pd.Series(issue_day_history, index=dates)
    except AssertionError as e:
        # TODO: turn this into a proper domain specific error and re-throw
        print e
        print dates
        print issue_day_history

    return history


def arrivals(histories, add_to=None):

    if add_to is None:
        arrivals = {}
    else:
        arrivals = add_to

    for history in histories:
        day = extract_date(history.created)
        if not day in arrivals:
            arrivals[day] = {}

        for item in history.items:
            if item.field == 'status':

                if not item.toString in arrivals[day]:
                    arrivals[day][item.toString] = 1
                else:
                    arrivals[day][item.toString] += 1

    return arrivals


def history_from_state_transitions(start_date, state_transitions, end_date):
    """
    Get a daily history of states based on state transitions
    """

    history = []

    to_state = None # This needs to be the default state

    last_date = start_date
    for state in state_transitions:

        date = state['timestamp'].date()

        num_days = (date - last_date).days
        for n in range(0, num_days):
            history.append(state['from'])

        last_date = date
        to_state = state['to']

    num_days = (end_date - last_date).days

    for n in range(0, num_days + 1):
        history.append(to_state)

    try:
        dates = [start_date + timedelta(days=x) for x in range(0, (end_date - start_date).days + 1)]

        history_df = pd.Series(history, index=dates)
    except  Exception as inst:
        print inst
        raise

    return history_df

def remove_gaps_from_state_transitions(state_transitions):
    """
    If a state transition has None as it's from replace that with the to of the previous state transition
    """

    new_state_transisions = []

    for index, transition in enumerate(state_transitions):

        new_transition = transition.copy()
        if new_transition['from'] is None:
            new_transition['from'] = state_transitions[index-1]['to']

        new_state_transisions.append(new_transition)

    return new_state_transisions
