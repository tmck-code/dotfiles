#!/usr/bin/env python3
'''Upload an .excalidraw file to an Excalidraw+ collection over the REST API.

Creates a scene in the target collection and replaces its content with the file,
or replaces the content of an existing scene with --scene-id. Stdlib only.

The API key is read from $EXCALIDRAW_API_KEY (or --api-key). Mint one in the
Excalidraw+ workspace settings; it is shown exactly once.

  ./upload_scene.py diagram.excalidraw --collection generated
  ./upload_scene.py diagram.excalidraw --collection mFUPur2mwj --name 'My scene'
  ./upload_scene.py diagram.excalidraw --scene-id APdEs2LYqDr    # replace in place
  ./upload_scene.py --list-collections
'''
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

RED    = '\033[31m'
GREEN  = '\033[32m'
YELLOW = '\033[33m'
DIM    = '\033[2m'
RESET  = '\033[0m'

# Documented base for the Excalidraw+ public-beta API. Note the doubled path
# segment: /api/v1, not /v1 - the bare /v1 and /v2 forms both 404.
DEFAULT_BASE_URL = 'https://api.excalidraw.com/api/v1'
APP_URL          = 'https://app.excalidraw.com'
PAGE_LIMIT       = 50

JSONDict = dict[str, object]


class ApiError(RuntimeError):
    'An Excalidraw+ API call returned a non-2xx response'


def request(base_url: str, api_key: str, method: str, path: str,
            body: bytes | None = None) -> JSONDict:
    'Issue one API call and decode its JSON object response'
    req = urllib.request.Request(
        url    = f'{base_url}{path}',
        method = method,
        data   = body,
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type':  'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read() or b'{}')
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', 'replace')[:400]
        raise ApiError(f'{method} {path} -> HTTP {exc.code}: {detail}') from exc
    except urllib.error.URLError as exc:
        raise ApiError(f'{method} {path} -> {exc.reason}') from exc

    if not isinstance(payload, dict):
        raise ApiError(f'{method} {path} -> expected a JSON object')
    return payload


def iter_collections(base_url: str, api_key: str) -> Iterator[JSONDict]:
    'Yield every collection, following the API pagination'
    offset = 0
    while True:
        page = request(
            base_url, api_key, 'GET',
            f'/collections?limit={PAGE_LIMIT}&offset={offset}',
        )
        data = page.get('data')
        if not isinstance(data, list):
            return
        yield from (item for item in data if isinstance(item, dict))
        if not page.get('hasNextPage') or not data:
            return
        offset += len(data)


def resolve_collection(base_url: str, api_key: str, ref: str) -> str:
    'Map a collection name (case-insensitive) or id to its id'
    collections = list(iter_collections(base_url, api_key))
    by_id = [c for c in collections if c.get('id') == ref]
    if by_id:
        return ref

    wanted = ref.casefold()
    matches = [c for c in collections if str(c.get('name', '')).casefold() == wanted]
    if len(matches) == 1:
        return str(matches[0]['id'])
    if len(matches) > 1:
        ids = ', '.join(str(c.get('id')) for c in matches)
        raise ApiError(f'collection name {ref!r} is ambiguous: {ids}')

    known = ', '.join(sorted(str(c.get('name')) for c in collections))
    raise ApiError(f'no collection named or id {ref!r}. Known: {known}')


def create_scene(base_url: str, api_key: str, collection_id: str,
                 name: str, pinned: bool) -> str:
    'Create an empty scene in the collection and return its id'
    body = json.dumps({'name': name, 'pinned': pinned}).encode()
    payload = request(
        base_url, api_key, 'POST', f'/collections/{collection_id}/scenes', body,
    )
    metadata = payload.get('metadata')
    source = metadata if isinstance(metadata, dict) else payload
    scene_id = source.get('id')
    if not isinstance(scene_id, str):
        raise ApiError(f'scene created but no id in response: {payload}')
    return scene_id


