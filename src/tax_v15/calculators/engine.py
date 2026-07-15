from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd

from ..models import CalculationResult
from ..rules import TaxRuleBook
from ..schemas import CSV_SCHEMAS
from .building_property_tax import calculate_building_property_tax
from .common import (
    END_DIGIT_TREATMENT_LEGAL_BASIS,
    END_DIGIT_TREATMENT_METHOD,
    END_DIGIT_TREATMENT_UNIT,
    truncate_to_ten_won,
)
from .comprehensive_real_estate_tax import calculate_comprehensive_land_tax, calculate_rural_special_tax
from .comprehensive_real_estate_tax import aggregate_official_land_values
from .land_property_tax import calculate_land_assessed_value, calculate_land_property_tax
from .supplementary_taxes import calculate_fire_resource_tax, calculate_local_education_tax, calculate_urban_area_tax


def _plain(value):
    return value


def _end_digit_values(result: CalculationResult) -> dict:
    before = result.calculated_tax
    is_tax_amount = (
        before is not None
        and result.status != "not_applicable"
        and result.tax_name != "토지 시가표준액"
    )
    if not is_tax_amount:
        return {
            "calculated_tax_before_end_digit_treatment": pd.NA,
            "end_digit_treatment_unit": pd.NA,
            "end_digit_treatment_method": pd.NA,
            "end_digit_treatment_legal_basis": pd.NA,
            "calculated_tax_after_end_digit_treatment": pd.NA,
            "end_digit_treatment_difference": pd.NA,
            "calculated_tax": before,
        }

    after = truncate_to_ten_won(before)
    return {
        "calculated_tax_before_end_digit_treatment": before,
        "end_digit_treatment_unit": END_DIGIT_TREATMENT_UNIT,
        "end_digit_treatment_method": END_DIGIT_TREATMENT_METHOD,
        "end_digit_treatment_legal_basis": END_DIGIT_TREATMENT_LEGAL_BASIS,
        "calculated_tax_after_end_digit_treatment": after,
        "end_digit_treatment_difference": before - after,
        "calculated_tax": after,
    }


