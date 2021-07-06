=============================
NDEx Indra Content Loader
=============================


.. image:: https://img.shields.io/pypi/v/ndexindraloader.svg
        :target: https://pypi.python.org/pypi/ndexindraloader

.. image:: https://img.shields.io/travis/ndexcontent/ndexindraloader.svg
        :target: https://travis-ci.com/ndexcontent/ndexindraloader

.. image:: https://readthedocs.org/projects/ndexindraloader/badge/?version=latest
        :target: https://ndexindraloader.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status

This loader annotates existing networks with `subgraph service <https://network.indra.bio/dev/subgraph>`__
created by `INDRA <https://indra.readthedocs.io>`__ The annotations added are put on
as a single separate edges (blue edges in image below)
within this edge are three main attributes:

* For **forward** interactions  ``SOURCE => TARGET``

* For **reverse** interactions ``TARGET => SOURCE``

* For **no direction** interactions ``SOURCE - TARGET``

Within the above attributes are interactions and web links back to INDRA containing evidence for the
interaction. In addition, there are boolean edge attributes denoting if the **forward** list
contains entries, named ``directed``, or if the **reverse** list contains entries ``reverse directed``

.. image:: https://github.com/ndexcontent/ndexindraloader/blob/main/docs/images/example.png
        :alt: Image of network annotated by INDRA subgraph service

.. image:: https://github.com/ndexcontent/ndexindraloader/blob/main/docs/images/example_edge.png
        :alt: Image of pop up dialog showing single INDRA subgraph service edge




Technical details
-------------------

.. note::

    Due to limitations with the service only networks with 100 nodes or less can be analyzed


.. note::

    The service takes a JSON document with a list of node names. This loader uses the node name
    in the network and also includes any entries under ``member`` node attribute as node names.

1. The service takes a list of node names and returns a JSON document containing edges and statements like
the following:

.. code-block::

    "edge": [
        {
          "name": "GRM7",
          "namespace": "HGNC",
          "identifier": "4599",
          "lookup": "https://identifiers.org/hgnc:4599"
        },
        {
          "name": "GRM4",
          "namespace": "HGNC",
          "identifier": "4596",
          "lookup": "https://identifiers.org/hgnc:4596"
        }
      ],
      "stmts": {
        "6773678678801811": {
          "stmt_type": "Inhibition",
          "evidence_count": 1,
          "stmt_hash": 6773678678801811,
          "source_counts": {
            "reach": 1
          },
          "belief": 0.65,
          "curated": false,
          "english": "GRM7 inhibits GRM4.",
          "weight": 0.4307829160924542,
          "residue": null,
          "position": null,
          "initial_sign": null,
          "db_url_hash": "https://db.indra.bio/statements/from_hash/6773678678801811?format=html",
        },
        .
        .



2. For each "edge", the statements above are grouped by their "english" phrase
   and put into one of three lists: forward (meaning source X target), reverse (meaning target X source), and
   no direction (if interaction was one of the following: ``ActiveForm, Association, Complex, Migration``)

3. These lists are renamed as follows:

   * **forward** ``SOURCE => TARGET``

   * **reverse** ``TARGET => SOURCE``

   * **no direction** ``SOURCE - TARGET``

   .. note::

        This approach results in a lot of unique node attributes.

4. The grouped statements are added as values to the above lists in the following format:

    .. code-block::

        <INTERACTION> (#, #, #)

    There are 46 interaction types and include names like `activates, binds, inhibits`.
    The ``#`` is evidence count for that statement and it is a click able html link to INDRA
    where the evidence for the given statement can be found.

    **Example:**

    .. code-block::

        activates(3,2), inhibits(1)

5. A single edge is created and the above edge attributes are added. The edge **interaction** is set to ``interacts with``

6. ``edge source`` edge attribute set to ``INDRA``.

6. If **forward** list contains entries then ``directed`` edge attribute is added and set to ``True`` otherwise set as ``False``

7. If **reverse** list contains entries then ``reverse directed`` edge attribute is added and set to ``True`` otherwise set as ``False``


Dependencies
------------

* `ndex2 <https://pypi.org/project/ndex2>`__
* `ndexutil <https://pypi.org/project/ndexutil>`__
* `requests <https://pypi.org/project/requests>`__
* `tqdm <https://pypi.org/project/tqdm>`__

Compatibility
-------------

* Python 3.3+

Installation
------------

.. code-block::

   git clone https://github.com/ndexcontent/ndexindraloader
   cd ndexindraloader
   make dist
   pip install dist/ndexloadindra*whl


Run **make** command with no arguments to see other build/deploy options including creation of Docker image 

.. code-block::

   make

Output:

.. code-block::

   clean                remove all build, test, coverage and Python artifacts
   clean-build          remove build artifacts
   clean-pyc            remove Python file artifacts
   clean-test           remove test and coverage artifacts
   lint                 check style with flake8
   test                 run tests quickly with the default Python
   test-all             run tests on every Python version with tox
   coverage             check code coverage quickly with the default Python
   docs                 generate Sphinx HTML documentation, including API docs
   servedocs            compile the docs watching for changes
   testrelease          package and upload a TEST release
   release              package and upload a release
   dist                 builds source and wheel package
   install              install the package to the active Python's site-packages
   dockerbuild          build docker image and store in local repository
   dockerpush           push image to dockerhub


Configuration
-------------

The **ndexloadindra.py** requires a configuration file in the following format be created.
The default path for this configuration is :code:`~/.ndexutils.conf` but can be overridden with
:code:`--conf` flag.

**Format of configuration file**

.. code-block::

    [<value in --profile (default ndexindraloader)>]

    user = <NDEx username>
    password = <NDEx password>
    server = <NDEx server(omit http) ie public.ndexbio.org>

    # Add the following to config
    # to use alternate destination account/server
    dest_user = <NDEx destination username>
    dest_password = <NDEx destination password>
    dest_server = <NDEx destination server (omit http) ie public.ndexbio.org>


**Example configuration file**

.. code-block::

    [ndexindraloader_dev]

    user = joe123
    password = somepassword123
    server = dev.ndexbio.org

With optional alternate destination:

.. code-block::

    user = joe123
    password = somepassword123
    server = dev.ndexbio.org

    dest_user = joebob123
    dest_password = anotherpassword123
    dest_server = public.ndexbio.org


Usage
-----

For information invoke :code:`ndexloadindra.py -h`

**Example usage**

**TODO:** Add information about example usage

.. code-block::

   ndexloadindra.py # TODO Add other needed arguments here


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _NDEx: http://www.ndexbio.org
