# -*- coding: utf-8 -*-

import time
import copy
import re
import logging
import requests
import math
import html
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


class StatementFilter(object):
    """
    Base class for classes that filter INDRA statements
    """
    def __init__(self):
        """
        Constructor
        """
        pass

    def get_description(self):
        """
        Subclasses should implement
        :return:
        """
        raise NotImplementedError('subclasses should implement')

    def filter(self, edge_evidence):
        """
        Subclasses should implement

        :param edge_evidence:
        :type edge_evidence: dict
        :return: Copy of edge_evidence with filtered statements removed and str report
                 in a tuple (evidence, report)
        :rtype: tuple
        """
        raise NotImplementedError('subclasses should implement')


class SparserComplexStatementFilter(StatementFilter):
    """
    Filter out Complexes that only have evidence from Sparser
    The rationale is that the Sparser reading system tends to
    pick up spurious complexes, and if Sparser is the only one
    having reported a certain Complex, without evidence from
    any other source, then its quality is likely to be low.


    """
    def __init__(self):
        """
        Constructor

        """
        super(StatementFilter, self).__init__()

    def get_description(self):
        """
        Outputs description of what this filter does

        :return: Summary of what this filter does
        :rtype: str
        """
        return 'SparserComplexStatementFilter: Removes statements for ' \
               'Complexes with only sparser ' \
               'as source of evidence'

    def filter(self, edge_evidence):
        """
        Removes incorrect statements

        :param edge_evidence:
        :return:
        """
        filtered_e = copy.deepcopy(edge_evidence)
        report = ''
        stmts_to_remove = set()
        for stmtkey in filtered_e['stmts'].keys():
            stmt = filtered_e['stmts'][stmtkey]
            # we only filter if type is Complex
            if stmt['stmt_type'] != 'Complex':
                continue

            # we have more then one source, no filtering
            # needed
            if len(stmt['source_counts'].keys()) > 1:
                continue

            source = list(stmt['source_counts'].keys())[0]
            # if the source is sparser regardless of evidence
            # count, toss it
            if source == 'sparser':
                stmts_to_remove.add(stmtkey)

        for stmtkey in stmts_to_remove:
            del filtered_e['stmts'][stmtkey]
        removed_cnt = len(stmts_to_remove)

        if removed_cnt > 0:
            report += 'Removed ' + str(removed_cnt) + ' sparser complex statements\n'
        return filtered_e, report


class MedscanStatementFilter(StatementFilter):
    """
    Filter out statements that only have evidence from medscan

    This is because medscan data is private and cannot be
    seen. https://ndexbio.atlassian.net/browse/UD-2091


    """
    def __init__(self):
        """
        Constructor

        """
        super(StatementFilter, self).__init__()

    def get_description(self):
        """
        Outputs description of what this filter does

        :return: Summary of what this filter does
        :rtype: str
        """
        return 'MedscanStatementFilter: Removes statements with ' \
               'only medscan ' \
               'as source of evidence'

    def filter(self, edge_evidence):
        """
        Removes incorrect statements

        :param edge_evidence:
        :return:
        """
        filtered_e = copy.deepcopy(edge_evidence)
        report = ''
        stmts_to_remove = set()
        for stmtkey in filtered_e['stmts'].keys():
            stmt = filtered_e['stmts'][stmtkey]

            # we have more then one source, no filtering
            # needed
            if len(stmt['source_counts'].keys()) > 1:
                continue

            source = list(stmt['source_counts'].keys())[0]
            # if the source is sparser regardless of evidence
            # count, toss it
            if source == 'medscan':
                stmts_to_remove.add(stmtkey)

        for stmtkey in stmts_to_remove:
            del filtered_e['stmts'][stmtkey]
        removed_cnt = len(stmts_to_remove)

        if removed_cnt > 0:
            report += 'Removed ' + str(removed_cnt) + ' medscan statements\n'
        return filtered_e, report


