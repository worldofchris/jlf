# JIRA _lean forward_

[![Build Status](https://travis-ci.org/worldofchris/jlf.png)](https://travis-ci.org/worldofchris/jlf)

## Extract _forward_ looking indicators from JIRA so we can measure:

* Throughput
* Cycle Time
* Drop Outs
* Ratio of Overhead / Value / Failure work

## Installation

* Clone this repo
* Create a virtual environment e.g.

        virtualenv jlf
        source jlf/bin/activate
	
* Install with setup.py

	    python setup.py install
	
## Running the tests

* Run the tests with:

	    nosetests

* To run a single test, specify the path to the module, the Test Case Class Name and the test Case Name.  e.g.

		nosetests jira_stats.test.test_get_issues:TestGetMetrics.testGetArrivalRate


	


