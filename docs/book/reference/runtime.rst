Runtime API reference
=====================

These signatures and docstrings are imported from the installed ``plumb``
package during the book build. The :doc:`../explanation/lifecycle` explains
when to use each operation.

Model
-----

.. autoclass:: plumb.Model
   :members: system, from_graph, by_class, find, find_all, check, resolve, compile, graph, save, validate, export_ontology

.. automethod:: plumb.core.Entity.describe_ports

.. autoattribute:: plumb.core.Entity.ports

Traversal
---------

.. autoclass:: plumb.core.Entity
   :no-index:
   :members: contents, descendants, container, containers, find, find_all, find_parent, find_parents, walk, find_next, find_all_next, find_previous, find_all_previous

.. autofunction:: plumb.exact

.. autoclass:: plumb.Hop
   :members:

.. autoclass:: plumb.Crossing
   :members:

Property schemas
----------------

.. autoclass:: plumb.PropertySchema
   :members: describe

.. autoclass:: plumb.qudt.QuantityAmount
   :members:

.. autoclass:: plumb.PropertySet
   :members:

.. automethod:: plumb.core.Entity.apply_properties

.. automethod:: plumb.core.Entity.quantity

.. autoclass:: plumb.PointRef
   :members: medium, quantity, apply_properties

.. autoclass:: plumb.PointGroupRef
   :members:

.. autoclass:: plumb.PortHandle
   :members: medium, direction, pair, quantity, apply_properties

Class discovery
---------------

Use ``SomeClass.meta["ChildName"]`` for a descendant scoped to that class.
The lookup also accepts the full Python name or ontology class IRI.

.. autoclass:: plumb.core.ClassMetaView
   :members: iri, label, definition, ontology, registry, parents, children, subclasses, descendants, tree, properties, port_contract, describe_ports, abstract

.. autoclass:: plumb.core.Registry
   :members: classes, subclasses, tree, resolve

.. autoclass:: plumb.core.EnumValue
   :members: iri, label, definition, parent, parents, children, descendants, tree, tree_text, is_a

.. autoclass:: plumb.core.PortContract
   :members:

.. autoclass:: plumb.core.PortSlot
   :members:

Connections and snapshots
-------------------------

.. autofunction:: plumb.connect

.. autoclass:: plumb.ConnectionHandle
   :members: medium, connection_class, label, comment, assign, quantity, apply_properties

.. autoclass:: plumb.ResolvedModel
   :members: entities, find, find_all, connection, point, explain, graph

.. autoclass:: plumb.ResolutionReport
   :members: satisfiable, complete

.. autoclass:: plumb.ResolutionExplanation
   :members:

Validation and errors
---------------------

.. autoclass:: plumb.ValidationReport
   :members: violations

.. autoclass:: plumb.core.Issue
   :members:

.. autoexception:: plumb.AmbiguousModelError

.. autoexception:: plumb.UnsatisfiableModelError

.. autoexception:: plumb.ValidationError
