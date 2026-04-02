"""Enum types used across the LGS Directory models."""

from __future__ import annotations

from enum import StrEnum


class StoreStatus(StrEnum):
    """Lifecycle status of a store."""

    CANDIDATE = "candidate"
    VERIFIED = "verified"
    ACTIVE = "active"
    UNRESPONSIVE = "unresponsive"
    CLOSED = "closed"


class DiscoverySource(StrEnum):
    """How a store was discovered."""

    WPN = "wpn"
    GOOGLE_PLACES = "google_places"
    TCGPLAYER = "tcgplayer"
    MANUAL = "manual"


class WpnLevel(StrEnum):
    """Wizards Play Network authorization level."""

    CORE = "core"
    PREMIUM = "premium"


class ChannelType(StrEnum):
    """Type of online presence channel."""

    WEBSITE = "website"
    TCGPLAYER = "tcgplayer"
    EBAY = "ebay"
    FACEBOOK = "facebook"
    OTHER = "other"


class Platform(StrEnum):
    """E-commerce platform running the storefront."""

    CRYSTAL_COMMERCE = "crystal_commerce"
    BINDERPOS = "binderpos"
    SHOPIFY = "shopify"
    SQUARESPACE = "squarespace"
    WOOCOMMERCE = "woocommerce"
    WORDPRESS_STRIPE = "wordpress_stripe"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class InventorySize(StrEnum):
    """Estimated MTG singles inventory size."""

    NONE = "none"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class PricingMethod(StrEnum):
    """How the store sets prices."""

    MANUAL = "manual"
    SYNCED = "synced"
    UNKNOWN = "unknown"


class PresenceStatus(StrEnum):
    """Status of an online presence."""

    ACTIVE = "active"
    UNREACHABLE = "unreachable"
    DEAD = "dead"


class CheckType(StrEnum):
    """Type of validation check."""

    HTTP_CHECK = "http_check"
    PLATFORM_DETECT = "platform_detect"
    SINGLES_DETECT = "singles_detect"
    CLOSURE_DETECT = "closure_detect"
    MANUAL_REVIEW = "manual_review"
    CONTENT_EXTRACT = "content_extract"
