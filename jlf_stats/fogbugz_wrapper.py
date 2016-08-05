"""
Wrapper around the FogBugz API to get data out and into a
common format for reporting on.
"""

from work import WorkItem
import re
import dateutil.parser
import fogbugz

# Event codes from http://help.fogcreek.com/8202/xml-api#Event_Codes
evtResolved = 14
evtEdited = 2
evtOpened = 1


class FogbugzWrapper(object):
    """
    Wrapper around a Fogbugz Instance
    """

    def __init__(self, config=None):

        self.fb = None
        self.categories = None
        self.responses = []
        self._work_items = []

        if config:
            self.fb = fogbugz.FogBugz(config['source']['url'],
                                      config['source']['token'])
            self.categories = config['categories']


    def work_items(self):

        self.responses = []
        for cat in self.categories:
            query = self.categories[cat]
            self.responses.append(self.fb.search(q=query,
                                                 cols="ixBug,dtOpened,dtClosed,sTitle,sStatus,sCategory,minievents"))

        self._work_items = []


        for response in self.responses:

            if response.cases is not None:
                for case in response.cases.findAll('case'):
                    work_item = self.work_item_from_xml(case)
                    self._work_items.append(work_item)

        return self._work_items

    def work_item_from_xml(self, case):
        """
        Extract a work_item from the xml returned by the FogBugz API
        """

        state_history = []
        date_created = dateutil.parser.parse(case.dtopened.text)

        # # store the closed date!
        # closed_date = None
        # if case.dtclosed.text:
        #     closed_date = dateutil.parser.parse(case.dtclosed.text)

        for event in case.minievents.childGenerator():

            transition = self.state_transition(timestamp=dateutil.parser.parse(event.dt.text),
                                               changes=event.schanges.text,
                                               event_code=int(event.evt.text))

            if transition is not None:
                state_history.append(transition)

        work_item = WorkItem(id=case.ixbug.text,
                             title=case.stitle.string,
                             state=str(case.sstatus.text),
                             type=case.scategory.text,
                             date_created=date_created,
                             category='wat',
                             history=state_history)

        return work_item

    def state_transition(self,
                         changes,
                         timestamp,
                         event_code):
        """
        Create a state_transition from FogBugz event details
        """

        if event_code == evtOpened:
            from_state = 'New'  # ???
            to_state = 'Open'

        elif event_code == evtResolved:
            m = re.match("^[^\']+\'([^\']+)\'[^\']+\'([^\']+)\'", changes)
            if m is not None:
                from_state = m.group(1)
                to_state = m.group(2)
            else:
                return None

        elif event_code == evtEdited:
            m = re.match("^Area changed from \'([^\']+)\' to \'([^\']+)\'", changes)
            if m is not None:
                from_state = m.group(1)
                to_state = m.group(2)
            else:
                return None

        else:
            return None

        return {'from': from_state,
                'to': to_state,
                'timestamp': timestamp}
