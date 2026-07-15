from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .constants import V15_DATA_DIR
from .schemas import CSV_SCHEMAS, coerce_to_schema, empty_frame


STRING_ID_COLUMNS = {
    "stock_code", "dart_corp_code", "pnu", "asset_id", "parcel_id", "building_id", "taxpayer_id",
}


def load_csv(file_name: str, data_dir: Path = V15_DATA_DIR) -> pd.DataFrame:
    path = data_dir / file_name
    if not path.exists() or path.stat().st_size == 0:
        return empty_frame(file_name)
    dtype = {column: "string" for column in STRING_ID_COLUMNS if column in CSV_SCHEMAS[file_name]}
    try:
        frame = pd.read_csv(path, dtype=dtype, keep_default_na=True)
    except pd.errors.EmptyDataError:
        return empty_frame(file_name)
    return coerce_to_schema(frame, file_name)


@dataclass(frozen=True)
class V15DataBundle:
    reits: pd.DataFrame
    coverage: pd.DataFrame
    documents: pd.DataFrame
    assets: pd.DataFrame
    parcels: pd.DataFrame
    buildings: pd.DataFrame
    taxpayers: pd.DataFrame
    rules: pd.DataFrame
    calculations: pd.DataFrame
    reconciliation: pd.DataFrame
    requests: pd.DataFrame
    validations: pd.DataFrame


def load_v15_bundle(data_dir: Path = V15_DATA_DIR) -> V15DataBundle:
    return V15DataBundle(
        reits=load_csv("reit_master.csv", data_dir),
        coverage=load_csv("coverage_manifest.csv", data_dir),
        documents=load_csv("source_document_manifest.csv", data_dir),
        assets=load_csv("asset_master.csv", data_dir),
        parcels=load_csv("parcel_master.csv", data_dir),
        buildings=load_csv("building_master.csv", data_dir),
        taxpayers=load_csv("taxpayer_structure.csv", data_dir),
        rules=load_csv("tax_rule_master.csv", data_dir),
        calculations=load_csv("tax_calculation_detail.csv", data_dir),
        reconciliation=load_csv("reconciliation.csv", data_dir),
        requests=load_csv("request_list.csv", data_dir),
        validations=load_csv("validation_result.csv", data_dir),
    )
