# -*- coding: utf-8 -*-

import time
import re
import logging
import requests

import ndexindraloader
from .exceptions import NDExIndraLoaderError


logger = logging.getLogger(__name__)


def get_members_of_family_node(net_cx=None, node_id=None):
    """
    Gets the members of a protein family by examining the `member`
    node attribute and stripping off the 'hgnc.symbol:' prefix

    :param net_cx:
    :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
    :param node_id: id of protein family node
    :type node_id: int
    :return: (list of node names, list of any issues encountered)
    :rtype: tuple
    """
    hgncprefix = 'hgnc.symbol:'
    hgncprefix_len = len(hgncprefix)
    member_name = 'member'
    n_attr = net_cx.get_node_attribute(node_id,
                                       member_name)
    if n_attr is None or n_attr == (None, None):
        return []
    m_list = n_attr['v']
    if not isinstance(m_list, list):
        return []
    node_names = []

    for entry in m_list:
        if entry.startswith(hgncprefix):
            name_only = entry[hgncprefix_len:]
        else:
            name_only = entry
        node_names.append(name_only)
    return node_names


def get_node_name_to_id_dict(net_cx=None):
    """

    :param net_cx:
    :return:
    :rtype: dict
    """
    node_dict = {}
    for node_id, node_obj in net_cx.get_nodes():
        node_members = get_members_of_family_node(net_cx=net_cx,
                                                  node_id=node_id)
        if len(node_members) > 0:
            for n in node_members:
                node_dict[n] = node_id
        node_dict[node_obj['n']] = node_id
    return node_dict


def is_family_node(net_cx=None, node_id=None):
    """

    :param net_cx:
    :param node_id:
    :return:
    """
    member_name = 'member'
    n_attr = net_cx.get_node_attribute(node_id,
                                       member_name)
    if n_attr is None or n_attr == (None, None):
        return False
    m_list = n_attr['v']
    if not isinstance(m_list, list):
        return False
    if len(m_list) > 0:
        return True
    return False


def get_node_id_to_name_dict(net_cx=None):
    """

    :param net_cx:
    :return:
    """
    node_dict = {}
    for node_id, node_obj in net_cx.get_nodes():
        node_dict[node_id] = node_obj['n']
    return node_dict


def remove_edge(net_cx=None, edge_id=None):
    """
    Removes edge attributes and its edge
    :param net_cx:
    :param edge_id:
    :return:
    """
    e_attr_names = set()
    for edge_attr in net_cx.get_edge_attributes(edge_id):
        e_attr_names.add(edge_attr['n'])
    for e_attr in e_attr_names:
        net_cx.remove_edge_attribute(edge_id, e_attr)
    net_cx.remove_edge(edge_id)


