#!/usr/bin/env python3
"""
Cribl Cloud Configuration Copy Tool

Copy sources, pipelines, and routes between worker groups in Cribl Cloud.
"""

import argparse
import json
import sys
import requests


def load_config(config_path):
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


def get_auth_token(client_id, client_secret):
    """Authenticate with Cribl Cloud and get Bearer token."""
    url = "https://login.cribl.cloud/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "audience": "https://api.cribl.cloud"
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code != 200:
        print(f"Error: Authentication failed ({response.status_code})")
        print(f"Response: {response.text}")
        sys.exit(1)

    data = response.json()
    return data.get("access_token")


def build_base_url(workspace, org_id, group=None):
    """Build the Cribl Cloud API base URL."""
    base = f"https://{workspace}-{org_id}.cribl.cloud/api/v1"
    if group:
        base = f"{base}/m/{group}"
    return base


def get_worker_groups(workspace, org_id, token):
    """Fetch available worker groups from Cribl Cloud API."""
    base_url = f"https://{workspace}-{org_id}.cribl.cloud/api/v1"
    url = f"{base_url}/master/groups"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Warning: Could not fetch worker groups ({response.status_code})")
        return []

    data = response.json()
    return data.get("items", [])


def select_worker_group(groups, prompt="Select a worker group"):
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


def select_resource_type():
    """Prompt user to select what type of resource to copy."""
    print("\nWhat would you like to copy?")
    print("  1. Sources")
    print("  2. Pipelines")
    print("  3. Routes")
    print("  4. Destinations")
    print("  5. All (Sources, Pipelines, Routes, Destinations)")

    while True:
        choice = input("\nSelect resource type (enter number, or comma-separated for multiple): ").strip()

        # Handle "all" option
        if choice == '5':
            return ['sources', 'pipelines', 'destinations', 'routes']

        # Handle single or multiple selections
        try:
            selections = [int(x.strip()) for x in choice.split(',')]
            resource_map = {1: 'sources', 2: 'pipelines', 3: 'routes', 4: 'destinations'}
            resources = []
            valid = True
            for sel in selections:
                if sel in resource_map:
                    if resource_map[sel] not in resources:
                        resources.append(resource_map[sel])
                elif sel == 5:
                    return ['sources', 'pipelines', 'destinations', 'routes']
                else:
                    print(f"Invalid selection: {sel}")
                    valid = False
                    break
            if valid and resources:
                return resources
        except ValueError:
            print("Please enter valid numbers (1-5), comma-separated for multiple")


# --- Sources ---

def get_sources(base_url, token):
    """Fetch all sources from Cribl Cloud API."""
    url = f"{base_url}/system/inputs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error: Failed to fetch sources ({response.status_code})")
        print(f"Response: {response.text}")
        return []

    data = response.json()
    return data.get("items", [])


def select_sources(sources):
    """Prompt user to select sources to copy."""
    if not sources:
        print("No sources found.")
        return []

    print("\nAvailable Sources:")
    for i, source in enumerate(sources, 1):
        source_id = source.get("id", "unknown")
        source_type = source.get("type", "unknown")
        collector_type = source.get("collector", {}).get("type", "")
        if collector_type:
            print(f"  {i}. {source_id} ({source_type}/{collector_type})")
        else:
            print(f"  {i}. {source_id} ({source_type})")

    print(f"\n  a. Select all sources")
    print(f"  n. Select none (skip sources)")

    while True:
        choice = input("\nSelect source(s) to copy (comma-separated numbers, 'a' for all, 'n' for none): ").strip().lower()

        if choice == 'a':
            return sources
        if choice == 'n':
            return []

        try:
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected = []
            valid = True
            for index in indices:
                if 0 <= index < len(sources):
                    selected.append(sources[index])
                else:
                    print(f"Invalid selection: {index + 1}")
                    valid = False
                    break
            if valid:
                return selected
        except ValueError:
            print("Please enter valid numbers separated by commas, 'a' for all, or 'n' for none")


def create_source(base_url, token, source_config):
    """Create a source in the target worker group."""
    url = f"{base_url}/system/inputs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    config_to_send = source_config.copy()
    config_to_send.pop("savedState", None)

    response = requests.post(url, json=config_to_send, headers=headers)
    return response


