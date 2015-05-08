from work import WorkItem
import re


class FogbugzWrapper(object):
    """
    Wrapper around a Fogbugz Instance
    """

    def issue_from_xml(self, case):

        work_item = WorkItem(id=case.ixbug.text,
                             state=str(case.sstatus.text),
                             history=[])

        return work_item

    def time_in_state(self, start_date, end_date, changes):

        days = (end_date - start_date).days

        print changes
        m = re.match("^[^\']+\'([A-Za-z _]+)\'", changes)
        if m is not None:
            state = m.group(1)
            return {'days': days, 'state': state}

        else:

            return None
