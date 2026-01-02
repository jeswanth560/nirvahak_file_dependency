import json
from pathlib import Path
from collections import deque


# Update these paths for your current structure
CONFIG_FILE = "../01_resources/version1_dependencies.json"
OUTPUT_FILE = "../03_output/results_version1.json"


# ----------------------------
# Step 1: Read JSON config (Version-1)
# ----------------------------
def read_json_file(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


# ----------------------------
# Step 2: Build dep_map from Version-1 JSON (all files included)
# ----------------------------
def build_dep_map_from_v1(files_list):
    dep_map = {}
    order_list = []  # preserves the JSON order

    for entry in files_list:
        name = entry["name"]
        deps = entry.get("depends_on", [])

        if name in dep_map:
            raise ValueError(f"Duplicate file name in JSON: {name}")

        if name in deps:
            raise ValueError(f"Invalid: '{name}' cannot depend on itself")

        dep_map[name] = deps
        order_list.append(name)

    # Validate: every dependency must exist in files list
    all_names = set(dep_map.keys())
    for name, deps in dep_map.items():
        for d in deps:
            if d not in all_names:
                raise ValueError(
                    f"Dependency '{d}' listed for '{name}' not found in JSON files list")

    return dep_map, order_list


# ----------------------------
# Step 3: Priority = JSON order (NOT filename)
# ----------------------------
def build_priority_from_order_list(order_list):
    priority = {}
    for idx, name in enumerate(order_list):
        priority[name] = idx
    return priority


# ----------------------------
# Step 4: Build connections for grouping (undirected)
# ----------------------------
def build_connections_for_grouping(dep_map):
    connections = {f: set() for f in dep_map.keys()}

    for file_name, deps in dep_map.items():
        for dep in deps:
            connections[file_name].add(dep)
            connections[dep].add(file_name)

    return connections


# ----------------------------
# Step 5: Find groups (connected components) using JSON priority
# ----------------------------
def find_groups(connections, priority):
    visited = set()
    groups = []

    all_files_ordered = list(connections.keys())
    all_files_ordered.sort(key=lambda x: priority[x])

    for start in all_files_ordered:
        if start in visited:
            continue

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

        groups.append(group)

    return groups


# ----------------------------
# Step 6: Topological sort inside a group (tie-break = JSON priority)
# ----------------------------
def order_group_by_dependencies(group, dep_map, priority):
    group_set = set(group)

    in_degree = {f: 0 for f in group}
    graph = {f: [] for f in group}

    for f in group:
        for d in dep_map.get(f, []):
            if d in group_set:
                graph[d].append(f)
                in_degree[f] += 1

    ready = [f for f in group if in_degree[f] == 0]
    ready.sort(key=lambda x: priority[x])

    q = deque(ready)
    ordered = []

    while q:
        current = q.popleft()
        ordered.append(current)

        dependents = list(graph[current])
        dependents.sort(key=lambda x: priority[x])

        for nxt in dependents:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                q.append(nxt)

        q = deque(sorted(list(q), key=lambda x: priority[x]))

    if len(ordered) != len(group):
        raise ValueError(f"Cycle detected in group: {group}")

    return ordered


# ----------------------------
# Step 7: Build output with sequence numbers (like your V1 screenshot)
# ----------------------------
def build_output(groups, dep_map, priority):
    output = {"groups": []}
    group_id = 1

    for group in groups:
        ordered_files = order_group_by_dependencies(group, dep_map, priority)

        text_files = []
        seq = 1
        for name in ordered_files:
            text_files.append({
                "sequence": seq,
                "name": name
            })
            seq += 1

        output["groups"].append({
            "group_id": group_id,
            "text_files": text_files
        })

        group_id += 1

    return output


# ----------------------------
# Main
# ----------------------------
def main():
    config = read_json_file(CONFIG_FILE)

    # Version-1 format: { "files": [ ... ] }
    files_list = config.get("files", [])
    if not files_list:
        raise ValueError(
            "Version-1 JSON must contain a non-empty 'files' list")

    dep_map, order_list = build_dep_map_from_v1(files_list)
    priority = build_priority_from_order_list(order_list)

    connections = build_connections_for_grouping(dep_map)
    groups = find_groups(connections, priority)

    result = build_output(groups, dep_map, priority)

    # Print output
    print("\n=== VERSION-1 GROUPED OUTPUT (TERMINAL) ===")
    print(json.dumps(result, indent=2))

    # Save output
    out_path = Path(OUTPUT_FILE)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nSaved output to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
