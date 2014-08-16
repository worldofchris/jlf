# JIRA _lean forward_ 

[![Build Status](https://travis-ci.org/worldofchris/jlf.png)](https://travis-ci.org/worldofchris/jlf)

## Extract _forward_ looking indicators from JIRA


![image](public/assets/cfd.png)

JLF pulls metrics out of JIRA so we can measure:

* Throughput
* Cycle Time
* Ratio of Overhead / Value / Failure work

It is intended to complement the existing [kanban reporting](https://confluence.atlassian.com/display/AGILE/JIRA+Agile+Documentation) built into Jira Agile.

## Installation

* Clone this repo
* Create a virtual environment e.g.

        virtualenv jlf
        source jlf/bin/activate
	
* Install with setup.py

	    python setup.py install
	
## Configuration

To start getting metrics out of JIRA you'll need a JSON config file describing your JIRA instance, the filters for the issues you want to report on, different types of work, cycles and the metrics you want to extract.

## Use

Once you have a config file you can run jlf with:

		jlf -c CONFIG_FILE -n NUM_WEEKS
		
Where `CONFIG_FILE` is the path to your config file and `NUM_WEEKS` is the number of weeks of work you want to report on.

## Running the tests

* Run the tests with:

	    nosetests

* To run a single test, specify the path to the module, the Test Case Class Name and the test Case Name.  e.g.

		nosetests jira_stats.test.test_get_issues:TestGetMetrics.testGetArrivalRate


	