def update_source(base_url, token, source_id, source_config):
    """Update an existing source in the target worker group."""
    url = f"{base_url}/system/inputs/{source_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    config_to_send = source_config.copy()
    config_to_send.pop("savedState", None)

    response = requests.patch(url, json=config_to_send, headers=headers)
    return response


def copy_sources(base_url, token, sources, existing_ids):
    """Copy sources to the target worker group."""
    results = {"created": [], "updated": [], "failed": []}

    for source in sources:
        source_id = source.get("id")

        if source_id in existing_ids:
            choice = input(f"  Source '{source_id}' already exists. Overwrite? (y/n): ").strip().lower()
            if choice == 'y':
                response = update_source(base_url, token, source_id, source)
                if response.status_code == 200:
                    print(f"    Updated: {source_id}")
                    results["updated"].append(source_id)
                else:
                    print(f"    Failed to update: {source_id} ({response.status_code})")
                    results["failed"].append(source_id)
            else:
                print(f"    Skipped: {source_id}")
        else:
            response = create_source(base_url, token, source)
            if response.status_code == 200:
                print(f"    Created: {source_id}")
                results["created"].append(source_id)
            else:
                print(f"    Failed to create: {source_id} ({response.status_code})")
                print(f"    Response: {response.text}")
                results["failed"].append(source_id)

    return results


# --- Pipelines ---

def get_pipelines(base_url, token):
    """Fetch all pipelines from Cribl Cloud API."""
    url = f"{base_url}/pipelines"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error: Failed to fetch pipelines ({response.status_code})")
        print(f"Response: {response.text}")
        return []

    data = response.json()
    return data.get("items", [])


def select_pipelines(pipelines):
    """Prompt user to select pipelines to copy."""
    if not pipelines:
        print("No pipelines found.")
        return []

    print("\nAvailable Pipelines:")
    for i, pipeline in enumerate(pipelines, 1):
        pipeline_id = pipeline.get("id", "unknown")
        description = pipeline.get("description", "")
        func_count = len(pipeline.get("conf", {}).get("functions", []))
        if description:
            print(f"  {i}. {pipeline_id} - {description} ({func_count} functions)")
        else:
            print(f"  {i}. {pipeline_id} ({func_count} functions)")

    print(f"\n  a. Select all pipelines")
    print(f"  n. Select none (skip pipelines)")

    while True:
        choice = input("\nSelect pipeline(s) to copy (comma-separated numbers, 'a' for all, 'n' for none): ").strip().lower()

        if choice == 'a':
            return pipelines
        if choice == 'n':
            return []

        try:
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected = []
            valid = True
            for index in indices:
                if 0 <= index < len(pipelines):
                    selected.append(pipelines[index])
                else:
                    print(f"Invalid selection: {index + 1}")
                    valid = False
                    break
            if valid:
                return selected
        except ValueError:
            print("Please enter valid numbers separated by commas, 'a' for all, or 'n' for none")


def create_pipeline(base_url, token, pipeline_config):
    """Create a pipeline in the target worker group."""
    url = f"{base_url}/pipelines"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=pipeline_config, headers=headers)
    return response


def update_pipeline(base_url, token, pipeline_id, pipeline_config):
    """Update an existing pipeline in the target worker group."""
    url = f"{base_url}/pipelines/{pipeline_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.patch(url, json=pipeline_config, headers=headers)
    return response


def copy_pipelines(base_url, token, pipelines, existing_ids):
    """Copy pipelines to the target worker group."""
    results = {"created": [], "updated": [], "failed": []}

    for pipeline in pipelines:
        pipeline_id = pipeline.get("id")

        if pipeline_id in existing_ids:
            choice = input(f"  Pipeline '{pipeline_id}' already exists. Overwrite? (y/n): ").strip().lower()
            if choice == 'y':
                response = update_pipeline(base_url, token, pipeline_id, pipeline)
                if response.status_code == 200:
                    print(f"    Updated: {pipeline_id}")
                    results["updated"].append(pipeline_id)
                else:
                    print(f"    Failed to update: {pipeline_id} ({response.status_code})")
                    results["failed"].append(pipeline_id)
            else:
                print(f"    Skipped: {pipeline_id}")
        else:
            response = create_pipeline(base_url, token, pipeline)
            if response.status_code == 200:
                print(f"    Created: {pipeline_id}")
                results["created"].append(pipeline_id)
            else:
                print(f"    Failed to create: {pipeline_id} ({response.status_code})")
                print(f"    Response: {response.text}")
                results["failed"].append(pipeline_id)

    return results


