=======
History
=======

0.2.0 (TBD)
------------------

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
  `All (X)` entry which has a broken link for now, but will link to all
  evidence for this edge on INDRA


0.1.0 (2021-05-28)
------------------

* First release on PyPI.