class SingleReadingStatementFilter(StatementFilter):
    """
    Filter out statements that have a single evidence from a reading system
    The rationale is that if there is a single evidence but from a curated
    resource (e.g., Pathway Commons or SIGNOR), it’s fine to keep it. But
    if it’s from a single reading system, its error rate is fairly high.
    Once we have more than one evidence, even if it’s from a single reading
    system, the precision is in the 75-80% range.

    """
    def __init__(self):
        """
        Constructor

        :param curationlist: list of curations from INDRA
        :type list:
        """
        super(StatementFilter, self).__init__()

    def get_description(self):
        """
        Outputs description of what this filter does

        :return: Summary of what this filter does
        :rtype: str
        """
        return 'SingleReadingStatementFilter: Removes statements with only one evidence ' \
               'that originated ' \
               'from only a single reading system'

    def filter(self, edge_evidence):
        """
        Removes incorrect statements

        :param edge_evidence:
        :return:
        """
        filtered_e = copy.deepcopy(edge_evidence)
        report = ''
        stmts_to_remove = set()
        for stmtkey in filtered_e['stmts'].keys():
            stmt = filtered_e['stmts'][stmtkey]
            # we have more then one source we are good
            if len(stmt['source_counts'].keys()) > 1:
                continue

            source = list(stmt['source_counts'].keys())[0]
            # if the source is a reading source and only 1 piece
            # of evidence. Toss it
            if source in ['eidos', 'trips', 'reach', 'sparser',
                          'medscan', 'rlimsp', 'isi']:
                if stmt['source_counts'][source] <= 1:
                    stmts_to_remove.add(stmtkey)

        for stmtkey in stmts_to_remove:
            del filtered_e['stmts'][stmtkey]
        removed_cnt = len(stmts_to_remove)

        if removed_cnt > 0:
            report += 'Removed ' + str(removed_cnt) +\
                      ' statements with only single reading system source\n'
        return filtered_e, report


class IncorrectStatementFilter(StatementFilter):
    """
    Filters out statements that are incorrect going off this definition:

    .. code-block:: python

        Filter out curated incorrect statements
        This requires first fetching the set of curations from the INDRA DB REST API and
        then applying a filter that removes incorrect statements based on those curations

        [{'curator': 'd6587e2bdde71e07',
          'date': 'Thu, 29 Nov 2018 18:00:08 GMT',
          'ev_json': None,
          'id': 196,
          'pa_hash': -31337470416928082,
          'pa_json': None,
          'source': 'DB REST API',
          'source_hash': -6988195563234119487,
          'tag': 'grounding',
          'text': '[ROS] -> MESH:D017382'},
         {'curator': 'd6587e2bdde71e07',
          'date': 'Tue, 04 Dec 2018 15:28:35 GMT',
          'ev_json': None,
          'id': 197,
          'pa_hash': 10615109383390843,
          'pa_json': None,
          'source': 'DB REST API',
          'source_hash': 5357869769322938035,
          'tag': 'grounding',
          'text': '[erbB] -> FPLX:ERBB'}]

        The important point here is to look at the "pa_hash" which corresponds
        to an INDRA Statement hash (that may be tied to one of the edges in
        your network). Note that each network edge can have multiple INDRA
        Statements associated with it and not all of them may be incorrect,
        one has to apply these curations at the level of individual Statements,
        before generating NDEx network edges.

        Another important point is to take into account the "tag" for each
        curation. For this, we need to note that each curation applies to a
        specific evidence for a statement, and not the statement as a whole.
        A "correct" tag means that the given evidence correctly supports the
        given statement.
        A "hypothesis" tag means that the evidence text is phrased as a
        hypothesis that, if taken as an assertion, supports the statement.
        Since this is often a minor issue, we tend to include these as correct.
        An "act_vs_amt" tag means that a statement about catalytic activation
        was interpreted as an amount regulation or vice versa. For the kind
        of networks we are building here, we consider this a minor issue and
        therefore include these as correct.
        Every other tag (e.g., "grounding", "wrong_relation", "polarity",
        etc.) mean that the evidence doesn't correctly support the Statement.
        Given these tags, we use the following logic to filter statements:
        If a statement only has incorrect curations and no correct curations,
        it is overall incorrect and needs to be filtered out
        If a statement has any correct curations even if it also has some
        incorrect curations, it is overall correct and should be kept
        All other statements can be kept
    """
    def __init__(self, curationlist=None):
        """
        Constructor

        :param curationlist: list of curations from INDRA
        :type list:
        """
        super(StatementFilter, self).__init__()
        self._curations = {}
        if curationlist is not None:
            for entry in curationlist:
                pa_hash = entry['pa_hash']
                if pa_hash not in self._curations:
                    self._curations[pa_hash] = []
                self._curations[pa_hash].append(entry)

    def get_description(self):
        """
        Outputs description of what this filter does

        :return: Summary of what this filter does
        :rtype: str
        """
        return 'IncorrectStatementFilter: Removes statements that lack ' \
               'good curations'

    def _is_at_least_one_curation_correct(self, curations=None):
        """
        check all the curations matching that hash
        remove statement if all curations do not have
        any of following tags: correct, hypothesis, act_vs_amt
        but keep if at least one does

        :param curations:
        :return:
        """
        for curation in curations:
            if curation['tag'] in ['correct', 'hypothesis', 'act_vs_amt']:
                return True
        return False

    def filter(self, edge_evidence):
        """
        Removes incorrect statements

        :param edge_evidence:
        :return:
        """
        filtered_e = copy.deepcopy(edge_evidence)
        report = ''
        stmts_to_remove = set()
        for stmtkey in filtered_e['stmts'].keys():
            intstmtkey = int(stmtkey)
            if intstmtkey not in self._curations:
                continue
            curations = self._curations[intstmtkey]
            if self._is_at_least_one_curation_correct(curations=curations) is False:
                stmts_to_remove.add(stmtkey)
                continue

        for stmtkey in stmts_to_remove:
            del filtered_e['stmts'][stmtkey]
        removed_cnt = len(stmts_to_remove)
        if removed_cnt > 0:
            report += 'Removed ' + str(removed_cnt) + ' statements that lacked good curations\n'
        return filtered_e, report