# --- Outputs/Destinations ---

def get_outputs(base_url, token):
    """Fetch all outputs/destinations from Cribl Cloud API."""
    url = f"{base_url}/system/outputs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error: Failed to fetch outputs ({response.status_code})")
        return []

    data = response.json()
    return data.get("items", [])


def select_outputs(outputs):
    """Prompt user to select outputs/destinations to copy."""
    if not outputs:
        print("No destinations found.")
        return []

    print("\nAvailable Destinations:")
    for i, output in enumerate(outputs, 1):
        output_id = output.get("id", "unknown")
        output_type = output.get("type", "unknown")
        description = output.get("description", "")
        if description:
            print(f"  {i}. {output_id} ({output_type}) - {description}")
        else:
            print(f"  {i}. {output_id} ({output_type})")

    print(f"\n  a. Select all destinations")
    print(f"  n. Select none (skip destinations)")

    while True:
        choice = input("\nSelect destination(s) to copy (comma-separated numbers, 'a' for all, 'n' for none): ").strip().lower()

        if choice == 'a':
            return outputs
        if choice == 'n':
            return []

        try:
            indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected = []
            valid = True
            for index in indices:
                if 0 <= index < len(outputs):
                    selected.append(outputs[index])
                else:
                    print(f"Invalid selection: {index + 1}")
                    valid = False
                    break
            if valid:
                return selected
        except ValueError:
            print("Please enter valid numbers separated by commas, 'a' for all, or 'n' for none")


def create_output(base_url, token, output_config):
    """Create an output/destination in the target worker group."""
    url = f"{base_url}/system/outputs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=output_config, headers=headers)
    return response


def update_output(base_url, token, output_id, output_config):
    """Update an existing output/destination in the target worker group."""
    url = f"{base_url}/system/outputs/{output_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.patch(url, json=output_config, headers=headers)
    return response


def copy_outputs(base_url, token, outputs, existing_ids):
    """Copy outputs/destinations to the target worker group."""
    results = {"created": [], "updated": [], "failed": []}

    for output in outputs:
        output_id = output.get("id")

        if output_id in existing_ids:
            choice = input(f"  Destination '{output_id}' already exists. Overwrite? (y/n): ").strip().lower()
            if choice == 'y':
                response = update_output(base_url, token, output_id, output)
                if response.status_code == 200:
                    print(f"    Updated: {output_id}")
                    results["updated"].append(output_id)
                else:
                    print(f"    Failed to update: {output_id} ({response.status_code})")
                    results["failed"].append(output_id)
            else:
                print(f"    Skipped: {output_id}")
        else:
            response = create_output(base_url, token, output)
            if response.status_code == 200:
                print(f"    Created: {output_id}")
                results["created"].append(output_id)
            else:
                print(f"    Failed to create: {output_id} ({response.status_code})")
                print(f"    Response: {response.text}")
                results["failed"].append(output_id)

    return results


# --- Routes ---

def get_routes(base_url, token):
    """Fetch all routes from Cribl Cloud API."""
    url = f"{base_url}/routes"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error: Failed to fetch routes ({response.status_code})")
        print(f"Response: {response.text}")
        return []

    data = response.json()
    # Routes API returns items which contains a 'routes' array
    items = data.get("items", [])
    if items and isinstance(items, list):
        # Get the routes from the first item (usually the 'default' route set)
        for item in items:
            if "routes" in item:
                return item.get("routes", [])
    return []


