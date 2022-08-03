#! /usr/bin/env python

import os
import argparse
import sys
import json
import uuid
import logging
import configparser
from logging import config
from tqdm import tqdm
import networkx as nx

import ndex2

from ndexutil.cytoscape import Py4CytoscapeWrapper
from ndexutil.cytoscape import DEFAULT_CYREST_API
from ndexutil.ndex import NDExExtraUtils

from ndexutil.config import NDExUtilConfig
import ndexindraloader
from ndexindraloader.exceptions import NDExIndraLoaderError
from ndexindraloader.indra import Indra
from ndexindraloader.indra import SelfLoopStatementFilter
from ndexindraloader.indra import IncorrectStatementFilter
from ndexindraloader.indra import SingleReadingStatementFilter
from ndexindraloader.indra import SparserComplexStatementFilter


logger = logging.getLogger(__name__)

TSV2NICECXMODULE = 'ndexutil.tsv.tsv2nicecx2'

LOG_FORMAT = "%(asctime)-15s %(levelname)s %(relativeCreated)dms " \
             "%(filename)s::%(funcName)s():%(lineno)d %(message)s"


class Formatter(argparse.ArgumentDefaultsHelpFormatter,
                argparse.RawDescriptionHelpFormatter):
    pass


def _parse_arguments(desc, args):
    """
    Parses command line arguments
    :param desc:
    :param args:
    :return:
    """
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=Formatter)
    parser.add_argument('--profile', help='Profile in configuration '
                                          'file to use to load '
                                          'NDEx credentials which means'
                                          'configuration under [XXX] will be'
                                          'used ',
                        default='ndexindraloader')
    parser.add_argument('input',
                        help='Network(s) to annotate. Input can be one of '
                             'the following: ' +
                             'CX file, '
                             'Text file with NDEx network IDs one per line')
    parser.add_argument('--indracachedir',
                        help='If set, code will look in this directory for '
                             'previous output of Indra REST call for a given '
                             'network and use that instead of making the '
                             'call. If no output exists, the REST query '
                             'is made and the results are saved here.')
    parser.add_argument('--curations',
                        help='INDRA curations json file')
    parser.add_argument('--saveasfile',
                        help='If set, writes Indra annotated networks as CX '
                             'under directory specified by the value of this '
                             'flag. If directory does not exist it will be '
                             'created')
    parser.add_argument('--savetoserver', action='store_true',
                        help='NOT IMPLEMENTED. WILL RAISE ERROR!!! '
                             'If set, saves networks to NDEx server set via '
                             '--profile configuration. For additional options '
                             'see --dest_networkset, --visibility flags')
    parser.add_argument('--dest_networkset',
                        help='NOT IMPLEMENTED. WILL RAISE ERROR!!! '
                             'If set, adds annotated networks to NDEx '
                             'NetworkSet with UUID passed in. Ignored '
                             'unless --savetoserver is set')
    parser.add_argument('--visibility', default='PUBLIC',
                        choices=['PUBLIC', 'PRIVATE'],
                        help='Sets visibility of new '
                             'networks. Ignored unless --savetoserver is set')
    parser.add_argument('--indexlevel', default='all',
                        choices=['none', 'meta', 'all'],
                        help='Sets how new networks are indexed. '
                             'Ignored unless --savetoserver is set.')
    parser.add_argument('--disableshowcase', default=False, action='store_true',
                        help='If set, new networks are NOT showcased. '
                             'Ignored unless --savetoserver is set.')
    parser.add_argument('--netprefix', default='INDRA annotated - ',
                        help='Text prepended to network name for networks '
                             'generated by this tool')
    parser.add_argument('--maxnetworksize', type=int, default=100,
                        help='Maximum number of nodes that can be in the '
                             'input network. Values exceeding this will '
                             'cause script skip the network and will cause'
                             'tool to skip network and log an error '
                             'level message')
    parser.add_argument('--remove_orig_edges', action='store_true',
                        help='If set, all original edges are removed')
    parser.add_argument('--sourcevalue',
                        help='If set, adds source edge attribute with value'
                             'passed in to existing edges of network')
    parser.add_argument('--style',
                        default=os.path.join(os.path.dirname(ndexindraloader.indra.__file__),
                                             'style.cx'),
                        help='If CX file, then style from that file is '
                             'applied to network.')
    parser.add_argument('--tmpdir', default='.',
                        help='Temp directory used for Cytoscape layouts')
    parser.add_argument('--layout', default='-',
                        help='Specifies layout '
                             'algorithm to run. If Cytoscape is running '
                             'and py4cytoscape is loaded any layout from '
                             'Cytoscape can be used. If "-" is passed in '
                             'force-directed from Cytoscape will '
                             'be used. If no Cytoscape is available, '
                             '"spring" from networkx is supported')
    parser.add_argument('--cyresturl',
                        default=DEFAULT_CYREST_API,
                        help='URL of CyREST API. Default value '
                             'is default for locally running Cytoscape')
    parser.add_argument('--disable_tqdm', action='store_true',
                        help='If set, disables tqdm progress bars')
    parser.add_argument('--logconf', default=None,
                        help='Path to python logging configuration file in '
                             'this format: https://docs.python.org/3/library/'
                             'logging.config.html#logging-config-fileformat '
                             'Setting this overrides -v parameter which uses '
                             ' default logger.')

    parser.add_argument('--conf', help='Configuration file to load '
                                       '(default ~/' +
                                       NDExUtilConfig.CONFIG_FILE + ')')
    parser.add_argument('--verbose', '-v', action='count', default=1,
                        help='Increases verbosity of logger to standard '
                             'error for log messages in this module and'
                             'in ' + TSV2NICECXMODULE + '. Messages are '
                             'output at these python logging levels '
                             '-v = ERROR, -vv = WARNING, -vvv = INFO, '
                             '-vvvv = DEBUG, -vvvvv = NOTSET (default no '
                             'logging)')
    parser.add_argument('--version', action='version',
                        version=('%(prog)s ' +
                                 ndexindraloader.__version__))

    return parser.parse_args(args)


