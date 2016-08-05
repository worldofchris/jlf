from jlf_stats.local_wrapper import LocalWrapper
from jlf_stats.work import WorkItem

class TestLocalWrapper:

    def testWorkItemFromJson(self):
        """
        Create a work item from its JSON serialization.
        """

        json_work_item = """
        {
            "id": "OPSTOOLS-1", 
            "title": null, 
            "type": "Defect"
            "category": "Ops Tools", 
            "date_created": "2012-01-01T00:00:00" 
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
                    "to": "pending"
                }, 
                {
                    "from": "pending", 
                    "timestamp": "2012-11-12T09:54:29.284000+00:00", 
                    "to": "Customer Approval"
                }
            ]
        }        
        """

        expected = 

        # Expect history to be...
