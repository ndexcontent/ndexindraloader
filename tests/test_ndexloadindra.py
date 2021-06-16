#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `ndexindraloader` package."""

import os
import json
import tempfile
import shutil

import unittest
from unittest.mock import MagicMock
from ndex2.nice_cx_network import NiceCXNetwork
from ndexutil.config import NDExUtilConfig
from ndexindraloader import ndexloadindra
from ndexindraloader.ndexloadindra import NDExIndraLoader
from ndexindraloader.exceptions import NDExIndraLoaderError


class TestNdexindraloader(unittest.TestCase):
    """Tests for `ndexindraloader` package."""

    def setUp(self):
        """Set up test fixtures, if any."""

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_parse_arguments(self):
        """Tests parse arguments"""
        res = ndexloadindra._parse_arguments('hi', ['input'])

        self.assertEqual(res.profile, 'ndexindraloader')
        self.assertEqual(res.verbose, 1)
        self.assertEqual(res.logconf, None)
        self.assertEqual(res.conf, None)

        someargs = ['-vv', '--conf', 'foo', '--logconf', 'hi',
                    '--profile', 'myprofy', 'inputdata']
        res = ndexloadindra._parse_arguments('hi', someargs)

        self.assertEqual(res.profile, 'myprofy')
        self.assertEqual(res.verbose, 3)
        self.assertEqual(res.logconf, 'hi')
        self.assertEqual(res.conf, 'foo')
        self.assertEqual(res.input, 'inputdata')

    def test_setup_logging(self):
        """ Tests logging setup"""
        try:
            ndexloadindra._setup_logging(None)
            self.fail('Expected AttributeError')
        except AttributeError:
            pass

        # args.logconf is None
        res = ndexloadindra._parse_arguments('hi', ['input'])
        ndexloadindra._setup_logging(res)

        # args.logconf set to a file
        try:
            temp_dir = tempfile.mkdtemp()

            logfile = os.path.join(temp_dir, 'log.conf')
            with open(logfile, 'w') as f:
                f.write("""[loggers]
keys=root

[handlers]
keys=stream_handler

[formatters]
keys=formatter

[logger_root]
level=DEBUG
handlers=stream_handler

[handler_stream_handler]
class=StreamHandler
level=DEBUG
formatter=formatter
args=(sys.stderr,)

[formatter_formatter]
format=%(asctime)s %(name)-12s %(levelname)-8s %(message)s""")

            res = ndexloadindra._parse_arguments('hi', ['--logconf',
                                                        logfile, 'input'])
            ndexloadindra._setup_logging(res)

        finally:
            shutil.rmtree(temp_dir)

    def test_main(self):
        """Tests main function"""

        # try where loading config is successful
        try:
            temp_dir = tempfile.mkdtemp()
            confile = os.path.join(temp_dir, 'some.conf')
            with open(confile, 'w') as f:
                f.write("""[hi]
                {user} = bob
                {pw} = smith
                {server} = dev.ndexbio.org
                {destuser} = destbob
                {destpass} = destpass
                {destserver} = test.ndexbio.org""".format(user=NDExUtilConfig.USER,
                                                          pw=NDExUtilConfig.PASSWORD,
                                                          server=NDExUtilConfig.SERVER,
                                                          destuser=NDExIndraLoader.DEST_USER,
                                                          destpass=NDExIndraLoader.DEST_PASSWORD,
                                                          destserver=NDExIndraLoader.DEST_SERVER))
            res = ndexloadindra.main(['myprog.py',
                                      '--conf',
                                      confile, '--profile',
                                      'hi', 'input'])
            self.assertEqual(res, 2)
        finally:
            shutil.rmtree(temp_dir)

    def test_get_next_network_from_input_invalid(self):

        try:
            temp_dir = tempfile.mkdtemp()
            nonexistantfile = os.path.join(temp_dir, 'doesnotexist')

            # what is interesting here is if i omit a,b,c= this method
            # fails raise the exception
            a, b, c = ndexloadindra.get_next_network_from_input(nonexistantfile)
            self.fail('Expected NDExIndraLoaderError')
        except NDExIndraLoaderError as e:
            self.assertEqual('Input must be a CX file ending with .cx or '
                             'a file with NDEx Network UUID one per line',
                             str(e))
        finally:
            shutil.rmtree(temp_dir)

    def test_get_next_network_from_input_single_cxfile(self):

        try:
            temp_dir = tempfile.mkdtemp()
            mynet = NiceCXNetwork()

            mynet.create_node('node1')
            outcxfile = os.path.join(temp_dir, 'foo.cx')
            with open(outcxfile, 'w') as f:
                json.dump(mynet.to_cx(), f)
                f.flush()

            for net_cx, file_name, cache_file in ndexloadindra.get_next_network_from_input(outcxfile):
                self.assertEqual(None, cache_file)
                self.assertEqual('foo.cx', file_name)
                self.assertEqual(1, len(net_cx.get_nodes()))
        finally:
            shutil.rmtree(temp_dir)

    def test_get_next_network_from_input_single_cxfile_withcache(self):

        try:
            temp_dir = tempfile.mkdtemp()
            mynet = NiceCXNetwork()

            mynet.create_node('node1')
            outcxfile = os.path.join(temp_dir, 'foo.cx')
            with open(outcxfile, 'w') as f:
                json.dump(mynet.to_cx(), f)
                f.flush()

            cachedir = os.path.join(temp_dir, 'cache')
            os.makedirs(cachedir, mode=0o755)
            thecachefile = os.path.join(cachedir, 'foo.cx.json')
            with open(thecachefile, 'w') as f:
                f.write('{}\n')
                f.flush()

            for net_cx, file_name, cache_file in ndexloadindra.get_next_network_from_input(outcxfile,
                                                                                           cachedir=cachedir):
                self.assertEqual(thecachefile, cache_file)
                self.assertEqual('foo.cx', file_name)
                self.assertEqual(1, len(net_cx.get_nodes()))
        finally:
            shutil.rmtree(temp_dir)

    def test_get_next_network_from_input_file_of_two_uuids(self):

        try:

            temp_dir = tempfile.mkdtemp()
            id_one = 'd2c3f73b-7d9c-4012-9dd6-08a159077439'
            id_two = '68e860d4-e6ed-49da-ba0b-5fb412108959'
            mynet = NiceCXNetwork()
            mynet.create_node('node1')

            mynet2 = NiceCXNetwork()
            mynet2.create_node('node2')

            uuidlist = os.path.join(temp_dir, 'foo.txt')
            with open(uuidlist, 'w') as f:
                f.write('tooshorttobeid\n')
                f.write(id_one + '\n')
                f.write(id_two + '\n')
                f.flush()

            cachedir = os.path.join(temp_dir, 'cache')
            os.makedirs(cachedir, mode=0o755)
            thecachefile = os.path.join(cachedir, id_one + '.json')
            with open(thecachefile, 'w') as f:
                f.write('{}\n')
                f.flush()

            ndexmock = MagicMock()
            ndexmock.create_nice_cx_from_server = MagicMock(side_effect=[mynet, mynet2])

            gen_rator = ndexloadindra.get_next_network_from_input(uuidlist,
                                                                  cachedir=cachedir,
                                                                  ndexobj=ndexmock)

            net_cx, file_name, cache_file = next(gen_rator)

            self.assertEqual(thecachefile, cache_file)
            self.assertEqual(id_one, file_name)
            self.assertEqual(1, len(net_cx.get_nodes()))
            self.assertEqual('node1', list(net_cx.get_nodes())[0][1]['n'])

            net_cx, file_name, cache_file = next(gen_rator)
            self.assertEqual(None, cache_file)
            self.assertEqual(id_two, file_name)
            self.assertEqual(1, len(net_cx.get_nodes()))
            self.assertEqual('node2', list(net_cx.get_nodes())[0][1]['n'])

            try:
                next(gen_rator)
                self.fail('Expected StopIteration')
            except StopIteration:
                pass

        finally:
            shutil.rmtree(temp_dir)

    def test_parse_config_all_set(self):
        try:
            temp_dir = tempfile.mkdtemp()
            mockargs = MagicMock()
            mockargs.conf = os.path.join(temp_dir, 'conffile')
            mockargs.profile='myprofile'
            with open(mockargs.conf, 'w') as f:
                f.write('[myprofile]\n')
                f.write(NDExUtilConfig.USER + '=theuser\n')
                f.write(NDExUtilConfig.PASSWORD + '=thepassword\n')
                f.write(NDExUtilConfig.SERVER + '=theserver\n')
                f.write(NDExIndraLoader.DEST_USER + '=destuser\n')
                f.write(NDExIndraLoader.DEST_PASSWORD + '=destpassword\n')
                f.write(NDExIndraLoader.DEST_SERVER + '=destserver\n')

            loader = NDExIndraLoader(mockargs)
            loader._parse_config()
            self.assertEqual('theuser', loader._user)
            self.assertEqual('thepassword', loader._pass)
            self.assertEqual('theserver', loader._server)
            self.assertEqual('destuser', loader._dest_user)
            self.assertEqual('destpassword', loader._dest_pass)
            self.assertEqual('destserver', loader._dest_server)
        finally:
            shutil.rmtree(temp_dir)

    def test_parse_config_dest_omitted(self):
        try:
            temp_dir = tempfile.mkdtemp()
            mockargs = MagicMock()
            mockargs.conf = os.path.join(temp_dir, 'conffile')
            mockargs.profile='myprofile'
            with open(mockargs.conf, 'w') as f:
                f.write('[myprofile]\n')
                f.write(NDExUtilConfig.USER + '=theuser\n')
                f.write(NDExUtilConfig.PASSWORD + '=thepassword\n')
                f.write(NDExUtilConfig.SERVER + '=theserver\n')

            loader = NDExIndraLoader(mockargs)
            loader._parse_config()
            self.assertEqual('theuser', loader._user)
            self.assertEqual('thepassword', loader._pass)
            self.assertEqual('theserver', loader._server)
            self.assertEqual('theuser', loader._dest_user)
            self.assertEqual('thepassword', loader._dest_pass)
            self.assertEqual('theserver', loader._dest_server)
        finally:
            shutil.rmtree(temp_dir)

    def test_load_style_template(self):
        try:
            temp_dir =tempfile.mkdtemp()
            mockargs =MagicMock()
            mockargs.style = os.path.join(temp_dir, 'style.cx')
            loader = NDExIndraLoader(mockargs)
            loader._load_style_template()

            # try loader where style file is missing
            self.assertEqual(None, loader._template)

            net = NiceCXNetwork()
            net.set_name('style network')
            with open(mockargs.style, 'w') as f:
                json.dump(net.to_cx(), f)

            loader._load_style_template()
            self.assertEqual('style network', loader._template.get_name())
        finally:
            shutil.rmtree(temp_dir)

    def test_create_saveasfile_dir(self):
        try:
            temp_dir = tempfile.mkdtemp()
            mockargs = MagicMock()
            mockargs.saveasfile = os.path.join(temp_dir, 'saveasdir')
            loader = NDExIndraLoader(mockargs)
            res = loader._create_saveasfile_dir()
            self.assertIsNotNone(res)
            self.assertTrue(os.path.isdir(res))
            self.assertTrue(os.path.isdir(mockargs.saveasfile))
        finally:
            shutil.rmtree(temp_dir)

    def test_create_indracache(self):
        try:
            temp_dir = tempfile.mkdtemp()
            mockargs = MagicMock()
            mockargs.indracachedir = os.path.join(temp_dir, 'cachedir')
            loader = NDExIndraLoader(mockargs)
            res = loader._create_indracache()
            self.assertIsNotNone(res)
            self.assertTrue(os.path.isdir(res))
            self.assertTrue(os.path.isdir(mockargs.indracachedir))
        finally:
            shutil.rmtree(temp_dir)

    def test_cartesian(self):
        mocknet = MagicMock()
        mocknet.pos = {0: (1, 2), 1: (3, 4)}
        loader = NDExIndraLoader(MagicMock())
        res = loader._cartesian(mocknet)
        self.assertEqual(0, res[0]['node'])
        self.assertEqual(1.0, res[0]['x'])
        self.assertEqual(-2.0, res[0]['y'])
        self.assertEqual(1, res[1]['node'])
        self.assertEqual(3.0, res[1]['x'])
        self.assertEqual(-4.0, res[1]['y'])

