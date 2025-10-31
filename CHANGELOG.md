# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.6] - 2025-10-31

### Changed
- Refactor: integrate the `vault` and `expire` arguments into class attribute (2025-10-31)


## [0.2.5] - 2025-08-22

### Fixed
- Update meta cache if coin not found to ensure works for new list coin

## [0.2.4] - 2025-08-11

### Added
- Support transfer between accounts
- Support transfer between perpetual and spot
- Support transfer between perpetual and vaults
- Support transfer HYPE between spot and staking
- Support withdraw
- Support token delegation
- Support approve agent wallet (api wallet)
- Support convert single user to multi-sig user


## [0.2.3] - 2025-08-07

### Added
- Support to enable/disable EVM big block for HyperEVM smart contract deploy (2025-08-05)

### Changed
- Refactor: Change project layout from 'flat layout' to 'src layout' (2025-08-07)
- Integrate `uv` and add Hyperliquid EVM client (2025-08-07)

### Updated
- Update aiohttp 3.11.13 -> 3.12.15 (2025-08-02)

## [0.2.2] - 2025-07-24

### Fixed
- Strip '.0' for sz in place_twap (2025-07-24)

## [0.2.1] - 2025-07-17

### Added
- Support cancel order by cloid (2025-07-17)

## [0.2.0] - 2025-07-16

### Added
- Support place twap and cancel twap (2025-07-16)
- Support modify order (2025-07-16)

## [0.1.27] - 2025-07-14

### Fixed
- Remove redundancy get_coin_name in canceling (2025-07-14)
- Remove customized coin symbols in metas to avoid conflict (2025-07-14)

## [0.1.26] - 2025-07-02

### Fixed
- Round px properly with tick and lot size (2025-07-02)

## [0.1.20] - 2025-06-30

### Changed
- Deprecate _slippage_price, add _round_sz_px (2025-06-30)
- Unify argument name for orders: limit_px -> px, reduce_only -> ro (2025-06-30)

## [0.1.19] - 2025-06-29

### Added
- Support place TP/SL orders in place_order (2025-06-29)
- Add batch_place_orders to aggregate multiple orders into one request (2025-06-29)
- Add batch_cancel_orders to make cancels more efficient (2025-06-29)
- Use batch_place_orders in close_all_positions (2025-06-29)
- Test for batching (batch_place_orders and batch_cancel_orders) (2025-06-29)

### Fixed
- Do not add builder into OrderAction if builder is None (2025-06-29)

### Changed
- Use modern typing (python 3.10 and above) (2025-06-29)
- Comprehensive for cancel_orders (2025-06-29)
- Use more generic way in tests (2025-06-29)

### Enhanced
- Init_metas if coin not found in self.coin_names at the first time (2025-06-29)

## [0.1.18] - 2025-06-15

### Fixed
- Fix typo in ClearinghouseState (2025-06-15)

### Changed
- Remove commented codes cause not use anymore (2025-06-03)
- Add USD transfer functionalities (2025-06-03)
- Enhance type annotations and improve error handling in AsyncAPI and AsyncHyper classes (2025-06-03)

## [0.1.17] - 2025-03-30

### Added
- Add spot account state and perp account state (2025-03-30)
- Retrieve user latest ledgers (deposit, withdraw, transfer) (2025-03-26)
- Add Order types for better type hints (2025-03-18)
- Support retrieve user's portfolio (2025-03-17)
- Support get market price for all coins (2025-03-17)
- Support get coin symbol via it's name, mainly for spot coin (2025-03-16)
- Support for get account state (2025-03-15)

### Fixed
- Wrong return type for latest fundings (2025-03-26)
- Typo for get_order_status return type (2025-03-18)
- Can not get the spot coin name with it's symbols (2025-03-17)
- get_coin_symbol error with coin name for spot (2025-03-16)
- Remove un-necessary argument for market price (2025-03-15)

## [0.1.2] - 2025-03-15

### Added
- Support close all positions (2025-03-15)
- Support cancel orders (2025-03-15)

### Changed
- Change name to async-hyperliquid (2025-03-14)

## [0.1.0] - 2025-03-14

### Added
- Initial commit with basic functionality (2025-03-14)
- Project url metas for PyPI (2025-03-14)
- Pre-commit configuration (2025-03-14)

### Fixed
- Wrong test arguments for update_leverage (2025-03-14)
- Signing error for place order (2025-03-14)

### Changed
- Ignore poetry build stuffs (2025-03-14)
- Ignore test cache files (2025-03-14)
