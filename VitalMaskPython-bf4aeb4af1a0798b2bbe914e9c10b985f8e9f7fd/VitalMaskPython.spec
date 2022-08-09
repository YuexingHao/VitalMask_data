# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from kivy_deps import sdl2, glew
import asyncio
import binascii
import bleak
import psycopg2
import csv

from kivy.tools.packaging.pyinstaller_hooks import get_deps_minimal, get_deps_all, hookspath, runtime_hooks

block_cipher = None


a = Analysis(['dashboard.py'],
             pathex=['C:\\Users\\Daniel\\Documents\\VitalMaskPython'],
             hookspath=hookspath(),
             runtime_hooks=runtime_hooks(),
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False,
             **get_deps_minimal(video=None))
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
	  a.binaries,
          [],
          exclude_binaries=True,
          name='VitalMaskPython',
          debug=True,
          bootloader_ignore_signals=False,
          strip=False,
          icon='applogo.ico',
          upx=True,
          console=False )
coll = COLLECT(exe, Tree('C:\\Users\\Daniel\\Documents\\VitalMaskPython'),
               a.binaries,
               a.zipfiles,
               a.datas,
               *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
               strip=False,
               upx=True,
               name='VitalMaskPython')