class SelfLoopStatementFilter(StatementFilter):
    """
    Filters out statements that are self loops, or
    where source and target are the same

    """
    def __init__(self):
        """
        Constructor
        """
        super(StatementFilter, self).__init__()

    def get_description(self):
        """
        Outputs description of what this filter does

        :return: Summary of what this filter does
        :rtype: str
        """
        return 'SelfLoopStatementFilter: Iterates through evidence ' \
               'statements and removes ' \
               'any where source and target are the same'

    def filter(self, edge_evidence):
        """
        Removes self loop statements
        following this rule from INDRA filtering guide:

        .. code-block:: python

            Filter out self-loops i.e., Statements all of whose participants are a single gene
               * These are not very interesting and are often the result of reading errors.


        :param edge_evidence:
        :return:
        """
        filtered_e = copy.deepcopy(edge_evidence)
        entity_name_set = set()
        report = ''
        removed_cnt = 0
        stmts_to_remove = set()
        for entity in edge_evidence['edge']:
            entity_name_set.add(entity['name'])

        if len(entity_name_set) <= 1:
            removed_cnt = len(filtered_e['stmts'])
            filtered_e['stmts'] = {}

        for stmtkey in filtered_e['stmts'].keys():
            stmt = filtered_e['stmts'][stmtkey]
            english_clean = re.sub('\.$', '', stmt['english'])
            split_english = english_clean.split()
            if split_english[0] == split_english[2]:
                stmts_to_remove.add(stmtkey)

        if len(stmts_to_remove) > 0:
            for stmtkey in stmts_to_remove:
                del filtered_e['stmts'][stmtkey]
            removed_cnt = len(stmts_to_remove)
        if removed_cnt > 0:
            report += 'Removed ' + str(removed_cnt) + ' self loop statements\n'
        return filtered_e, report


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
                 default_browser_target=DEFAULT_BROWSER_TARGET,
                 stmtfilters=None):
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

        self._stmtfilters = stmtfilters


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

    def _filter_statements(self, edge_evidence=None):
        """
        Filters single **edge_evidence** parameter passed in following these rules:

        * Filter out curated incorrect statements



        Example Edge evidence:

        .. code-block:: python

            {'edge': [{'name': 'SDC4',
                       'namespace': 'HGNC',
                       'identifier': '10661',
                       'lookup': 'https://identifiers.org/hgnc:10661',
                       'sign': None},
                      {'name': 'FGFR1',
                       'namespace': 'HGNC',
                       'identifier': '3688',
                       'lookup': 'https://identifiers.org/hgnc:3688',
                       'sign': None}],
              'stmts': {'-18861998898188963': {'stmt_type': 'Complex',
                                               'evidence_count': 1,
                                               'stmt_hash': -18861998898188963,
                                               'source_counts': {'sparser': 1},
                                               'belief': 0.65,
                                               'curated': False,
                                               'english': 'SDC4 binds FGFR1.',
                                               'weight': 0.4307829160924542,
                                               'residue': None,
                                               'position': None,
                                               'initial_sign': None,
                                               'db_url_hash': 'https://db.indra.bio/statements/from_hash/-18861998898188963?format=html&ev_limit=10'},
                         '-5411687829567042': {'stmt_type': 'Complex',
                                               'evidence_count': 2,
                                               'stmt_hash': -5411687829567042,
                                               'source_counts': {'sparser': 2},
                                               'belief': 0.86,
                                               'curated': False,
                                               'english': 'SDC4 binds FGFR1.',
                                               'weight': 0.15082288973458366,
                                               'residue': None, 'position': None,
                                               'initial_sign': None,
                                               'db_url_hash': 'https://db.indra.bio/statements/from_hash/-5411687829567042?format=html&ev_limit=10'},
                         '15679352643449856': {'stmt_type': 'Activation',
                                               'evidence_count': 1,
                                               'stmt_hash': 15679352643449856,
                                               'source_counts': {'medscan': 1},
                                               'belief': 0.65,
                                               'curated': False,
                                               'english': 'SDC4 activates FGFR1.',
                                               'weight': 0.4307829160924542,
                                               'residue': None,
                                               'position': None,
                                               'initial_sign': None,
                                               'db_url_hash': 'https://db.indra.bio/statements/from_hash/15679352643449856?format=html&ev_limit=10'}},
                 'belief': 0.98285,
                 'weight': 0.01729876457832946,
                 'db_url_edge': 'https://db.indra.bio/statements/from_agents?subject=10661@HGNC&object=3688@HGNC&ev_limit=10&format=html',
                 'url_by_type': {'Complex': 'https://db.indra.bio/statements/from_agents?subject=10661@HGNC&object=3688@HGNC&ev_limit=10&format=html&type=Complex',
                                 'Activation': 'https://db.indra.bio/statements/from_agents?subject=10661@HGNC&object=3688@HGNC&ev_limit=10&format=html&type=Activation'}
            }


        :param net_cx: Network (not sure if i need this)
        :type net_cx: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :param edge_evidence: Raw edge evidence as dict from INDRA
        :type edge_evidence: dict
        :param curations: Curation data from INDRA
        :type curations: dict
        :return:
        """
        if self._stmtfilters is None or len(self._stmtfilters) == 0:
            return edge_evidence
        filtered_e = edge_evidence
        for sfilter in self._stmtfilters:
            filtered_e, report = sfilter.filter(filtered_e)
        return filtered_e

    def annotate_network(self, net_cx=None, indraresult=None,
                         netprefix='INDRA annotated - ',
                         remove_orig_edges=False,
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

        for raw_edge_evidence in result['edges']:
            edge_evidence = self._filter_statements(raw_edge_evidence)

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

        param_str = {'Remove Original Edges': remove_orig_edges}

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
            html.escape(thesubject) + '&object=' + html.escape(theobject) + '&type=' + html.escape(thetype) +\
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
            html.escape(theagent0) + '&agent1=' + html.escape(theagent1) +\
            '&format=html&expand_all=false'

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
