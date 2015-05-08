import BeautifulSoup
import unittest
     # Going to need to change the name of this package
from jira_stats.fogbugz_wrapper import FogbugzWrapper
from jira_stats.work import WorkItem
from datetime import date


class TestGetMetrics(unittest.TestCase):

    def testGetIssueFromFogBugz(self):

        source = """
        <case ixbug="1838" operations="edit,reopen,remind"><ixbug>1838</ixbug><stitle><![CDATA[Engine not working, throwing up this for no reason]]></stitle><sstatus><![CDATA[Closed (Fixed)]]></sstatus><scategory><![CDATA[Bug]]></scategory><minievents><event ixbugevent="13032" ixbug="1838"><ixbugevent>13032</ixbugevent><evt>1</evt><sverb><![CDATA[Opened]]></sverb><ixperson>14</ixperson><ixpersonassignedto>0</ixpersonassignedto><dt>2015-03-06T12:15:41Z</dt><femail>false</femail><fhtml>false</fhtml><fexternal>false</fexternal><schanges></schanges><sformat></sformat><evtdescription><![CDATA[Opened by Bob The-Dev]]></evtdescription><sperson><![CDATA[Bob The-Dev]]></sperson></event><event ixbugevent="13033" ixbug="1838"><ixbugevent>13033</ixbugevent><evt>3</evt><sverb><![CDATA[Assigned]]></sverb><ixperson>14</ixperson><ixpersonassignedto>2</ixpersonassignedto><dt>2015-03-06T12:15:41Z</dt><femail>false</femail><fhtml>false</fhtml><fexternal>false</fexternal><schanges></schanges><sformat></sformat><evtdescription><![CDATA[Assigned to Sarah Code by Bob The-Dev]]></evtdescription><sperson><![CDATA[Bob The-Dev]]></sperson></event><event ixbugevent="13036" ixbug="1838"><ixbugevent>13036</ixbugevent><evt>14</evt><sverb><![CDATA[Resolved]]></sverb><ixperson>2</ixperson><ixpersonassignedto>14</ixpersonassignedto><dt>2015-03-07T10:02:06Z</dt><femail>false</femail><fhtml>false</fhtml><fexternal>false</fexternal><schanges><![CDATA[Status changed from 'Active' to 'Resolved (Fixed)'.
        ]]></schanges><sformat></sformat><evtdescription><![CDATA[Resolved (Fixed) and assigned to Bob The-Dev by Sarah Code]]></evtdescription><sperson><![CDATA[Sarah Code]]></sperson></event><event ixbugevent="13039" ixbug="1838"><ixbugevent>13039</ixbugevent><evt>6</evt><sverb><![CDATA[Closed]]></sverb><ixperson>14</ixperson><ixpersonassignedto>0</ixpersonassignedto><dt>2015-03-07T12:41:31Z</dt><femail>false</femail><fhtml>false</fhtml><fexternal>false</fexternal><schanges></schanges><sformat></sformat><evtdescription><![CDATA[Closed by Bob The-Dev]]></evtdescription><sperson><![CDATA[Bob The-Dev]]></sperson></event></minievents></case>
        """

        soup = BeautifulSoup.BeautifulSoup(source)

        our_fogbugz = FogbugzWrapper()

        actual = our_fogbugz.issue_from_xml(soup.case)
        expected = WorkItem(id="1838",
                            state="Closed (Fixed)",
                            history=[])

        self.assertEqual(actual.to_JSON(), expected.to_JSON())

    def testGetStateTransitionFromFogBugz(self):

        """
        It looks like state transistions need to be pulled out of the schanges element.


        "Edited Area changed from '{FROM_STATE}' to '{TO_STATE}'"

        "Resolved Status changed from '{FROM_STATE}' to '{TO_STATE}'"

        Q. What is the difference between an Area and a Status?
        """

        expected = {'state': 'Open',
                    'days':  2}

        our_fogbugz = FogbugzWrapper()

        actual = our_fogbugz.time_in_state(start_date=date(2015, 03, 05),
                                           end_date=date(2015, 03, 07),
                                           changes="Edited Area changed from 'Open' to 'Closed'")

        self.assertEqual(actual, expected)
