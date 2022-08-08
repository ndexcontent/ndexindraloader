#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `MedscanStatementFilter` package."""

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
from ndexindraloader.indra import MedscanStatementFilter


class TestMedscanStatementFilter(unittest.TestCase):
    """Tests for Sparser package."""

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

    def test_description(self):
        filter = MedscanStatementFilter()
        self.assertEqual('MedscanStatementFilter: '
                         'Removes statements with only medscan ' +
                         'as source of evidence', filter.get_description())


    def test_filter_remove_matching_complex(self):
        filter = MedscanStatementFilter()

        edge_evidence = {'stmts': {'1': {'stmt_type': 'something',
                                         'source_counts': {'medscan': 2}}}}
        res, report = filter.filter(edge_evidence)
        self.assertEqual('Removed 1 medscan statements\n', report)
        self.assertEqual({'stmts': {}}, res)

    def test_filter_multiple_sources_complex(self):
        filter = MedscanStatementFilter()

        edge_evidence = {'stmts': {'1': {'stmt_type': 'Complex',
                                         'source_counts': {'sparser': 2,
                                                           'medscan': 1}}}}
        res, report = filter.filter(edge_evidence)
        self.assertEqual('', report)
        self.assertEqual(edge_evidence, res)

    def test_filter_remove_some_statements(self):
        filter = MedscanStatementFilter()

        edge_evidence = {'stmts': {'1': {'stmt_type': 'Complex',
                                         'source_counts': {'sparser': 2,
                                                           'medscan': 1}},
                                   '2': {'stmt_type': 'x',
                                         'source_counts': {'medscan': 1}},
                                   '3': {'stmt_type': 'Complex',
                                         'source_counts': {'eidos': 1}},
                                   '4': {'stmt_type': 'y',
                                         'source_counts': {'medscan': 50}}
                                   }}
        res, report = filter.filter(edge_evidence)

        self.assertEqual('Removed 2 medscan statements\n', report)
        del edge_evidence['stmts']['2']
        del edge_evidence['stmts']['4']

        self.assertEqual(edge_evidence, res)

    def test_filter_on_ephb(self):
        filter = MedscanStatementFilter()
        with open(TestMedscanStatementFilter.EPHB_FORWARDING_INDRA,
                  'r') as f:
            indrares = json.load(f)
        for raw_edge_evidence in indrares['edges']:
            edge_evidence, report = filter.filter(raw_edge_evidence)
            if len(report) == 0:
                self.assertEqual(raw_edge_evidence, edge_evidence)
            else:
                self.assertNotEqual(raw_edge_evidence, edge_evidence)

















