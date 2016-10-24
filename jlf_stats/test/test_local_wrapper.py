from jlf_stats.local_wrapper import LocalWrapper
from jlf_stats.work import WorkItem
from dateutil.tz import tzutc

import tempfile
from datetime import datetime
import unittest
import json


class TestLocalWrapper(unittest.TestCase):

    def testWorkItemFromJson(self):
        """
        Create a work item from its JSON serialization.
        """

        work_item = [{"id": "OPSTOOLS-1",
                      "title": "Engine not working, throwing up this for no reason",
                      "type": "Defect",
                      "category": "Awesome Software",
                      "date_created": "2015-11-11T18:09:00",
                      "state": "In Progress",
                      "state_transitions": [
                          {
                              "from": "queued",
                              "timestamp": "2012-11-12T09:54:29.284000+00:00",
                              "to": "In Progress"
                          },
                          {
                              "from": "In Progress",
                              "timestamp": "2012-11-12T09:54:29.284000+00:00",
                              "to": "Pending"
                          },
                          {
                              "from": "Pending",
                              "timestamp": "2012-11-12T09:54:29.284000+00:00",
                              "to": "Customer Approval"
                          }]}]

        expected_history = [{u'from': u'queued',
                             u'to':   u'In Progress',
                             u'timestamp': datetime(2012, 11, 12, 9, 54, 29, 284000, tzinfo=tzutc())},
                            {u'from': u'In Progress',
                             u'to':   u'Pending',
                             u'timestamp': datetime(2012, 11, 12, 9, 54, 29, 284000, tzinfo=tzutc())},
                            {u'from': u'Pending',
                             u'to':   u'Customer Approval',
                             u'timestamp': datetime(2012, 11, 12, 9, 54, 29, 284000, tzinfo=tzutc())}]

        expected = [WorkItem(id=u'OPSTOOLS-1',
                             state=u'In Progress',
                             title=u'Engine not working, throwing up this for no reason',
                             type=u'Defect',
                             category=u'Awesome Software',
                             date_created=datetime(2015, 11, 11, 18, 9, 0),
                             history=expected_history)]

        local_data_file = tempfile.NamedTemporaryFile(delete=False)
        json.dump(work_item, local_data_file)
        local_data_file.close()

        local_data_config = {'source': {'type': 'local',
                                        'file': local_data_file.name}}
        our_local = LocalWrapper(local_data_config)

        self.maxDiff = None
        self.assertEqual(expected[0].__dict__, our_local.work_items()[0].__dict__)
