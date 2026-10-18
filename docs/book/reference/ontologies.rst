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

.. autoclass:: objectrdf.s223.Chiller
   :members:

WaTr equipment
--------------

.. autoclass:: objectrdf.watr.Pump
   :members:

.. autoclass:: objectrdf.watr.Tank
   :members:

.. autoclass:: objectrdf.watr.CoagulationBasin
   :members:

.. autoclass:: objectrdf.watr.FlocculationBasin
   :members:

.. autoclass:: objectrdf.watr.RapidSandFilter
   :members:

.. autoclass:: objectrdf.watr.ChlorinationUnit
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

Generated domain configurations
--------------------------------

.. autoclass:: objectrdf.watr.drinking_water.CoagulationStage
   :members:

.. autoclass:: objectrdf.watr.drinking_water.FlocculationStage
   :members:

.. autoclass:: objectrdf.watr.drinking_water.ClarificationStage
   :members:

.. autoclass:: objectrdf.watr.drinking_water.RapidSandFiltrationStage
   :members:

.. autoclass:: objectrdf.watr.drinking_water.ChlorinationStage
   :members:

.. autoclass:: objectrdf.s223.hvac.AirWaterCoolingCoil
   :members:

.. autoclass:: objectrdf.watr.asm2d.AerobicStage
   :members:

.. autoclass:: objectrdf.watr.asm2d.AerobicDesign
   :members:

.. autoclass:: objectrdf.watr.seawater_ro.MembraneDesign
   :members:

Common entity API
-----------------

.. autoclass:: objectrdf.Entity
   :members: name, type, label, comment, contains, port, ports, apply_properties, quantity
