
# Python Memory Management

Python uses automatic memory management.

CPython primarily uses reference counting and supplements
it with a cyclic garbage collector.

## Reference Counting

Each Python object maintains a reference count.

When the reference count reaches zero, the object can
usually be deallocated.

## Garbage Collection

The cyclic garbage collector identifies unreachable
reference cycles that reference counting alone cannot
collect.

## Memory Allocation

CPython uses an internal memory allocator called pymalloc
for many small object allocations.
