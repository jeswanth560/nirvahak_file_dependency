import json

INPUT_JSON = "dependencies.json"
OUTPUT_JSON = "grouped_files.json"


def load_dependencies(path: str):
    with open(path, "r") as f:
        data = json.load(f)
    return data["files"]


def group_files(files):
    """
    Group files into:
      - group 1: no dependencies
      - group 2: exactly 1 dependency
      - group 3: more than 1 dependency 
    """
    group1 = []  # no dependencies
    group2 = []  # exactly 1 dependency
    group3 = []  # more than 1 dependency

    for item in files:
        # Convert file1.sql -> file1.txt for the OUTPUT
        name = item["name"].replace(".sql", ".txt")
        deps = item.get("depends_on", [])

        if len(deps) == 0:
            group1.append(name)
        elif len(deps) == 1:
            group2.append(name)
        else:
            group3.append(name)

    def build_group(group_id, description, names):
        return {
            "group_id": group_id,
            "description": description,
            "text_files": [
                {"id": idx + 1, "name": fname} for idx, fname in enumerate(names)
            ],
        }

    result = {
        "groups": [
            build_group(1, "files with no dependencies", group1),
            build_group(2, "files with exactly 1 dependency", group2),
            build_group(3, "files with more than 1 dependency", group3),
        ]
    }

    return result


def main():
    files = load_dependencies(INPUT_JSON)
    grouped = group_files(files)

    print(json.dumps(grouped, indent=2))

    with open(OUTPUT_JSON, "w") as f:
        json.dump(grouped, f, indent=2)


if __name__ == "__main__":
    main()
