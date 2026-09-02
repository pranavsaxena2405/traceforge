from datetime import datetime, timezone
from fastapi import status


def test_health_endpoint(app_client_no_db):
    """Test /health endpoint."""
    response = app_client_no_db.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data


def test_trace_ingestion_and_retrieval(client):
    """Test trace ingestion POST and retrieval GET endpoints."""
    trace_id = "a1b2c3d4e5f67890a1b2c3d4e5f67890"
    span_id = "1122334455667788"
    start_time = datetime.now(timezone.utc).isoformat()
    end_time = datetime.now(timezone.utc).isoformat()

    payload = {
        "trace_id": trace_id,
        "name": "api_test_trace",
        "start_time": start_time,
        "end_time": end_time,
        "duration_ms": 150.5,
        "status": "OK",
        "attributes": {"environment": "pytest"},
        "spans": [
            {
                "span_id": span_id,
                "trace_id": trace_id,
                "parent_span_id": None,
                "name": "root_span",
                "span_type": "agent",
                "start_time": start_time,
                "end_time": end_time,
                "duration_ms": 150.5,
                "status": "OK",
                "attributes": {"version": "1.0"},
            }
        ],
    }

    # 1. Ingest Trace
    ingest_resp = client.post("/api/v1/traces", json=payload)
    assert ingest_resp.status_code == status.HTTP_201_CREATED
    ingest_data = ingest_resp.json()
    assert ingest_data["trace_id"] == trace_id
    assert len(ingest_data["spans"]) == 1

    # 2. Retrieve Trace
    get_resp = client.get(f"/api/v1/traces/{trace_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    get_data = get_resp.json()
    assert get_data["trace_id"] == trace_id
    assert get_data["name"] == "api_test_trace"
    assert get_data["spans"][0]["span_id"] == span_id


def test_trace_ingestion_idempotency(client):
    """Test that ingesting the same trace_id twice updates existing records without error."""
    trace_id = "ffffffffffffffffffffffffffffffff"
    span_id = "eeeeeeeeeeeeeeee"
    start_time = datetime.now(timezone.utc).isoformat()
    end_time = datetime.now(timezone.utc).isoformat()

    payload1 = {
        "trace_id": trace_id,
        "name": "initial_name",
        "start_time": start_time,
        "end_time": end_time,
        "duration_ms": 100.0,
        "status": "OK",
        "attributes": {"initial": True},
        "spans": [
            {
                "span_id": span_id,
                "trace_id": trace_id,
                "parent_span_id": None,
                "name": "span_initial",
                "span_type": "agent",
                "start_time": start_time,
                "end_time": end_time,
                "duration_ms": 100.0,
                "status": "OK",
                "attributes": {"initial": True},
            }
        ],
    }

    # First ingestion
    resp1 = client.post("/api/v1/traces", json=payload1)
    assert resp1.status_code == status.HTTP_201_CREATED

    # Second ingestion with updated attributes
    payload2 = dict(payload1)
    payload2["name"] = "updated_name"
    payload2["attributes"] = {"initial": True, "updated": True}
    payload2["spans"][0]["name"] = "span_updated"
    payload2["spans"][0]["attributes"] = {"initial": True, "updated": True}

    resp2 = client.post("/api/v1/traces", json=payload2)
    assert resp2.status_code == status.HTTP_201_CREATED

    # Fetch and check updated values
    get_resp = client.get(f"/api/v1/traces/{trace_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    data = get_resp.json()
    assert data["name"] == "updated_name"
    assert data["attributes"]["updated"] is True
    assert data["spans"][0]["name"] == "span_updated"


def test_get_nonexistent_trace(client):
    """Test retrieving non-existent trace returns 404."""
    resp = client.get("/api/v1/traces/nonexistent_id_0000000000000000")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_invalid_payload_handling(client):
    """Test sending invalid payload returns 422 Unprocessable Entity."""
    invalid_payload = {"invalid_field": True}
    resp = client.post("/api/v1/traces", json=invalid_payload)
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_traces_pagination(client):
    """Test GET /api/v1/traces pagination and summary listing."""
    # Ingest two distinct traces
    for i in range(2):
        t_id = f"1111111111111111111111111111100{i}"
        start_time = datetime.now(timezone.utc).isoformat()
        payload = {
            "trace_id": t_id,
            "name": f"list_test_trace_{i}",
            "start_time": start_time,
            "end_time": start_time,
            "duration_ms": 10.0 * (i + 1),
            "status": "OK",
            "attributes": {"index": i},
            "spans": [],
        }
        client.post("/api/v1/traces", json=payload)

    # Fetch list
    resp = client.get("/api/v1/traces?limit=10&offset=0")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "total" in data
    assert data["total"] >= 2
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 2


def test_dashboard_ui_endpoint(app_client_no_db):
    """Test dashboard UI returns index.html HTML page."""
    resp = app_client_no_db.get("/")
    assert resp.status_code == status.HTTP_200_OK
    assert "TRACEFORGE" in resp.text
    assert "html" in resp.headers.get("content-type", "")