def _setup_logging(args):
    """
    Sets up logging based on parsed command line arguments.
    If args.logconf is set use that configuration otherwise look
    at args.verbose and set logging for this module and the one
    in ndexutil specified by TSV2NICECXMODULE constant
    :param args: parsed command line arguments from argparse
    :raises AttributeError: If args is None or args.logconf is None
    :return: None
    """

    if args.logconf is None:
        level = (50 - (10 * args.verbose))
        logging.basicConfig(format=LOG_FORMAT,
                            level=level)
        logging.getLogger(TSV2NICECXMODULE).setLevel(level)
        logger.setLevel(level)
        return

    # logconf was set use that file
    logging.config.fileConfig(args.logconf,
                              disable_existing_loggers=False)


def get_next_network_from_input(input, cachedir=None, server=None, username=None,
                                password=None, ndexobj=ndex2):
    """
    Generator to get networks from `input` which can be a path to a
    single CX file or a file containing a list of NDEx network UUIDs
    one per line

    :param input: Path to a single CX file or a file
                  containing a list of NDEx network UUIDs
    :type input: str
    :return: (:py:class:`ndex2.nice_cx_network.NiceCXNetwork,
              CX file name or NDEx UUID,
              path to cache file or None)
    :rtype: tuple
    """

    # if input is a file
    if os.path.isfile(input):
        # and ends with .cx assume it is a CX file and load that
        if input.lower().endswith('.cx'):
            net_cx = ndex2.create_nice_cx_from_file(input)
            file_name = os.path.basename(input)
            cache_file = None
            if cachedir is not None:
                cache_file = os.path.join(cachedir,
                                          file_name + '.json')
                if not os.path.isfile(cache_file):
                    cache_file = None
            yield net_cx, file_name, cache_file
            return

        # otherwise assume file is a list of NDEx network ids
        with open(input, 'r') as f:
            for line in f:
                clean_line = line.rstrip()
                if len(clean_line) < 36:
                    continue
                net_cx = ndexobj.create_nice_cx_from_server(server=server,
                                                            username=username,
                                                            password=password,
                                                            uuid=clean_line)
                cache_file = None
                if cachedir is not None:
                    cache_file = os.path.join(cachedir,
                                              clean_line + '.json')
                    if not os.path.isfile(cache_file):
                        cache_file = None
                yield net_cx, clean_line, cache_file
        return

    raise NDExIndraLoaderError('Input must be a CX file ending with .cx or '
                               'a file with NDEx Network UUID one per line')
    # TODO: add support to load single NDEx UUID and NetworkSet UUID
    # input is not a file so let's try to load it as a straight network

    # if above fails try to load entry as a networkset
    # and iterate through all the network ids


