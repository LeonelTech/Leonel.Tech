"""Minimal command-line entrypoint.

Two subcommands for the MVP:

* ``acervo serve`` — start the loopback web app.
* ``acervo preserve`` — run a full preservation session from the terminal,
  useful for automation and for the end-to-end acceptance test (ACC-001).
"""

from __future__ import annotations

import argparse
import sys

from acervo import __version__
from acervo.db.base import init_db, session_scope
from acervo.services import sessions as svc
from acervo.services.manifest import write_manifest
from acervo.db.models import CatalogingSession
from sqlalchemy import select


def _cmd_serve(_args: argparse.Namespace) -> int:
    from acervo.main import main as serve_main

    serve_main()
    return 0


def _cmd_preserve(args: argparse.Namespace) -> int:
    init_db()
    with session_scope() as session:
        col = svc.create_collection(session, args.collection)
        media = svc.register_source_media(session, col, args.media_label or args.source, args.source)
        cat = svc.start_session(
            session,
            col,
            media,
            source_root=args.source,
            destination_root=args.destination,
            profile=args.profile,
        )
        cat_ident = cat.identifier
        cat_id = cat.id

    stats = svc.run_preservation(cat_id)

    with session_scope() as session:
        cat = session.execute(
            select(CatalogingSession).where(CatalogingSession.identifier == cat_ident)
        ).scalar_one()
        artifacts = write_manifest(session, cat, f"{args.destination}/00_COLLECTION_CONTROL")

    print(f"Session:      {cat_ident}")
    print(f"Discovered:   {stats.discovered}")
    print(f"Validated:    {stats.validated}")
    print(f"Duplicates:   {stats.duplicates}")
    print(f"Quarantined:  {stats.quarantined}")
    print(f"Bytes:        {stats.bytes_validated}")
    print(f"Manifest:     {artifacts.json_path} (sha256={artifacts.manifest_sha256[:16]}…)")
    if stats.errors:
        print("Errors:")
        for err in stats.errors:
            print(f"  - {err}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="acervo", description="Acervo cataloging platform")
    parser.add_argument("--version", action="version", version=f"acervo {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="start the loopback web application")
    serve.set_defaults(func=_cmd_serve)

    pres = sub.add_parser("preserve", help="run a preservation session from the terminal")
    pres.add_argument("--collection", required=True, help="research collection name")
    pres.add_argument("--source", required=True, help="source folder/device path")
    pres.add_argument("--destination", required=True, help="destination repository path")
    pres.add_argument("--media-label", default=None, help="label for the source media")
    pres.add_argument("--profile", default="preservation_only")
    pres.set_defaults(func=_cmd_preserve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
