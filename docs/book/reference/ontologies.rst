Generated ontology API reference
================================

The class signatures, inherited members, and ontology definitions below come
from generated Python packages at build time. Use a class's ``.meta`` property
to inspect its source IRI, definition, parents, and effective property specs.
The :doc:`catalog` lists every importable S223 and WaTr class.

S223 equipment and connection points
------------------------------------

.. autoclass:: objectrdf.s223.Damper
   :members:

.. autoclass:: objectrdf.s223.Fan
   :members:

.. automethod:: objectrdf.s223.ConnectionPoint.declare

.. autoclass:: objectrdf.s223.Chiller
   :members:

WaTr equipment
--------------

.. autoclass:: objectrdf.watr.Pump
   :members:

.. autoclass:: objectrdf.watr.Tank
   :members:

.. autoclass:: objectrdf.watr.Chiller
   :members:

WaTr process and objective vocabulary
-------------------------------------

.. autoclass:: objectrdf.watr.Process
   :members:

.. autoclass:: objectrdf.watr.Process_Sedimentation
   :members:

.. autoclass:: objectrdf.watr.TreatmentObjective
   :members:

.. autoclass:: objectrdf.watr.TreatmentObjective_Clarification
   :members:

.. autoclass:: objectrdf.watr.SedimentationTank
   :members:

Common entity API and recipe declarations
-----------------------------------------

.. autoclass:: objectrdf.Entity
   :members: name, type, label, comment, contains, port, ports

.. autofunction:: objectrdf.fixed

.. autofunction:: objectrdf.default

.. autofunction:: objectrdf.choose
