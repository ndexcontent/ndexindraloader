#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `SingleReadingStatementFilter` package."""

import os
import json


import unittest
from ndexindraloader.indra import SingleReadingStatementFilter


class TestSingleReadingStatementFilter(unittest.TestCase):
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
        filter = SingleReadingStatementFilter()
        self.assertEqual('SingleReadingStatementFilter: Removes statements ' +
                         'with only one evidence ' +
                         'that originated ' +
                         'from only a single reading system',
                         filter.get_description())

    def test_filter_multiple_sources(self):
        filter = SingleReadingStatementFilter()

        edge_evidence = {'stmts': {'1': {'stmt_type': 'Activation',
                                         'source_counts': {'sparser': 1,
                                                           'eidos': 1}}}}
        res, report = filter.filter(edge_evidence)
        self.assertEqual('', report)
        self.assertEqual(edge_evidence, res)

    def test_filter_remove_matching_singlereadingsource(self):
        filter = SingleReadingStatementFilter()

        edge_evidence = {'stmts': {'1': {'stmt_type': 'Complex',
                                         'source_counts': {'sparser': 1}}}}
        res, report = filter.filter(edge_evidence)
        self.assertEqual('Removed 1 statements with only single '
                         'reading system source\n', report)
        self.assertEqual({'stmts': {}}, res)

    def test_filter_all_reading_sources(self):
        filter = SingleReadingStatementFilter()
        for src in ['eidos', 'trips', 'reach','sparser',
                    'medscan', 'rlimsp', 'isi']:
            edge_evidence = {'stmts': {'1': {'stmt_type': 'foo',
                                             'source_counts': {src: 1}}}}
            res, report = filter.filter(edge_evidence)
            self.assertEqual('Removed 1 statements with only single '
                             'reading system source\n', report)
            self.assertEqual({'stmts': {}}, res)

    def test_filter_multiple_sources(self):
        filter = SingleReadingStatementFilter()

        edge_evidence = {'stmts': {'1': {'stmt_type': 'Complex',
                                         'source_counts': {'sparser': 1,
                                                           'medscan': 1}}}}
        res, report = filter.filter(edge_evidence)
        self.assertEqual('', report)
        self.assertEqual(edge_evidence, res)

    def test_filter_remove_some_statements(self):
        filter = SingleReadingStatementFilter()

        edge_evidence = {'stmts': {'1': {'stmt_type': 'Complex',
                                         'source_counts': {'sparser': 2,
                                                           'medscan': 1}},
                                   '2': {'stmt_type': 'Complex',
                                         'source_counts': {'sparser': 1}},
                                   '3': {'stmt_type': 'Complex',
                                         'source_counts': {'eidos': 1}},
                                   '4': {'stmt_type': 'Complex',
                                         'source_counts': {'sparser': 50}}
                                   }}
        res, report = filter.filter(edge_evidence)

        self.assertEqual('Removed 2 statements with only single '
                         'reading system source\n', report)
        del edge_evidence['stmts']['2']
        del edge_evidence['stmts']['3']

        self.assertEqual(edge_evidence, res)

    def test_filter_on_ephb(self):
        filter = SingleReadingStatementFilter()
        with open(TestSingleReadingStatementFilter.EPHB_FORWARDING_INDRA,
                  'r') as f:
            indrares = json.load(f)
        for raw_edge_evidence in indrares['edges']:
            edge_evidence, report = filter.filter(raw_edge_evidence)
            if len(report) == 0:
                self.assertEqual(raw_edge_evidence, edge_evidence)
            else:
                self.assertNotEqual(raw_edge_evidence, edge_evidence)

















