#!/usr/bin/env python
"""
Get forward looking metrics from JIRA
"""

from jira_stats.jira_wrapper import JiraWrapper

import json
from datetime import datetime, timedelta
import argparse

def main():

    parser = argparse.ArgumentParser(description='Get forward looking metrics from JIRA')

    parser.add_argument('-n', action="store", dest="num_weeks", type=int, default=6)
    parser.add_argument('-c', action="store", dest="config_filename", default='config.json')
    parser.add_argument('-s', action="store", dest="swimlane_category", default=None)

    args = parser.parse_args()

    config_file = open(args.config_filename)
    config = json.load(config_file)

    our_jira = JiraWrapper(config=config)

    work = our_jira.issues()

    end_date = datetime.now()
    start_date = end_date - timedelta(weeks=args.num_weeks)

    throughput_frame = work.throughput(cumulative=True,
                                   from_date=start_date.date(),
                                   to_date=end_date.date(),
                                   category=args.swimlane_category)

    if throughput_frame is not None:
        throughput_frame.to_excel('throughput.xls')

    done_frame = work.done

    if done_frame is not None:
        done_frame.to_excel('done.xls')

    ongoing_frame = work.ongoing

    if ongoing_frame is not None:
        ongoing_frame.to_excel('ongoing.xls')

if __name__ == "__main__":
    main()
