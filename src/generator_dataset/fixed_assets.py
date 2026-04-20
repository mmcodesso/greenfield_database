from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FixedAssetOpeningProfile:
    asset_account_number: str
    description: str
    gross_opening_balance: float
    accumulated_depreciation_account_number: str | None
    opening_accumulated_depreciation: float
    useful_life_months: int


OPENING_FIXED_ASSET_PROFILES = {
    "1110": FixedAssetOpeningProfile(
        asset_account_number="1110",
        description="Furniture and fixtures",
        gross_opening_balance=850000.0,
        accumulated_depreciation_account_number="1150",
        opening_accumulated_depreciation=210000.0,
        useful_life_months=96,
    ),
    "1120": FixedAssetOpeningProfile(
        asset_account_number="1120",
        description="Warehouse equipment",
        gross_opening_balance=3200000.0,
        accumulated_depreciation_account_number="1160",
        opening_accumulated_depreciation=960000.0,
        useful_life_months=144,
    ),
    "1130": FixedAssetOpeningProfile(
        asset_account_number="1130",
        description="Office equipment",
        gross_opening_balance=500000.0,
        accumulated_depreciation_account_number="1170",
        opening_accumulated_depreciation=75000.0,
        useful_life_months=72,
    ),
    "1140": FixedAssetOpeningProfile(
        asset_account_number="1140",
        description="Leasehold improvements",
        gross_opening_balance=0.0,
        accumulated_depreciation_account_number=None,
        opening_accumulated_depreciation=0.0,
        useful_life_months=0,
    ),
}


def fixed_asset_opening_profiles() -> dict[str, FixedAssetOpeningProfile]:
    return dict(OPENING_FIXED_ASSET_PROFILES)


def fixed_asset_profile(asset_account_number: str) -> FixedAssetOpeningProfile:
    return OPENING_FIXED_ASSET_PROFILES[str(asset_account_number)]


def depreciable_fixed_asset_profiles() -> dict[str, FixedAssetOpeningProfile]:
    return {
        account_number: profile
        for account_number, profile in OPENING_FIXED_ASSET_PROFILES.items()
        if profile.accumulated_depreciation_account_number and profile.useful_life_months > 0
    }


def fixed_asset_opening_balance_amounts() -> dict[str, tuple[str, float, float]]:
    amounts: dict[str, tuple[str, float, float]] = {}
    for profile in OPENING_FIXED_ASSET_PROFILES.values():
        amounts[profile.asset_account_number] = (
            f"{profile.description} opening balance",
            float(profile.gross_opening_balance),
            0.0,
        )
        if profile.accumulated_depreciation_account_number:
            amounts[profile.accumulated_depreciation_account_number] = (
                f"Accumulated depreciation {profile.description.lower()} opening balance",
                0.0,
                float(profile.opening_accumulated_depreciation),
            )
    return amounts
