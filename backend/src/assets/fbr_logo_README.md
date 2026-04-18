# FBR Logo Placeholder

**IMPORTANT**: This is a placeholder file. The official FBR Digital Invoicing System logo must be obtained before production deployment.

## Required Logo Specifications

- **Format**: PNG (preferred) or SVG
- **Resolution**: Minimum 300 DPI for print quality
- **Dimensions**: Flexible (will be scaled to fit invoice layout)
- **Color**: Official FBR branding colors
- **Filename**: fbr_logo.png

## How to Obtain

1. **Option A (Recommended)**: Contact FBR technical support for official logo file
2. **Option B**: Download from FBR digital invoicing portal (if accessible)
3. **Option C**: Extract from FBR official website at https://fbr.gov.pk/

## Installation

Once obtained, replace this file with the actual logo:
```bash
# Place the logo file in this directory
cp /path/to/official/fbr_logo.png backend/src/assets/fbr_logo.png
```

## Development Note

The PDF service will check for this file and raise an error if missing. For development purposes, you can:
- Use this placeholder (PDF generation will fail with clear error message)
- Create a temporary logo image for testing
- Skip logo validation during development (not recommended)

**Status**: ⚠️ PLACEHOLDER - Official logo required for production
