import json
from pathlib import Path
from collections import deque

CONFIG_FILE = "../resources/dependencies_v2.json"
OUTPUT_FILE = "../output/results_v2.json"


# ----------------------------
# Step 0: Build priority order from dependency.json (Option 1)
# Priority comes from:
#   1) dependent_files list order (as written in JSON)
#   2) depends_on list order (as written in JSON)
#   3) remaining files (not mentioned in JSON) keep discovery order
# ----------------------------
def build_priority_from_json(dependent_entries, all_files):
    priority = {}
    idx = 0

    # 1) dependent_files order
    for entry in dependent_entries:
        name = entry["name"]
        if name not in priority:
            priority[name] = idx
            idx += 1

        # also prioritize dependencies in the exact order they appear
        for dep in entry.get("depends_on", []):
            if dep not in priority:
                priority[dep] = idx
                idx += 1

    # 2) remaining files keep discovery order (NO filename sorting)
    for f in all_files:
        if f not in priority:
            priority[f] = idx
            idx += 1

    return priority

# Step 1: Read JSON config


def read_json_file(file_path):
    config_path = Path(file_path).resolve()
    with open(config_path, "r") as f:
        data = json.load(f)
    return data, config_path.parent

# Step 2: Scan scripts folder and collect all file names


def scan_folder_for_files(folder_path, pattern):
    folder = Path(folder_path)

    if not folder.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder.resolve()}")

    if not folder.is_dir():
        raise ValueError(f"Path is not a folder: {folder.resolve()}")

    all_files = []
    for item in folder.glob(pattern):
        if item.is_file():
            all_files.append(item.name)

    if len(all_files) == 0:
        raise ValueError(
            f"No files found with pattern '{pattern}' in {folder.resolve()}")

    return all_files

# Step 3: Build dependency map


def build_full_dependency_map(all_files, dependent_entries):
    # Default: everything independent
    dep_map = {}
    for f in all_files:
        dep_map[f] = []

    # Apply dependency overrides from JSON
    for entry in dependent_entries:
        file_name = entry["name"]
        depends_on_list = entry.get("depends_on", [])

        if file_name not in dep_map:
            raise ValueError(
                f"'{file_name}' is listed in JSON but not found in folder")

        if file_name in depends_on_list:
            raise ValueError(
                f"Invalid config: '{file_name}' cannot depend on itself")

        for dep in depends_on_list:
            if dep not in dep_map:
                raise ValueError(
                    f"Dependency '{dep}' for '{file_name}' not found in folder")

        dep_map[file_name] = depends_on_list

    return dep_map

# Step 4: Create "connections" (for grouping)
# We treat A depends on B as connection both ways (A <-> B)


def build_connections_for_grouping(dep_map):
    connections = {}

    # initialize empty connection set for each file
    for f in dep_map.keys():
        connections[f] = set()

    # for each dependency, connect both ways
    for file_name, deps in dep_map.items():
        for dep in deps:
            connections[file_name].add(dep)
            connections[dep].add(file_name)

    return connections


# Step 5: Find groups (connected components)
# NOTE: ordering uses JSON priority, not filename sorting.
def find_groups(connections, priority):
    visited = set()
    groups = []

    # loop through files in priority order (stable + JSON-driven)
    all_files_ordered = list(connections.keys())
    all_files_ordered.sort(key=lambda x: priority[x])

    for start in all_files_ordered:
        if start in visited:
            continue

        # Collect one full group (DFS-style)
        stack = [start]
        visited.add(start)
        group = []

        while stack:
            current = stack.pop()
            group.append(current)

            neighbors = list(connections[current])
            neighbors.sort(key=lambda x: priority[x])

            for nb in neighbors:
                if nb not in visited:
                    visited.add(nb)
                    stack.append(nb)

        # Do NOT sort group by filename; keep discovery/priority-driven collection
        groups.append(group)

    return groups

# Step 6: Order one group safely


def order_group_by_dependencies(group, dep_map, priority):
    group_set = set(group)

    # in_degree[file] = how many prerequisites inside this group
    in_degree = {}
    for f in group:
        in_degree[f] = 0

    # graph[dep] = list of files that depend on dep
    graph = {}
    for f in group:
        graph[f] = []

    # Build directed graph inside this group
    for f in group:
        deps = dep_map.get(f, [])
        for d in deps:
            if d in group_set:
                graph[d].append(f)
                in_degree[f] += 1

    # Start with nodes that have no remaining prerequisites
    ready = []
    for f in group:
        if in_degree[f] == 0:
            ready.append(f)

    ready.sort(key=lambda x: priority[x])

    q = deque(ready)
    ordered = []

    while q:
        current = q.popleft()
        ordered.append(current)

        # Reduce in_degree for dependents in JSON priority order
        dependents = list(graph[current])
        dependents.sort(key=lambda x: priority[x])

        for nxt in dependents:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                q.append(nxt)

        # Keep queue deterministic based on JSON priority
        q = deque(sorted(list(q), key=lambda x: priority[x]))

    # Cycle check
    if len(ordered) != len(group):
        raise ValueError(f"Cycle detected in group: {group}")

    return ordered

# Step 7: Build final output JSON


def build_output(groups, dep_map, priority):
    output = {"groups": []}

    group_id = 1
    for group in groups:
        ordered_files = order_group_by_dependencies(group, dep_map, priority)
        # Convert ["file1.txt","file2.txt"] into
        # [{"sequence":1,"name":"file1.txt"}, ...]
        files_with_sequence = []
        seq = 1
        for file_name in ordered_files:
            files_with_sequence.append({
                "ID": seq,
                "name": file_name
            })
            seq += 1

        output["groups"].append({
            "group_id": group_id,
            "files_in_order": files_with_sequence
        })

        group_id += 1

    return output

# Main


def main():
    config, config_dir = read_json_file(CONFIG_FILE)

    if config.get("version") != 2:
        raise ValueError("This script expects version 2 config JSON")

    source_cfg = config["all_files_source"]
    folder_path = (config_dir / source_cfg["path"]).resolve()

    pattern = source_cfg.get("pattern", "*.txt")

    # Discover all files (discovery order, no sorting)
    all_files = scan_folder_for_files(str(folder_path), pattern)

    # Build full dependency map from V2 JSON (dependent files only)
    dependent_entries = config.get("dependent_files", [])
    dep_map = build_full_dependency_map(all_files, dependent_entries)

    # Build JSON-driven priority map (Option 1)
    priority = build_priority_from_json(dependent_entries, all_files)

    # Group files by connected components using priority order
    connections = build_connections_for_grouping(dep_map)
    groups = find_groups(connections, priority)

    # Topologically order each group using priority tie-breaks
    result = build_output(groups, dep_map, priority)

    # Print to terminal
    print("\n=== GROUPED OUTPUT (TERMINAL) ===")
    print(json.dumps(result, indent=2))

    # Save to file
    out_path = Path(OUTPUT_FILE)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nSaved output to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
