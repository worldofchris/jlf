from work import WorkItem


class FogbugzWrapper(object):
    """
    Wrapper around a Fogbugz Instance
    """

    def issue_from_xml(self, case):

        work_item = WorkItem(id=case.ixbug.text,
                             state=str(case.sstatus.text),
                             history=[])

        return work_item
