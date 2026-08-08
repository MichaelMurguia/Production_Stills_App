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


def configure_graceful_deploys(service_id: str) -> None:
    """Deploys must never kill a render mid-flight (observed live
    2026-08-02: a fleet update restarted a tenant during its first panel
    generation). Overlap starts the new instance before the old one
    stops; draining gives in-flight requests five minutes to finish —
    longer than any single render call."""
    _gql(
        """mutation($environmentId: String!, $serviceId: String!,
                    $input: ServiceInstanceUpdateInput!) {
             serviceInstanceUpdate(environmentId: $environmentId,
                                   serviceId: $serviceId, input: $input) }""",
        {"environmentId": environment_id(),
         "serviceId": service_id,
         "input": {"overlapSeconds": 60, "drainingSeconds": 300}})


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


def volume_capabilities() -> dict:
    """What Railway's API actually offers for volumes, asked of the schema
    rather than assumed (2026-08-07: one studio's volume is 108x smaller
    than another's and needs growing — the question is whether we can do
    it from here or whether it is a dashboard action).

    A FIXED introspection query: no caller input reaches it, so this can
    never become an arbitrary-GraphQL hole behind the admin token.
    """
    data = _gql("""query {
        mutationType: __type(name: "Mutation") { fields { name } }
        updateInput: __type(name: "VolumeUpdateInput") { inputFields { name } }
        createInput: __type(name: "VolumeCreateInput") { inputFields { name } }
        volume: __type(name: "Volume") { fields { name } }
        instance: __type(name: "VolumeInstance") { fields { name } }
        instanceUpdate: __type(name: "VolumeInstanceUpdateInput") {
          inputFields { name } }
      }""", {})
    names = [f["name"] for f in (data.get("mutationType") or {}).get("fields", [])]

    def fields(key: str, prop: str) -> list:
        return [f["name"] for f in (data.get(key) or {}).get(prop, [])]

    out = {
        "volume_mutations": sorted(n for n in names if "olume" in n),
        "volume_update_input": fields("updateInput", "inputFields"),
        "volume_create_input": fields("createInput", "inputFields"),
        "volume_fields": fields("volume", "fields"),
        "volume_instance_fields": fields("instance", "fields"),
        "volume_instance_update_input": fields("instanceUpdate", "inputFields"),
    }
    # The whole point of asking: is there a size anywhere we can set?
    sizey = [k for k, v in out.items()
             if k.endswith("input") and any("size" in f.lower() for f in v)]
    out["resizable_via"] = sizey
    return out


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


def list_custom_domains(service_id: str) -> list[dict]:
    data = _gql(
        """query($projectId: String!, $environmentId: String!, $serviceId: String!) {
             domains(projectId: $projectId, environmentId: $environmentId,
                     serviceId: $serviceId) {
               customDomains { id domain } } }""",
        {"projectId": project_id(), "environmentId": environment_id(),
         "serviceId": service_id})
    return (data.get("domains") or {}).get("customDomains") or []


def list_services() -> list[dict]:
    """All services in the project — {id, name}. Ops tooling: lets the
    wildcard-attach endpoint find the storefront service by name instead
    of anyone digging ids out of Railway's UI."""
    data = _gql(
        """query($projectId: String!) {
             project(id: $projectId) {
               services { edges { node { id name } } } } }""",
        {"projectId": project_id()})
    return [e["node"] for e in
            ((data.get("project") or {}).get("services") or {}).get("edges", [])]


def create_custom_domain_records(service_id: str, domain: str) -> list[dict]:
    """Attach a domain and return EVERY DNS record Railway asks for
    (wildcards need both the CNAME and an _acme-challenge record for the
    certificate). Each record: {hostlabel, requiredValue}."""
    data = _gql(
        """mutation($input: CustomDomainCreateInput!) {
             customDomainCreate(input: $input) {
               id domain status { dnsRecords { hostlabel requiredValue } } } }""",
        {"input": {
            "projectId": project_id(),
            "environmentId": environment_id(),
            "serviceId": service_id,
            "domain": domain,
        }})
    return (((data.get("customDomainCreate") or {}).get("status") or {})
            .get("dnsRecords") or [])


def service_domains(service_id: str) -> list[str]:
    """The service's *.up.railway.app hostnames — the always-reliable door."""
    data = _gql(
        """query($projectId: String!, $environmentId: String!, $serviceId: String!) {
             domains(projectId: $projectId, environmentId: $environmentId,
                     serviceId: $serviceId) {
               serviceDomains { domain } } }""",
        {"projectId": project_id(), "environmentId": environment_id(),
         "serviceId": service_id})
    return [d["domain"] for d in
            ((data.get("domains") or {}).get("serviceDomains") or [])]


def delete_custom_domain(domain_id: str) -> None:
    _gql("""mutation($id: String!) { customDomainDelete(id: $id) }""",
         {"id": domain_id})


def redeploy(service_id: str) -> None:
    """Redeploy so variables set after the initial build take effect."""
    _gql(
        """mutation($environmentId: String!, $serviceId: String!) {
             serviceInstanceRedeploy(environmentId: $environmentId,
                                     serviceId: $serviceId) }""",
        {"environmentId": environment_id(),
         "serviceId": service_id})


def list_deployments(service_id: str, limit: int = 3) -> list[dict]:
    """Most recent deployments for a service — {id, status, createdAt,
    meta}. Ops visibility: shows whether a fleet update actually queued a
    build, what commit it took, and whether it failed."""
    data = _gql(
        """query($input: DeploymentListInput!, $first: Int!) {
             deployments(input: $input, first: $first) {
               edges { node { id status createdAt meta } } } }""",
        {"input": {"projectId": project_id(),
                   "environmentId": environment_id(),
                   "serviceId": service_id},
         "first": limit})
    return [e["node"] for e in
            (data.get("deployments") or {}).get("edges", [])]


def deploy_latest(service_id: str, commit_sha: str = "") -> None:
    """Build and deploy the service at commit_sha — the fleet-update
    primitive ("updates land the day they ship"). Without an explicit
    sha, Railway rebuilds the commit the service is PINNED to (observed
    live 2026-08-01: a fleet update 'succeeded' by rebuilding the
    day-one commit), so the caller passes the released sha — normally
    the storefront's own RAILWAY_GIT_COMMIT_SHA, since storefront and
    tenants deploy from the same repo and branch."""
    variables: dict = {"environmentId": environment_id(),
                       "serviceId": service_id}
    if commit_sha:
        _gql(
            """mutation($environmentId: String!, $serviceId: String!,
                        $commitSha: String) {
                 serviceInstanceDeploy(environmentId: $environmentId,
                                       serviceId: $serviceId,
                                       commitSha: $commitSha) }""",
            {**variables, "commitSha": commit_sha})
        return
    _gql(
        """mutation($environmentId: String!, $serviceId: String!) {
             serviceInstanceDeploy(environmentId: $environmentId,
                                   serviceId: $serviceId) }""",
        variables)


def delete_service(service_id: str) -> None:
    _gql("""mutation($id: String!) { serviceDelete(id: $id) }""",
         {"id": service_id})
