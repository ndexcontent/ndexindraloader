#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `SelfLoopStatementFilter` package."""

import os
import json


import unittest
from ndexindraloader.indra import SelfLoopStatementFilter


class TestSelfLoopStatementFilter(unittest.TestCase):
    """Tests for Sparser package."""

    EPHB_FORWARDING_INDRA = os.path.join(os.path.dirname(__file__), 'data',
                                         '01c81f4a-6192-11e5-8ac5-06603eb7f'
                                         '303.json')

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_description(self):
        filter = SelfLoopStatementFilter()
        self.assertEqual('SelfLoopStatementFilter: Iterates through ' +
                         'evidence statements and removes ' +
                         'any where source and target are the same',
                         filter.get_description())

    def test_filter_where_only_one_entry_in_edge(self):
        filter = SelfLoopStatementFilter()

        edge_evidence = {'edge': [{'name': 'foo'}],
                         'stmts': {'hi': 'there'}}

        res, report = filter.filter(edge_evidence)
        self.assertEqual('Removed 1 self loop statements\n', report)
        edge_evidence['stmts'] = {}
        self.assertEqual(edge_evidence, res)

    def test_filter_where_stmt_points_to_self(self):
        filter = SelfLoopStatementFilter()

        edge_evidence = {'edge': [{'name': 'foo'},
                                  {'name': 'bar'}],
                         'stmts': {'1': {'english': 'foo binds foo.'}}}

        res, report = filter.filter(edge_evidence)
        self.assertEqual('Removed 1 self loop statements\n', report)
        edge_evidence['stmts'] = {}
        self.assertEqual(edge_evidence, res)

    def test_filter_where_one_stmt_points_to_self(self):
        filter = SelfLoopStatementFilter()

        edge_evidence = {'edge': [{'name': 'foo'},
                                  {'name': 'bar'}],
                         'stmts': {'1': {'english': 'foo binds foo.'},
                                   '2': {'english': 'foo binds bar.'}}}

        res, report = filter.filter(edge_evidence)
        self.assertEqual('Removed 1 self loop statements\n', report)
        del edge_evidence['stmts']['1']
        self.assertEqual(edge_evidence, res)

    def test_filter_where_all_stmts_good(self):
        filter = SelfLoopStatementFilter()

        edge_evidence = {'edge': [{'name': 'foo'},
                                  {'name': 'bar'}],
                         'stmts': {'1': {'english': 'foo abc bar.'},
                                   '2': {'english': 'foo binds bar.'}}}

        res, report = filter.filter(edge_evidence)
        self.assertEqual('', report)
        self.assertEqual(edge_evidence, res)

    def test_filter_on_ephb(self):
        filter = SelfLoopStatementFilter()
        with open(TestSelfLoopStatementFilter.EPHB_FORWARDING_INDRA,
                  'r') as f:
            indrares = json.load(f)
        for raw_edge_evidence in indrares['edges']:
            edge_evidence, report = filter.filter(raw_edge_evidence)
            if len(report) == 0:
                self.assertEqual(raw_edge_evidence, edge_evidence)
            else:
                self.assertNotEqual(raw_edge_evidence, edge_evidence)

















