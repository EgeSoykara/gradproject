"""Unpack the supplied engine beside Django and apply its compatibility patch."""

import argparse
import os
import stat
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

UI_ROOT = Path(__file__).resolve().parent.parent
ENGINE_DIR = 'PortfolioAI_Ege'
REQUIRED = (
    'pyproject.toml',
    'service_bridge.py',
    'data/snapshot/USDTRY.parquet',
    'data/universe_scores.json',
    'models/sentiment/model.safetensors',
    'models/final/metadata.json',
)


def verify_engine(engine):
    missing = [name for name in REQUIRED if not (engine / name).is_file()]
    if missing:
        raise ValueError(f'Engine files are missing: {", ".join(missing)}')


def unpack_engine(archive, staging):
    with ZipFile(archive) as package:
        entries = []
        for entry in package.infolist():
            parts = PurePosixPath(entry.filename).parts
            if not parts or parts[0] != ENGINE_DIR:
                continue
            if any(
                part.lower() in {'env', '.git', '__pycache__', '.ruff_cache'}
                or (part.lower().startswith('.env') and part.lower() != '.env.example')
                for part in parts
            ):
                continue
            if stat.S_ISLNK(entry.external_attr >> 16) or any(
                part == '..' or '\\' in part or os.path.isreserved(part) for part in parts
            ):
                raise ValueError(f'Unsafe path in the engine archive: {entry.filename}')
            entries.append(entry)
        package.extractall(staging, entries)


def apply_patch(engine):
    patch = UI_ROOT / 'integrations' / 'ai-engine.patch'
    command = ['git', 'apply', '--ignore-space-change']
    applied = subprocess.run(
        [*command, '--reverse', '--check', str(patch)], cwd=engine, capture_output=True
    )
    if applied.returncode:
        subprocess.run([*command, '--check', str(patch)], cwd=engine, check=True)
        subprocess.run([*command, str(patch)], cwd=engine, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    if not args.archive.is_file():
        parser.error(f'File not found: {args.archive}')

    engine = UI_ROOT.parent / ENGINE_DIR
    if engine.exists():
        verify_engine(engine)
        apply_patch(engine)
    else:
        with tempfile.TemporaryDirectory(prefix='.engine-', dir=engine.parent) as staging:
            unpack_engine(args.archive, staging)
            extracted = Path(staging) / ENGINE_DIR
            verify_engine(extracted)
            apply_patch(extracted)
            extracted.rename(engine)

    for source in (engine / 'results/dashboard_examples').glob('persona_*.json'):
        destination = UI_ROOT / 'dashboard/mock' / source.name
        if not destination.exists():
            destination.write_bytes(source.read_bytes())
    print(f'Engine ready at {engine}')


if __name__ == '__main__':
    main()
