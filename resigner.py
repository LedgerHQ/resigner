#!/usr/bin/env python3

from src.api import SigningService

# For running through uwgsi
resigner = SigningService()


if __name__ == '__main__':
  # Run Resigner locally
  _resigner = SigningService(debug=True)
  _resigner.run()