def get_routes_config(base_url, token):
    """Fetch full routes configuration from Cribl Cloud API."""
    url = f"{base_url}/routes"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error: Failed to fetch routes ({response.status_code})")
        print(f"Response: {response.text}")
        return None

    data = response.json()
    items = data.get("items", [])
    if items:
        return items[0]  # Return the full config object
    return None


def select_routes(routes):
    """Prompt user to select routes to copy."""
    if not routes:
        print("No routes found.")
        return []

    print("\nAvailable Routes:")
    for i, route in enumerate(routes, 1):
        route_id = route.get("id", "unknown")
        route_name = route.get("name", route_id)
        pipeline = route.get("pipeline", "none")
        output = route.get("output", "default")
        filter_expr = route.get("filter", "true")
        enabled = "enabled" if route.get("final", False) is False else "final"

        # Truncate filter if too long
        if len(filter_expr) > 40:
            filter_expr = filter_expr[:37] + "..."

        print(f"  {i}. {route_name} -> pipeline:{pipeline} -> output:{output}")
        print(f"      filter: {filter_expr}")

    print(f"\n  a. Select all routes")
    print(f"  n. Select none (skip routes)")

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


def update_routes(base_url, token, routes_config):
    """Update routes configuration in the target worker group."""
    url = f"{base_url}/routes/default"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.patch(url, json=routes_config, headers=headers)
    return response


def validate_route_dependencies(routes, target_pipeline_ids, target_output_ids):
    """Check if routes have dependencies that exist in target worker group."""
    valid_routes = []
    invalid_routes = []

    # Add special outputs that are always valid
    valid_outputs = target_output_ids | {"default", "devnull", ""}

    for route in routes:
        route_name = route.get("name", route.get("id", "unknown"))
        pipeline = route.get("pipeline", "")
        output = route.get("output", "default")
        missing_pipelines = []
        missing_outputs = []

        # Check pipeline (empty string or passthru are always valid)
        if pipeline and pipeline != "passthru" and pipeline not in target_pipeline_ids:
            missing_pipelines.append(pipeline)

        # Check output
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


def copy_routes(base_url, token, selected_routes, existing_routes, target_pipeline_ids, target_output_ids,
                source_pipelines=None, source_outputs=None, existing_target_pipeline_ids=None, existing_target_output_ids=None):
    """Copy routes to the target worker group."""
    results = {"created": [], "updated": [], "failed": [], "skipped": []}
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

def commit_changes(workspace, org_id, token, group, message="Cribl Export Tool: Configuration update"):
    """Commit pending configuration changes for a worker group."""
    base_url = f"https://{workspace}-{org_id}.cribl.cloud/api/v1"
    url = f"{base_url}/version/commit"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "message": message,
        "group": group
    }

    response = requests.post(url, json=payload, headers=headers)
    return response


def deploy_changes(workspace, org_id, token, group, version):
    """Deploy committed changes to a worker group."""
    base_url = f"https://{workspace}-{org_id}.cribl.cloud/api/v1"
    url = f"{base_url}/master/groups/{group}/deploy"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "version": version
    }

    response = requests.patch(url, json=payload, headers=headers)
    return response


def commit_and_deploy(workspace, org_id, token, group, message=None):
    """Commit and deploy changes to a worker group."""
    default_suffix = "Cribl Export Tool: Configuration update"

    if message:
        commit_message = f"{message} | {default_suffix}"
    else:
        commit_message = default_suffix

    print(f"\nCommitting changes to '{group}'...")
    print(f"  Message: {commit_message}")

    # Commit
    commit_response = commit_changes(workspace, org_id, token, group, commit_message)

    if commit_response.status_code != 200:
        print(f"  Failed to commit ({commit_response.status_code})")
        print(f"  Response: {commit_response.text}")
        return False

    commit_data = commit_response.json()
    items = commit_data.get("items", [])

    if not items:
        print("  No changes to commit.")
        return True

    commit_hash = items[0].get("commit")
    summary = items[0].get("summary", {})

    print(f"  Commit successful: {commit_hash[:12]}...")
    print(f"  Changes: {summary.get('changes', 0)}, Insertions: {summary.get('insertions', 0)}, Deletions: {summary.get('deletions', 0)}")

    # Deploy
    print(f"\nDeploying to '{group}'...")
    deploy_response = deploy_changes(workspace, org_id, token, group, commit_hash)

    if deploy_response.status_code == 200:
        print("  Deploy successful!")
        return True
    else:
        print(f"  Failed to deploy ({deploy_response.status_code})")
        print(f"  Response: {deploy_response.text}")
        return False


