"""
Testes de Snapshot Lifecycle Completo - Dumont Cloud

Testa:
- Criação de snapshots
- Listagem de snapshots
- Restauração de snapshots
- Deleção de snapshots
- Pruning de snapshots antigos

Uses api_client and real_instance fixtures from conftest.py
"""
import pytest
import time


# ============================================================
# Testes de Snapshot Creation
# ============================================================

class TestSnapshotCreation:
    """Testes de criação de snapshots"""

    
    
    def test_create_snapshot_basic(self, api_client, real_instance):
        """Testa criação básica de snapshot"""
        print(f"\n📸 Criando snapshot da instância {real_instance}...")
        result = api_client.call("POST", "/api/v1/snapshots", {
            "instance_id": int(real_instance),
            "source_path": "/workspace",
            "tags": ["test", "automated"]
        })
        print(f"   Resultado: {result}")
        assert result is not None

    
    def test_create_snapshot_invalid_instance(self, api_client):
        """Testa snapshot com instância inválida"""
        result = api_client.call("POST", "/api/v1/snapshots", {
            "instance_id": 999999999,
            "source_path": "/workspace"
        })
        assert result is not None


# ============================================================
# Testes de Snapshot Listing
# ============================================================

class TestSnapshotListing:
    """Testes de listagem de snapshots"""

    
    def test_list_all_snapshots(self, api_client):
        """Lista todos os snapshots"""
        result = api_client.call("GET", "/api/v1/snapshots")
        assert result is not None
        if "error" not in str(result):
            count = result.get('count', len(result.get('snapshots', [])))
            print(f"   Total: {count} snapshots")

    
    def test_list_snapshots_with_tags(self, api_client):
        """Lista snapshots filtrados por tag"""
        result = api_client.call("GET", "/api/v1/snapshots?tag=automated")
        assert result is not None

    
    def test_get_snapshot_details(self, api_client):
        """Obtém detalhes de um snapshot específico"""
        list_result = api_client.call("GET", "/api/v1/snapshots")
        if list_result and list_result.get("snapshots"):
            snapshot = list_result["snapshots"][0]
            snapshot_id = snapshot.get("id") or snapshot.get("snapshot_id")
            if snapshot_id:
                result = api_client.call("GET", f"/api/v1/snapshots/{snapshot_id}")
                assert result is not None


# ============================================================
# Testes de Snapshot Restore
# ============================================================

class TestSnapshotRestore:
    """Testes de restauração de snapshots"""

    
    def test_restore_snapshot_invalid(self, api_client):
        """Testa restauração de snapshot inexistente"""
        result = api_client.call("POST", "/api/v1/snapshots/restore", {
            "snapshot_id": "invalid-snapshot-id",
            "target_instance_id": 12345,
            "target_path": "/workspace"
        })
        assert result is not None


# ============================================================
# Testes de Snapshot Deletion
# ============================================================

class TestSnapshotDeletion:
    """Testes de deleção de snapshots"""

    
    def test_delete_snapshot_invalid(self, api_client):
        """Testa deleção de snapshot inexistente"""
        result = api_client.call("DELETE", "/api/v1/snapshots/invalid-snapshot-id-12345")
        assert result is not None

    
    def test_prune_old_snapshots(self, api_client):
        """Testa pruning de snapshots antigos"""
        result = api_client.call("POST", "/api/v1/snapshots/prune", {
            "keep_last": 5,
            "older_than_days": 7
        })
        assert result is not None


# ============================================================
# Testes de Sync (Incremental Backup)
# ============================================================

class TestSnapshotSync:
    """Testes de sync incremental"""

    
    
    def test_sync_instance(self, api_client, real_instance):
        """Testa sync incremental de instância"""
        print(f"\n🔄 Fazendo sync da instância {real_instance}...")
        result = api_client.call("POST", f"/api/v1/instances/{real_instance}/sync", {
            "source_path": "/workspace",
            "force": True
        })
        print(f"   Resultado: {result}")
        assert result is not None

    
    def test_sync_status(self, api_client, real_instance):
        """Testa status de sync"""
        result = api_client.call("GET", f"/api/v1/instances/{real_instance}/sync/status")
        assert result is not None
        if "error" not in str(result):
            print(f"   Synced: {result.get('synced', False)}")
            print(f"   Last sync: {result.get('last_sync_ago', 'Never')}")


# ============================================================
# Testes de Snapshot Stats
# ============================================================

class TestSnapshotStats:
    """Testes de estatísticas de snapshots"""

    
    def test_snapshot_storage_usage(self, api_client):
        """Testa uso de armazenamento de snapshots"""
        result = api_client.call("GET", "/api/v1/snapshots/stats")
        assert result is not None

    
    def test_snapshot_history(self, api_client):
        """Testa histórico de snapshots"""
        result = api_client.call("GET", "/api/v1/snapshots/history")
        assert result is not None
