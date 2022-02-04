=======
History
=======

0.2.0 (TBD)
------------------

* Added ``__relationship_score`` which is natural log of total evidence count for edge

* Updated style file in package and set ``--style`` flag to apply that style by default

* Renamed ``edge source`` to ``__edge_source``

* Renamed edge attributes ``directed`` to ``__directed`` and
  ``reverse directed`` to ``__reverse directed``. Updated ``style.cx``
  style to reflect this change.

* Web links to INDRA evidence should all open in the same tab on a
  web browser

* For ``ndexloadindra.py``, an invalid profile is ignored unless
  ``--savetoserver`` is set

* Collapsed edge attributes ``SOURCE - TARGET``, ``SOURCE => TARGET``,
  and ``TARGET => SOURCE`` into ``relationships`` edge attribute. This
  attribute now lists the statements with protein names along with an
  `All Evidences (X)` which links to all evidence for this edge on INDRA


0.1.0 (2021-05-28)
------------------

* First release on PyPI.
