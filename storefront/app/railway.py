"""Minimal Railway GraphQL client for tenant provisioning.

One tenant = one Railway service in the tenants project, deployed from this
repo's root (`uvicorn app.main:app`), with a volume for SCREENBOARD_HOME and
a generated *.up.railway.app domain. Every call raises RailwayError with the
API's own message; the provisioner records it on the workspace row — a
stated gate, never a mystery.

NOTE: mutation shapes follow Railway's public GraphQL API (backboard v2).
The first live provision is a supervised test (like the Stripe sandbox
pass) — if Railway has drifted a field name, the workspace lands FAILED
with the exact error to fix here.
"""
from __future__ import annotations

import json
import urllib.request

from . import settings


class RailwayError(RuntimeError):
    pass


def _gql(query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        settings.RAILWAY_API_URL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {settings.RAILWAY_API_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            out = json.loads(r.read().decode())
    except Exception as e:
        raise RailwayError(f"Railway API unreachable: {e}") from e
    if out.get("errors"):
        raise RailwayError("; ".join(
            str(e.get("message", "?")) for e in out["errors"]))
    return out.get("data") or {}


def create_service(name: str) -> str:
    """Create a service in the tenants project from the product repo;
    returns the service id. Railway starts a deploy automatically."""
    data = _gql(
        """mutation($input: ServiceCreateInput!) {
             serviceCreate(input: $input) { id } }""",
        {"input": {
            "projectId": settings.RAILWAY_PROJECT_ID,
            "name": name,
            "source": {"repo": settings.TENANT_REPO},
            "branch": settings.TENANT_BRANCH,
        }})
    return data["serviceCreate"]["id"]


def set_start_command(service_id: str, start_command: str) -> None:
    _gql(
        """mutation($environmentId: String!, $serviceId: String!,
                    $input: ServiceInstanceUpdateInput!) {
             serviceInstanceUpdate(environmentId: $environmentId,
                                   serviceId: $serviceId, input: $input) }""",
        {"environmentId": settings.RAILWAY_ENVIRONMENT_ID,
         "serviceId": service_id,
         "input": {"startCommand": start_command}})


def upsert_variables(service_id: str, variables: dict[str, str]) -> None:
    _gql(
        """mutation($input: VariableCollectionUpsertInput!) {
             variableCollectionUpsert(input: $input) }""",
        {"input": {
            "projectId": settings.RAILWAY_PROJECT_ID,
            "environmentId": settings.RAILWAY_ENVIRONMENT_ID,
            "serviceId": service_id,
            "variables": variables,
        }})


def create_volume(service_id: str, mount_path: str) -> str:
    data = _gql(
        """mutation($input: VolumeCreateInput!) {
             volumeCreate(input: $input) { id } }""",
        {"input": {
            "projectId": settings.RAILWAY_PROJECT_ID,
            "environmentId": settings.RAILWAY_ENVIRONMENT_ID,
            "serviceId": service_id,
            "mountPath": mount_path,
        }})
    return data["volumeCreate"]["id"]


def create_domain(service_id: str) -> str:
    """Generate the tenant's *.up.railway.app domain; returns the hostname."""
    data = _gql(
        """mutation($input: ServiceDomainCreateInput!) {
             serviceDomainCreate(input: $input) { domain } }""",
        {"input": {
            "environmentId": settings.RAILWAY_ENVIRONMENT_ID,
            "serviceId": service_id,
        }})
    return data["serviceDomainCreate"]["domain"]


def redeploy(service_id: str) -> None:
    """Redeploy so variables set after the initial build take effect."""
    _gql(
        """mutation($environmentId: String!, $serviceId: String!) {
             serviceInstanceRedeploy(environmentId: $environmentId,
                                     serviceId: $serviceId) }""",
        {"environmentId": settings.RAILWAY_ENVIRONMENT_ID,
         "serviceId": service_id})


def delete_service(service_id: str) -> None:
    _gql("""mutation($id: String!) { serviceDelete(id: $id) }""",
         {"id": service_id})