def count_elements(payload: JSONDict) -> int:
    'Count elements in a scene-content response, tolerating either shape'
    elements = payload.get('elements')
    if not isinstance(elements, list):
        content = payload.get('content')
        elements = content.get('elements') if isinstance(content, dict) else None
    return len(elements) if isinstance(elements, list) else -1


def load_scene_file(path: Path) -> tuple[bytes, int]:
    'Read the .excalidraw file, validating it before anything is uploaded'
    raw = path.read_bytes()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiError(f'{path} is not valid JSON: {exc}') from exc
    if not isinstance(parsed, dict) or 'elements' not in parsed:
        raise ApiError(f'{path} has no "elements" key - is it an .excalidraw file?')
    return raw, count_elements(parsed)


def upload(args: argparse.Namespace, api_key: str) -> int:
    'Create-or-reuse a scene, replace its content, and verify the round-trip'
    path = Path(args.file)
    raw, local_count = load_scene_file(path)

    scene_id = args.scene_id
    collection_id = None
    if scene_id is None:
        collection_id = resolve_collection(args.base_url, api_key, args.collection)
        name = args.name or path.stem
        scene_id = create_scene(
            args.base_url, api_key, collection_id, name, args.pinned,
        )
        print(f'{DIM}created scene {scene_id} in collection {collection_id}{RESET}')

    request(args.base_url, api_key, 'PUT', f'/scenes/{scene_id}/content', raw)

    stored = count_elements(
        request(args.base_url, api_key, 'GET', f'/scenes/{scene_id}/content'),
    )
    if stored != local_count:
        print(
            f'{YELLOW}warning: uploaded {local_count} elements but the API '
            f'reports {stored}{RESET}',
            file = sys.stderr,
        )

    print(f'{GREEN}uploaded {stored} elements{RESET}')
    print(f'scene id: {scene_id}')
    if collection_id:
        print(f'url:      {APP_URL}/o/{collection_id}/{scene_id}')
    return 0


def list_collections(args: argparse.Namespace, api_key: str) -> int:
    'Print every collection id and name'
    for collection in iter_collections(args.base_url, api_key):
        default = f' {DIM}(default){RESET}' if collection.get('isDefault') else ''
        print(f'{collection.get("id"):<14}{collection.get("name")}{default}')
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description     = __doc__,
        formatter_class = argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('file', nargs='?', help='path to the .excalidraw file')
    parser.add_argument('-c', '--collection',
                        help = 'target collection name or id (required to create)')
    parser.add_argument('-n', '--name',
                        help = 'scene name (default: the file stem)')
    parser.add_argument('-s', '--scene-id',
                        help = 'replace this existing scene instead of creating one')
    parser.add_argument('-p', '--pinned', action='store_true',
                        help = 'pin the new scene in its collection')
    parser.add_argument('-l', '--list-collections', action='store_true',
                        help = 'list collections and exit')
    parser.add_argument('--api-key', default=os.environ.get('EXCALIDRAW_API_KEY'),
                        help = 'defaults to $EXCALIDRAW_API_KEY')
    parser.add_argument('--base-url', default=DEFAULT_BASE_URL,
                        help = f'API base URL (default: {DEFAULT_BASE_URL})')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.api_key:
        print(f'{RED}no API key: set $EXCALIDRAW_API_KEY or pass --api-key{RESET}',
              file=sys.stderr)
        return 2

    if not args.list_collections:
        if not args.file:
            print(f'{RED}a file is required unless --list-collections{RESET}',
                  file=sys.stderr)
            return 2
        if not args.scene_id and not args.collection:
            print(f'{RED}--collection is required unless --scene-id is given{RESET}',
                  file=sys.stderr)
            return 2

    action = list_collections if args.list_collections else upload
    try:
        return action(args, args.api_key)
    except (ApiError, OSError) as exc:
        print(f'{RED}{exc}{RESET}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
