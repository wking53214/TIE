# Provenance

TIE preserves source identity, source location, conversation/message/segment references, extraction origin, transformation origin, origin kind, and optional version/lineage identifiers.

TIE computes SHA-256 hashes for segment checksums, source text identity, and evidence IDs. It does not provide tamper evidence over its own records (the optional CNS connector can bind a package to a verdict, but nothing in TIE itself chains or signs records), append-only persistence, or database-backed provenance; those mechanisms were not recovered from the supplied summaries. The signature check applies only to HERALD exports TIE receives.
