Generated ontology API reference
================================

The class signatures, inherited members, and ontology definitions below come
from generated Python packages at build time. Use a class's ``.meta`` property
to inspect its source IRI, definition, parents, and effective property specs.
The :doc:`catalog` lists every importable S223 and WaTr class.

S223 equipment and connection points
------------------------------------

.. autoclass:: plumb.s223.Damper
   :members:

.. autoclass:: plumb.s223.Fan
   :members:

.. autoclass:: plumb.s223.Chiller
   :members:

WaTr equipment
--------------

.. autoclass:: plumb.watr.Pump
   :members:

.. autoclass:: plumb.watr.Tank
   :members:

.. autoclass:: plumb.watr.CoagulationBasin
   :members:

.. autoclass:: plumb.watr.FlocculationBasin
   :members:

.. autoclass:: plumb.watr.RapidSandFilter
   :members:

.. autoclass:: plumb.watr.ChlorinationUnit
   :members:

WaTr process and objective vocabulary
-------------------------------------

.. autoclass:: plumb.watr.Process
   :members:

.. autoclass:: plumb.watr.Process_Settling
   :members:

.. autoclass:: plumb.watr.TreatmentObjective
   :members:

.. autoclass:: plumb.watr.TreatmentObjective_Clarification
   :members:

.. autoclass:: plumb.watr.SedimentationTank
   :members:

Generated domain configurations
--------------------------------

.. autoclass:: plumb.watr.drinking_water.CoagulationStage
   :members:

.. autoclass:: plumb.watr.drinking_water.FlocculationStage
   :members:

.. autoclass:: plumb.watr.drinking_water.ClarificationStage
   :members:

.. autoclass:: plumb.watr.drinking_water.RapidSandFiltrationStage
   :members:

.. autoclass:: plumb.watr.drinking_water.ChlorinationStage
   :members:

.. autoclass:: plumb.s223.hvac.AirWaterCoolingCoil
   :members:

.. autoclass:: plumb.watr.asm2d.AerobicStage
   :members:

.. autoclass:: plumb.watr.asm2d.AerobicDesign
   :members:

.. autoclass:: plumb.watr.seawater_ro.MembraneDesign
   :members:

Common entity API
-----------------

.. autoclass:: plumb.Entity
   :members: name, type, label, comment, contains, port, ports, apply_properties, quantity
