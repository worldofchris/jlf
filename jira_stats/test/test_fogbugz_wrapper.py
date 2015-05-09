# -*- coding: utf-8 -*-

import BeautifulSoup
import unittest
     # Going to need to change the name of this package
from jira_stats.fogbugz_wrapper import FogbugzWrapper, evtResolved, evtEdited
from jira_stats.work import WorkItem
from datetime import date, datetime
import mock
import os


class TestGetMetrics(unittest.TestCase):

    def testGetWorkItemFromFogBugzCase(self):

        source = """
        <case ixbug="1838" operations="edit,reopen,remind"><ixbug>1838</ixbug><dtopened>2015-03-04T12:15:41Z</dtopened><dtclosed>2015-03-10T12:41:31Z</dtclosed><stitle><![CDATA[Engine not working, throwing up this for no reason]]></stitle><sstatus><![CDATA[Closed (Fixed)]]></sstatus><scategory><![CDATA[Bug]]></scategory><minievents><event ixbugevent="13032" ixbug="1838"><ixbugevent>13032</ixbugevent><evt>1</evt><sverb><![CDATA[Opened]]></sverb><ixperson>14</ixperson><ixpersonassignedto>0</ixpersonassignedto><dt>2015-03-06T12:15:41Z</dt><femail>false</femail><fhtml>false</fhtml><fexternal>false</fexternal><schanges></schanges><sformat></sformat><evtdescription><![CDATA[Opened by Bob The-Dev]]></evtdescription><sperson><![CDATA[Bob The-Dev]]></sperson></event><event ixbugevent="13033" ixbug="1838"><ixbugevent>13033</ixbugevent><evt>3</evt><sverb><![CDATA[Assigned]]></sverb><ixperson>14</ixperson><ixpersonassignedto>2</ixpersonassignedto><dt>2015-03-06T12:15:41Z</dt><femail>false</femail><fhtml>false</fhtml><fexternal>false</fexternal><schanges></schanges><sformat></sformat><evtdescription><![CDATA[Assigned to Sarah Code by Bob The-Dev]]></evtdescription><sperson><![CDATA[Bob The-Dev]]></sperson></event><event ixbugevent="13036" ixbug="1838"><ixbugevent>13036</ixbugevent><evt>14</evt><sverb><![CDATA[Resolved]]></sverb><ixperson>2</ixperson><ixpersonassignedto>14</ixpersonassignedto><dt>2015-03-07T10:02:06Z</dt><femail>false</femail><fhtml>false</fhtml><fexternal>false</fexternal><schanges><![CDATA[Status changed from 'Active' to 'Resolved (Fixed)'.
        ]]></schanges><sformat></sformat><evtdescription><![CDATA[Resolved (Fixed) and assigned to Bob The-Dev by Sarah Code]]></evtdescription><sperson><![CDATA[Sarah Code]]></sperson></event><event ixbugevent="13039" ixbug="1838"><ixbugevent>13039</ixbugevent><evt>6</evt><sverb><![CDATA[Closed]]></sverb><ixperson>14</ixperson><ixpersonassignedto>0</ixpersonassignedto><dt>2015-03-07T12:41:31Z</dt><femail>false</femail><fhtml>false</fhtml><fexternal>false</fexternal><schanges></schanges><sformat></sformat><evtdescription><![CDATA[Closed by Bob The-Dev]]></evtdescription><sperson><![CDATA[Bob The-Dev]]></sperson></event></minievents></case>
        """

        soup = BeautifulSoup.BeautifulSoup(source)

        our_fogbugz = FogbugzWrapper()

        actual = our_fogbugz.work_item_from_xml(soup.case)
        expected = WorkItem(id="1838",
                            state="Closed (Fixed)",
                            title="Engine not working, throwing up this for no reason",
                            type="Bug",
                            history=[{'from': "Active",
                                      'timestamp': "2015-03-07T10:02:06+00:00",
                                      'to': "Resolved (Fixed)"}])

        self.assertEqual(actual.to_JSON(), expected.to_JSON())

    # Will need test for issue with no closed date

    def testGetStateTransitionFromFogBugz(self):

        """
        It looks like state transistions need to be pulled out of the schanges element.


        "Edited Area changed from '{FROM_STATE}' to '{TO_STATE}'"

        "Resolved Status changed from '{FROM_STATE}' to '{TO_STATE}'"

        Q. What is the difference between an Area and a Status?
        """

        expected = {'from': 'Open',
                    'to':   'Closed',
                    'timestamp':  datetime(2015, 03, 07, 13, 10, 20)}

        our_fogbugz = FogbugzWrapper()

        actual = our_fogbugz.state_transition(timestamp=datetime(2015, 03, 07, 13, 10, 20),
                                              event_code=evtResolved,
                                              changes="Resolved Status changed from 'Open' to 'Closed'")

        self.assertEqual(actual, expected)

    def testGetStateTransitionFromAreaChange(self):

        expected = {'from': 'In Progress',
                    'to':   'Not Started',
                    'timestamp':  datetime(2015, 03, 07, 13, 10, 20)}

        our_fogbugz = FogbugzWrapper()

        actual = our_fogbugz.state_transition(timestamp=datetime(2015, 03, 07, 13, 10, 20),
                                              event_code=evtEdited,
                                              changes="Area changed from 'In Progress' to 'Not Started'.")

        self.assertEqual(actual, expected)

    def testConnectToFogBugz(self):

        patcher = mock.patch('fogbugz.FogBugz')
        mock_fogbugz = patcher.start()

        config = {'source': {'type': 'fogbugz',
                             'url': 'https://worldofchris.fogbugz.com',
                             'token': '33vvjghjeis7439a29qqg29azqq8q1'},
                  'categories': None}

        our_fogbugz = FogbugzWrapper(config)

        mock_fogbugz.assert_called_with(config['source']['url'], config['source']['token'])

    def testGetCasesFromFogBugz(self):

        mock_fogbugz_client = mock.Mock()
        mock_fogbugz_client.search.side_effect = self.serve_dummy_cases

        patcher = mock.patch('fogbugz.FogBugz')
        mock_fogbugz = patcher.start()

        mock_fogbugz.return_value = mock_fogbugz_client

        config = {'source':     {'type': 'fogbugz',
                                 'url': 'https://worldofchris.fogbugz.com',
                                 'token': '33vvjghjeis7439a29qqg29azqq8q1'},
                  'categories': {'all': '*'}}

        our_fogbugz = FogbugzWrapper(config)
        actual = our_fogbugz.work_items()

        mock_fogbugz_client.search.assert_called_with(config['categories']['all'])

        self.assertEqual(len(actual), 3)

##############################################################################################

    def serve_dummy_cases(self, query):

        filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data/cases.xml")

        with open(filename, "r") as xml:
            source = xml.read()

            return BeautifulSoup.BeautifulSoup(source)
