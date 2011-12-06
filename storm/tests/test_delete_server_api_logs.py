import os
import re
import time

from nose.plugins.attrib import attr
from storm import openstack
from storm import exceptions
from storm.common.utils.data_utils import rand_name
from storm.common.log_parser import CustomLogParser
import storm.config
import unittest2 as unittest

#file to which request specific logs are written.
REQUEST_LOGFILE = "/var/log/test_delete_server_api.log"
#file containing server logs (to read from )
SERVER_LOGFILE = "/var/log/user.log"


class DeleteServersTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.os = openstack.Manager()
        cls.client = cls.os.servers_client
        cls.config = storm.config.StormConfig()
        cls.image_ref = cls.config.env.image_ref
        cls.flavor_ref = cls.config.env.flavor_ref
        if os.path.exists(REQUEST_LOGFILE):
            os.remove(REQUEST_LOGFILE)

    def tearDown(self):
        self.__log_testcase_data("%s%s" % ("-" * 50, "\n"))

    def __log_testcase_data(self, param):
        fp = open(REQUEST_LOGFILE, "a")
        fp.write(str(param) + "\n")
        fp.close()

    def __verify_messages(self, log_data, expected_log_list):
        self.__log_testcase_data("".join(log_data))
        self.__log_testcase_data("\n\n\n")

        all_found = True
        for log_msg in expected_log_list:
            found = False
            for log_line in log_data:
                if re.search(log_msg, log_line):
                    found = True
                    break
            if not found:
                self.__log_testcase_data("Not found: %s" % log_msg)
                all_found = False
        return all_found

    @attr(type='smoke')
    def test_delete_server(self):
        """Create a Server and call the delete server API."""
        name = rand_name('server')
        resp, body = self.client.create_server(name,
                                               self.image_ref,
                                               self.flavor_ref)
        self.assertTrue('request_id' in resp.keys())
        server_id = body['id']
        #Wait for the server to become active
        self.client.wait_for_server_status(server_id, 'ACTIVE')

        #call delete server API.
        resp, body = self.client.delete_server(server_id)

        #TODO: replace hard coded wait with more appropriate wait.
        time.sleep(2)

        #fetch the logs for current request.
        log_parser = CustomLogParser(SERVER_LOGFILE)
        filtered_logs = log_parser.fetch_request_logs(resp['request_id'])

        #check for expected logs in filtered_logs
        expected_log_list = ['AUDIT [\s\S]+ Terminating instance \d+',
                             'INFO [\s\S]+ Instance \S+ destroyed '\
                             'successfully',
                             'INFO [\s\S]+ Now deallocating fixed ip for '\
                             'instance |\d+|',
                             'INFO [\s\S]+ returned with HTTP 204']
        result = self.__verify_messages(filtered_logs, expected_log_list)
        self.assertTrue(result, "Check test case logs in: %s" % \
                        REQUEST_LOGFILE)

    @attr(type='smoke')
    def test_delete_server_invalid_serverid(self):
        """Create a Server and call the delete server API."""
        server_id = rand_name('instance')
        #call delete server API.
        resp, body = self.client.delete_server(server_id)

        #fetch the logs for current request.
        log_parser = CustomLogParser(SERVER_LOGFILE)
        filtered_logs = log_parser.fetch_request_logs(resp['request_id'])

        #check for expected logs in filtered_logs
        expected_log_list = ['INFO [\s\S]+ HTTP exception thrown: The '\
                             'resource could not be found',
                             'INFO [\s\S]+ returned with HTTP 404']
        result = self.__verify_messages(filtered_logs, expected_log_list)
        self.assertTrue(result, "Check test case logs in: %s" % \
                        REQUEST_LOGFILE)
