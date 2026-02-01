#!/usr/bin/env python
"""Generate a secure secret key for use in .env files."""

import secrets
import argparse


def generate_secret_key(length: int = 32) -> str:
    """Generate a cryptographically secure random hex string.
    
    Args:
        length: Number of random bytes (output will be 2x this in hex chars).
                Default 32 bytes = 64 hex characters = 256 bits.
    
    Returns:
        A secure random hex string.
    """
    return secrets.token_hex(length)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a secure secret key for JWT or other cryptographic uses."
    )
    parser.add_argument(
        "-l", "--length",
        type=int,
        default=32,
        help="Number of random bytes (default: 32, produces 64 hex characters)"
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=1,
        help="Number of keys to generate (default: 1)"
    )
    
    args = parser.parse_args()
    
    for _ in range(args.count):
        print(generate_secret_key(args.length))


if __name__ == "__main__":
    main()
