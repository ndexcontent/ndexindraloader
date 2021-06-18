#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `indra` package."""

import os
import json
import tempfile
import shutil

import unittest
from unittest.mock import MagicMock
from ndex2.nice_cx_network import NiceCXNetwork
import ndex2
from ndexindraloader.exceptions import NDExIndraLoaderError
from ndexindraloader.indra import Indra
from ndexindraloader import indra


class TestIndra(unittest.TestCase):
    """Tests for `indra` package."""

    EPHB_FORWARDING_CX = os.path.join(os.path.dirname(__file__), 'data',
                                      '01c81f4a-6192-11e5-8ac5-06603eb7f'
                                      '303.cx')

    EPHB_FORWARDING_INDRA = os.path.join(os.path.dirname(__file__), 'data',
                                         '01c81f4a-6192-11e5-8ac5-06603eb7f'
                                         '303.json')
    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_get_members_of_family_node(self):
        net = NiceCXNetwork()
        node_one = net.create_node('node1')
        self.assertEqual([], indra.get_members_of_family_node(net_cx=net,
                                                              node_id=node_one))

        # try where member attribute is not a list
        net.set_node_attribute(node=node_one, attribute_name='member', values='hi')
        self.assertEqual([], indra.get_members_of_family_node(net_cx=net,
                                                              node_id=node_one))

        # try with valid list
        net.set_node_attribute(node=node_one, attribute_name='member',
                               values=['hgnc.symbol:gene1',
                                       'gene2'],
                               type='list_of_string', overwrite=True)

        res = indra.get_members_of_family_node(net_cx=net,
                                               node_id=node_one)
        self.assertEqual(2, len(res))
        self.assertTrue('gene1' in res)
        self.assertTrue('gene2' in res)

    def test_is_family_node(self):
        net = NiceCXNetwork()
        node_one = net.create_node('node1')
        self.assertFalse(indra.is_family_node(net_cx=net, node_id=node_one))
        net.set_node_attribute(node=node_one, attribute_name='member', values='hi')
        self.assertFalse(indra.is_family_node(net_cx=net, node_id=node_one))
        net.set_node_attribute(node=node_one, attribute_name='member', values=[],
                               type='list_of_string', overwrite=True)
        self.assertFalse(indra.is_family_node(net_cx=net, node_id=node_one))
        net.set_node_attribute(node=node_one, attribute_name='member', values=['hi'],
                               type='list_of_string', overwrite=True)
        self.assertTrue(indra.is_family_node(net_cx=net, node_id=node_one))

    def test_get_node_name_to_id_dict(self):
        net = NiceCXNetwork()

        node_one = net.create_node('node1')
        node_two = net.create_node('node2')
        node_three = net.create_node('node3')
        node_four = net.create_node('node4')

        net.set_node_attribute(node=node_four, attribute_name='member',
                               values=['hgnc.symbol:gene1',
                                       'gene2'],
                               type='list_of_string', overwrite=True)

        node_dict = indra.get_node_name_to_id_dict(net_cx=net)
        self.assertEqual(6, len(node_dict))

        self.assertEqual(node_one, node_dict['node1'])
        self.assertEqual(node_two, node_dict['node2'])
        self.assertEqual(node_three, node_dict['node3'])
        self.assertEqual(node_four, node_dict['node4'])
        self.assertEqual(node_four, node_dict['gene1'])
        self.assertEqual(node_four, node_dict['gene2'])

    def test_get_node_id_to_name_dict(self):
        net = NiceCXNetwork()

        node_one = net.create_node('node1')
        node_two = net.create_node('node2')
        node_three = net.create_node('node3')
        node_four = net.create_node('node4')

        node_dict = indra.get_node_id_to_name_dict(net_cx=net)
        self.assertEqual(4, len(node_dict))

        self.assertEqual('node1', node_dict[node_one])
        self.assertEqual('node2', node_dict[node_two])
        self.assertEqual('node3', node_dict[node_three])
        self.assertEqual('node4', node_dict[node_four])

    def test_remove_edge(self):
        net = NiceCXNetwork()
        node_one = net.create_node('node1')
        node_two = net.create_node('node2')
        e_one = net.create_edge(edge_source=node_one, edge_target=node_two)
        net.set_edge_attribute(e_one, 'foo', values='somedata')
        e_two = net.create_edge(edge_source=node_two, edge_target=node_one)
        self.assertEqual(2, len(net.get_edges()))
        indra.remove_edge(net_cx=net, edge_id=e_one)
        self.assertEqual(1, len(net.get_edges()))
        indra.remove_edge(net_cx=net, edge_id=e_two)
        self.assertEqual(0, len(net.get_edges()))

    def test_add_source_to_existing_edges_sourceval_is_none(self):
        net = NiceCXNetwork()
        node_one = net.create_node('node1')
        node_two = net.create_node('node2')
        e_one = net.create_edge(edge_source=node_one, edge_target=node_two)
        e_two = net.create_edge(edge_source=node_two, edge_target=node_one)

        indraobj = Indra()
        indraobj._add_source_to_existing_edges(net_cx=net, source_value=None)

        e_attr = net.get_edge_attribute(e_one, Indra.SOURCE)
        self.assertEqual((None, None), e_attr)

        e_attr = net.get_edge_attribute(e_two, Indra.SOURCE)
        self.assertEqual((None, None), e_attr)

    def test_add_source_to_existing_edges(self):
        net = NiceCXNetwork()
        node_one = net.create_node('node1')
        node_two = net.create_node('node2')
        e_one = net.create_edge(edge_source=node_one, edge_target=node_two)
        e_two = net.create_edge(edge_source=node_two, edge_target=node_one)

        indraobj = Indra()
        indraobj._add_source_to_existing_edges(net_cx=net, source_value='some source')

        e_attr = net.get_edge_attribute(e_one, Indra.SOURCE)
        self.assertEqual('some source', e_attr['v'])

        e_attr = net.get_edge_attribute(e_two, Indra.SOURCE)
        self.assertEqual('some source', e_attr['v'])

    def test_remove_original_edges(self):
        net = NiceCXNetwork()
        node_one = net.create_node('node1')
        node_two = net.create_node('node2')
        e_one = net.create_edge(edge_source=node_one, edge_target=node_two)
        net.set_edge_attribute(e_one, 'foo', values='somedata')
        net.create_edge(edge_source=node_two, edge_target=node_one)
        indraobj = Indra()
        indraobj._remove_original_edges(net_cx=net)
        self.assertEqual(2, len(net.get_edges()))

        indraobj._remove_original_edges(net_cx=net, remove_orig_edges=False)
        self.assertEqual(2, len(net.get_edges()))

        indraobj._remove_original_edges(net_cx=net, remove_orig_edges=True)
        self.assertEqual(0, len(net.get_edges()))

    def test_get_indra_query_dict(self):
        net = NiceCXNetwork()
        net.create_node('node1')
        node_two = net.create_node('node2')

        net.set_node_attribute(node=node_two, attribute_name='member',
                               values=['hgnc.symbol:gene1',
                                       'gene2'],
                               type='list_of_string', overwrite=True)

        indraobj = Indra()
        res = indraobj._get_indra_query_dict(net_cx=net)
        self.assertTrue('nodes' in res)
        self.assertEqual(4, len(res['nodes']))

        node_dict = {}
        for entry in res['nodes']:
            node_dict[entry['name']] = entry
        self.assertEqual({'name': 'node1',
                          'namespace': '0',
                          'identifier': '0',
                          'lookup': None}, node_dict['node1'])
        self.assertEqual({'name': 'node2',
                          'namespace': '0',
                          'identifier': '0',
                          'lookup': None}, node_dict['node2'])
        self.assertEqual({'name': 'gene1',
                          'namespace': '0',
                          'identifier': '0',
                          'lookup': None}, node_dict['gene1'])
        self.assertEqual({'name': 'gene2',
                          'namespace': '0',
                          'identifier': '0',
                          'lookup': None}, node_dict['gene2'])

    def test_get_source_target_key(self):
        indraobj = Indra()
        res = indraobj._get_source_target_key(src_node_id=0, target_node_id=1)
        self.assertEqual(('0_1', False), res)

        res = indraobj._get_source_target_key(src_node_id=0, target_node_id=0)
        self.assertEqual(('0_0', False), res)

        res = indraobj._get_source_target_key(src_node_id=1, target_node_id=0)
        self.assertEqual(('0_1', True), res)

    def test_annotate_with_ephb_network_and_cached_indra_res(self):
        net = ndex2.create_nice_cx_from_file(TestIndra.EPHB_FORWARDING_CX)

        with open(TestIndra.EPHB_FORWARDING_INDRA, 'r') as f:
            indrares = json.load(f)

        indraobj = Indra()
        res_cx, result = indraobj.annotate_network(net_cx=net,
                                                   indraresult=indrares,
                                                   source_value='NCI PID')
        self.assertIsNotNone(res_cx)
        self.assertIsNotNone(result)
        self.assertEqual('INDRA annotated - EPHB forward signaling',
                         res_cx.get_name())
        self.assertEqual(42, len(res_cx.get_nodes()))
        self.assertEqual(503, len(res_cx.get_edges()))

        name_to_id_dict = indra.get_node_name_to_id_dict(res_cx)

        rap1a = name_to_id_dict['RAP1A']
        rap1b = name_to_id_dict['RAP1B']

        rap_edge = None
        for edge_id, edge_obj in res_cx.get_edges():
            if edge_obj['s'] == rap1a and edge_obj['t'] == rap1b:
                rap_edge = edge_id
                self.assertEqual('interacts with', edge_obj['i'])
                break

        self.assertIsNotNone(rap_edge)
        src_to_tar = res_cx.get_edge_attribute(rap_edge, 'SOURCE => TARGET')
        self.assertEqual(2, len(src_to_tar['v']))

        tar_to_src = res_cx.get_edge_attribute(rap_edge, 'TARGET => SOURCE')
        self.assertEqual(2, len(tar_to_src['v']))

        src_tar = res_cx.get_edge_attribute(rap_edge, 'SOURCE - TARGET')
        self.assertEqual(1, len(src_tar['v']))










