"""
Scry Test Suite
===============

Enterprise-grade test suite for the Scry screen reader auto-answer application.

Test Categories:
- Unit Tests: Testing individual functions/classes in isolation
- Integration Tests: Testing component interactions
- End-to-End Tests: Full system flow tests
- Security Tests: Cryptography, key management, input validation
- Performance Tests: Stress testing, timing, resource usage
- Contract Tests: API and interface contracts

Test Naming Convention:
- test_<component>_<scenario>_<expected_behavior>
- Example: test_gemini_malformed_response_returns_none

Fixtures:
- See conftest.py for reusable fixtures
- All tests should be isolated and repeatable

Coverage Target: 80%+ line coverage
"""

__version__ = "1.0.0"
