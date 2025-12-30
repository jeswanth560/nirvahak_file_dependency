import json
from pathlib import Path

CONFIG_FILE = "../input/dependencies_v2.json"
RESULT_FILE = "../output/results.json"


def read_config():
    print("Step 1: Reading config JSON...")
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    print("Config loaded.\n")
    return config


def get_all_files_from_folder(folder_path, pattern):
    print("Step 2: Scanning folder for files...")
    print("Folder:", folder_path)
    print("Pattern:", pattern)

    folder = Path(folder_path)

    # Validate folder
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder_path}")
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")

    # Collect filenames
    all_files = []
    for path_obj in folder.glob(pattern):
        if path_obj.is_file():
            all_files.append(path_obj.name)

    all_files.sort()  # keep order stable

    if len(all_files) == 0:
        raise ValueError(
            f"No files found using pattern '{pattern}' in {folder_path}")

    print(f"Found {len(all_files)} files.\n")
    return all_files


def build_default_dependency_map(all_files):
    print("Step 3: Building default dependency map (all files independent by default)...")

    dep_map = {}
    for filename in all_files:
        dep_map[filename] = []   # default: no dependencies

    print("Default dependency map created.\n")
    return dep_map


def apply_dependency_overrides(dep_map, dependent_files):
    print("Step 4: Applying dependency overrides from JSON...")

    for item in dependent_files:
        name = item["name"]
        depends_on = item.get("depends_on", [])

        # Validation checks (simple and readable)
        if name not in dep_map:
            raise ValueError(
                f"JSON lists '{name}' but it is not found in scripts folder.")

        if name in depends_on:
            raise ValueError(f"Invalid: '{name}' cannot depend on itself.")

        # Apply override
        dep_map[name] = depends_on

        print(f"Applied: {name} depends_on {depends_on}")

    print("\nOverrides applied.\n")
    return dep_map


def split_files(dep_map):
    print("Step 5: Splitting into independent vs dependent...")

    independent_files = []
    dependent_files = {}

    for filename, deps in dep_map.items():
        if len(deps) == 0:
            independent_files.append(filename)
        else:
            dependent_files[filename] = deps

    independent_files.sort()

    print("Split complete.\n")
    return independent_files, dependent_files


def main():
    config = read_config()

    if config.get("version") != 2:
        raise ValueError("This script expects version 2 config.")

    source = config["all_files_source"]
    folder_path = source["path"]
    pattern = source.get("pattern", "*.txt")

    all_files = get_all_files_from_folder(folder_path, pattern)

    dep_map = build_default_dependency_map(all_files)

    dependent_list_from_json = config.get("dependent_files", [])
    dep_map = apply_dependency_overrides(dep_map, dependent_list_from_json)

    independent, dependent = split_files(dep_map)
    # Step 6: Save output to results.json
    results = {
        "total_files": len(dep_map),
        "independent_files": independent,
        "dependent_files": []
    }

    for file_name, deps in dependent.items():
        results["dependent_files"].append({
            "name": file_name,
            "depends_on": deps
        })

    with open(RESULT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {RESULT_FILE}")

    print("===== FINAL OUTPUT =====")
    print("Total files:", len(all_files))
    print("Independent files:", len(independent))
    print("Dependent files:", len(dependent))

    print("\n--- Independent Files (default) ---")
    for f in independent:
        print(" ", f)

    print("\n--- Dependent Files (explicit) ---")
    for f, deps in dependent.items():
        print(f" {f} depends_on {deps}")


if __name__ == "__main__":
    main()
