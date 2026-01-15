#!/usr/bin/env python3
"""
Cribl Cloud Configuration Copy Tool

Copy sources, pipelines, and routes between worker groups in Cribl Cloud.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import requests


# Type aliases for clarity
Config = dict[str, Any]
Resource = dict[str, Any]
ResourceList = list[Resource]
CopyResults = dict[str, list[str]]


def load_config(config_path: str) -> Config:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}")
        print("Copy config.example.json to config.json and fill in your credentials.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        sys.exit(1)


def make_auth_headers(token: str) -> dict[str, str]:
    """Create authorization headers for API requests."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def get_auth_token(client_id: str, client_secret: str) -> str:
    """Authenticate with Cribl Cloud and get Bearer token."""
    url = "https://login.cribl.cloud/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": "https://api.cribl.cloud"
    }

    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})

    if response.status_code != 200:
        print(f"Error: Authentication failed ({response.status_code})")
        print(f"Response: {response.text}")
        sys.exit(1)

    return response.json().get("access_token")


def build_base_url(workspace: str, org_id: str, group: str | None = None) -> str:
    """Build the Cribl Cloud API base URL."""
    base = f"https://{workspace}-{org_id}.cribl.cloud/api/v1"
    if group:
        return f"{base}/m/{group}"
    return base


def get_worker_groups(workspace: str, org_id: str, token: str) -> ResourceList:
    """Fetch available worker groups from Cribl Cloud API."""
    base_url = f"https://{workspace}-{org_id}.cribl.cloud/api/v1"
    url = f"{base_url}/master/groups"

    response = requests.get(url, headers=make_auth_headers(token))

    if response.status_code != 200:
        print(f"Warning: Could not fetch worker groups ({response.status_code})")
        return []

    return response.json().get("items", [])


