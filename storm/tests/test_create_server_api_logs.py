import os
import re

from nose.plugins.attrib import attr
from storm import openstack
from storm import exceptions
from storm.common.utils.data_utils import rand_name
from storm.common.log_parser import CustomLogParser
import storm.config
import unittest2 as unittest

#file to which request specific logs are written.
REQUEST_LOGFILE = "/var/log/test_create_server_api.log"
#file containing server logs (to read from )
SERVER_LOGFILE = "/var/log/user.log"


class CreateServersTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.os = openstack.Manager()
        cls.client = cls.os.servers_client
        cls.config = storm.config.StormConfig()
        cls.image_ref = cls.config.env.image_ref
        cls.invalid_image_ref = cls.config.env.get('invalid_image_ref', 200)
        cls.flavor_ref = cls.config.env.flavor_ref
        cls.invalid_flavor_ref = cls.config.env.get('invalid_flavor_ref', 200)
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
    def test_create_server_invalid_image(self):
        """Call Create Server API with invalid image."""
        name = rand_name('server')
        try:
            resp, body = self.client.create_server(name,
                                                   self.invalid_image_ref,
                                                   self.flavor_ref)
        except exceptions.BadRequest, e:
            resp = e.response_headers

        self.assertTrue('request_id' in resp.keys())
        log_parser = CustomLogParser(SERVER_LOGFILE)
        filtered_logs = log_parser.fetch_request_logs(resp['request_id'])
        expected_log_list = ['INFO [\s\S]+ HTTP exception thrown: Cannot find'\
                             ' requested image %s' % self.invalid_image_ref,
                             'INFO [\s\S]+ returned with HTTP 400']
        result = self.__verify_messages(filtered_logs, expected_log_list)
        self.assertTrue(result, "Check test case logs in: %s" % \
                        REQUEST_LOGFILE)

    @attr(type='smoke')
    def test_create_server_invalid_flavor(self):
        """Call Create Server API with invalid flavor."""
        name = rand_name('server')
        try:
            resp, body = self.client.create_server(name,
                                                   self.image_ref,
                                                   self.invalid_flavor_ref)
        except exceptions.BadRequest, e:
            resp = e.response_headers

        self.assertTrue('request_id' in resp.keys())
        log_parser = CustomLogParser(SERVER_LOGFILE)
        filtered_logs = log_parser.fetch_request_logs(resp['request_id'])
        expected_log_list = ['INFO [\s\S]+ HTTP exception thrown: Invalid '\
                             'flavorRef provided',
                             'INFO [\s\S]+ returned with HTTP 400']
        result = self.__verify_messages(filtered_logs, expected_log_list)
        self.assertTrue(result, "Check test case logs in: %s" % \
                        REQUEST_LOGFILE)

    @attr(type='smoke')
    def test_create_server(self):
        """Call Create Server API with valid input."""
        name = rand_name('server')
        resp, body = self.client.create_server(name,
                                               self.image_ref,
                                               self.flavor_ref)
        self.assertTrue('request_id' in resp.keys())
        #Wait for the server to become active
        self.client.wait_for_server_status(body['id'], 'ACTIVE')

        #fetch the logs for current request.
        log_parser = CustomLogParser(SERVER_LOGFILE)
        filtered_logs = log_parser.fetch_request_logs(resp['request_id'])

        #check for expected logs in filtered_logs
        expected_log_list = ['AUDIT [\s\S]+ instance \d+: starting',
                             'INFO [\s\S]+ instance \S+: Creating image',
                             'INFO [\s\S]+ Instance \S+ spawned successfully',
                             'INFO [\s\S]+ returned with HTTP 202']
        result = self.__verify_messages(filtered_logs, expected_log_list)
        self.assertTrue(result, "Check test case logs in: %s" % \
                        REQUEST_LOGFILE)
