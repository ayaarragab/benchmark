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