def select_worker_group(groups: ResourceList, prompt: str = "Select a worker group") -> str | None:
    """Prompt user to select a worker group interactively."""
    if not groups:
        print("No worker groups found.")
        return None

    print("\nAvailable Worker Groups:")
    for i, group in enumerate(groups, 1):
        group_id = group.get("id", "unknown")
        description = group.get("description", "")
        if description:
            print(f"  {i}. {group_id} - {description}")
        else:
            print(f"  {i}. {group_id}")

    while True:
        try:
            choice = input(f"\n{prompt} (enter number): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(groups):
                return groups[index].get("id")
            print(f"Please enter a number between 1 and {len(groups)}")
        except ValueError:
            print("Please enter a valid number")


def select_resource_type() -> list[str]:
    """Prompt user to select what type of resource to copy."""
    print("\nWhat would you like to copy?")
    print("  1. Sources")
    print("  2. Pipelines")
    print("  3. Routes")
    print("  4. Destinations")
    print("  5. All (Sources, Pipelines, Routes, Destinations)")

    all_resources = ['sources', 'pipelines', 'destinations', 'routes']
    resource_map = {1: 'sources', 2: 'pipelines', 3: 'routes', 4: 'destinations'}

    while True:
        choice = input("\nSelect resource type (enter number, or comma-separated for multiple): ").strip()

        if choice == '5':
            return all_resources

        try:
            selections = [int(x.strip()) for x in choice.split(',')]
            resources = []
            valid = True

            for sel in selections:
                if sel == 5:
                    return all_resources
                if sel in resource_map:
                    if resource_map[sel] not in resources:
                        resources.append(resource_map[sel])
                else:
                    print(f"Invalid selection: {sel}")
                    valid = False
                    break

            if valid and resources:
                return resources
        except ValueError:
            print("Please enter valid numbers (1-5), comma-separated for multiple")


# --- Generic Resource Operations ---

def format_source_item(source: Resource) -> str:
    """Format a source item for display."""
    source_id = source.get("id", "unknown")
    source_type = source.get("type", "unknown")
    collector_type = source.get("collector", {}).get("type", "")
    if collector_type:
        return f"{source_id} ({source_type}/{collector_type})"
    return f"{source_id} ({source_type})"


def format_pipeline_item(pipeline: Resource) -> str:
    """Format a pipeline item for display."""
    pipeline_id = pipeline.get("id", "unknown")
    description = pipeline.get("description", "")
    func_count = len(pipeline.get("conf", {}).get("functions", []))
    if description:
        return f"{pipeline_id} - {description} ({func_count} functions)"
    return f"{pipeline_id} ({func_count} functions)"


def format_output_item(output: Resource) -> str:
    """Format an output/destination item for display."""
    output_id = output.get("id", "unknown")
    output_type = output.get("type", "unknown")
    description = output.get("description", "")
    if description:
        return f"{output_id} ({output_type}) - {description}"
    return f"{output_id} ({output_type})"


def select_items(
    items: ResourceList,
    resource_name: str,
    format_func: callable
) -> ResourceList:
    """Generic function to prompt user to select items from a list."""
    if not items:
        print(f"No {resource_name} found.")
        return []

    print(f"\nAvailable {resource_name.title()}:")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {format_func(item)}")

    print(f"\n  a. Select all {resource_name}")
    print(f"  n. Select none (skip {resource_name})")

    while True:
        choice = input(f"\nSelect {resource_name} to copy (comma-separated numbers, 'a' for all, 'n' for none): ").strip().lower()

        if choice == 'a':
            return items
        if choice == 'n':
            return []

        try:
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected = []
            valid = True

            for index in indices:
                if 0 <= index < len(items):
                    selected.append(items[index])
                else:
                    print(f"Invalid selection: {index + 1}")
                    valid = False
                    break

            if valid:
                return selected
        except ValueError:
            print("Please enter valid numbers separated by commas, 'a' for all, or 'n' for none")


def fetch_resources(base_url: str, token: str, endpoint: str, resource_name: str) -> ResourceList:
    """Fetch resources from a Cribl Cloud API endpoint."""
    url = f"{base_url}/{endpoint}"
    response = requests.get(url, headers=make_auth_headers(token))

    if response.status_code != 200:
        print(f"Error: Failed to fetch {resource_name} ({response.status_code})")
        print(f"Response: {response.text}")
        return []

    return response.json().get("items", [])


def create_resource(
    base_url: str,
    token: str,
    endpoint: str,
    config: Resource,
    strip_fields: list[str] | None = None
) -> requests.Response:
    """Create a resource via POST request."""
    url = f"{base_url}/{endpoint}"
    config_to_send = config.copy()

    for field in (strip_fields or []):
        config_to_send.pop(field, None)

    return requests.post(url, json=config_to_send, headers=make_auth_headers(token))


def update_resource(
    base_url: str,
    token: str,
    endpoint: str,
    resource_id: str,
    config: Resource,
    strip_fields: list[str] | None = None
) -> requests.Response:
    """Update a resource via PATCH request."""
    url = f"{base_url}/{endpoint}/{resource_id}"
    config_to_send = config.copy()

    for field in (strip_fields or []):
        config_to_send.pop(field, None)

    return requests.patch(url, json=config_to_send, headers=make_auth_headers(token))


def copy_resources(
    base_url: str,
    token: str,
    resources: ResourceList,
    existing_ids: set[str],
    endpoint: str,
    resource_name: str,
    strip_fields: list[str] | None = None
) -> CopyResults:
    """Copy resources to the target worker group."""
    results: CopyResults = {"created": [], "updated": [], "failed": []}

    for resource in resources:
        resource_id = resource.get("id")

        if resource_id in existing_ids:
            choice = input(f"  {resource_name.title()} '{resource_id}' already exists. Overwrite? (y/n): ").strip().lower()
            if choice == 'y':
                response = update_resource(base_url, token, endpoint, resource_id, resource, strip_fields)
                if response.status_code == 200:
                    print(f"    Updated: {resource_id}")
                    results["updated"].append(resource_id)
                else:
                    print(f"    Failed to update: {resource_id} ({response.status_code})")
                    results["failed"].append(resource_id)
            else:
                print(f"    Skipped: {resource_id}")
        else:
            response = create_resource(base_url, token, endpoint, resource, strip_fields)
            if response.status_code == 200:
                print(f"    Created: {resource_id}")
                results["created"].append(resource_id)
            else:
                print(f"    Failed to create: {resource_id} ({response.status_code})")
                print(f"    Response: {response.text}")
                results["failed"].append(resource_id)

    return results


# --- Sources ---

def get_sources(base_url: str, token: str) -> ResourceList:
    """Fetch all sources from Cribl Cloud API."""
    return fetch_resources(base_url, token, "system/inputs", "sources")


def select_sources(sources: ResourceList) -> ResourceList:
    """Prompt user to select sources to copy."""
    return select_items(sources, "sources", format_source_item)


def create_source(base_url: str, token: str, source_config: Resource) -> requests.Response:
    """Create a source in the target worker group."""
    return create_resource(base_url, token, "system/inputs", source_config, ["savedState"])


def update_source(base_url: str, token: str, source_id: str, source_config: Resource) -> requests.Response:
    """Update an existing source in the target worker group."""
    return update_resource(base_url, token, "system/inputs", source_id, source_config, ["savedState"])


def copy_sources(base_url: str, token: str, sources: ResourceList, existing_ids: set[str]) -> CopyResults:
    """Copy sources to the target worker group."""
    return copy_resources(base_url, token, sources, existing_ids, "system/inputs", "source", ["savedState"])


# --- Pipelines ---

def get_pipelines(base_url: str, token: str) -> ResourceList:
    """Fetch all pipelines from Cribl Cloud API."""
    return fetch_resources(base_url, token, "pipelines", "pipelines")


def select_pipelines(pipelines: ResourceList) -> ResourceList:
    """Prompt user to select pipelines to copy."""
    return select_items(pipelines, "pipelines", format_pipeline_item)


def create_pipeline(base_url: str, token: str, pipeline_config: Resource) -> requests.Response:
    """Create a pipeline in the target worker group."""
    return create_resource(base_url, token, "pipelines", pipeline_config)


def update_pipeline(base_url: str, token: str, pipeline_id: str, pipeline_config: Resource) -> requests.Response:
    """Update an existing pipeline in the target worker group."""
    return update_resource(base_url, token, "pipelines", pipeline_id, pipeline_config)


def copy_pipelines(base_url: str, token: str, pipelines: ResourceList, existing_ids: set[str]) -> CopyResults:
    """Copy pipelines to the target worker group."""
    return copy_resources(base_url, token, pipelines, existing_ids, "pipelines", "pipeline")


# --- Outputs/Destinations ---

def get_outputs(base_url: str, token: str) -> ResourceList:
    """Fetch all outputs/destinations from Cribl Cloud API."""
    return fetch_resources(base_url, token, "system/outputs", "outputs")


def select_outputs(outputs: ResourceList) -> ResourceList:
    """Prompt user to select outputs/destinations to copy."""
    return select_items(outputs, "destinations", format_output_item)


def create_output(base_url: str, token: str, output_config: Resource) -> requests.Response:
    """Create an output/destination in the target worker group."""
    return create_resource(base_url, token, "system/outputs", output_config)


def update_output(base_url: str, token: str, output_id: str, output_config: Resource) -> requests.Response:
    """Update an existing output/destination in the target worker group."""
    return update_resource(base_url, token, "system/outputs", output_id, output_config)


def copy_outputs(base_url: str, token: str, outputs: ResourceList, existing_ids: set[str]) -> CopyResults:
    """Copy outputs/destinations to the target worker group."""
    return copy_resources(base_url, token, outputs, existing_ids, "system/outputs", "destination")


# --- Routes ---

def get_routes(base_url: str, token: str) -> ResourceList:
    """Fetch all routes from Cribl Cloud API."""
    url = f"{base_url}/routes"
    response = requests.get(url, headers=make_auth_headers(token))

    if response.status_code != 200:
        print(f"Error: Failed to fetch routes ({response.status_code})")
        print(f"Response: {response.text}")
        return []

    # Routes API returns items which contains a 'routes' array
    items = response.json().get("items", [])
    if items and isinstance(items, list):
        # Get the routes from the first item (usually the 'default' route set)
        for item in items:
            if "routes" in item:
                return item.get("routes", [])
    return []


def get_routes_config(base_url: str, token: str) -> Resource | None:
    """Fetch full routes configuration from Cribl Cloud API."""
    url = f"{base_url}/routes"
    response = requests.get(url, headers=make_auth_headers(token))

    if response.status_code != 200:
        print(f"Error: Failed to fetch routes ({response.status_code})")
        print(f"Response: {response.text}")
        return None

    items = response.json().get("items", [])
    return items[0] if items else None


def format_route_item(route: Resource) -> str:
    """Format a route item for display."""
    route_name = route.get("name", route.get("id", "unknown"))
    pipeline = route.get("pipeline", "none")
    output = route.get("output", "default")
    filter_expr = route.get("filter", "true")

    if len(filter_expr) > 40:
        filter_expr = filter_expr[:37] + "..."

    return f"{route_name} -> pipeline:{pipeline} -> output:{output}\n      filter: {filter_expr}"


def select_routes(routes: ResourceList) -> ResourceList:
    """Prompt user to select routes to copy."""
    if not routes:
        print("No routes found.")
        return []

    print("\nAvailable Routes:")
    for i, route in enumerate(routes, 1):
        print(f"  {i}. {format_route_item(route)}")

    print("\n  a. Select all routes")
    print("  n. Select none (skip routes)")

    while True:
        choice = input("\nSelect route(s) to copy (comma-separated numbers, 'a' for all, 'n' for none): ").strip().lower()

        if choice == 'a':
            return routes
        if choice == 'n':
            return []

        try:
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected = []
            valid = True

            for index in indices:
                if 0 <= index < len(routes):
                    selected.append(routes[index])
                else:
                    print(f"Invalid selection: {index + 1}")
                    valid = False
                    break

            if valid:
                return selected
        except ValueError:
            print("Please enter valid numbers separated by commas, 'a' for all, or 'n' for none")


def update_routes(base_url: str, token: str, routes_config: Resource) -> requests.Response:
    """Update routes configuration in the target worker group."""
    url = f"{base_url}/routes/default"
    return requests.patch(url, json=routes_config, headers=make_auth_headers(token))


def validate_route_dependencies(
    routes: ResourceList,
    target_pipeline_ids: set[str],
    target_output_ids: set[str]
) -> tuple[ResourceList, list[dict[str, Any]]]:
    """Check if routes have dependencies that exist in target worker group."""
    valid_routes = []
    invalid_routes = []
    valid_outputs = target_output_ids | {"default", "devnull", ""}

    for route in routes:
        route_name = route.get("name", route.get("id", "unknown"))
        pipeline = route.get("pipeline", "")
        output = route.get("output", "default")
        missing_pipelines = []
        missing_outputs = []

        if pipeline and pipeline != "passthru" and pipeline not in target_pipeline_ids:
            missing_pipelines.append(pipeline)

        if output and output not in valid_outputs:
            missing_outputs.append(output)

        if missing_pipelines or missing_outputs:
            invalid_routes.append({
                "route": route,
                "name": route_name,
                "missing_pipelines": missing_pipelines,
                "missing_outputs": missing_outputs
            })
        else:
            valid_routes.append(route)

    return valid_routes, invalid_routes


def copy_routes(
    base_url: str,
    token: str,
    selected_routes: ResourceList,
    existing_routes: ResourceList,
    target_pipeline_ids: set[str],
    target_output_ids: set[str],
    source_pipelines: ResourceList | None = None,
    source_outputs: ResourceList | None = None,
    existing_target_pipeline_ids: set[str] | None = None,
    existing_target_output_ids: set[str] | None = None
) -> dict[str, Any]:
    """Copy routes to the target worker group."""
    results: dict[str, Any] = {"created": [], "updated": [], "failed": [], "skipped": []}
    dep_results = {"pipelines_created": [], "outputs_created": [], "pipelines_failed": [], "outputs_failed": []}

    # Validate route dependencies first
    valid_routes, invalid_routes = validate_route_dependencies(
        selected_routes, target_pipeline_ids, target_output_ids
    )

    # Report invalid routes
    if invalid_routes:
        print("\n  Warning: Some routes have missing dependencies in target worker group:")
        all_missing_pipelines = set()
        all_missing_outputs = set()
        for item in invalid_routes:
            missing_desc = []
            for p in item['missing_pipelines']:
                missing_desc.append(f"pipeline '{p}'")
                all_missing_pipelines.add(p)
            for o in item['missing_outputs']:
                missing_desc.append(f"output '{o}'")
                all_missing_outputs.add(o)
            print(f"    - {item['name']}: missing {', '.join(missing_desc)}")

        print("\n  Options:")
        print("    1. Skip routes with missing dependencies")
        print("    2. Copy missing dependencies from source, then copy routes")
        print("    3. Cancel route copy entirely")

        while True:
            choice = input("\n  Select option (1, 2, or 3): ").strip()
            if choice == '1':
                for item in invalid_routes:
                    results["skipped"].append(item["name"])
                    print(f"    Skipping: {item['name']}")
                break
            elif choice == '2':
                # Copy missing dependencies
                print("\n  Copying missing dependencies...")

                # Separate pack pipelines from regular pipelines
                missing_pack_pipelines = {p for p in all_missing_pipelines if p.startswith("pack:")}
                missing_regular_pipelines = all_missing_pipelines - missing_pack_pipelines

                # Warn about pack pipelines (cannot be auto-copied)
                if missing_pack_pipelines:
                    print(f"\n  Warning: Pack pipelines cannot be auto-copied. Missing: {', '.join(missing_pack_pipelines)}")
                    print("  Please manually install these packs in the target worker group first.")

                # Copy missing regular pipelines
                if missing_regular_pipelines and source_pipelines:
                    pipelines_to_copy = [p for p in source_pipelines if p.get("id") in missing_regular_pipelines]
                    if pipelines_to_copy:
                        print(f"\n  Copying {len(pipelines_to_copy)} missing pipeline(s)...")
                        for pipeline in pipelines_to_copy:
                            pipeline_id = pipeline.get("id")
                            if pipeline_id in (existing_target_pipeline_ids or set()):
                                print(f"    Pipeline '{pipeline_id}' already exists, skipping")
                                target_pipeline_ids.add(pipeline_id)
                            else:
                                response = create_pipeline(base_url, token, pipeline)
                                if response.status_code == 200:
                                    print(f"    Created pipeline: {pipeline_id}")
                                    target_pipeline_ids.add(pipeline_id)
                                    dep_results["pipelines_created"].append(pipeline_id)
                                else:
                                    print(f"    Failed to create pipeline: {pipeline_id} ({response.status_code})")
                                    dep_results["pipelines_failed"].append(pipeline_id)
                    elif missing_regular_pipelines:
                        print(f"  Warning: Could not find source pipelines: {', '.join(missing_regular_pipelines)}")

                # Copy missing outputs
                if all_missing_outputs and source_outputs:
                    outputs_to_copy = [o for o in source_outputs if o.get("id") in all_missing_outputs]
                    if outputs_to_copy:
                        print(f"\n  Copying {len(outputs_to_copy)} missing destination(s)...")
                        for output in outputs_to_copy:
                            output_id = output.get("id")
                            if output_id in (existing_target_output_ids or set()):
                                print(f"    Destination '{output_id}' already exists, skipping")
                                target_output_ids.add(output_id)
                            else:
                                response = create_output(base_url, token, output)
                                if response.status_code == 200:
                                    print(f"    Created destination: {output_id}")
                                    target_output_ids.add(output_id)
                                    dep_results["outputs_created"].append(output_id)
                                else:
                                    print(f"    Failed to create destination: {output_id} ({response.status_code})")
                                    dep_results["outputs_failed"].append(output_id)
                    else:
                        print(f"  Warning: Could not find source destinations: {', '.join(all_missing_outputs)}")

                # Re-validate routes after copying dependencies
                valid_routes, still_invalid = validate_route_dependencies(
                    selected_routes, target_pipeline_ids, target_output_ids
                )

                if still_invalid:
                    print("\n  Some routes still have missing dependencies after copy:")
                    for item in still_invalid:
                        missing_desc = []
                        for p in item['missing_pipelines']:
                            missing_desc.append(f"pipeline '{p}'")
                        for o in item['missing_outputs']:
                            missing_desc.append(f"output '{o}'")
                        print(f"    - {item['name']}: missing {', '.join(missing_desc)}")
                        results["skipped"].append(item["name"])
                break
            elif choice == '3':
                print("  Route copy cancelled.")
                for item in invalid_routes:
                    results["skipped"].append(item["name"])
                results["dep_results"] = dep_results
                return results
            else:
                print("  Please enter 1, 2, or 3")

    if not valid_routes:
        print("\n  No valid routes to copy.")
        return results

    # Build a map of existing routes by id
    existing_route_map = {r.get("id"): r for r in existing_routes}
    existing_route_ids = set(existing_route_map.keys())

    # Build the new routes list
    new_routes = list(existing_routes)  # Start with existing routes

    for route in valid_routes:
        route_id = route.get("id")
        route_name = route.get("name", route_id)

        if route_id in existing_route_ids:
            choice = input(f"  Route '{route_name}' already exists. Overwrite? (y/n): ").strip().lower()
            if choice == 'y':
                # Find and replace the existing route
                for i, existing in enumerate(new_routes):
                    if existing.get("id") == route_id:
                        new_routes[i] = route
                        results["updated"].append(route_name)
                        print(f"    Will update: {route_name}")
                        break
            else:
                print(f"    Skipped: {route_name}")
        else:
            # Add new route at the beginning (before default route)
            # Find the position before any "final" routes
            insert_pos = 0
            for i, existing in enumerate(new_routes):
                if existing.get("final", False):
                    insert_pos = i
                    break
                insert_pos = i + 1

            new_routes.insert(insert_pos, route)
            results["created"].append(route_name)
            print(f"    Will create: {route_name}")

    # Only update if there are changes
    if results["created"] or results["updated"]:
        print("\n  Applying route changes...")
        routes_config = {"id": "default", "routes": new_routes}
        response = update_routes(base_url, token, routes_config)

        if response.status_code == 200:
            print("    Routes updated successfully.")
        else:
            print(f"    Failed to update routes ({response.status_code})")
            print(f"    Response: {response.text}")
            # Mark all as failed
            results["failed"] = results["created"] + results["updated"]
            results["created"] = []
            results["updated"] = []

    results["dep_results"] = dep_results
    return results


# --- Commit and Deploy ---

DEFAULT_COMMIT_MESSAGE = "Cribl Export Tool: Configuration update"


def commit_changes(
    workspace: str,
    org_id: str,
    token: str,
    group: str,
    message: str = DEFAULT_COMMIT_MESSAGE
) -> requests.Response:
    """Commit pending configuration changes for a worker group."""
    base_url = f"https://{workspace}-{org_id}.cribl.cloud/api/v1"
    url = f"{base_url}/version/commit"
    payload = {"message": message, "group": group}
    return requests.post(url, json=payload, headers=make_auth_headers(token))


def deploy_changes(
    workspace: str,
    org_id: str,
    token: str,
    group: str,
    version: str
) -> requests.Response:
    """Deploy committed changes to a worker group."""
    base_url = f"https://{workspace}-{org_id}.cribl.cloud/api/v1"
    url = f"{base_url}/master/groups/{group}/deploy"
    return requests.patch(url, json={"version": version}, headers=make_auth_headers(token))


def commit_and_deploy(
    workspace: str,
    org_id: str,
    token: str,
    group: str,
    message: str | None = None
) -> bool:
    """Commit and deploy changes to a worker group."""
    commit_message = f"{message} | {DEFAULT_COMMIT_MESSAGE}" if message else DEFAULT_COMMIT_MESSAGE

    print(f"\nCommitting changes to '{group}'...")
    print(f"  Message: {commit_message}")

    commit_response = commit_changes(workspace, org_id, token, group, commit_message)

    if commit_response.status_code != 200:
        print(f"  Failed to commit ({commit_response.status_code})")
        print(f"  Response: {commit_response.text}")
        return False

    items = commit_response.json().get("items", [])

    if not items:
        print("  No changes to commit.")
        return True

    commit_hash = items[0].get("commit")
    summary = items[0].get("summary", {})

    print(f"  Commit successful: {commit_hash[:12]}...")
    print(f"  Changes: {summary.get('changes', 0)}, Insertions: {summary.get('insertions', 0)}, Deletions: {summary.get('deletions', 0)}")

    print(f"\nDeploying to '{group}'...")
    deploy_response = deploy_changes(workspace, org_id, token, group, commit_hash)

    if deploy_response.status_code == 200:
        print("  Deploy successful!")
        return True

    print(f"  Failed to deploy ({deploy_response.status_code})")
    print(f"  Response: {deploy_response.text}")
    return False


def validate_config(config: Config) -> None:
    """Validate that required config fields are present."""
    required_fields = ["client_id", "client_secret", "workspace", "org_id"]
    for field in required_fields:
        if not config.get(field):
            print(f"Error: Missing required config field: {field}")
            sys.exit(1)


def print_results_summary(name: str, results: CopyResults, include_skipped: bool = False) -> None:
    """Print a summary of copy results for a resource type."""
    print(f"{name}:")
    print(f"  Created: {len(results.get('created', []))}")
    print(f"  Updated: {len(results.get('updated', []))}")
    if include_skipped:
        print(f"  Skipped: {len(results.get('skipped', []))}")
    print(f"  Failed:  {len(results.get('failed', []))}")

    if include_skipped and results.get('skipped'):
        print(f"  Skipped items: {', '.join(results['skipped'])}")
    if results.get('failed'):
        print(f"  Failed items: {', '.join(results['failed'])}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy Cribl Cloud sources, pipelines, and routes between worker groups."
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config file (default: config.json)"
    )
    args = parser.parse_args()

    config = load_config(args.config)
    validate_config(config)

    print("Authenticating with Cribl Cloud...")
    token = get_auth_token(config["client_id"], config["client_secret"])
    print("Authentication successful.")

    print("\nFetching worker groups...")
    groups = get_worker_groups(config["workspace"], config["org_id"], token)

    if not groups:
        print("No worker groups found. Exiting.")
        sys.exit(1)

    resource_types = select_resource_type()

    print("\n--- SOURCE WORKER GROUP ---")
    source_group = select_worker_group(groups, "Select SOURCE worker group (copy from)")

    if not source_group:
        print("No source worker group selected. Exiting.")
        sys.exit(1)

    print(f"\nSelected source group: {source_group}")

    source_base_url = build_base_url(config["workspace"], config["org_id"], source_group)

    # Fetch and select resources
    selected_sources: ResourceList = []
    selected_pipelines: ResourceList = []
    selected_outputs: ResourceList = []
    selected_routes: ResourceList = []
    all_source_pipelines: ResourceList = []
    all_source_outputs: ResourceList = []

    if 'sources' in resource_types:
        print(f"\nFetching sources from: {source_group}")
        sources = get_sources(source_base_url, token)
        print(f"Found {len(sources)} source(s).")
        if sources:
            selected_sources = select_sources(sources)
            print(f"Selected {len(selected_sources)} source(s).")

    if 'pipelines' in resource_types or 'routes' in resource_types:
        print(f"\nFetching pipelines from: {source_group}")
        all_source_pipelines = get_pipelines(source_base_url, token)
        print(f"Found {len(all_source_pipelines)} pipeline(s).")
        if 'pipelines' in resource_types and all_source_pipelines:
            selected_pipelines = select_pipelines(all_source_pipelines)
            print(f"Selected {len(selected_pipelines)} pipeline(s).")

    if 'destinations' in resource_types or 'routes' in resource_types:
        print(f"\nFetching destinations from: {source_group}")
        all_source_outputs = get_outputs(source_base_url, token)
        print(f"Found {len(all_source_outputs)} destination(s).")
        if 'destinations' in resource_types and all_source_outputs:
            selected_outputs = select_outputs(all_source_outputs)
            print(f"Selected {len(selected_outputs)} destination(s).")

    if 'routes' in resource_types:
        print(f"\nFetching routes from: {source_group}")
        routes = get_routes(source_base_url, token)
        print(f"Found {len(routes)} route(s).")
        if routes:
            selected_routes = select_routes(routes)
            print(f"Selected {len(selected_routes)} route(s).")

    if not any([selected_sources, selected_pipelines, selected_outputs, selected_routes]):
        print("\nNo resources selected to copy. Exiting.")
        return

    print("\n--- TARGET WORKER GROUP ---")
    target_group = select_worker_group(groups, "Select TARGET worker group (copy to)")

    if not target_group:
        print("No target worker group selected. Exiting.")
        sys.exit(1)

    if target_group == source_group:
        print("Warning: Source and target groups are the same!")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Exiting.")
            return

    print(f"\nSelected target group: {target_group}")

    target_base_url = build_base_url(config["workspace"], config["org_id"], target_group)

    # Get existing resources in target
    existing_source_ids: set[str] = set()
    existing_pipeline_ids: set[str] = set()
    existing_output_ids: set[str] = set()
    existing_routes: ResourceList = []

    if selected_sources:
        print(f"Checking existing sources in: {target_group}")
        existing_source_ids = {s.get("id") for s in get_sources(target_base_url, token)}

    if selected_pipelines or selected_routes:
        print(f"Checking existing pipelines in: {target_group}")
        existing_pipeline_ids = {p.get("id") for p in get_pipelines(target_base_url, token)}

    if selected_outputs or selected_routes:
        print(f"Checking existing destinations in: {target_group}")
        existing_output_ids = {o.get("id") for o in get_outputs(target_base_url, token)}

    if selected_routes:
        print(f"Checking existing routes in: {target_group}")
        existing_routes = get_routes(target_base_url, token)

    # Confirm copy operation
    print(f"\nReady to copy from '{source_group}' to '{target_group}':")
    if selected_sources:
        print(f"  - {len(selected_sources)} source(s)")
    if selected_pipelines:
        print(f"  - {len(selected_pipelines)} pipeline(s)")
    if selected_outputs:
        print(f"  - {len(selected_outputs)} destination(s)")
    if selected_routes:
        print(f"  - {len(selected_routes)} route(s)")

    confirm = input("\nProceed? (y/n): ").strip().lower()

    if confirm != 'y':
        print("Operation cancelled.")
        return

    # Copy resources
    source_results = {"created": [], "updated": [], "failed": []}
    pipeline_results = {"created": [], "updated": [], "failed": []}
    output_results = {"created": [], "updated": [], "failed": []}
    route_results = {"created": [], "updated": [], "failed": [], "skipped": [], "dep_results": {}}

    if selected_sources:
        print("\nCopying sources...")
        source_results = copy_sources(target_base_url, token, selected_sources, existing_source_ids)

    if selected_pipelines:
        print("\nCopying pipelines...")
        pipeline_results = copy_pipelines(target_base_url, token, selected_pipelines, existing_pipeline_ids)
        # Update existing_pipeline_ids with newly created pipelines for route validation
        existing_pipeline_ids.update(pipeline_results['created'])
        existing_pipeline_ids.update(pipeline_results['updated'])

    if selected_outputs:
        print("\nCopying destinations...")
        output_results = copy_outputs(target_base_url, token, selected_outputs, existing_output_ids)
        # Update existing_output_ids with newly created outputs for route validation
        existing_output_ids.update(output_results['created'])
        existing_output_ids.update(output_results['updated'])

    if selected_routes:
        print("\nCopying routes...")
        route_results = copy_routes(
            target_base_url, token, selected_routes, existing_routes,
            existing_pipeline_ids, existing_output_ids,
            source_pipelines=all_source_pipelines,
            source_outputs=all_source_outputs,
            existing_target_pipeline_ids=existing_pipeline_ids,
            existing_target_output_ids=existing_output_ids
        )

    # Summary
    print("\n--- SUMMARY ---")
    if selected_sources:
        print_results_summary("Sources", source_results)
    if selected_pipelines:
        print_results_summary("Pipelines", pipeline_results)
    if selected_outputs:
        print_results_summary("Destinations", output_results)
    if selected_routes:
        print_results_summary("Routes", route_results, include_skipped=True)

        # Show dependencies that were auto-copied
        dep_results = route_results.get('dep_results', {})
        if dep_results.get('pipelines_created') or dep_results.get('outputs_created'):
            print("\nAuto-copied dependencies for routes:")
            if dep_results.get('pipelines_created'):
                print(f"  Pipelines created: {', '.join(dep_results['pipelines_created'])}")
            if dep_results.get('outputs_created'):
                print(f"  Destinations created: {', '.join(dep_results['outputs_created'])}")
            if dep_results.get('pipelines_failed'):
                print(f"  Pipelines failed: {', '.join(dep_results['pipelines_failed'])}")
            if dep_results.get('outputs_failed'):
                print(f"  Destinations failed: {', '.join(dep_results['outputs_failed'])}")

    # Check if any changes were made
    total_created = (
        len(source_results.get('created', [])) +
        len(pipeline_results.get('created', [])) +
        len(output_results.get('created', [])) +
        len(route_results.get('created', []))
    )
    total_updated = (
        len(source_results.get('updated', [])) +
        len(pipeline_results.get('updated', [])) +
        len(output_results.get('updated', [])) +
        len(route_results.get('updated', []))
    )

    if total_created > 0 or total_updated > 0:
        # Offer to commit and deploy
        print(f"\n--- COMMIT & DEPLOY ---")
        deploy_choice = input(f"Commit and deploy changes to '{target_group}'? (y/n): ").strip().lower()

        if deploy_choice == 'y':
            user_message = input("Enter commit message (press Enter for default): ").strip()
            success = commit_and_deploy(
                config["workspace"],
                config["org_id"],
                token,
                target_group,
                user_message if user_message else None
            )
            if success:
                print("\nAll done! Changes have been committed and deployed.")
            else:
                print("\nCommit/deploy failed. You may need to commit and deploy manually in the Cribl UI.")
        else:
            print("\nChanges saved but not committed. Remember to commit and deploy in the Cribl UI.")
    else:
        print("\nNo changes were made.")


if __name__ == "__main__":
    main()
