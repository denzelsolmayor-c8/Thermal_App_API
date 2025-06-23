import pandas as pd

# Excel-to-database mapping
mapping = {
    "CameraID": [
        {"table": "camera_configs", "column": "camera_id"},
        {"table": "camera_in_zone", "column": "camera_id"},
        {"table": "camera_presets", "column": "camera_id"},
    ],
    "IP Camera": [{"table": "camera_configs", "column": "camera_ip"}],
    "NEW TAG": [{"table": "camera_configs", "column": "camera_name"}],
    "BAY": [
        {"table": "camera_configs", "column": "camera_location"},
        {"table": "camera_in_zone", "column": "zone_id"},
        {"table": "zones", "column": "zone_id"},
    ],
    "Bay Name": [{"table": "zones", "column": "zone_name"}],
    "Point in Preset": [{"table": "camera_presets", "column": "preset_number"}],
    # optional
    "DESCRIPTION(V1)": [{"table": "temperatures", "column": "description"}],
}


def preview_mapped_data(file):
    sheets_to_process = ["105", "205"]
    dfs = pd.read_excel(file, sheet_name=sheets_to_process)

    preview_data = {table: [] for table in set(
        m["table"] for maps in mapping.values() for m in maps)}

    for _, df in dfs.items():
        for _, row in df.iterrows():
            # 🔍 Skip if DESCRIPTION(V1) contains "alarm"
            description_value = str(row.get("DESCRIPTION(V1)", "")).lower()
            if "alarm" in description_value:
                continue

            row_data_by_table = {}

            for header, value in row.items():
                if pd.isna(value) or header not in mapping:
                    continue

                for m in mapping[header]:
                    table = m["table"]
                    column = m["column"]
                    row_data_by_table.setdefault(table, {})[column] = value

            for table, values in row_data_by_table.items():
                preview_data[table].append(values)

    return {k: v for k, v in preview_data.items() if v}
