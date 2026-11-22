# Performance experiment policy

Reported workstation RAM is 32 GB, not yet confirmed by local inventory. Early GRM baseline: one expensive builder at a time; soft safety target 18–20 GiB Private Bytes; warning at 20 GiB; controlled stop/checkpoint at 24 GiB. Do not confuse Private Bytes with Working Set; log both and the managed heap.

Suggested CSV: stage,start_utc,end_utc,private_bytes,working_set,managed_heap,available_ram_bytes,temp_disk_bytes,object_count,exit_code.

Hypotheses to **measure**, not assume: resident lazy-build caches, duplicate satellite image buffers, OSM graph materialization, concurrent builders and full-WRP in-memory object collection. Test the unmodified GRM first, then minimal instrumented patches in a separate branch. Compare memory and output hashes on the same small fixed dataset.

Record disk by raw/cache/intermediate/build/output; compute estimates only after 10.24 km pilot. Target Q0=absent, Q1=sparse, Q2=normal, Q3=landmark; actual object density limits and performance budgets require testing in Arma.
