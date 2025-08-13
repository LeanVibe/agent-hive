from datetime import datetime

from external_api.envoy_exporter import export_envoy_virtual_host


def test_envoy_exporter_basic_route():
    routing_config = {
        "routes": [
            {
                "match": {"path": "/api/v1/users", "methods": ["GET"]},
                "backends": [{"service": "user-service"}],
                "rewrite": "/users",
                "retries": {"count": 2, "backoff_ms": 50},
                "timeouts": {"request_timeout": 2},
            }
        ]
    }

    vhost = export_envoy_virtual_host(routing_config, name="gw", domains=["*"])

    assert vhost["name"] == "gw"
    assert vhost["domains"] == ["*"]
    assert len(vhost["routes"]) == 1

    route = vhost["routes"][0]
    match = route["match"]
    action = route["route"]

    # Match should use prefix for exact path pattern
    assert match.get("prefix") == "/api/v1/users"
    # Method filter added as :method header
    assert any(h.get("name") == ":method" and h.get("exact_match") == "GET" for h in match.get("headers", []))

    # Cluster name derived from service
    assert action.get("cluster") == "cluster_user_service"
    # Prefix rewrite applied
    assert action.get("prefix_rewrite") == "/users"
    # Timeout seconds present
    assert action.get("timeout", {}).get("seconds") == 2
    # Retry policy basics
    assert action.get("retry_policy", {}).get("num_retries") == 2
