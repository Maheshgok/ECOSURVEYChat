#!/usr/bin/env python3
"""Fix indentation errors in models/__init__.py"""

import sys

filepath = r'c:\Users\Dell 5330\OneDrive\Documents\ECOSURVEYCHat\backend\app\models\__init__.py'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 259 (index 258) - remove extra indent for TopicBrief.updated_at
if len(lines) > 258 and lines[258].strip().startswith('updated_at'):
    lines[258] = '    updated_at = Column(DateTime(timezone=True), server_default=func.now())\n'
    print("Fixed line 259: TopicBrief.updated_at")
    
# Fix line 272 (index 271) - remove extra indent for ClaimCard.updated_at
if len(lines) > 271 and lines[271].strip().startswith('updated_at'):
    lines[271] = '    updated_at = Column(DateTime(timezone=True), server_default=func.now())\n'
    print("Fixed line 272: ClaimCard.updated_at")
    
# Fix lines 274-276 (indexes 273-275) - __table_args__ indentation
if len(lines) > 275 and lines[273].strip().startswith('__table_args__'):
    lines[273] = '    __table_args__ = (\n'
    lines[274] = '        CheckConstraint("confidence >= 0 AND confidence <= 1"),\n'
    lines[275] = '    )\n'
    print("Fixed lines 274-276: ClaimCard.__table_args__")

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)
    
print("\n✓ All indentation errors fixed")
