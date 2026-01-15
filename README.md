# Cribl Cloud Configuration Copy Tool

Copy sources, pipelines, routes, and destinations between worker groups with a Cribl Cloud leader.

For Packs we have this nice option in the GUI to "Copy Selectected Packs to Another Worker Group"

<img width="722" height="119" alt="Screenshot 2026-01-15 at 01 35 54" src="https://github.com/user-attachments/assets/9ed34063-db6b-43ab-a46d-72ad805c7b62" />

Wouldn't it be great if we could do the same for Global Sources, Pipelines, Routes, Destinations. Some sources like exec and the script collector cannot be bundled in a pack as of this writing. 

Current State:
<img width="495" height="114" alt="Screenshot 2026-01-15 at 01 37 19" src="https://github.com/user-attachments/assets/3e2b0e64-7314-47ac-b4f7-fcbcd92b0575" />

With cribl_migrate.py you now have an interactive terminal to copy these config's easily to other Worker Groups Hybrid or Cribl Managed all done via API. 

## Features

- Copy **Sources** between worker groups
- Copy **Pipelines** between worker groups
- Copy **Routes** between worker groups (with automatic dependency resolution)
- Copy **Destinations** between worker groups
- Interactive selection of resources to copy
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

OR

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
