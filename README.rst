linkermapviz
============

Interactive visualization of GNU ld’s linker map with a tree map. Usage:

.. code:: bash

   pip install .
   gcc -Wl,-Map,output.map -o output input.c
   linkermapviz < output.map

Works best with ``-ffunction-sections -fdata-sections`` and statically linked
code (e.g. for bare-metal embedded systems).

