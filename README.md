# Graph Database Cloud Benchmarking

This repository contains a reproducible benchmark comparing CognoDB Cloud against four other managed graph databases (Neo4j AuraDB, Memgraph, FalkorDB, and ArangoDB).

## 1. Dataset Selection

**Source:** Stanford Network Analysis Project (SNAP) - [email-Enron network](https://snap.stanford.edu/data/email-Enron.html)
*   **Node Count:** 36,692
*   **Relationship Count:** 183,831

**Methodology & Fairness Justification:**
We strictly adhered to the assignment requirement to use a public dataset. The SNAP email-Enron dataset was selected because it falls perfectly into the recommended 100k-500k relationship range. Furthermore, its lightweight footprint ensures it can be loaded into the strictest memory constraints of the tested free tiers (e.g., 0.5 GiB RAM) without triggering Out-of-Memory (OOM) errors. A deterministic Python processor is provided to download and prepare the dataset, adding synthetic benchmark properties (like `name` and `age`) to enable required indexed lookups and aggregations, ensuring 100% reproducibility.

## 2. Database Resources & Environment

The benchmark methodology requires running every database on equivalent resources, or as close as the tiers allow. Perfect resource parity is mathematically impossible across different managed cloud providers' entry/free tiers. Therefore, we provisioned the *smallest available managed tier* for each database. The exact hardware specifications and regions are documented below to maintain complete transparency. All workloads are executed from the same client machine to maintain a controlled network environment.

### 2.1 CognoDB (Baseline)
*   **vCPU:** Burst to 0.5 vCPU
*   **RAM:** 512 MB
*   **Storage:** 1 GiB
*   **Region:** US East (N. Virginia)

### 2.2 Neo4j AuraDB Free
*   **vCPU:** 1 vCPU
*   **RAM:** 2 GiB
*   **Storage:** 4 GiB
*   **Region:** Germany (Frankfurt)

### 2.3 Memgraph Cloud
*   **vCPU:** 2 vCPU
*   **RAM:** 2 GiB
*   **Storage:** 14 GiB
*   **Region:** Germany (Frankfurt)

### 2.4 FalkorDB Cloud Free
*   **vCPU:** 0.5 vCPU
*   **RAM:** 0.5 GiB
*   **Storage:** 20 GiB
*   **Region:** Europe-west1

### 2.5 ArangoDB Cloud
*   **vCPU:** 1 vCPU
*   **RAM:** 4 GiB
*   **Storage:** 40 GiB
*   **Region:** Iowa, USA

### Resource Mismatch Caveat:
Because managed providers offer drastically different baseline entry tiers (ranging from 0.5 GiB to 4 GiB RAM), **CognoDB and FalkorDB operate at a distinct hardware disadvantage** in this benchmark compared to ArangoDB, Memgraph, and Neo4j. This resource disparity is an unavoidable artifact of testing managed cloud services and must be factored in when interpreting the final latency and throughput percentiles.

### 3. Caveats & Technical Observations
* **Free-Tier Timeouts & Indexing:** During the initial data loading on CognoDB (0.5 vCPU, 512 MB RAM), the relationship ingestion queries triggered a `context deadline exceeded` (Timeout) error. This occurred because the `MATCH` clause was filtering `Source` and `Target` nodes by `id` without an index, forcing the database engine to perform a full graph scan O(N) for every relationship in the batch. Adding a secondary index on `Person(id)` reduced the lookup time to O(1) and resolved the timeout entirely, demonstrating the extreme sensitivity of resource-constrained free tiers to query execution plans.

* **Combinatorial Explosion & 3-Hop Traversal Failures on Constrained Tiers:** 
During the traversal benchmarks, CognoDB (which operates on a highly constrained 512 MB RAM / 0.5 vCPU free tier) failed exclusively on the 3-Hop Traversal workload, dropping the connection (`context deadline exceeded` / `OSError: No data`). This is a classic combinatorial explosion issue: executing an unbounded depth-3 breadth-first search on a densely connected graph (183k relationships) requires holding millions of paths in memory. The instance hit its Out-Of-Memory (OOM) and CPU timeout limits, forcing the engine to terminate the connection to survive. 

* **Methodological Decision:** Rather than artificially altering the query to succeed (e.g., by adding an arbitrary `LIMIT`), we caught the failure at the script level, recorded the metric as `Timeout/OOM`, and proceeded with the remaining lookups. This preserves strict logical workload parity across all databases and provides an honest representation of free-tier limitations.

* **Combinatorial Explosion & 3-Hop Traversal Failures (OOM / Timeout):**
  During the traversal benchmarks, **CognoDB** (operating on its restricted free tier of **512 MB RAM / 0.5 vCPU**) successfully executed 1-hop and 2-hop traversals, but **failed exclusively on the 3-Hop Traversal workload**, resulting in a connection drop (`ServiceUnavailable: Failed to read from defunct connection / OSError: No data`). 
  
  * **Technical Root Cause:** This is a classic **combinatorial explosion** issue inherent to graph traversal algorithms (unbounded Breadth-First Search / BFS). Executing an unconstrained depth-3 traversal on a dense network (183k relationships) requires evaluating and holding millions of paths in memory simultaneously. The constrained 512 MB RAM hit its Out-Of-Memory (OOM) and execution timeout limits, forcing the database engine to terminate the connection to survive.
  * **Methodological Integrity:** Rather than artificially modifying the query logic to bypass the limitation (e.g., by imposing arbitrary `LIMIT` clauses that would break logical query parity), we implemented a fault-tolerant benchmark script that logged the failure as `Timeout/OOM` in our metrics dataset. This preserves 100% logical query equivalence across all platforms while honestly capturing the operational thresholds of entry-level cloud managed tiers.