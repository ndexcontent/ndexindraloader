=======
History
=======

0.2.0 (TBD)
------------------

* Filter out self-loops i.e., Statements all of whose participants are a single gene
  These are not very interesting and are often the result of reading errors.

* Filter out members of Complexes that are not in the gene set
  This is necessary because INDRA Complexes can have > 2 members e g., Complex(A, B, C)
  and it’s possible that only A and B are in the gene set but C isn’t. We make sure C
  doesn’t show up in the network.

* Filter out statements that have a single evidence from a reading system.
  The rationale is that if there is a single evidence but from a curated resource (e.g.,
  Pathway Commons or SIGNOR), it’s fine to keep it. But if it’s from a single reading
  system, its error rate is fairly high. Once we have more than one evidence, even
  if it’s from a single reading system, the precision is in the 75-80% range.

* Filter out Complexes that only have evidence from Sparser. The rationale is that
  the Sparser reading system tends to pick up spurious complexes, and if Sparser
  is the only one having reported a certain Complex, without evidence from any
  other source, then its quality is likely to be low.

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
