"""
Get our historic throughput from JIRA for all projects
"""

from jira_stats.jira_wrapper import JiraWrapper

import json
from datetime import datetime, timedelta
import argparse

def main():

    parser = argparse.ArgumentParser(description='Get Throughput from JIRA')

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

    throughput_frame.to_excel('throughput.xls')

    all_frame = work.issues
    all_frame.to_excel('issues.xls')

if __name__ == "__main__":
    main()
