from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Dict, List, Optional

from pydantic import Field
from pydantic.dataclasses import dataclass


class ConfirmationStatus(StrEnum):
    CONFIRMED = "confirmed"
    FINALIZED = "finalized"
    PROCESSED = "processed"


@dataclass
class SignatureResult:
    signature: str
    slot: int
    err: Annotated[Optional[Dict], Field(default=None)]
    memo: Annotated[Optional[str], Field(default=None)]
    block_time: Annotated[Optional[int], Field(default=None, alias="blockTime")]
    confirmation_status: Annotated[Optional[ConfirmationStatus], Field(default=None, alias="confirmationStatus")]


@dataclass
class NativeTransfer:
    from_user_account: Annotated[str, Field(alias="fromUserAccount")]
    to_user_account: Annotated[str, Field(alias="toUserAccount")]
    amount: Annotated[int, Field(description="The amount fo sol sent (in lamports)")]


@dataclass
class TokenTransfer:
    from_user_account: Annotated[str, Field(alias="fromUserAccount")]
    to_user_account: Annotated[str, Field(alias="toUserAccount")]
    from_token_account: Annotated[str, Field(alias="fromTokenAccount")]
    to_token_account: Annotated[str, Field(alias="toTokenAccount")]
    token_amount: Annotated[Decimal, Field(alias="tokenAmount", description="The number of tokens sent.")]
    mint: str


@dataclass
class RawTokenAmount:
    token_amount: Annotated[Decimal, Field(alias="tokenAmount")]
    decimals: int


@dataclass
class TokenBalanceChange:
    user_account: Annotated[str, Field(alias="userAccount")]
    token_account: Annotated[str, Field(alias="tokenAccount")]
    mint: str
    raw_token_amount: Annotated[RawTokenAmount, Field(alias="rawTokenAmount")]


@dataclass
class InnerInstruction:
    data: str
    program_id: Annotated[str, Field(alias="programId")]
    accounts: List[str]


@dataclass
class Instruction:
    data: str
    program_id: Annotated[str, Field(alias="programId")]
    accounts: List[str]
    inner_instructions: Annotated[List[InnerInstruction], Field(alias="innerInstructions")]


@dataclass
class TransactionError:
    error: str


@dataclass
class Nft:
    mint: str
    token_standard: Annotated[str, Field(alias="tokenStandard")]


@dataclass
class NftEvent:
    description: str
    type: str
    source: str
    amount: Annotated[int, Field(description="The amount of the NFT transaction (in lamports)")]
    fee: int
    fee_payer: Annotated[str, Field(alias="feePayer")]
    signature: str
    slot: int
    timestamp: int
    sale_type: Annotated[str, Field(alias="saleType")]
    buyer: str
    seller: str
    staker: str
    ntfs: List[Nft]


@dataclass
class AccountData:
    account: str
    native_balance_change: Annotated[
        Decimal, Field(alias="nativeBalanceChange", description="Native (SOL) balance change of the account.")
    ]
    token_balance_changes: Annotated[List[TokenBalanceChange], Field(alias="tokenBalanceChanges")]


@dataclass
class NativeAmount:
    account: str
    amount: Annotated[str, Field(description="The amount of the balance change")]


@dataclass
class ProgramInfo:
    source: str
    account: str
    program_name: Annotated[str, Field(alias="programName")]
    instruction_name: Annotated[str, Field(alias="instructionName")]


@dataclass
class InnerSwap:
    program_info: ProgramInfo
    token_inputs: Annotated[List[TokenTransfer], Field(alias="tokenInputs")]
    token_outputs: Annotated[List[TokenTransfer], Field(alias="tokenOutputs")]
    token_fees: Annotated[List[TokenTransfer], Field(alias="tokenFees")]
    native_fees: Annotated[List[NativeTransfer], Field(alias="nativeFees")]


@dataclass
class SwapEvent:
    native_input: Annotated[NativeAmount, Field(alias="nativeAmount")]
    native_output: Annotated[NativeAmount, Field(alias="nativeAmount")]
    token_inputs: Annotated[List[TokenBalanceChange], Field(alias="tokenInputs")]
    token_outputs: Annotated[List[TokenBalanceChange], Field(alias="tokenOutputs")]
    tokens_fees: Annotated[List[TokenBalanceChange], Field(alias="tokensFees")]
    native_fees: Annotated[List[NativeAmount], Field(alias="nativeFees")]
    inner_swaps: Annotated[List[InnerSwap], Field(alias="innerSwaps")]


@dataclass
class Compressed:
    type: str
    tree_id: Annotated[str, Field(alias="treeId")]
    asset_id: Annotated[str, Field(alias="assetId")]
    leaf_index: Annotated[int, Field(alias="leafIndex")]
    instruction_index: Annotated[int, Field(alias="instructionIndex")]
    inner_instruction_index: Annotated[int, Field(alias="innerInstructionIndex")]
    new_leaf_owner: Annotated[str, Field(alias="newLeafOwner")]
    old_leaf_owner: Annotated[str, Field(alias="oldLeafOwner")]


@dataclass
class Authority:
    account: str
    from_: Annotated[str, Field(alias="from")]
    to: str
    instruction_index: Annotated[int, Field(alias="instructionIndex")]
    inner_instruction_index: Annotated[int, Field(alias="innerInstructionIndex")]


@dataclass
class TransactionEvent:
    nft: NftEvent
    swap: SwapEvent
    compressed: Compressed
    distributed_compression_rewards: Annotated[int, Field(alias="distributedCompressionRewards")]


@dataclass
class EnhancedTransaction:
    description: str
    type: str
    source: str
    fee: int
    fee_payer: Annotated[str, Field(alias="feePayer")]
    signature: str
    slot: int
    timestamp: int
    native_transfers: Annotated[List[NativeTransfer], Field(alias="nativeTransfers")]
    token_transfers: Annotated[List[TokenTransfer], Field(alias="tokenTransfers")]
    account_data: Annotated[List[AccountData], Field(alias="accountData")]
    instructions: List[Instruction]
    # Disabled for simplicity for now.
    # transaction_error: Annotated[Optional[TransactionError], Field(alias="transactionError", default=None)]
    # events: TransactionEvent
