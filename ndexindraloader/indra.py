# -*- coding: utf-8 -*-

import time
import re
import logging
import requests
import math
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
    :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
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
    :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
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
    Gets dict from network where key is node id and value
    is the name of node

    :param net_cx: Network to build dict from
    :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
    :return: map of node id to node names
    :rtype: dict
    """
    node_dict = {}
    for node_id, node_obj in net_cx.get_nodes():
        node_dict[node_id] = node_obj['n']
    return node_dict


def remove_edge(net_cx=None, edge_id=None):
    """
    Removes edge attributes and its edge

    :param net_cx: Network to remove edge from
    :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
    :param edge_id:
    :return:
    """
    e_attr_names = set()
    e_attribs = net_cx.get_edge_attributes(edge_id)
    if e_attribs is not None:
        for edge_attr in e_attribs:
            e_attr_names.add(edge_attr['n'])
    for e_attr in e_attr_names:
        net_cx.remove_edge_attribute(edge_id, e_attr)
    net_cx.remove_edge(edge_id)


class Indra(object):
    """
    Class to query INDRA service and annotate a
    :py:class:`~ndex2.nice_cx_network.NiceCXNetwork` network
    """

    SUBGRAPH_ENDPOINT = 'https://network.indra.bio/api/subgraph'
    """
    Endpoint for INDRA subgraph service
    """

    STATEMENT_URL = 'https://db.indra.bio/statements'
    """
    URL Prefix for INDRA statements website
    """

    NON_DIRECTIONAL_TYPES = ['ActiveForm', 'Association', 'Complex',
                             'Migration']
    """
    These statement types aka 'stmt_type' are non directional
    """

    SOURCE = '__edge_source'
    """
    Name of edge attribute to denote source of edge
    """

    RELATIONSHIPS = 'Relationships'
    """
    Name of edge attribute containing relationships between two nodes
    """

    DIRECTED = '__directed'
    """
    Name of edge attribute to denote that edge is directed
    """

    REVERSE_DIRECTED = '__reverse_directed'
    """
        Name of edge attribute to denote that edge is directed in reverse
    """

    RELATIONSHIP_SCORE = '__relationship_score'
    """
    Name of edge attribute that holds the natural log of evidence
    count from INDRA for the edge
    """

    DEFAULT_BROWSER_TARGET = 'INDRA_Evidence'
    """
    Default target value set for html links
    """

    def __init__(self, subgraph_endpoint=None,
                 timeout=600,
                 default_browser_target=DEFAULT_BROWSER_TARGET):
        """
        Constructor

        :param subgraph_endpoint: REST endpoint for INDRA sub graph service
        :type subgraph_endpoint: str
        :param timeout: Timeout in seconds for REST web requests
        :type timeout: float or int
        :param default_browser_target: Value to set in ```target``` attribute for
                                       html links. If _blank then a new tab will
                                       be opened every time a user clicks a link.
                                       See https://www.w3schools.com/tags/att_a_target.asp
                                       for more information
        :type default_browser_target: str
        """
        self._timeout = timeout
        self._subgraph_endpoint = Indra.SUBGRAPH_ENDPOINT

        self._browser_target = default_browser_target

        if self._browser_target is None:
            self._browser_target = Indra.DEFAULT_BROWSER_TARGET

        if subgraph_endpoint is not None:
            self._subgraph_endpoint = subgraph_endpoint

    def _get_indra_result(self, net_cx=None, indraresult=None):
        """
        Queries INDRA REST service with given network unless
        **indraresult** is not ``None`` in which case that is returned

        :param net_cx: Network to use for query
        :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :param indraresult: Way to pass in cached result that is
                            used in leiu of querying the INDRA service.
        :type indraresult: dict
        :return: Value of **indraresult** if not ``None`` otherwise
                 response from querying INDRA service
        :rtype: dict
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

    def _add_source_to_existing_edges(self, net_cx=None, source_value=None):
        """
        Adds source value if flag is set

        :param net_cx:
        :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :return:
        """
        if source_value is None:
            return
        for edge_id, edge_obj in net_cx.get_edges():
            e_attr = net_cx.get_edge_attribute(edge_id, Indra.SOURCE)
            if e_attr == (None, None):
                net_cx.set_edge_attribute(edge_id, Indra.SOURCE, source_value)

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
                         netprefix='INDRA annotated - ',
                         remove_orig_edges=False,
                         min_evidence_cnt=1,
                         keep_self_edges=False,
                         source_value=None):
        """

        :param net_cx:
        :param indraresult:
        :param netprefix:
        :param remove_orig_edges:
        :param min_evidence_cnt:
        :param keep_self_edges:
        :param source_value:
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

            # INDRA offers other nodes that are not in the original network
            # we are ignoring these for now
            if src_name not in node_name_to_id_dict or target_name not in node_name_to_id_dict:
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
            self._single_edge_adder(net_cx=net_cx,
                                    src_node_id=s_node_id,
                                    target_node_id=t_node_id,
                                    stmt_list=stmt_hash[key])

        net_cx.set_network_attribute('__INDRA query time in seconds',
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
                                     values=str(desc) +
                                     '\n\n<b>Additional edges added by ' +
                                     'NDExIndraLoader (version: ' +
                                     ndexindraloader.__version__ +
                                     ')</b> using <a href="https://www.' +
                                     'indra.bio" target="' +
                                     Indra.DEFAULT_BROWSER_TARGET +
                                     '">INDRA ' +
                                     'service</a><br/>')

        net_cx.set_network_attribute('INDRA parameters', values=param_str)
        net_cx.set_name(netprefix + net_cx.get_name())

        self._add_source_to_existing_edges(net_cx=net_cx, source_value=source_value)

        return net_cx, result

    def query_indra(self, net_cx=None):
        """
        Queries indra subgraph endpoint

        :param net_cx: network used to build query for INDRA
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
        to INDRA format.

        INDRA format:

        .. code-block::

            [
             {'name': <NODE NAME>,
              'namespace': '',
              'identifier': '',
              'lookup': ''}
            ]

        :param net_cx: Network to extract node names from
        :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :return: dict in INDRA format denoted above.
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

    def _get_unique_statments(self, stmt_list=None):
        """
        Iterates through statements and returns a list of
        unique statements. Duplicates are ones with identical 'stmt_hash' values

        :param stmt_list:
        :type stmt_list: list
        :return unique statements
        :rtype: list
        """
        stmt_hash_set = set()
        unique_stmt_list = []
        for stmt in stmt_list:
            if stmt['stmt_hash'] in stmt_hash_set:
                continue
            stmt_hash_set.add(stmt['stmt_hash'])
            unique_stmt_list.append(stmt)
        return unique_stmt_list

    def _merge_matching_statements(self, stmt_list=None):
        """
        Iterates through the statements and those that have matching
        english statements are merged into one statement with evidence
        counts added

        :param stmt_list:
        :type stmt_list: list
        :return unique statements
        :rtype: list
        """
        stmt_english_set = set()
        stmt_english_dict = {}
        for stmt in stmt_list:
            if stmt['english'] not in stmt_english_dict:
                stmt_english_dict[stmt['english']] = []
            stmt_english_dict[stmt['english']].append(stmt)

        unique_stmt_list = []
        for key in stmt_english_dict.keys():
            stmt_list = stmt_english_dict[key]
            total_evidence_count = 0
            for stmt in stmt_list:
                total_evidence_count += stmt['evidence_count']
            stmt_list[0]['evidence_count'] = total_evidence_count
            unique_stmt_list.append(stmt_list[0])

        return unique_stmt_list


    def _remove_period_from_statements(self, stmt_list=None):
        for stmt in stmt_list:
            stmt['english'] = re.sub('\.$', '', stmt['english'])

    def _single_edge_adder(self, net_cx=None, src_node_id=None,
                           target_node_id=None,
                           stmt_list=None):
        """
        Given a list of statements `stmt_list` this method adds a single
        edge to the network `net_cx`. This is done by first
        removing statements with duplicate hash values and adding
        them to a single attribute ``Relationships`` with a link
        back to INDRA showing evidence

        Other added attributes:

        ``__directed`` - ``True`` if there are one or more
                       forward statements.

        ``__reverse_directed`` - ``True`` if there are one or
                       more reverse statements.

        ``__edge_source`` - Set to ``INDRA``

        :param net_cx: Network to update
        :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :param src_node_id: Source Node Id
        :type src_node_id: int
        :param target_node_id: Target Node Id
        :type target_node_id: int
        :param stmt_list: Statements which are `dict` objects
        :type stmt_list: list
        :return: Id of edge created
        :rtype: int
        """
        edge_id = net_cx.create_edge(edge_source=src_node_id,
                                     edge_target=target_node_id,
                                     edge_interaction='interacts with')

        unique_byhash_stmt_list = self._get_unique_statments(stmt_list=stmt_list)

        self._remove_period_from_statements(stmt_list=unique_byhash_stmt_list)

        unique_stmt_list = self._merge_matching_statements(stmt_list=unique_byhash_stmt_list)

        full_list_tuple = []
        forward_count = 0
        reverse_count = 0
        total_evidence_cnt = 0
        for stmt in unique_stmt_list:

            if stmt['stmt_type'] not in Indra.NON_DIRECTIONAL_TYPES:
                if stmt['isreversed'] is True:
                    reverse_count += 1
                else:
                    forward_count += 1

            # add tuple containing statement and evidence count
            # which will be used to sort the list later
            full_list_tuple.append((stmt['english'] + '(' +
                                    self._create_indra_evidence_url(evidence_cnt=stmt['evidence_count'],
                                                                    thesubject=stmt['source_node'],
                                                                    theobject=stmt['target_node'],
                                                                    thetype=stmt['stmt_type']) +
                                   ')', int(stmt['evidence_count'])))
            try:
                total_evidence_cnt += int(stmt['evidence_count'])
            except ValueError as ve:
                logger.warning('Expected a number for evidence_count in this '
                               'statement, but got: ' +
                               str(stmt['evidence_count']) +
                               ' full statement: ' + str(stmt))
            # nodirection[inter_only].append((stmt['evidence_count'], stmt['db_url_hash']))
        all_url = self._create_indra_all_evidence_url(evidence_cnt=total_evidence_cnt,
                                                      theagent0=stmt['source_node'],
                                                      theagent1=stmt['target_node'])

        # sort the list in descending order based on evidence count
        # element 1 of tuple
        full_list = self._sort_evidence_tuple_list(full_list_tuple)
        net_cx.set_edge_attribute(edge_id, Indra.RELATIONSHIPS,
                                  'All Evidences (' +
                                  all_url + ')<ul><li/>' +
                                  '<li/>'.join(full_list) + '</ul>',
                                  type='string')

        net_cx.set_edge_attribute(edge_id, Indra.SOURCE,
                                  'INDRA')

        net_cx.set_edge_attribute(edge_id, Indra.RELATIONSHIP_SCORE,
                                  math.log(float(total_evidence_cnt)),
                                  type='double')

        directedval = False

        if forward_count > 0:
            directedval = True

        reversedirectedval = False
        if reverse_count > 0:
            reversedirectedval = True

        net_cx.set_edge_attribute(edge_id, Indra.DIRECTED, directedval,
                                  type='boolean')
        net_cx.set_edge_attribute(edge_id, Indra.REVERSE_DIRECTED,
                                  reversedirectedval,
                                  type='boolean')
        return edge_id

    def _sort_evidence_tuple_list(self, list_of_tuples):
        """
        Takes a list of tuples, splitting them into set by ``PROTEIN1``
        For each of those groups the tuples are sorted in descending order
        with highest evidence count first. Those groups are then put into
        another list and ordered by the highest evidence count found in
        each group. The statements are then extracted in order from this
        list and returned to the caller

        :param list_of_tuples: containing tuples
               ``(PROTEIN1 INTERACTION PROTEIN, EVIDENCE COUNT)``
        :type list_of_tuples: list
        :return:
        """
        # create a dict where protein is key and value is list of
        # statements with that protein at beginning
        protein_dict = {}
        for a_tuple in list_of_tuples:
            protein = re.sub(' .*', '', a_tuple[0])
            if protein not in protein_dict:
                protein_dict[protein] = []
            protein_dict[protein].append(a_tuple)
        logger.debug('Protein dict: ' + str(protein_dict))

        sorted_tuple_list = []
        # sort each group by evidence count and add to a new tuple
        for protein_key in protein_dict.keys():
            # sort the statements by evidence count in descending order
            protein_dict[protein_key].sort(key=lambda y: y[1], reverse=True)

            # get the maximum evidence count (assume it is second element of first tuple)
            max_evidence_cnt_for_grp = protein_dict[protein_key][0][1]

            # replace protein_dict[protein_key] with just list of statements since we no longer
            # need the evidence count cause we already sorted by that value
            protein_dict[protein_key] = [a_tuple[0] for a_tuple in protein_dict[protein_key]]

            # make a new list of tuples where 1st element is max evidence count and second is the list
            # of statements ie (EVIDENCE COUNT, [STATEMENTS....])
            sorted_tuple_list.append((max_evidence_cnt_for_grp, protein_dict[protein_key]))

        # sort [(EVIDENCE COUNT, [STATEMENTS....])] by  EVIDENCE COUNT
        sorted_tuple_list.sort(key=lambda y: y[0], reverse=True)
        logger.debug('sorted tuple list after sort: ' + str(sorted_tuple_list))

        # create list of lists of just statements ie [[STATEMENTS...]]
        list_o_list = [a_tuple[1] for a_tuple in sorted_tuple_list]
        logger.debug('list_o_list: ' + str(list_o_list))

        # Flatten list of lists into single list
        final_list = []
        for list_ele in list_o_list:
            final_list.extend(list_ele)
        return final_list

    def _create_indra_evidence_url(self, evidence_cnt=0,
                                   thesubject=None,
                                   theobject=None,
                                   thetype=None):
        """

        :param evidence_cnt:
        :param thesubject:
        :param theobject:
        :param thetype:
        :return:
        """
        indra_url = Indra.STATEMENT_URL + '/from_agents?subject=' +\
            thesubject + '&object=' + theobject + '&type=' + thetype +\
            '&format=html&expand_all=true'

        return '<a href="' + str(indra_url) +\
               '" target="' + self._browser_target + '">' +\
               str(evidence_cnt) + '</a>'

    def _create_indra_all_evidence_url(self, evidence_cnt=0, theagent0=None,
                                       theagent1=None):
        """

        :param self:
        :param evidence_cnt:
        :param theagent0:
        :param theagent1:
        :return:
        """
        indra_url = Indra.STATEMENT_URL + '/from_agents?agent0=' +\
            theagent0 + '&agent1=' + theagent1 +\
            '&format=html&expand_all=true'

        return '<a href="' + str(indra_url) +\
               '" target="' + self._browser_target + '">' +\
               str(evidence_cnt) + '</a>'

    def _create_interaction_list(self, url_dict):
        """

        :param url_dict:
        :return:
        """
        the_list = []
        logger.debug('url_dict: ' + str(url_dict))
        sorted_keys = sorted(url_dict.keys())
        for key in sorted_keys:
            url_str = key + '('
            first = True
            url_dict[key].sort(key=lambda x: x[0], reverse=True)
            for entry in url_dict[key]:
                if first is False:
                    url_str += ','
                url_str += '<a href="' + entry[1] +\
                           '" target="_blank">' + str(entry[0]) + '</a>'
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