def main():
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

    required_fields = ["client_id", "client_secret", "workspace", "org_id"]
    for field in required_fields:
        if not config.get(field):
            print(f"Error: Missing required config field: {field}")
            sys.exit(1)

    print("Authenticating with Cribl Cloud...")
    token = get_auth_token(config["client_id"], config["client_secret"])
    print("Authentication successful.")

    print("\nFetching worker groups...")
    groups = get_worker_groups(config["workspace"], config["org_id"], token)

    if not groups:
        print("No worker groups found. Exiting.")
        sys.exit(1)

    # Select what to copy
    resource_types = select_resource_type()

    # Select source worker group
    print("\n--- SOURCE WORKER GROUP ---")
    source_group = select_worker_group(groups, "Select SOURCE worker group (copy from)")

    if not source_group:
        print("No source worker group selected. Exiting.")
        sys.exit(1)

    print(f"\nSelected source group: {source_group}")

    source_base_url = build_base_url(
        config["workspace"],
        config["org_id"],
        source_group
    )

    # Fetch and select resources
    selected_sources = []
    selected_pipelines = []
    selected_outputs = []
    selected_routes = []

    # Store all source data for dependency resolution
    all_source_pipelines = []
    all_source_outputs = []

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

    if not selected_sources and not selected_pipelines and not selected_outputs and not selected_routes:
        print("\nNo resources selected to copy. Exiting.")
        return

    # Select target worker group
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

    target_base_url = build_base_url(
        config["workspace"],
        config["org_id"],
        target_group
    )

    # Get existing resources in target
    existing_source_ids = set()
    existing_pipeline_ids = set()
    existing_output_ids = set()
    existing_routes = []

    if selected_sources:
        print(f"Checking existing sources in: {target_group}")
        existing_sources = get_sources(target_base_url, token)
        existing_source_ids = {s.get("id") for s in existing_sources}

    if selected_pipelines or selected_routes:
        print(f"Checking existing pipelines in: {target_group}")
        existing_pipelines = get_pipelines(target_base_url, token)
        existing_pipeline_ids = {p.get("id") for p in existing_pipelines}

    if selected_outputs or selected_routes:
        print(f"Checking existing destinations in: {target_group}")
        existing_outputs = get_outputs(target_base_url, token)
        existing_output_ids = {o.get("id") for o in existing_outputs}

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
        print("Sources:")
        print(f"  Created: {len(source_results['created'])}")
        print(f"  Updated: {len(source_results['updated'])}")
        print(f"  Failed:  {len(source_results['failed'])}")
        if source_results['failed']:
            print(f"  Failed items: {', '.join(source_results['failed'])}")

    if selected_pipelines:
        print("Pipelines:")
        print(f"  Created: {len(pipeline_results['created'])}")
        print(f"  Updated: {len(pipeline_results['updated'])}")
        print(f"  Failed:  {len(pipeline_results['failed'])}")
        if pipeline_results['failed']:
            print(f"  Failed items: {', '.join(pipeline_results['failed'])}")

    if selected_outputs:
        print("Destinations:")
        print(f"  Created: {len(output_results['created'])}")
        print(f"  Updated: {len(output_results['updated'])}")
        print(f"  Failed:  {len(output_results['failed'])}")
        if output_results['failed']:
            print(f"  Failed items: {', '.join(output_results['failed'])}")

    if selected_routes:
        print("Routes:")
        print(f"  Created: {len(route_results['created'])}")
        print(f"  Updated: {len(route_results['updated'])}")
        print(f"  Skipped: {len(route_results['skipped'])}")
        print(f"  Failed:  {len(route_results['failed'])}")
        if route_results['skipped']:
            print(f"  Skipped items: {', '.join(route_results['skipped'])}")
        if route_results['failed']:
            print(f"  Failed items: {', '.join(route_results['failed'])}")

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
