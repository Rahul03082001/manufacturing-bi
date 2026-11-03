# Five interview questions and implementation-grounded answers

**1. How do you prevent a bad load from changing a trusted dashboard?**
Every attempt has a new run ID. Candidate rows and SQL outputs are built separately from the published snapshot. The pipeline records successful checks and switches a singleton publication pointer in one transaction. A database trigger requires SUCCESS and all eight critical checks. Failed attempts append evidence and leave the pointer unchanged. Four fault/recovery tests prove this; the dashboard warns when the latest completed attempt failed.

**2. Why is the reconciliation meaningful if all data is synthetic?**
Finance is a separate CSV exported from clean event history and independently ingested. The pipeline never derives finance from its inventory mart. Omitting a posting therefore produces a difference. An independent hand-written fixture expects 10 received minus 3 issued at $25 = $175 on both sides. The generator still shares initial history across sources, so this is not independent organizational assurance; offsetting errors can cancel at the daily grain.

**3. What SQL techniques did you use, and why does grain matter?**
Window functions compute running stock in deterministic event-time/movement-ID order. CTEs build a date/item spine so quiet days retain closing stock. Inventory and finance aggregate independently before joining at day/account grain; joining detailed facts first could multiply values. A left join checks PO receipts, retaining unreceived PO lines. Money remains integer cents through calculation.

**4. What does idempotent mean here?**
Identical full deliveries create different audit run IDs but identical published business rows and totals. It is versioned snapshot processing, not incremental ingestion or CDC. The rerun test compares every published item/day balance and key uniqueness. This simplifies recovery at this scale but repeats historical storage and needs a retention design for larger workloads.

**5. How did you demonstrate least privilege and lineage?**
The bootstrap owner creates objects. Runtime pipeline is a non-superuser with insert/read access to evidence and candidate data, plus guarded publication changes. Reporter has SELECT only on approved business/status views and receives no owner or pipeline password. Real PostgreSQL tests prove denied writes/raw reads and denied audit edits. Received copies, source IDs, filename/hash/row/load time/run ID, SQL models and a manual lineage table connect displayed metrics to inputs. Owners/admins can override restrictions, and solo development is not segregation of duties or SOX certification.