class NDExIndraLoader(object):
    """
    Class to load content
    """

    DEST_USER = 'dest_user'
    DEST_PASSWORD = 'dest_password'
    DEST_SERVER = 'dest_server'

    def __init__(self, args,
                 py4cyto=Py4CytoscapeWrapper(),
                 ndexextra=NDExExtraUtils()):
        """

        :param args:
        """
        self._conf_file = args.conf
        self._profile = args.profile
        self._user = None
        self._pass = None
        self._server = None
        self._dest_user = None
        self._dest_pass = None
        self._dest_server = None
        self._args = args
        self._template = None
        self._py4 = py4cyto
        self._ndexextra = ndexextra
        try:
            self._visibility = args.visibility
        except AttributeError:
            self._visibility = 'PUBLIC'
        try:
            self._indexlevel = args.indexlevel
        except AttributeError:
            logger.error('showcase was not found in args. Setting value to ALL')
            self._indexlevel = 'ALL'

        try:
            self._showcase = not args.disableshowcase
        except AttributeError:
            logger.error('showcase was not found in args. Setting value to True')
            self._showcase = True

        self._networksystemproperty_retry = 3
        self._networksystemproperty_wait = 1

    def _parse_config(self):
            """
            Parses config
            :return:
            """
            ncon = NDExUtilConfig(conf_file=self._conf_file)
            con = ncon.get_config()
            self._user = con.get(self._profile, NDExUtilConfig.USER)
            self._pass = con.get(self._profile, NDExUtilConfig.PASSWORD)
            self._server = con.get(self._profile, NDExUtilConfig.SERVER)

            if con.has_option(self._profile,
                                      NDExIndraLoader.DEST_USER):
                self._dest_user = con.get(self._profile,
                                          NDExIndraLoader.DEST_USER)
            else:
                self._dest_user = self._user

            if con.has_option(self._profile,
                                      NDExIndraLoader.DEST_PASSWORD):
                self._dest_pass = con.get(self._profile,
                                          NDExIndraLoader.DEST_PASSWORD)
            else:
                self._dest_pass = self._pass

            if con.has_option(self._profile,
                                        NDExIndraLoader.DEST_SERVER):
                self._dest_server = con.get(self._profile,
                                            NDExIndraLoader.DEST_SERVER)
            else:
                self._dest_server = self._server

    def _load_style_template(self):
        """
        Loads the CX network specified by self._args.style into self._template
        :return:
        """
        if self._args.style is not None and os.path.isfile(self._args.style):
            self._template = ndex2.create_nice_cx_from_file(os.path.abspath(self._args.style))

    def _create_saveasfile_dir(self):
        """

        :return:
        """
        if self._args.saveasfile is not None:
            outdir = os.path.abspath(self._args.saveasfile)
            if not os.path.isdir(outdir):
                logger.debug('Creating directory: ' + outdir)
                os.makedirs(outdir, mode=0o755)
            return outdir
        return None

    def _create_indracache(self):
        """

        :return:
        """
        if self._args.indracachedir is not None:
            cachedir = os.path.abspath(self._args.indracachedir)
            if not os.path.isdir(cachedir):
                logger.debug('Creating indra cache directory')
                os.makedirs(cachedir, mode=0o755)
            return cachedir
        return None

    def _cartesian(self, g):
        """
        Converts node coordinates from a :py:class:`networkx.Graph` object
        to a list of dicts with following format:

        [{'node': <node id>,
          'x': <x position>,
          'y': <y position>}]

        :param g:
        :return: coordinates
        :rtype: list
        """
        return [{'node': n,
                 'x': float(g.pos[n][0]),
                 'y': -float(g.pos[n][1])} for n in g.pos]

    def _apply_simple_spring_layout(self, network, iterations=50):
        """
        Applies simple spring network by using
        :py:func:`networkx.drawing.spring_layout` and putting the
        coordinates into 'cartesianLayout' aspect on the 'network' passed
        in

        :param network: Network to update
        :type network: :py:class:`~ndex2.nice_cx_network.NiceCXNetwork`
        :param iterations: Number of iterations to use for networkx spring layout call
                           default is 50
        :type iterations: int
        :return: None
        """

        num_nodes = len(network.get_nodes())
        my_networkx = network.to_networkx(mode='default')
        if num_nodes < 10:
            nodescale = num_nodes*20
        elif num_nodes < 20:
            nodescale = num_nodes*15
        elif num_nodes < 100:
            nodescale = num_nodes*10
        else:
            nodescale = num_nodes*5

        my_networkx.pos = nx.drawing.spring_layout(my_networkx,
                                                   scale=nodescale,
                                                   k=1.8,
                                                   iterations=iterations)
        cartesian_aspect = self._cartesian(my_networkx)
        network.set_opaque_aspect("cartesianLayout", cartesian_aspect)

    def _apply_cytoscape_layout(self, network):
        """
        Applies Cytoscape layout on network
        :param network:
        :return:
        """

        try:
            self._py4.cytoscape_ping()
        except Exception as e:
            raise NDExIndraLoaderError('Cytoscape needs to be running to run '
                                       'layout: ' + str(self._args.layout))

        tmp_cx_file = os.path.join(self._args.tmpdir,
                                   str(uuid.uuid4()) +
                                   '-tmp.cx')

        with open(tmp_cx_file, 'w') as f:
            json.dump(network.to_cx(), f)

        annotated_cx_file = os.path.join(self._args.tmpdir,
                                         str(uuid.uuid4()) +
                                         'annotated.tmp.cx')

        self._ndexextra.add_node_id_as_node_attribute(cxfile=tmp_cx_file,
                                                      outcxfile=annotated_cx_file)
        file_size = os.path.getsize(annotated_cx_file)

        logger.info('Importing network from file: ' + annotated_cx_file +
                    ' (' + str(file_size) + ' bytes) into Cytoscape')
        net_dict = self._py4.import_network_from_file(annotated_cx_file,
                                                      base_url=self._args.cyresturl)
        if 'networks' not in net_dict:
            raise NDExIndraLoaderError('Error network view could not '
                                       'be created, this could be cause '
                                       'this network is larger then '
                                       '100,000 edges. Try increasing '
                                       'viewThreshold property in '
                                       'Cytoscape preferences')

        os.unlink(annotated_cx_file)
        net_suid = net_dict['networks'][0]

        logger.info('Applying layout ' + self._args.layout +
                    ' on network with suid: ' +
                    str(net_suid) + ' in Cytoscape')
        res = self._py4.layout_network(layout_name=self._args.layout,
                                       network=net_suid,
                                       base_url=self._args.cyresturl)
        logger.debug(res)

        os.unlink(tmp_cx_file)

        logger.info('Writing cx to: ' + tmp_cx_file)
        res = self._py4.export_network(filename=tmp_cx_file, type='CX',
                                       network=net_suid,
                                       base_url=self._args.cyresturl)
        self._py4.delete_network(network=net_suid,
                                 base_url=self._args.cyresturl)
        logger.debug(res)

        layout_aspect = self._ndexextra.extract_layout_aspect_from_cx(input_cx_file=tmp_cx_file)
        network.set_opaque_aspect('cartesianLayout', layout_aspect)

    def run(self):
        """
        Runs content loading for NDEx Indra Content Loader

        :return:
        """
        try:
            self._parse_config()
        except configparser.NoSectionError as ne:
            if self._args.savetoserver is True:
                raise NDExIndraLoaderError('No section found in config file '
                                           'needed for --savetoserver flag. '
                                           'Be sure to set --profile '
                                           'correctly: ' + str(ne))

        cachedir = self._create_indracache()
        outdir = self._create_saveasfile_dir()

        if self._args.savetoserver is True:
            client = ndex2.client.Ndex2(host=self._dest_server,
                                        username=self._dest_user,
                                        password=self._dest_pass,
                                        user_agent='NDExIndraLoader/' +
                                                   str(ndexindraloader.__version__))

        self._load_style_template()
        t_progress = tqdm(desc='Indra annotate', unit=' tasks',
                          disable=self._args.disable_tqdm)

        stmtfilters = [SelfLoopStatementFilter(),
                       IncorrectStatementFilter(self._get_curation_list(self._args.curations)),
                       SingleReadingStatementFilter(),
                       SparserComplexStatementFilter()]
        indra = Indra(stmtfilters=stmtfilters)
        for net_tuple in get_next_network_from_input(self._args.input,
                                                     cachedir=cachedir,
                                                     server=self._server,
                                                     username=self._user,
                                                     password=self._pass):

            logger.debug('Processing: ' + net_tuple[0].get_name())

            num_nodes = len(net_tuple[0].get_nodes())
            if num_nodes > self._args.maxnetworksize:
                logger.error('Network has ' + str(num_nodes) +
                             ' which exceeds ' + str(self._args.maxnetworksize) +
                             '. To increase set --maxnetworksize flag. skipping')
                continue
            if net_tuple[2] is None:
                save_indra_res = True
                indra_data = None
            else:
                with open(net_tuple[2], 'r') as f:
                    indra_data = json.load(f)
                logger.info('Using cached INDRA version: ' + net_tuple[2])
                save_indra_res = False

            net_cx, indra_res = indra.annotate_network(net_cx=net_tuple[0],
                                                       netprefix=self._args.netprefix,
                                                       indraresult=indra_data,
                                                       source_value=self._args.sourcevalue)

            if self._template is not None:
                logger.debug('Applying style from file: ' + self._args.style)
                net_cx.apply_style_from_network(self._template)

            if self._args.layout is not None:
                if self._args.layout == 'spring':
                    self._apply_simple_spring_layout(net_cx)
                else:
                    if self._args.layout == '-':
                        self._args.layout = 'force-directed'
                    self._apply_cytoscape_layout(net_cx)

            if outdir is not None:
                outfile = os.path.join(outdir,
                                       net_tuple[1] + '.cx')
                logger.debug('Saving network to file: ' + outfile)
                with open(outfile, 'w') as f:
                    json.dump(net_cx.to_cx(), f)

            if save_indra_res is True:
                if cachedir is not None:
                    outfile = os.path.join(cachedir,
                                           net_tuple[1] + '.json')
                    logger.debug('Saving INDRA json to file: ' + outfile)
                    with open(outfile, 'w') as f:
                        json.dump(indra_res, f)

            if self._args.savetoserver is True:
                logger.debug('Saving network as a new network to user ' +
                             str(self._dest_user) + ' on NDEx '
                             'server: ' + str(self._dest_server))
                client.save_new_network(net_cx.to_cx())
            t_progress.update()

        t_progress.close()

        return 0

    def _get_curation_list(self, curation):
        """

        :param curation:
        :return:
        """
        with open(curation, 'r') as f:
            return json.load(f)