def _record(
    result: CalculationResult,
    *,
    tax_year: int,
    reit_name: str,
    taxpayer_id: str = "",
    asset_id: str = "",
    parcel_id: str = "",
    building_id: str = "",
    tax_classification: str = "",
    taxable_area=None,
    ownership_share=None,
) -> dict:
    record = {
        "tax_year": tax_year,
        "reit_name": reit_name,
        "taxpayer_id": taxpayer_id,
        "asset_id": asset_id,
        "parcel_id": parcel_id,
        "building_id": building_id,
        "tax_name": result.tax_name,
        "tax_classification": tax_classification,
        "official_value": _plain(result.official_value),
        "taxable_area": taxable_area,
        "ownership_share": ownership_share,
        "fair_market_value_ratio": _plain(result.fair_market_value_ratio),
        "tax_base": _plain(result.tax_base),
        "bracket": result.bracket,
        "base_amount": _plain(result.base_amount),
        "tax_rate": _plain(result.tax_rate),
        "multiplier": _plain(result.multiplier),
        "verified_tax": pd.NA,
        "variance": pd.NA,
        "calculation_status": result.status,
        "law_name": result.law_name,
        "article": result.article,
        "formula_text": result.formula_text,
        "input_source": result.input_source or "; ".join(result.issues),
        "source_url": result.source_url,
        "calculation_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    record.update(_end_digit_values(result))
    return record


def _taxpayer_for_asset(taxpayers: pd.DataFrame, asset_id: str) -> pd.Series | None:
    if taxpayers.empty or "asset_id" not in taxpayers.columns:
        return None
    rows = taxpayers[taxpayers["asset_id"].fillna("").astype(str).eq(str(asset_id))]
    if len(rows) != 1:
        return None
    return rows.iloc[0]


def calculate_holding_tax_detail(
    reit_name: str,
    assets: pd.DataFrame,
    parcels: pd.DataFrame,
    buildings: pd.DataFrame,
    taxpayers: pd.DataFrame,
    rule_rows: pd.DataFrame,
    tax_year: int,
) -> pd.DataFrame:
    """Calculate only source-backed asset-level amounts; all unresolved items fail closed."""
    rules = TaxRuleBook(rule_rows, tax_year)
    records: list[dict] = []
    selected_assets = assets[assets["reit_name"].fillna("").astype(str).eq(str(reit_name))].copy()
    if selected_assets.empty:
        return pd.DataFrame(columns=CSV_SCHEMAS["tax_calculation_detail.csv"])

    for _, asset in selected_assets.iterrows():
        asset_id = str(asset.get("asset_id", ""))
        taxpayer = _taxpayer_for_asset(taxpayers, asset_id)
        if taxpayer is None:
            blocked = CalculationResult.blocked(
                "납세의무자 판정",
                "manual_review_required",
                "자산별 납세의무자를 하나로 확인할 수 없습니다.",
            )
            records.append(_record(blocked, tax_year=tax_year, reit_name=reit_name, asset_id=asset_id))
        asset_parcels = parcels[parcels["asset_id"].fillna("").astype(str).eq(asset_id)]
        for _, parcel in asset_parcels.iterrows():
            parcel_id = str(parcel.get("parcel_id", ""))
            taxpayer_id = "" if taxpayer is None else str(taxpayer.get("taxpayer_id", ""))
            classification = "undetermined" if taxpayer is None else str(taxpayer.get("tax_classification", "undetermined"))
            assessed = calculate_land_assessed_value(parcel)
            records.append(
                _record(
                    assessed,
                    tax_year=tax_year,
                    reit_name=reit_name,
                    taxpayer_id=taxpayer_id,
                    asset_id=asset_id,
                    parcel_id=parcel_id,
                    tax_classification=classification,
                    taxable_area=parcel.get("taxable_area_m2"),
                    ownership_share=parcel.get("ownership_share"),
                )
            )
            if taxpayer is None:
                continue
            property_tax = calculate_land_property_tax(parcel, taxpayer, rules)
            records.append(
                _record(
                    property_tax,
                    tax_year=tax_year,
                    reit_name=reit_name,
                    taxpayer_id=taxpayer_id,
                    asset_id=asset_id,
                    parcel_id=parcel_id,
                    tax_classification=classification,
                    taxable_area=parcel.get("taxable_area_m2"),
                    ownership_share=parcel.get("ownership_share"),
                )
            )
            urban = calculate_urban_area_tax(
                property_tax.tax_base,
                str(parcel.get("tax_urban_area_status", "unknown")),
                rules,
            )
            education = calculate_local_education_tax(property_tax, rules)
            for supplemental in (urban, education):
                records.append(
                    _record(
                        supplemental,
                        tax_year=tax_year,
                        reit_name=reit_name,
                        taxpayer_id=taxpayer_id,
                        asset_id=asset_id,
                        parcel_id=parcel_id,
                        tax_classification=classification,
                    )
                )

        asset_buildings = buildings[buildings["asset_id"].fillna("").astype(str).eq(asset_id)]
        for _, building in asset_buildings.iterrows():
            building_id = str(building.get("building_id", ""))
            taxpayer_id = "" if taxpayer is None else str(taxpayer.get("taxpayer_id", ""))
            classification = "building" if taxpayer is not None else "undetermined"
            property_tax = calculate_building_property_tax(building, rules)
            urban = calculate_urban_area_tax(
                property_tax.tax_base,
                str(building.get("urban_area_status", "unknown")),
                rules,
            )
            education = calculate_local_education_tax(property_tax, rules)
            fire = calculate_fire_resource_tax(building, rules)
            for result in (property_tax, urban, education, fire):
                records.append(
                    _record(
                        result,
                        tax_year=tax_year,
                        reit_name=reit_name,
                        taxpayer_id=taxpayer_id,
                        asset_id=asset_id,
                        building_id=building_id,
                        tax_classification=classification,
                    )
                )

    # Comprehensive real estate tax is a taxpayer-level national aggregation.
    for taxpayer_id, group in taxpayers[taxpayers["asset_id"].isin(selected_assets["asset_id"])].groupby("taxpayer_id"):
        classifications = set(group["tax_classification"].dropna().astype(str))
        classification = next(iter(classifications)) if len(classifications) == 1 else "undetermined"
        taxpayer_asset_ids = set(group["asset_id"].dropna().astype(str))
        taxpayer_parcels = parcels[parcels["asset_id"].fillna("").astype(str).isin(taxpayer_asset_ids)].copy()
        if "taxpayer_id" not in taxpayer_parcels.columns:
            taxpayer_parcels["taxpayer_id"] = str(taxpayer_id)
        else:
            blank_taxpayer = taxpayer_parcels["taxpayer_id"].fillna("").astype(str).eq("")
            taxpayer_parcels.loc[blank_taxpayer, "taxpayer_id"] = str(taxpayer_id)
        nationwide_verified = bool(
            len(group) > 0
            and group["nationwide_land_aggregation_verified"].fillna(False).astype(str).str.lower().isin(
                ["true", "1", "verified", "yes"]
            ).all()
        )
        nationwide_value = (
            aggregate_official_land_values(taxpayer_parcels.to_dict("records"), str(taxpayer_id))
            if nationwide_verified
            else None
        )
        credit_values = pd.to_numeric(group["property_tax_credit"], errors="coerce").dropna().unique()
        property_tax_credit = Decimal(str(credit_values[0])) if len(credit_values) == 1 else None
        comp = calculate_comprehensive_land_tax(
            official_value=nationwide_value,
            classification=classification,
            property_tax_credit=property_tax_credit,
            rules=rules,
            nationwide_aggregation_verified=nationwide_verified,
            classification_verified=bool(
                len(group) > 0
                and group["validation_status"].isin(["verified_notice", "official_source_calculated"]).all()
                and group["tax_classification"].fillna("").ne("undetermined").all()
            ),
        )
        rural = calculate_rural_special_tax(comp, rules)
        records.append(_record(comp, tax_year=tax_year, reit_name=reit_name, taxpayer_id=str(taxpayer_id), tax_classification=classification))
        records.append(_record(rural, tax_year=tax_year, reit_name=reit_name, taxpayer_id=str(taxpayer_id), tax_classification=classification))

    return pd.DataFrame(records, columns=CSV_SCHEMAS["tax_calculation_detail.csv"])
