"""
SPEC-010 / STORY-006: Cross-Tenant Scatter-Gather

Tests for TenantStorageManager.query_across_tenants.
"""

import logging
import pytest
from unittest.mock import MagicMock, patch

from team_mind_mcp.tenant_manager import TenantStorageManager
from team_mind_mcp.storage import StorageAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_manager(tmp_path):
    mgr = TenantStorageManager(str(tmp_path / "mind"))
    mgr.initialize()
    return mgr


# ---------------------------------------------------------------------------
# AC-1: Single tenant — results have tenant_id injected
# ---------------------------------------------------------------------------

def test_single_tenant_results_have_tenant_id_injected(tmp_path):
    """query_across_tenants injects tenant_id into each result dict."""
    mgr = make_manager(tmp_path)

    fake_results = [
        {"id": 1, "uri": "doc1", "final_rank": 0.5},
        {"id": 2, "uri": "doc2", "final_rank": 0.8},
    ]

    def query_fn(adapter):
        return list(fake_results)

    results = mgr.query_across_tenants(
        query_fn=query_fn,
        sort_key="final_rank",
        sort_descending=False,
        tenant_ids=["default"],
    )

    assert len(results) == 2
    assert all(r["tenant_id"] == "default" for r in results)
    mgr.close()


# ---------------------------------------------------------------------------
# AC-2: Multiple tenants — merged and sorted by final_rank ascending
# ---------------------------------------------------------------------------

def test_multiple_tenants_merged_sorted_ascending_by_final_rank(tmp_path):
    """Results from multiple tenants are merged and sorted by final_rank ascending."""
    mgr = make_manager(tmp_path)
    mgr.create_tenant("t1")
    mgr.create_tenant("t2")

    def query_fn(adapter):
        # Use adapter identity to return different results per tenant
        if "t1" in adapter.db_path:
            return [{"id": 10, "uri": "a", "final_rank": 0.9}]
        else:
            return [{"id": 20, "uri": "b", "final_rank": 0.3}]

    results = mgr.query_across_tenants(
        query_fn=query_fn,
        sort_key="final_rank",
        sort_descending=False,
        tenant_ids=["t1", "t2"],
    )

    assert len(results) == 2
    # Ascending: lower final_rank first
    assert results[0]["final_rank"] == 0.3
    assert results[1]["final_rank"] == 0.9
    mgr.close()


# ---------------------------------------------------------------------------
# AC-3: Multiple tenants — merged and sorted by weight_rank descending
# ---------------------------------------------------------------------------

def test_multiple_tenants_sorted_descending_by_weight_rank(tmp_path):
    """Results are sorted by weight_rank descending when sort_descending=True."""
    mgr = make_manager(tmp_path)
    mgr.create_tenant("t1")
    mgr.create_tenant("t2")

    def query_fn(adapter):
        if "t1" in adapter.db_path:
            return [{"id": 1, "uri": "doc-a", "weight_rank": 2.5}]
        else:
            return [
                {"id": 2, "uri": "doc-b", "weight_rank": 4.0},
                {"id": 3, "uri": "doc-c", "weight_rank": 1.0},
            ]

    results = mgr.query_across_tenants(
        query_fn=query_fn,
        sort_key="weight_rank",
        sort_descending=True,
        tenant_ids=["t1", "t2"],
    )

    assert len(results) == 3
    # Descending: higher weight_rank first
    assert results[0]["weight_rank"] == 4.0
    assert results[1]["weight_rank"] == 2.5
    assert results[2]["weight_rank"] == 1.0
    mgr.close()


# ---------------------------------------------------------------------------
# AC-4: tenant_ids parameter limits queried tenants
# ---------------------------------------------------------------------------

def test_tenant_ids_limits_which_tenants_are_queried(tmp_path):
    """When tenant_ids is specified, only those tenants are queried."""
    mgr = make_manager(tmp_path)
    mgr.create_tenant("included")
    mgr.create_tenant("excluded")

    queried_tenants = []

    def query_fn(adapter):
        queried_tenants.append(adapter.db_path)
        return [{"id": 1, "final_rank": 0.5}]

    mgr.query_across_tenants(
        query_fn=query_fn,
        sort_key="final_rank",
        sort_descending=False,
        tenant_ids=["default", "included"],
    )

    # "excluded" tenant should not be queried
    assert not any("excluded" in p for p in queried_tenants)
    assert any("included" in p for p in queried_tenants)
    mgr.close()


# ---------------------------------------------------------------------------
# AC-5: tenant_ids=None queries all registered tenants
# ---------------------------------------------------------------------------

def test_tenant_ids_none_queries_all_tenants(tmp_path):
    """When tenant_ids is None, all registered tenants are queried."""
    mgr = make_manager(tmp_path)
    mgr.create_tenant("t1")
    mgr.create_tenant("t2")

    queried_tenants = []

    def query_fn(adapter):
        queried_tenants.append(adapter.db_path)
        return []

    mgr.query_across_tenants(
        query_fn=query_fn,
        sort_key="final_rank",
        sort_descending=False,
        tenant_ids=None,
    )

    # All 3 tenants (default + t1 + t2) should have been queried
    assert len(queried_tenants) == 3
    mgr.close()


# ---------------------------------------------------------------------------
# AC-6: Tenant with no matching docs contributes no results
# ---------------------------------------------------------------------------

def test_tenant_with_empty_results_contributes_nothing(tmp_path):
    """A tenant that returns an empty list contributes no results to the merge."""
    mgr = make_manager(tmp_path)
    mgr.create_tenant("empty-tenant")
    mgr.create_tenant("full-tenant")

    def query_fn(adapter):
        if "empty-tenant" in adapter.db_path:
            return []
        else:
            return [{"id": 1, "uri": "doc", "final_rank": 0.4}]

    results = mgr.query_across_tenants(
        query_fn=query_fn,
        sort_key="final_rank",
        sort_descending=False,
        tenant_ids=["empty-tenant", "full-tenant"],
    )

    assert len(results) == 1
    assert results[0]["uri"] == "doc"
    mgr.close()