def main(args):
    """
    Main entry point for program
    :param args:
    :return:
    """
    desc = """
    Version {version}

    Annotates NDEx with INDRA and optionally loads networks into 
    NDEx (http://ndexbio.org).
    
    To connect to NDEx server a configuration file must be passed
    into --conf parameter. If --conf is unset the configuration 
    the path ~/{confname} is examined. 
         
    The configuration file should be formatted as follows:
         
    [<value in --profile (default ndexindraloader)>]
         
    {user} = <NDEx username>
    {password} = <NDEx password>
    {server} = <NDEx server(omit http) ie public.ndexbio.org>
    
    # Add the following to config
    # to use alternate destination account/server
    {destuser} = <NDEx destination username>
    {destpassword} = <NDEx destination password>  
    {destserver} = <NDEx destination server (omit http) ie public.ndexbio.org>

    
    """.format(confname=NDExUtilConfig.CONFIG_FILE,
               user=NDExUtilConfig.USER,
               password=NDExUtilConfig.PASSWORD,
               server=NDExUtilConfig.SERVER,
               destuser=NDExIndraLoader.DEST_USER,
               destpassword=NDExIndraLoader.DEST_PASSWORD,
               destserver=NDExIndraLoader.DEST_SERVER,
               version=ndexindraloader.__version__)
    theargs = _parse_arguments(desc, args[1:])
    theargs.program = args[0]
    theargs.version = ndexindraloader.__version__

    try:
        _setup_logging(theargs)
        loader = NDExIndraLoader(theargs)
        return loader.run()
    except Exception as e:
        logger.exception('Caught exception: ' + str(e))
        return 2
    finally:
        logging.shutdown()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv))
