from datetime import date, timedelta, datetime
from dateutil import rrule

def week_start_date(year, week):
    """
    Taken from http://stackoverflow.com/a/1287862/1064619
    """

    d = date(year, 1, 1)
    delta_days = d.isoweekday() - 1
    delta_weeks = week
    if year == d.isocalendar()[0]:
        delta_weeks -= 1
    delta = timedelta(days=-delta_days, weeks=delta_weeks)
    return d + delta

def fill_date_index_blanks(index):

    index_list = index.tolist()

    start_date = datetime.strptime(index_list[0][:10], '%Y-%m-%d')

    end_date = datetime.strptime(index_list[-1][:10], '%Y-%m-%d')

    num_weeks = rrule.rrule(rrule.WEEKLY,
                            dtstart=start_date,
                            until=end_date).count()

    new_index = [week_start_date((start_date + timedelta(weeks=i)).isocalendar()[0],
                                 (start_date + timedelta(weeks=i)).isocalendar()[1]).strftime('%Y-%m-%d') for i in range(0, num_weeks)]

    return new_index
