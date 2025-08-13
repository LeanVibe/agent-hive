"""
Envoy Configuration Exporter for API Gateway Routing DSL

Converts the API Gateway's declarative routing DSL into Envoy's
HTTP Connection Manager `virtual_host` and `route` configurations.
"""

from typing import Dict, Any, List, Optional, Callable
import re
import logging

logger = logging.getLogger(__name__)


def _default_cluster_name_for_service(service_name: str) -> str:
    """Default function to map a service name to an Envoy cluster name."""
    return f"cluster_{service_name.replace('-', '_').replace('.', '_')}"


def export_envoy_virtual_host(
    routing_config: Dict[str, Any],
    name: str = "api-gateway",
    domains: Optional[List[str]] = None,
    cluster_name_for_service: Optional[Callable[[str], str]] = None,
) -> Dict[str, Any]:
    """
    Exports the API Gateway's routing DSL to an Envoy virtual_host structure.

    Args:
        routing_config: The API Gateway's declarative routing configuration.
        name: The name for the Envoy virtual host.
        domains: List of domains for which this virtual host is applicable (e.g., ["*"]).
        cluster_name_for_service: Optional function to map service names to Envoy cluster names.

    Returns:
        A dictionary representing an Envoy virtual_host configuration.
    """
    if domains is None:
        domains = ["*"]

    if cluster_name_for_service is None:
        cluster_name_for_service = _default_cluster_name_for_service

    envoy_routes: List[Dict[str, Any]] = []

    for idx, route_rule in enumerate(routing_config.get("routes", [])):
        match = route_rule.get("match", {})
        backends = route_rule.get("backends", [])
        rewrite = route_rule.get("rewrite")
        shadow = route_rule.get("shadow")
        timeouts = route_rule.get("timeouts", {})
        retries = route_rule.get("retries", {})

        if not match or not backends:
            logger.warning(f"Skipping invalid route rule at index {idx}: {route_rule}")
            continue

        # Determine route match
        route_match: Dict[str, Any] = {}
        path_pattern = match.get("path")
        use_regex = bool(match.get("regex", False))

        if use_regex and isinstance(path_pattern, str):
            route_match["safe_regex_match"] = {"regex": path_pattern}
        elif isinstance(path_pattern, str) and "*" in path_pattern:
            # Convert wildcard to Envoy's prefix/regex if needed, or just prefix
            if path_pattern.endswith("*"):
                route_match["prefix"] = path_pattern.rstrip("*")
            else:
                # Fallback to regex for more complex wildcards
                regex = re.escape(path_pattern).replace("\\*", ".*")
                route_match["safe_regex_match"] = {"regex": regex}
        else:
            # Exact match or simple prefix treated as prefix for simplicity
            route_match["prefix"] = path_pattern

        methods = match.get("methods")
        if methods:
            if len(methods) == 1:
                route_match["headers"] = [
                    {"name": ":method", "exact_match": str(methods[0]).upper()}
                ]
            else:
                logger.warning(
                    f"Route {idx} has multiple methods {methods}. Envoy export will not filter by method."
                )

        headers = match.get("headers", {})
        if headers:
            envoy_headers = []
            for hk, hv in headers.items():
                envoy_headers.append({"name": hk, "exact_match": hv})
            if "headers" in route_match:
                route_match["headers"].extend(envoy_headers)
            else:
                route_match["headers"] = envoy_headers

        # Determine route action (cluster and optional rewrite)
        route_action: Dict[str, Any] = {}
        selected_backend = backends[0]  # MVP: pick the first backend
        cluster_name = cluster_name_for_service(str(selected_backend.get("service", "")))
        route_action["cluster"] = cluster_name

        if rewrite:
            if isinstance(rewrite, dict) and rewrite.get("regex"):
                route_action["regex_rewrite"] = {
                    "pattern": {"google_re2": {}, "regex": match.get("path")},
                    "substitution": rewrite.get("value"),
                }
            elif isinstance(rewrite, str):
                # Simple prefix rewrite
                route_action["prefix_rewrite"] = rewrite

        # Timeouts
        if isinstance(timeouts.get("request_timeout"), (int, float)):
            route_action["timeout"] = {"seconds": int(timeouts["request_timeout"]) }

        # Retries
        if isinstance(retries.get("count", 0), (int, float)) and int(retries.get("count", 0)) > 0:
            route_action["retry_policy"] = {
                "retry_on": "5xx,connect-failure,refused-stream",
                "num_retries": int(retries["count"]),
                "per_try_timeout": {"seconds": 1},
            }
            if isinstance(retries.get("backoff_ms", 0), (int, float)) and int(retries.get("backoff_ms", 0)) > 0:
                route_action["retry_policy"]["retry_back_off"] = {
                    "base_interval": {"nanos": int(float(retries["backoff_ms"]) * 1_000_000)}
                }

        # Shadow routing (request mirroring)
        if isinstance(shadow, dict) and shadow.get("service") and float(shadow.get("percentage", 0)) > 0:
            route_action["request_mirror_policies"] = [
                {
                    "cluster": cluster_name_for_service(str(shadow["service"])),
                    "runtime_fraction": {
                        "default_value": {
                            "numerator": int(float(shadow.get("percentage", 0))),
                            "denominator": "HUNDRED",
                        }
                    },
                }
            ]

        envoy_routes.append({"match": route_match, "route": route_action})

    virtual_host = {"name": name, "domains": domains, "routes": envoy_routes}
    return virtual_host
