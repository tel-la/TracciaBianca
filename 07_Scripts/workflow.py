#!/usr/bin/env python3
"""CLI: eseguire con qgis_python.sh, non con il Python di sistema."""
import argparse
import json
import os
from pathlib import Path

from qgis.core import QgsApplication, QgsProcessingFeedback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init', help='Catalogazione iniziale, senza cancellazioni')
    p = sub.add_parser('prepare')
    p.add_argument('name')
    p.add_argument('--bbox', nargs=4, type=float, required=True, metavar=('WEST', 'SOUTH', 'EAST', 'NORTH'))
    p.add_argument('--source', action='append', default=[])
    p.add_argument('--crs', default='EPSG:32633')
    p.add_argument('--maxzoom', type=int, default=16)
    p.add_argument('--max-missing-percent', type=float, default=0)
    for cmd in ('update', 'export', 'check'):
        p = sub.add_parser(cmd)
        p.add_argument('area', type=Path)
        if cmd == 'update':
            p.add_argument('--max-missing-percent', type=float)
        if cmd == 'export':
            p.add_argument('--minzoom', type=int)
            p.add_argument('--maxzoom', type=int)
            p.add_argument('--max-missing-percent', type=float)
            p.add_argument('--mode', choices=['single','split'])
            p.add_argument('--max-bytes', type=int)
            p.add_argument('--warning-bytes', type=int)
    sub.add_parser('list')
    p = sub.add_parser('grid', help='Crea/estende la griglia alpina; senza bbox usa Lago Maggiore–Friuli')
    p.add_argument('--bbox', nargs=4, type=float)
    p.add_argument('--all-cells', action='store_true', help='Non applica il filtro altimetrico delle montagne')
    p.add_argument('--min-elevation', type=float, default=600)
    p.add_argument('--min-mountain-percent', type=float, default=1.0)
    p = sub.add_parser('prepare-cells'); p.add_argument('cells', nargs='+')
    p.add_argument('--max-missing-percent', type=float, default=0.01)
    p = sub.add_parser('rename-cell'); p.add_argument('cell'); p.add_argument('name')
    sub.add_parser('atlas', help='Genera catalogo, QGIS e PDF')
    p = sub.add_parser('publish-cell'); p.add_argument('cell')
    args = parser.parse_args()
    runtime = args.root / '.qgis_runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    app = QgsApplication([], False, str(runtime) + '/')
    app.setPrefixPath(os.environ.get('QGIS_PREFIX_PATH', '/Applications/QGIS.app/Contents/Resources/qgis'), True)
    app.initQgis()
    # Solo il provider nativo necessario all'export: niente profili, script o plugin globali.
    from qgis.analysis import QgsNativeAlgorithms
    QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
    from scialpinismo.engine import Workflow
    feedback = QgsProcessingFeedback()
    feedback.progressChanged.connect(lambda v: None)
    w = Workflow(args.root, feedback=feedback, log=print)
    try:
        from scialpinismo import atlas
        if args.command in ('grid','prepare-cells','rename-cell','atlas','publish-cell'):
            if args.command == 'prepare-cells':
                result = atlas.prepare_cells(w, args.cells, args.max_missing_percent)
            else:
                with w.locked():
                    if args.command == 'grid':
                        result = atlas.make_grid(w, args.bbox, mountain_only=not args.all_cells,
                                                 min_elevation_m=args.min_elevation,
                                                 min_mountain_percent=args.min_mountain_percent)
                    elif args.command == 'rename-cell': result = atlas.rename_cell(w, args.cell, args.name)
                    elif args.command == 'atlas': result = atlas.build_catalog(w)
                    elif args.command == 'publish-cell': result = atlas.publish_cell(w, args.cell)
        elif args.command == 'init':
            result = w.initialize()
        elif args.command == 'list':
            result = w.sources()
        elif args.command == 'prepare':
            result = w.prepare_bbox(args.name, args.bbox, args.source, args.crs, args.maxzoom,
                                    args.max_missing_percent)
        elif args.command == 'update':
            result = w.update(args.area, max_missing_percent=args.max_missing_percent)
        elif args.command == 'export':
            if args.max_missing_percent is not None:
                w.update(args.area, max_missing_percent=args.max_missing_percent)
            result = w.export(args.area, args.minzoom, args.maxzoom, mode=args.mode, maxbytes=args.max_bytes, warning_bytes=args.warning_bytes)
        else:
            result = w.check(args.area)
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    except Exception as exc:
        import traceback
        traceback.print_exc()
        parser.exit(1, f'\nERRORE: {exc}\n')
    finally:
        app.exitQgis()


if __name__ == '__main__':
    main()
