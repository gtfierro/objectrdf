Runtime API reference
=====================

These signatures and docstrings are imported from the installed ``objectrdf``
package during the book build. The :doc:`../explanation/lifecycle` explains
when to use each operation.

Model
-----

.. autoclass:: objectrdf.Model
   :members: system, from_graph, by_class, find, find_all, check, resolve, compile, graph, save, validate, export_ontology

.. automethod:: objectrdf.core.Entity.describe_ports

.. autoattribute:: objectrdf.core.Entity.ports

.. automethod:: objectrdf.core.Entity.apply_property_block

.. automethod:: objectrdf.PortHandle.apply_property_block

Property schemas
----------------

.. autoclass:: objectrdf.PropertySchema
   :members: describe

.. autoclass:: objectrdf.qudt.QuantityAmount
   :members:

.. autoclass:: objectrdf.PropertySet
   :members:

.. automethod:: objectrdf.core.Entity.apply_properties

.. automethod:: objectrdf.PortHandle.apply_properties

Property bundles
----------------

.. autoclass:: objectrdf.PropertyBundle
   :members: quantity, property, apply, describe, parameters
   :special-members: __call__

Class discovery
---------------

Use ``SomeClass.meta["ChildName"]`` for a descendant scoped to that class.
The lookup also accepts the full Python name or ontology class IRI.

.. autoclass:: objectrdf.core.ClassMetaView
   :members: iri, label, definition, ontology, registry, parents, children, subclasses, descendants, tree, properties, port_contract, describe_ports, abstract

.. autoclass:: objectrdf.core.Registry
   :members: classes, subclasses, tree, resolve

.. autoclass:: objectrdf.core.EnumValue
   :members: iri, label, definition, parent, parents, children, descendants, tree, tree_text, is_a

.. autoclass:: objectrdf.core.PortContract
   :members:

.. autoclass:: objectrdf.core.PortSlot
   :members:

Connections and snapshots
-------------------------

.. autofunction:: objectrdf.connect

.. autoclass:: objectrdf.ConnectionHandle
   :members: medium, connection_class, label, comment, assign

.. autoclass:: objectrdf.ResolvedModel
   :members: entities, connection, point, explain, graph

.. autoclass:: objectrdf.ResolutionReport
   :members: satisfiable, complete

.. autoclass:: objectrdf.ResolutionExplanation
   :members:

Validation and errors
---------------------

.. autoclass:: objectrdf.ValidationReport
   :members: violations

.. autoclass:: objectrdf.core.Issue
   :members:

.. autoexception:: objectrdf.AmbiguousModelError

.. autoexception:: objectrdf.UnsatisfiableModelError

.. autoexception:: objectrdf.ValidationError
