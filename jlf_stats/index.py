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

    if isinstance(index_list[0], basestring):
        start_date = datetime.strptime(index_list[0][:10], '%Y-%m-%d')
        end_date = datetime.strptime(index_list[-1][:10], '%Y-%m-%d')
    else:
        start_date = index_list[0]
        end_date = index_list[-1]

    num_weeks = rrule.rrule(rrule.WEEKLY,
                            dtstart=start_date,
                            until=end_date).count()

    new_index = [week_start_date((start_date + timedelta(weeks=i)).isocalendar()[0],
                                 (start_date + timedelta(weeks=i)).isocalendar()[1]) for i in range(0, num_weeks)]

    if isinstance(start_date, basestring):
        for item in new_index:
            item = item.strftime('%Y-%m-%d')

    return new_index
