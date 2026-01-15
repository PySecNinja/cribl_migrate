# Cribl Cloud Configuration Copy Tool

## Overview

This tool facilitates the copying of configurations between worker groups and edge fleets on a Cribl Cloud leader. While Cribl's GUI handles Packs efficiently, moving individual global configurations often requires manual intervention. This utility handles that process via the API.

## The Challenge

Currently, the Cribl GUI provides a convenient native option to **"Copy Selected Packs to Another Worker Group"**:

<img width="722" height="119" alt="Screenshot 2026-01-15 at 01 35 54" src="https://github.com/user-attachments/assets/9ed34063-db6b-43ab-a46d-72ad805c7b62" />


However, this functionality does not extend to **Global Sources, Pipelines, Routes, or Destinations**. 

This limitation becomes a significant bottleneck when:
* **Migrating Large Configs:** Moving 30+ sources manually is tedious and error-prone.
* **Handling Non-Packable Items:** Certain sources—such as `exec` and the Script Collector—cannot be bundled in a Pack (as of this writing), forcing administrators to manually recreate them in target groups.

**Sources Example - Missing Button:**

<img width="591" height="117" alt="Screenshot 2026-01-15 at 01 47 05" src="https://github.com/user-attachments/assets/12400b18-4e5c-4c5c-9b7e-207415ec558d" />

## The Solution: `cribl_migrate.py`

`cribl_migrate.py` bridges this gap by providing an interactive terminal interface to copy these configurations easily to other Worker Groups.

## Features

- Copy **Sources** between worker groups
- Copy **Pipelines** between worker groups
- Copy **Routes** between worker groups (with automatic dependency resolution)
- Copy **Destinations** between worker groups
- Interactive CLI: Simple prompts guide the migration process.
- Automatic conflict detection with overwrite prompts
- Commit and deploy changes directly from the tool

## Requirements

- Python 3.6+
- `requests` library

```bash
pip install requests
```

## Configuration

Create a `config.json` file with your Cribl Cloud credentials:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "workspace": "your-workspace",
  "org_id": "your-org-id"
}
```

You can obtain API credentials from the Cribl Cloud UI under **Settings > API Credentials**.

## Usage

```bash
python cribl_migrate.py
```

OR

```bash
python cribl_migrate.py --config config.json
```

### Interactive Menu

1. Select resource type(s) to copy:
   - `1` - Sources
   - `2` - Pipelines
   - `3` - Routes
   - `4` - Destinations
   - `5` - All (Sources, Pipelines, Routes, Destinations)

2. Select source worker group (copy from)

3. Select specific resources or use `a` for all, `n` for none

4. Select target worker group (copy to)

5. Confirm overwrites for existing resources

6. Optionally commit and deploy changes

## Route Dependency Resolution

When copying routes, the tool validates that referenced pipelines and destinations exist in the target worker group. If dependencies are missing, you can:

1. **Skip** routes with missing dependencies
2. **Auto-copy** missing pipelines and destinations from source
3. **Cancel** the route copy operation

**Note:** Pack pipelines (e.g., `pack:cribl-windows-events`) cannot be auto-copied. Install required packs manually in the target worker group before copying routes that depend on them.

## Example

```
$ python cribl_migrate.py

Authenticating with Cribl Cloud...
Authentication successful.

Fetching worker groups...

What would you like to copy?
  1. Sources
  2. Pipelines
  3. Routes
  4. Destinations
  5. All (Sources, Pipelines, Routes, Destinations)

Select resource type (enter number, or comma-separated for multiple): 5

--- SOURCE WORKER GROUP ---
Available Worker Groups:
  1. default - Default Worker Group
  2. production
  3. development

Select SOURCE worker group (copy from) (enter number): 1
Selected source group: default

...

--- SUMMARY ---
Sources:
  Created: 10
  Updated: 5
  Failed:  0
Pipelines:
  Created: 8
  Updated: 3
  Failed:  0
...

Commit and deploy changes to 'development'? (y/n): y
Committing changes...
Deploy successful!
```

## License

MIT
