import click
import requests
import time
import logging
import ssl
import sys
import json
from collections import namedtuple


ssl._create_default_https_context = ssl._create_unverified_context

logging.basicConfig(level=logging.INFO)
requests.packages.urllib3.disable_warnings()

session = requests.Session()

patch_header = {'Content-Type': 'application/strategic-merge-patch+json'}

Pod = namedtuple('Pod', ['namespace', 'name'])


class DrainNode:

    def __init__(self, apiserver, user, password, node, reverse):

        self._apiserver = apiserver
        self._session = requests.Session()
        self._session.auth = (user, password)
        self._node = node
        self._reverse = reverse

    def check_node_readiness(self):
        nodeinfo = self._session.get('{api}/api/v1/nodes/{node}'.format(api=self._apiserver, node=self._node),
                                     verify=False)
        node = json.loads(nodeinfo.text)
        if node['status']['conditions'][0]['status'] != "True":
            logging.error("Refusing to action upon node {node} which has a \"{status}\" (non-True) status.".format(node=self._node, status=node['status']['conditions'][0]['status']))
            sys.exit(1)

    def set_node_schedulable(self, **kwargs):
        patch_spec = {}
        patch_spec['kind'] = 'Node'
        patch_spec['apiVersion'] = 'v1'
        patch_spec['metadata'] = {}
        patch_spec['metadata']['name'] = self._node
        patch_spec['spec'] = {}
        patch_spec['spec']['unschedulable'] = kwargs['unschedulable']

        r = self._session.patch('{api}/api/v1/nodes/{node}'.format(api=self._apiserver, node=self._node),
                                json=patch_spec,
                                verify=False,
                                headers=patch_header)
        if r.status_code is 200:
            return True
        else:
            return False

    def get_pods_on_node(self):
        pods_on_host = []
        r = self._session.get('{api}/api/v1/pods'.format(api=self._apiserver),
                              verify=False)

        pods = json.loads(r.text)

        for pod in pods['items']:
            if pod['spec']['nodeName'] == self._node:
                if 'annotations' in pod['metadata'].keys():
                    if 'kubernetes.io/config.source' in pod['metadata']['annotations'].keys():
                        # this is a local kubelet manifest pod, so ignore it
                        logging.debug("kubelet-manifest pod: {name}".format(name=pod['metadata']['name']))
                    else:
                        pods_on_host.append(Pod(pod['metadata']['namespace'], pod['metadata']['name']))
                else:
                    # data structure did not contain an annotations section, so pod is not a kubelet manifest.
                    pods_on_host.append(Pod(pod['metadata']['namespace'], pod['metadata']['name']))

        return pods_on_host

    def terminate_pod(self, pod_tuple):
        self._session.delete('{api}/api/v1/namespaces/{ns}/pods/{pod}'.format(api=self._apiserver, ns=pod_tuple.namespace, pod=pod_tuple.name),
                             verify=False)


@click.command()
@click.option('--reverse', envvar='K8SDRAIN_REVERSE', is_flag=True, default=False, help="Reinstate node for scheduling")
@click.option('--user', envvar='K8SDRAIN_USER', help="Username for api")
@click.option('--password', envvar='K8SDRAIN_PASSWORD', help="Password for api")
@click.option('--master', envvar='K8SDRAIN_MASTER', help="URL for API Access")
@click.argument('node')
def main(reverse, node, user, password, master):
    '''This script will drain a node in preparation for maintenance on the node'''

    # create object to hold our variables and functions in
    drain = DrainNode(master, user, password, node, reverse)

    # Sanity check that we should action on this node.  One should only run this script on Ready nodes.
    drain.check_node_readiness()

    if drain._reverse is True:
        # we want to reinstate the named node
        if drain.set_node_schedulable(unschedulable=False):
            logging.info("Node {node} is now schedulable again.".format(node=drain._node))
            sys.exit(0)
        else:
            logging.error("Unable to set node {node} to schedulable.".format(node=drain._node))
            sys.exit(1)
    else:
        # set selected node to not schedulable
        if drain.set_node_schedulable(unschedulable=True):
            logging.info("Node {node} set to unschedulable.".format(node=drain._node))
        else:
            logging.error("Unable to set node {node} as unschedulable.".format(node=drain._node))
            sys.exit(1)

    # Find pods that need to be drained and drain them
    pods_to_drain = drain.get_pods_on_node()
    while (len(pods_to_drain) > 0):
        logging.info("{x} pods left to drain".format(x=len(pods_to_drain)))
        for pod in pods_to_drain:
            logging.info("Attempting to terminate {ns}/{pod}".format(ns=pod.namespace, pod=pod.name))
            drain.terminate_pod(pod)
            time.sleep(1)
        pods_to_drain = drain.get_pods_on_node()

    logging.info("Process complete, {node} should now be safe to turn off.".format(node=drain._node))


if __name__ == '__main__':
    main(auto_envvar_prefix='K8SDRAIN')
