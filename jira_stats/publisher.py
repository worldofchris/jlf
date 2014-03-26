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

        if report['metric'] == 'throughput':
            data = jira.throughput(from_date, to_date, cumulative=False)

        if report['metric'] == 'cumulative-throughput':
            data = jira.throughput(from_date, to_date, cumulative=True)

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

                data.to_excel(writer, '-'.join(sheet_name))

    if isinstance(writer, pd.ExcelWriter):
        writer.save()
