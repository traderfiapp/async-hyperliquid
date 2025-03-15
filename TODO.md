# TODO List for Async Hyperliquid

This document outlines pending features, improvements, and tasks for the Async Hyperliquid project.

## High Priority

- [ ] Implement missing order management methods:
  - `get_all_positions()`: Add functionality to retrieve user's positions
  - [ ] `modify_order()`: Add functionality to modify existing orders
  - [ ] `close_all_positions()`: Add functionality to close all open positions
  - [ ] `close_position()`: Add functionality to close a specific position

- [ ] Add comprehensive error handling:
  - [ ] Implement proper exception handling and custom exceptions
  - [ ] Add retry logic for network failures
  - [ ] Improve error messages and logging

## Medium Priority

- [ ] Enhance documentation:
  - [ ] Add detailed docstrings to all methods and classes
  - [ ] Create examples for common use cases
  - [ ] Document all API parameters and return types
  - [ ] Generate API documentation using Sphinx

- [ ] Improve test coverage:
  - [ ] Add unit tests for utility functions
  - [ ] Add mock tests for API interactions
  - [ ] Add integration tests for the entire workflow
  - [ ] Implement CI/CD pipeline

- [ ] Add WebSocket support:
  - [ ] Implement market data streaming
  - [ ] Add user data streaming (order updates, position changes)
  - [ ] Ensure proper reconnection handling

## Low Priority

- [ ] Add convenience methods:
  - [ ] Account balance summary
  - [ ] Position risk calculation
  - [ ] Order book analysis
  - [ ] Market trend indicators

- [ ] Performance optimizations:
  - [ ] Connection pooling
  - [ ] Request batching
  - [ ] Caching frequently accessed data

- [ ] Additional features:
  - [ ] Support for more order types
  - [ ] Command-line interface (CLI)
  - [ ] Rate limiting management
  - [ ] Historical data retrieval and analysis

## Project Management

- [ ] Release process:
  - [ ] Define semantic versioning strategy
  - [ ] Create CHANGELOG.md
  - [ ] Set up automated releases

- [ ] Community:
  - [ ] Create contribution guidelines
  - [ ] Add issue templates
  - [ ] Improve README with badge status
