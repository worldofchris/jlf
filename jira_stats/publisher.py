"""
Jira Stats Publisher.

Takes a report config detailing which reports to publish and
a Jira Wrapper which provides the data for the reports
"""

import os
import pandas as pd

def publish(config, jira, from_date, to_date):
    
    writer = None

    if config['format'] == 'xlsx':
        excel_basename = config['name']
        excel_filename = os.path.join(config['location'], 
                                      excel_basename + '.xlsx')
        writer = pd.ExcelWriter(excel_filename) # , engine='xlsxwriter')


    for report in config['reports']:

        data = None

        types = report['types']
        if types == 'foreach':
            types = []
            for type in config['types']:
                types.append(type)
 
        if report['metric'] == 'throughput':

            data = jira.throughput(from_date,
                                   to_date,
                                   cumulative=False,
                                   types=types)

        if report['metric'] == 'cumulative-throughput':
            data = jira.throughput(from_date, to_date, cumulative=True, types=types)

        if report['metric'] == 'demand':
            data = jira.demand(from_date, to_date, report['types'])

        if report['metric'] == 'done':
            # It seems inconsistent that 'done' does not allow you to specify a date range.
            # If it did then all the metric functions could have the same interface
            # so making this code DRYer and more succinct
            data = jira.done()

        if report['metric'] == 'cycle-time':
            data = jira.cycle_time(from_date, to_date, report['types'], report['cycles'])

        if data is not None:
            if isinstance(writer, pd.ExcelWriter):

                sheet_name = []
                if isinstance(report['types'], list):
                    sheet_name.extend(report['types'])

                try:
                    if isinstance(report['cycles'], list):
                        sheet_name.extend(report['cycles'])

                except KeyError:
                    pass

                sheet_name.append(report['metric'])

                data.to_excel(writer, worksheet_title('-'.join(sheet_name)))

    if isinstance(writer, pd.ExcelWriter):
        writer.save()


def worksheet_title(full_title):
    """
    Shorten the title if it is not going to fit on the worksheet
    """

    _MAX_LENGTH = 30

    excess = len(full_title) - _MAX_LENGTH

    if excess > 0:
        parts = full_title.split('-')
        shorten_by = excess / len(parts)

        short_title = full_title

        while len(short_title) > _MAX_LENGTH:
            longest = max(parts[:-1], key=len)
            if len(longest) > shorten_by:
                parts[parts.index(longest)] = longest[:-shorten_by]

                short_title = ''
                for part in parts[:-1]:
                    short_title += part
                    short_title += '-'

                short_title += parts[-1]
            else:
                short_title = short_title[:_MAX_LENGTH-len(parts[-1])] + parts[-1]

        return short_title

    else:
        return full_title