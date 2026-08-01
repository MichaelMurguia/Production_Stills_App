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


_ctx_cache: dict = {}


def _project_ctx() -> tuple[str, str]:
    """(project_id, environment_id). With a project token both come from
    the token itself (query { projectToken }); with an account token the
    project id is configured and the environment resolves to "production"
    (or the only one). Nobody digs ids out of Railway's UI."""
    if _ctx_cache:
        return _ctx_cache["project"], _ctx_cache["environment"]
    if settings.RAILWAY_PROJECT_TOKEN:
        data = _gql("query { projectToken { projectId environmentId } }", {})
        tok = data.get("projectToken") or {}
        if not tok.get("projectId"):
            raise RailwayError("project token did not resolve to a project")
        _ctx_cache.update(project=tok["projectId"],
                          environment=tok["environmentId"])
    else:
        project = settings.RAILWAY_PROJECT_ID
        env = settings.RAILWAY_ENVIRONMENT_ID
        if not env:
            data = _gql(
                """query($projectId: String!) {
                     environments(projectId: $projectId) {
                       edges { node { id name } } } }""",
                {"projectId": project})
            nodes = [e["node"] for e in data["environments"]["edges"]]
            if not nodes:
                raise RailwayError("the tenants project has no environments")
            env = next((n["id"] for n in nodes if n["name"] == "production"),
                       nodes[0]["id"])
        _ctx_cache.update(project=project, environment=env)
    return _ctx_cache["project"], _ctx_cache["environment"]


def project_id() -> str:
    return _project_ctx()[0]


def environment_id() -> str:
    return _project_ctx()[1]


def _gql(query: str, variables: dict) -> dict:
    if settings.RAILWAY_PROJECT_TOKEN:
        auth_headers = {"Project-Access-Token": settings.RAILWAY_PROJECT_TOKEN}
    else:
        auth_headers = {"Authorization": f"Bearer {settings.RAILWAY_API_TOKEN}"}
    req = urllib.request.Request(
        settings.RAILWAY_API_URL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Content-Type": "application/json",
                 # Cloudflare 403s the default Python-urllib agent (verified
                 # 2026-08-01: same request, 200 with a real UA, 403 without).
                 "User-Agent": "screenboard-provisioner/1.0",
                 **auth_headers})
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
            "projectId": project_id(),
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
        {"environmentId": environment_id(),
         "serviceId": service_id,
         "input": {"startCommand": start_command}})


def upsert_variables(service_id: str, variables: dict[str, str]) -> None:
    _gql(
        """mutation($input: VariableCollectionUpsertInput!) {
             variableCollectionUpsert(input: $input) }""",
        {"input": {
            "projectId": project_id(),
            "environmentId": environment_id(),
            "serviceId": service_id,
            "variables": variables,
        }})


def create_volume(service_id: str, mount_path: str) -> str:
    data = _gql(
        """mutation($input: VolumeCreateInput!) {
             volumeCreate(input: $input) { id } }""",
        {"input": {
            "projectId": project_id(),
            "environmentId": environment_id(),
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
            "environmentId": environment_id(),
            "serviceId": service_id,
        }})
    return data["serviceDomainCreate"]["domain"]


def create_custom_domain(service_id: str, domain: str) -> str:
    """Attach a custom domain (e.g. studio-4.app.screenboardstudio.com).
    Returns any DNS target Railway reports so ops can verify the wildcard
    record; TLS issues automatically once DNS resolves."""
    data = _gql(
        """mutation($input: CustomDomainCreateInput!) {
             customDomainCreate(input: $input) {
               id domain status { dnsRecords { requiredValue } } } }""",
        {"input": {
            "projectId": project_id(),
            "environmentId": environment_id(),
            "serviceId": service_id,
            "domain": domain,
        }})
    recs = (((data.get("customDomainCreate") or {}).get("status") or {})
            .get("dnsRecords") or [])
    return recs[0].get("requiredValue", "") if recs else ""


def redeploy(service_id: str) -> None:
    """Redeploy so variables set after the initial build take effect."""
    _gql(
        """mutation($environmentId: String!, $serviceId: String!) {
             serviceInstanceRedeploy(environmentId: $environmentId,
                                     serviceId: $serviceId) }""",
        {"environmentId": environment_id(),
         "serviceId": service_id})


def delete_service(service_id: str) -> None:
    _gql("""mutation($id: String!) { serviceDelete(id: $id) }""",
         {"id": service_id})
