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
from ndexindraloader.ndexloadindra import NDExIndraLoader
from ndexindraloader.exceptions import NDExIndraLoaderError
from ndexindraloader.indra import Indra


class TestIndra(unittest.TestCase):
    """Tests for `indra` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_add_source_to_existing_edges_sourceval_is_none(self):
        net = NiceCXNetwork()
        node_one = net.create_node('node1')
        node_two = net.create_node('node2')
        e_one = net.create_edge(edge_source=node_one, edge_target=node_two)
        e_two = net.create_edge(edge_source=node_two, edge_target=node_one)

        indra = Indra()
        indra._add_source_to_existing_edges(net_cx=net, source_value=None)

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

        indra = Indra()
        indra._add_source_to_existing_edges(net_cx=net, source_value='some source')

        e_attr = net.get_edge_attribute(e_one, Indra.SOURCE)
        self.assertEqual('some source', e_attr['v'])

        e_attr = net.get_edge_attribute(e_two, Indra.SOURCE)
        self.assertEqual('some source', e_attr['v'])


