"""Typed dataclasses — data contract for encoder/decoder/profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class Layer1Config:
    protocol_version: int = 1
    perm_read: bool = True
    perm_write: bool = True
    perm_correct: bool = False
    perm_represent: bool = False
    default_split_order: int = 0
    opposing_account_explicit: bool = False
    compound_mode_active: bool = False
    bitledger_optional: bool = False
    checksum: Optional[int] = None
    sender_id: int = 0
    sub_entity_id: int = 0
    domain: int = 0  # 0=financial per wire table


@dataclass
class Layer2Config:
    transmission_type: int = 1  # 1=0b01 pre-converted; never use 0 (invalid 00)
    optimal_split: int = 8
    decimal_position: int = 2  # 0-7 wire; 2 means code 010 for D=2
    reserved: int = 1  # bit 48 equivalent region — carried in byte packing
    compound_prefix: int = 0  # 0b00 none … 0b11 unlimited
    scaling_factor_index: int = 0
    enquiry_bell: bool = False
    acknowledge_bell: bool = False
    group_sep: int = 0
    record_sep: int = 0
    file_sep: int = 0
    entity_id: int = 0
    currency_code: int = 0
    rounding_balance: int = 0


@dataclass
class TransactionRecord:
    multiplicand: int = 0
    multiplier: int = 0
    rounding_flag: bool = False
    rounding_dir: int = 0
    split_order: int = 0
    direction: int = 0
    status: int = 0
    debit_credit: int = 0
    quantity_present: bool = False
    account_pair: int = 0
    bl_direction: int = 0
    bl_status: int = 0
    completeness: int = 0
    extension_flag: bool = False
    extensions: list[int] = field(default_factory=list)
    true_value: Decimal = field(default_factory=lambda: Decimal(0))
    decoded_value: Optional[Decimal] = None
    quantity: int = 1
    continuation_subtype: Optional[int] = None  # 0–3 when account_pair == 0b1111


@dataclass
class SessionState:
    layer1: Layer1Config = field(default_factory=Layer1Config)
    layer2: Layer2Config = field(default_factory=Layer2Config)
    current_sf_index: int = 0
    current_currency: int = 0
    current_split: int = 8
    compound_open: bool = False
    compound_group_id: int = 0
    records_received: int = 0
    enquiry_pending: bool = False
    batch_rounding_sum: Decimal = field(default_factory=lambda: Decimal(0))


@dataclass
class ControlRecord:
    type_bits: int  # 3 bits
    payload: int  # 4 bits (or escape follows)
    escape_payload: Optional[int] = None
