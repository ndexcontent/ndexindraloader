#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `IncorrectStatementFilter` package."""

import os
import json


import unittest
from ndexindraloader.indra import IncorrectStatementFilter


class TestIncorrectStatementFilter(unittest.TestCase):
    """Tests for Sparser package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_description(self):
        filter = IncorrectStatementFilter()
        self.assertEqual('IncorrectStatementFilter: Removes statements '
                         'that lack ' +
                         'good curations',
                         filter.get_description())

    def test_is_at_least_one_curation_correct(self):
        # empty curations
        filter = IncorrectStatementFilter()
        self.assertFalse(filter._is_at_least_one_curation_correct([]))

        # one with incorrect tag
        self.assertFalse(filter._is_at_least_one_curation_correct([{'tag': 'grounding'}]))

        # one with correct tag
        for gtag in ['correct', 'hypothesis', 'act_vs_amt']:
            self.assertTrue(filter._is_at_least_one_curation_correct([{'tag': gtag}]))

        # multiple with only one correct tag
        self.assertTrue(filter._is_at_least_one_curation_correct([{'tag': 'bad'},
                                                                  {'tag': 'act_vs_amt'},
                                                                  {'tag': 'uhoh'}]))

    def test_filter_no_matching_curations(self):
        filter = IncorrectStatementFilter()

        edge_evidence = {'stmts': {'1': {'stmt_type': 'Activation',
                                         'source_counts': {'sparser': 1,
                                                           'eidos': 1}}}}
        res, report = filter.filter(edge_evidence)
        self.assertEqual('', report)
        self.assertEqual(edge_evidence, res)

    def test_filter_curations_good(self):
        curations = [{'pa_hash': 1,
                      'tag': 'correct'},
                     {'pa_hash': 1,
                      'tag': 'hypothesis'},
                     {'pa_hash': 1,
                      'tag': 'act_vs_amt'},
                     ]
        filter = IncorrectStatementFilter(curationlist=curations)

        edge_evidence = {'stmts': {'1': {'stmt_type': 'Activation',
                                         'source_counts': {'sparser': 1,
                                                           'eidos': 1}}}}
        res, report = filter.filter(edge_evidence)
        self.assertEqual('', report)
        self.assertEqual(edge_evidence, res)

    def test_filter_curations_bad(self):
        curations = [{'pa_hash': 1,
                      'tag': 'grounding'},
                     {'pa_hash': 1,
                      'tag': 'asdf'},
                     {'pa_hash': 1,
                      'tag': 'something'},
                     ]
        filter = IncorrectStatementFilter(curationlist=curations)

        edge_evidence = {'stmts': {'1': {'stmt_type': 'Activation',
                                         'source_counts': {'sparser': 1,
                                                           'eidos': 1}}}}
        res, report = filter.filter(edge_evidence)
        self.assertEqual('Removed 1 statements that lacked good '
                         'curations\n', report)
        self.assertEqual({'stmts': {}}, res)

    def test_filter_one_good_one_bad_stmt(self):
        curations = [{'pa_hash': 1,
                      'tag': 'grounding'},
                     {'pa_hash': 1,
                      'tag': 'asdf'},
                     {'pa_hash': 1,
                      'tag': 'something'},
                     {'pa_hash': 2,
                                'tag': 'correct'}
                     ]
        filter = IncorrectStatementFilter(curationlist=curations)

        edge_evidence = {'stmts': {'1': {'stmt_type': 'Activation',
                                         'source_counts': {'sparser': 1,
                                                           'eidos': 1}},
                                   '2': {'stmt_type': 'Activation',
                                         'source_counts': {'sparser': 1,
                                         'eidos': 1}}}}

        res, report = filter.filter(edge_evidence)
        self.assertEqual('Removed 1 statements that lacked good '
                         'curations\n', report)
        del edge_evidence['stmts']['1']
        self.assertEqual(edge_evidence, res)
