# ---------------------------------------------------------------------------
# AC-7: sort_descending=False puts lower values first
# ---------------------------------------------------------------------------

def test_sort_descending_false_puts_lower_values_first(tmp_path):
    """sort_descending=False (ascending) means lower sort_key values appear first."""
    mgr = make_manager(tmp_path)

    def query_fn(adapter):
        return [
            {"id": 3, "final_rank": 0.7},
            {"id": 1, "final_rank": 0.1},
            {"id": 2, "final_rank": 0.4},
        ]

    results = mgr.query_across_tenants(
        query_fn=query_fn,
        sort_key="final_rank",
        sort_descending=False,
        tenant_ids=["default"],
    )

    ranks = [r["final_rank"] for r in results]
    assert ranks == sorted(ranks)  # ascending
    assert ranks[0] == 0.1
    mgr.close()


# ---------------------------------------------------------------------------
# AC-8: sort_descending=True puts higher values first
# ---------------------------------------------------------------------------

def test_sort_descending_true_puts_higher_values_first(tmp_path):
    """sort_descending=True (descending) means higher sort_key values appear first."""
    mgr = make_manager(tmp_path)

    def query_fn(adapter):
        return [
            {"id": 1, "weight_rank": 1.0},
            {"id": 2, "weight_rank": 3.5},
            {"id": 3, "weight_rank": 2.2},
        ]

    results = mgr.query_across_tenants(
        query_fn=query_fn,
        sort_key="weight_rank",
        sort_descending=True,
        tenant_ids=["default"],
    )

    ranks = [r["weight_rank"] for r in results]
    assert ranks == sorted(ranks, reverse=True)  # descending
    assert ranks[0] == 3.5
    mgr.close()


# ---------------------------------------------------------------------------
# AC-9: Results missing sort_key go to the end
# ---------------------------------------------------------------------------

def test_results_missing_sort_key_go_to_end_ascending(tmp_path):
    """Results without the sort_key are placed at the end (ascending sort)."""
    mgr = make_manager(tmp_path)

    def query_fn(adapter):
        return [
            {"id": 1, "uri": "no-rank"},  # no final_rank
            {"id": 2, "uri": "ranked", "final_rank": 0.5},
        ]

    results = mgr.query_across_tenants(
        query_fn=query_fn,
        sort_key="final_rank",
        sort_descending=False,
        tenant_ids=["default"],
    )

    # The ranked result should come first; missing key goes last
    assert results[0]["uri"] == "ranked"
    assert results[-1]["uri"] == "no-rank"
    mgr.close()


def test_results_missing_sort_key_go_to_end_descending(tmp_path):
    """Results without the sort_key are placed at the end (descending sort)."""
    mgr = make_manager(tmp_path)

    def query_fn(adapter):
        return [
            {"id": 1, "uri": "no-rank"},  # no weight_rank
            {"id": 2, "uri": "ranked", "weight_rank": 2.0},
        ]

    results = mgr.query_across_tenants(
        query_fn=query_fn,
        sort_key="weight_rank",
        sort_descending=True,
        tenant_ids=["default"],
    )

    assert results[0]["uri"] == "ranked"
    assert results[-1]["uri"] == "no-rank"
    mgr.close()


# ---------------------------------------------------------------------------
# AC-10: Tenant that fails get_adapter is skipped silently
# ---------------------------------------------------------------------------

def test_failed_get_adapter_tenant_is_skipped_silently(tmp_path, caplog):
    """A tenant that fails get_adapter is skipped and a warning is logged."""
    mgr = make_manager(tmp_path)
    mgr.create_tenant("good-tenant")
    # "bad-tenant" is not registered — get_adapter will raise ValueError

    def query_fn(adapter):
        return [{"id": 1, "final_rank": 0.3}]

    with caplog.at_level(logging.WARNING, logger="team_mind_mcp.tenant_manager"):
        results = mgr.query_across_tenants(
            query_fn=query_fn,
            sort_key="final_rank",
            sort_descending=False,
            tenant_ids=["good-tenant", "bad-tenant"],
        )

    # Only the good tenant's result is returned
    assert len(results) == 1
    assert all(r["tenant_id"] == "good-tenant" for r in results)

    # A warning should have been logged for the bad tenant
    assert any("bad-tenant" in record.message for record in caplog.records)
    mgr.close()


# ---------------------------------------------------------------------------
# AC-11: tenant_id is injected into every result dict from every tenant
# ---------------------------------------------------------------------------

def test_tenant_id_injected_correctly_for_each_tenant(tmp_path):
    """Each result dict has the correct tenant_id for the tenant it came from."""
    mgr = make_manager(tmp_path)
    mgr.create_tenant("tenant-a")
    mgr.create_tenant("tenant-b")

    def query_fn(adapter):
        if "tenant-a" in adapter.db_path:
            return [{"id": 1, "final_rank": 0.2}]
        elif "tenant-b" in adapter.db_path:
            return [{"id": 2, "final_rank": 0.6}]
        return []

    results = mgr.query_across_tenants(
        query_fn=query_fn,
        sort_key="final_rank",
        sort_descending=False,
        tenant_ids=["tenant-a", "tenant-b"],
    )

    assert len(results) == 2
    result_by_rank = {r["final_rank"]: r for r in results}
    assert result_by_rank[0.2]["tenant_id"] == "tenant-a"
    assert result_by_rank[0.6]["tenant_id"] == "tenant-b"
    mgr.close()
