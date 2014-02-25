from datetime import date, datetime

"""States between which we consider an issue to be being worked on
   for the purposes of calculating cycletime"""

START_STATE = 'In Progress'
END_STATE = 'Customer Approval'
REOPENED_STATE = 'Reopened'

def cycle_time(histories,
               start_state=START_STATE,
               end_state=END_STATE,
               reopened_state=REOPENED_STATE):

    """Calculate how long it has taken an issue to get from START_STATE
       to END_STATE"""

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

    return ((end_date - start_date).days) + 1


def time_in_states(histories, from_date=None, until_date=None):
    """
    How long did an issue spend in each state in its history.

    For the first state it was in count 'from' the start of the period we
    are interested in, typically when the issue was created

    For the last state it was in count from the time the state was entered
    until the date specified in 'until' - typically today's date
    """

    time_in_states = []

    current_state = None

    if from_date is None:
        from_date = date(1970, 01, 01)

    if hasattr(from_date, 'date'):
        prev_state_change_date = from_date.date()
    else:
        prev_state_change_date = from_date

    for history in histories:
        for item in history.items:
            if item.field == 'status':

                state_change_date = datetime.strptime(history.created[:10],
                                                      '%Y-%m-%d').date()

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
