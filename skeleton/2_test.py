#!/usr/bin/python
import sys
from tools.unetlab import UNetLab
from tools.testflows import TestFlows
from tools.traceroute import Traceroute
import tools.file_io as file_io
from tools.globals import *


UNL = UNetLab(**file_io.read_yaml('{}/unetlab.yml'.format(NET_DIR)))
TEST_FLOWS = TestFlows(file_io.read_txt('{}/traffic_flows.txt'.format(TEST_DIR)))


def conf_shut_intf(intf):
    return conf_run_intf(intf, 'shutdown')


def conf_unshut_intf(intf):
    return conf_run_intf(intf, 'no shutdown')


def conf_run_intf(intf, command):
    return '\r\n'.join(['enable', 'conf t', 'interface {}'.format(intf), command, 'end'])


def run_tests(tests, lab):
    failed = False
    for seq, fail_condition in sorted(tests.keys()):
        print
        print("*** TESTING SCENARIO {}".format(seq))
        for fail_point in fail_condition:
            if not fail_point.dev == 'None':
                fail_node = fail_point.node(lab)
                fail_node.configure(conf_shut_intf(fail_point.intf))
                print("*** FAILURE CONDITION CREATED: {}".format(fail_point))
        for (from_point, to_point), flow_data in tests[(seq, fail_condition)].iteritems():
            flow = flow_data['parsed']
            print("*** TESTING FLOW FROM {} TO {}".format(from_point, to_point))
            from_node = from_point.node(lab)
            trace_command = 'traceroute {} {} numeric'.format(to_point.ip, 'source ' + from_point.intf)
            enable = 'enable\rconf t\rno logging console\rend\r'
            trace_result = from_node.configure(enable + trace_command)
            traceroute = Traceroute(trace_result)
            traceroute.parse()
            traceroute.resolve()
            rc = traceroute.verify(flow)
            if rc > 0:
                failed = True
                print('!!! FAILED FLOW FROM {} TO {}'.format(from_point, to_point))
                print('!!! EXPECTED PATH: {}, ACTUAL PATH: {}'
                      .format('->'.join(flow_data['text'].split(', ')), traceroute.as_string([from_point.dev])))
            else:
                print ('*** SUCCESSFUL FLOW')
        for fail_point in fail_condition:
            if not fail_point.dev == 'None':
                fail_node = fail_point.node(lab)
                fail_node.configure(conf_unshut_intf(fail_point.intf))
                print("*** FAILURE CONDITION RESTORED: {}".format(fail_point))
    return failed


def main():
    try:
        lab = UNL.get_lab()
        print("*** CONNECTED TO UNL")
        flows = TEST_FLOWS.parse()
        failed = run_tests(flows, lab)
        print("*** TESTS COMPLETED")
    except:
        raise
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
