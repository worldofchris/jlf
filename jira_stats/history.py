from datetime import date, datetime

"""States between which we consider an issue to be being worked on
   for the purposes of calculating cycletime"""

CREATED_STATE = 'Open'
START_STATE = 'In Progress'
END_STATE = 'Customer Approval'
REOPENED_STATE = 'Reopened'

def cycle_time(histories,
               start_state=START_STATE,
               end_state=END_STATE,
               exit_state=None,
               reopened_state=REOPENED_STATE,
               created_state=CREATED_STATE,
               created_date=None):

    """Calculate how long it has taken an issue to get from START_STATE
       to END_STATE.  If we want to count from the date an issue was created
       we need to specify the date the issue was created and the CREATED_STATE
       if different from the default."""

    if start_state == created_state:

        start_date = created_date
    else:
        start_date = None

    end_date = None

    for history in histories:
        for item in history.items:
            if item.field == 'status':

                new_start_date = None

                if item.toString == start_state:

                    new_start_date = datetime.strptime(history.created[:10],
                                                       '%Y-%m-%d')

                if item.fromString == start_state:

                    new_start_date = datetime.strptime(history.created[:10],
                                                       '%Y-%m-%d')

                if new_start_date is not None:

                    if start_date is None:
                        start_date = new_start_date
                    else:
                        if new_start_date < start_date:
                            start_date = new_start_date

                if exit_state is not None:

                    if item.fromString == exit_state:
                        end_date = datetime.strptime(history.created[:10],
                                                     '%Y-%m-%d')
                else:
                    if item.toString == end_state:

                        # We ignore transitions to end_state if
                        # they are from reopened.
                        # This is because we sometime have to re-open
                        # tickets just to fix
                        # details of ownership, component, type or resolution.
                        if item.fromString != reopened_state:
                            end_date = datetime.strptime(history.created[:10],
                                                         '%Y-%m-%d')

    if start_date is None or end_date is None:
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