class Indra(object):
    """
    Class to query Indra service
    """

    SUBGRAPH_ENDPOINT = 'https://network.indra.bio/dev/subgraph'
    """
    Endpoint for Indra subgraph service
    """

    NON_DIRECTIONAL_TYPES = ['ActiveForm', 'Association', 'Complex',
                             'Migration']

    def __init__(self, subgraph_endpoint=None,
                 timeout=600):
        """
        Constructor

        :param subgraph_endpoint: REST endpoint for Indra sub graph service
        :type subgraph_endpoint: str
        :param timeout: Timeout in seconds for REST web requests
        :type timeout: float or int
        """
        self._timeout = timeout
        self._subgraph_endpoint = Indra.SUBGRAPH_ENDPOINT

        if subgraph_endpoint is not None:
            self._subgraph_endpoint = subgraph_endpoint

    def _get_indra_result(self, net_cx=None, indraresult=None):
        """

        :param net_cx:
        :param indraresult:
        :return:
        """
        if indraresult is not None:
            return indraresult, 0
        resp, elapsed_time = self.query_indra(net_cx=net_cx)
        if resp.status_code != 200:
            raise NDExIndraLoaderError('Caught non 200 http code from '
                                       'query : ' + str(resp.status_code) +
                                       ' : ' + str(resp.text))
        try:
            return resp.json(), elapsed_time
        except Exception as e:
            raise NDExIndraLoaderError('Caught Exception attempting to parse json from '
                                       'query ' + str(e))

    def _remove_original_edges(self, net_cx=None, remove_orig_edges=None):
        """
        Removes original edges from network inplace
        if `remove_orig_edges` is ``True``

        :param net_cx: Network to remove edges on
        :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :param remove_orig_edges: If ``True`` then original edges are removed
                                  from network otherwise nothing is done.
        :type remove_orig_edges: bool
        :return: None
        """
        if remove_orig_edges is None or remove_orig_edges is False:
            return
        logger.info('Removing original edges')

        edges_to_remove = []
        for edge_id, edge_obj in net_cx.get_edges():
            edges_to_remove.append(edge_id)
        for e in edges_to_remove:
            remove_edge(net_cx=net_cx, edge_id=e)
        del edges_to_remove

    def annotate_network(self, net_cx=None, indraresult=None,
                         netprefix='Indra annotated - ',
                         remove_orig_edges=False,
                         min_evidence_cnt=1,
                         keep_self_edges=False):
        """

        :param net_cx:
        :param maxnetworksize:
        :return:
        """

        result, elapsed_time = self._get_indra_result(net_cx=net_cx,
                                                      indraresult=indraresult)

        stmt_hash = {}

        self._remove_original_edges(net_cx=net_cx,
                                    remove_orig_edges=remove_orig_edges)

        node_name_to_id_dict = get_node_name_to_id_dict(net_cx=net_cx)
        for edge_evidence in result['edges']:
            src_name = edge_evidence['edge'][0]['name']
            target_name = edge_evidence['edge'][1]['name']

            # Indra offers other nodes that are not in the original network
            # we are ignoring these for now
            if src_name not in node_name_to_id_dict or \
                target_name not in node_name_to_id_dict:
                continue

            src_node_id = node_name_to_id_dict[src_name]
            target_node_id = node_name_to_id_dict[target_name]

            for stmtkey in edge_evidence['stmts'].keys():
                stmt = edge_evidence['stmts'][stmtkey]
                if stmt['evidence_count'] < min_evidence_cnt:
                    continue

                # Skip self edges
                if src_node_id == target_node_id and keep_self_edges is False:
                    continue

                stmt['source_node'] = src_name
                stmt['source_node_id'] = src_node_id
                stmt['target_node'] = target_name
                stmt['target_node_id'] = target_node_id

                logger.debug(stmtkey + ' > ' + src_name +
                             ' => ' + target_name + ' ---> ' + str(stmt))
                src_tar_key, \
                isreveresed = self._get_source_target_key(src_node_id=src_node_id,
                                                          target_node_id=target_node_id)
                stmt['isreversed'] = isreveresed
                if src_tar_key not in stmt_hash:
                    stmt_hash[src_tar_key] = []
                stmt_hash[src_tar_key].append(stmt)

        for key in stmt_hash.keys():
            logger.debug(key + ' # of statements: ' + str(len(stmt_hash[key])))
            for stmt in stmt_hash[key]:
                logger.debug(stmt['stmt_type'] + ' (' + stmt['english'] +
                            ') belief=' + str(stmt['belief']) +
                            ' hash=' + str(stmt['stmt_hash']))
            split_key = key.split('_')
            s_node_id = int(split_key[0])
            t_node_id = int(split_key[1])
            edge_id = self._single_edge_adder(net_cx=net_cx,
                                              src_node_id=s_node_id,
                                              target_node_id=t_node_id,
                                              stmt_list=stmt_hash[key])

        net_cx.set_network_attribute('Indra query time in seconds',
                                     values=str(elapsed_time))

        desc_obj = net_cx.get_network_attribute('description')
        if desc_obj is None:
            desc = ''
        else:
            desc = desc_obj['v']

        param_str = {'Keep Self Edges': keep_self_edges,
                     'Min Evidence Count': min_evidence_cnt,
                     'Remove Original Edges': remove_orig_edges}

        net_cx.set_network_attribute('description',
                                     values='<b>Network annotated by '
                                            'NDExIndraLoader (version: ' +
                                            ndexindraloader.__version__ + ')</b><br/><br/>\n\n' +
                                            desc + '<br/>\n<b>Indra annotation '
                                                   'parameters:</b> ' + str(param_str))
        net_cx.set_name(netprefix + net_cx.get_name())

        return net_cx, result

    def query_indra(self, net_cx=None):
        """
        Queries indra subgraph endpoint

        :param net_cx: network used to build query for Indra
        :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :param subgraph_endpoint:
        :return: (requests.Response, Request duration in seconds)
        :rtype: tuple
        """
        n_dict = self._get_indra_query_dict(net_cx=net_cx)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(n_dict)
        start_time = int(time.time())
        resp = requests.post(self._subgraph_endpoint,
                             json=n_dict, timeout=self._timeout)
        return resp, int(time.time()) - start_time

    def _get_indra_query_dict(self, net_cx=None):
        """
        This function takes the network in `net_cx` and extracts
        all the node names to create a :py:func:`dict` that conforms
        to Indra format.

        Indra format:

        .. code-block::

            [
             {'name': <NODE NAME>,
              'namespace': '',
              'identifier': '',
              'lookup': ''}
            ]

        :param net_cx: Network to extract node names from
        :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :return:
        :rtype: dict
        """
        n_dict = {'nodes': []}
        for node_id, node_obj in net_cx.get_nodes():
            node_members = get_members_of_family_node(net_cx=net_cx,
                                                      node_id=node_id)

            n_dict['nodes'].append({'name': node_obj['n'],
                                    'namespace': '0',
                                    'identifier': '0',
                                    'lookup': None})
            if len(node_members) > 0:
                for n in node_members:
                    n_dict['nodes'].append({'name': n,
                                            'namespace': '0',
                                            'identifier': '0',
                                            'lookup': None})
        return n_dict

    def _single_edge_adder(self, net_cx=None, src_node_id=None,
                           target_node_id=None,
                           stmt_list=None):
        """
        Given a list of statements `stmt_list` this method adds a single
        edge to the network `net_cx`. This is done by first merging all
        the statements with matching english statements and
        adding them to one of three list attributes
        (forward statements aka source to target,
        reverse statements target to source,
        and no direction statements) on the edge. The merged
        statement has the interaction followed by parenthesis
        that contain numbers corresponding to number of sources
        for each statement. For web enabled network viewers
        these numbers are links to INDRA database showing the
        evidence.

        The forward statement attribute name is:
        ``SOURCE NODE NAME => TARGET NODE NAME``

        The reverse statement attribute name is:
        ``TARGET NODE NAME => SOURCE NODE NAME``

        The no direction statement attribute name is:
        ``SOURCE NODE NAME - TARGET NODE NAME``


        Other added attributes:

        ``Directed`` - ``True`` if there are one or more
                       forward statements.

        ``Reverse Directed`` - ``True`` if there are one or
                       more reverse statements.

        ``Created by Indra`` - Set to ``True``

        :param net_cx: Network to update
        :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :param src_node_id: Source Node Id
        :type src_node_id: int
        :param target_node_id: Target Node Id
        :type target_node_id: int
        :param stmt_list: Statements which are `dict` objects
        :type stmt_list: list
        :return:
        """
        edge_id = net_cx.create_edge(edge_source=src_node_id,
                                     edge_target=target_node_id,
                                     edge_interaction='interacts with')

        english_stmt_dict = {}
        src_node_names = set()
        target_node_names = set()
        stmt_hash_set = set()
        for stmt in stmt_list:
            if stmt['stmt_hash'] in stmt_hash_set:
                continue
            stmt_hash_set.add(stmt['stmt_hash'])
            clean_english = re.sub('\.$', '', stmt['english'])
            if clean_english not in english_stmt_dict:
                english_stmt_dict[clean_english] = []
            english_stmt_dict[clean_english].append(stmt)

            if stmt['isreversed'] is True:
                target_node_names.add(stmt['source_node'])
                src_node_names.add(stmt['target_node'])
            else:
                src_node_names.add(stmt['source_node'])
                target_node_names.add(stmt['target_node'])

        src_is_family = is_family_node(net_cx, src_node_id)
        target_is_family = is_family_node(net_cx, target_node_id)
        forward = {}
        reverse = {}
        nodirection = {}

        src_name_str = ', '.join(src_node_names)
        tar_name_str = ', '.join(target_node_names)

        for key in english_stmt_dict:
            for stmt in english_stmt_dict[key]:
                split_key = key.split(' ')

                if src_is_family is True:
                    start_offset = 0
                else:
                    start_offset = 1
                if target_is_family is True:
                    end_offset = len(split_key)
                else:
                    end_offset = -1
                inter_only = ' '.join(split_key[start_offset:end_offset])
                # url_str = '<a href="' + stmt['db_url_hash'] + '" target="_blank">' + inter_only + '</a>'
                if stmt['stmt_type'] in Indra.NON_DIRECTIONAL_TYPES:
                    if inter_only not in nodirection:
                        nodirection[inter_only] = []
                    nodirection[inter_only].append((stmt['evidence_count'], stmt['db_url_hash']))
                else:
                    if stmt['isreversed'] is True:
                        if inter_only not in reverse:
                            reverse[inter_only] = []
                        reverse[inter_only].append((stmt['evidence_count'], stmt['db_url_hash']))
                    else:
                        if inter_only not in forward:
                            forward[inter_only] = []
                        forward[inter_only].append((stmt['evidence_count'], stmt['db_url_hash']))

        forward_list = self._create_interaction_list(forward)
        net_cx.set_edge_attribute(edge_id, '  ' + src_name_str + ' => ' + tar_name_str,
                                  forward_list, type='list_of_string')

        reverse_list = self._create_interaction_list(reverse)
        net_cx.set_edge_attribute(edge_id, ' ' + tar_name_str + ' => ' + src_name_str,
                                  reverse_list, type='list_of_string')

        nodirect_list = self._create_interaction_list(nodirection)

        net_cx.set_edge_attribute(edge_id, ' ' + src_name_str + ' - ' + tar_name_str,
                                  nodirect_list, type='list_of_string')

        net_cx.set_edge_attribute(edge_id, 'Created by Indra',
                                  True, type='boolean')

        directedval = False

        if len(forward_list) > 0:
            directedval = True

        reversedirectedval = False
        if len(reverse_list) > 0:
            reversedirectedval = True

        net_cx.set_edge_attribute(edge_id, 'Directed', directedval,
                                  type='boolean')
        net_cx.set_edge_attribute(edge_id, 'Reverse Directed',
                                  reversedirectedval,
                                  type='boolean')

        return edge_id

    def _create_interaction_list(self, url_dict):
        """

        :param url_dict:
        :return:
        """
        the_list = []
        sorted_keys = sorted(url_dict.keys())
        for key in sorted_keys:
            url_str = key + '('
            first = True
            url_dict[key].sort(key=lambda x: x[0], reverse=True)
            for entry in url_dict[key]:
                if first is False:
                    url_str += ','
                url_str += '<a href="' + entry[1] + '">' + str(entry[0]) + '</a>'
                first = False
            the_list.append(url_str + ')')
        return the_list

    def _get_source_target_key(self, src_node_id=None, target_node_id=None):
        """
        Creates key string in form of ``<SOURCE NODE ID>_<TARGET NODE ID>``
        if value of ``src_node_id`` is equal or less then ``target_node_id``
        otherwise ``<TARGET NODE ID>_<SOURCE NODE ID>``

        :param src_node_id: Id of source node
        :type src_node_id: int
        :param target_node_id: Id of target node
        :type target_node_id: int

        :return: (key of source target, ``True`` if target was put first)
        :rtype: tuple
        """
        if src_node_id <= target_node_id:
            return str(src_node_id) + '_' + str(target_node_id), False
        return str(target_node_id) + '_' + str(src_node_id), True

