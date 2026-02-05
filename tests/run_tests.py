#!/usr/bin/env python
"""
Test Runner Script
===================

Comprehensive test runner for the Scry test suite.
Provides various test execution modes and reporting options.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --quick            # Run fast tests only
    python run_tests.py --unit             # Run unit tests only
    python run_tests.py --integration      # Run integration tests only
    python run_tests.py --security         # Run security tests only
    python run_tests.py --performance      # Run performance tests only
    python run_tests.py --e2e              # Run E2E tests only
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --parallel         # Run tests in parallel
    python run_tests.py --verbose          # Verbose output
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


# Test directory
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent


def run_command(cmd: list, cwd: Path = PROJECT_ROOT) -> int:
    """Run a command and return the exit code."""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, cwd=str(cwd))
    return result.returncode


def get_pytest_base_cmd() -> list:
    """Get the base pytest command."""
    return [sys.executable, "-m", "pytest"]


def run_all_tests(verbose: bool = False) -> int:
    """Run all tests."""
    cmd = get_pytest_base_cmd() + [str(TEST_DIR)]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_unit_tests(verbose: bool = False) -> int:
    """Run unit tests only."""
    cmd = get_pytest_base_cmd() + [str(TEST_DIR / "unit")]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_integration_tests(verbose: bool = False) -> int:
    """Run integration tests only."""
    cmd = get_pytest_base_cmd() + [str(TEST_DIR / "integration")]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_security_tests(verbose: bool = False) -> int:
    """Run security tests only."""
    cmd = get_pytest_base_cmd() + [
        str(TEST_DIR / "security"),
        "-m", "security"
    ]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_performance_tests(verbose: bool = False) -> int:
    """Run performance tests only."""
    cmd = get_pytest_base_cmd() + [
        str(TEST_DIR / "performance"),
        "-m", "performance"
    ]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_e2e_tests(verbose: bool = False) -> int:
    """Run E2E tests only."""
    cmd = get_pytest_base_cmd() + [
        str(TEST_DIR / "e2e"),
        "-m", "e2e"
    ]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_contract_tests(verbose: bool = False) -> int:
    """Run contract tests only."""
    cmd = get_pytest_base_cmd() + [
        str(TEST_DIR / "contract"),
        "-m", "contract"
    ]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_quick_tests(verbose: bool = False) -> int:
    """Run quick tests (excluding slow and performance)."""
    cmd = get_pytest_base_cmd() + [
        str(TEST_DIR),
        "-m", "not slow and not performance",
    ]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_with_coverage(verbose: bool = False) -> int:
    """Run tests with coverage reporting."""
    cmd = get_pytest_base_cmd() + [
        str(TEST_DIR),
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=60",
    ]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_parallel(verbose: bool = False) -> int:
    """Run tests in parallel."""
    cmd = get_pytest_base_cmd() + [
        str(TEST_DIR),
        "-n", "auto",  # Requires pytest-xdist
    ]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_specific_tests(pattern: str, verbose: bool = False) -> int:
    """Run tests matching a specific pattern."""
    cmd = get_pytest_base_cmd() + [
        str(TEST_DIR),
        "-k", pattern,
    ]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def run_failed_tests(verbose: bool = False) -> int:
    """Re-run only failed tests from last run."""
    cmd = get_pytest_base_cmd() + [
        str(TEST_DIR),
        "--lf",  # Last failed
    ]
    if verbose:
        cmd.append("-v")
    return run_command(cmd)


def main():
    parser = argparse.ArgumentParser(
        description="Scry Test Suite Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_tests.py                    # Run all tests
    python run_tests.py --quick            # Run fast tests only
    python run_tests.py --unit --verbose   # Run unit tests with verbose output
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py -k test_gemini     # Run tests matching pattern
        """
    )
    
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all tests (default)",
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Run quick tests only (no slow or performance)",
    )
    parser.add_argument(
        "--unit", "-u",
        action="store_true",
        help="Run unit tests only",
    )
    parser.add_argument(
        "--integration", "-i",
        action="store_true",
        help="Run integration tests only",
    )
    parser.add_argument(
        "--security", "-s",
        action="store_true",
        help="Run security tests only",
    )
    parser.add_argument(
        "--performance", "-p",
        action="store_true",
        help="Run performance tests only",
    )
    parser.add_argument(
        "--e2e", "-e",
        action="store_true",
        help="Run E2E tests only",
    )
    parser.add_argument(
        "--contract",
        action="store_true",
        help="Run contract tests only",
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run with coverage reporting",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)",
    )
    parser.add_argument(
        "--failed", "-f",
        action="store_true",
        help="Re-run only failed tests from last run",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "-k",
        type=str,
        metavar="PATTERN",
        help="Run tests matching pattern",
    )
    
    args = parser.parse_args()
    
    # Determine which test mode to run
    if args.k:
        exit_code = run_specific_tests(args.k, args.verbose)
    elif args.unit:
        exit_code = run_unit_tests(args.verbose)
    elif args.integration:
        exit_code = run_integration_tests(args.verbose)
    elif args.security:
        exit_code = run_security_tests(args.verbose)
    elif args.performance:
        exit_code = run_performance_tests(args.verbose)
    elif args.e2e:
        exit_code = run_e2e_tests(args.verbose)
    elif args.contract:
        exit_code = run_contract_tests(args.verbose)
    elif args.quick:
        exit_code = run_quick_tests(args.verbose)
    elif args.coverage:
        exit_code = run_with_coverage(args.verbose)
    elif args.parallel:
        exit_code = run_parallel(args.verbose)
    elif args.failed:
        exit_code = run_failed_tests(args.verbose)
    else:
        # Default: run all tests
        exit_code = run_all_tests(args.verbose)
    
    # Print summary
    print(f"\n{'='*60}")
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Tests failed with exit code: {exit_code}")
    print(f"{'='*60}\n")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
