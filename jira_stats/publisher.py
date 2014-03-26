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
        if report['metric'] == 'throughput':
            data = jira.throughput(from_date, to_date)

        if data is not None:
            if isinstance(writer, pd.ExcelWriter):
                sheet_name = report['metric']
                data.to_excel(writer, sheet_name)

    if isinstance(writer, pd.ExcelWriter):
        writer.save()
