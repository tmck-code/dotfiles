#!/usr/bin/env python3
"""UserPromptSubmit hook: surface the Docker skills when a prompt is Docker-shaped.

Reads the hook payload on stdin; if the user's prompt mentions Docker/image/build
concerns, injects a system-reminder nudging Claude toward the docker-fastapi skill
(backend) and docker-web-ui skill (frontend). Silent (no output) otherwise.
"""

import json
import re
import sys

# Word-ish boundaries so 'dockerfile', 'docker-compose', 'dockerized' all hit,
# but 'image' alone does not (too noisy) — it must pair with a build/size concern.
TRIGGERS = re.compile(
    r'''
      docker                      # docker, dockerfile, docker-compose, dockerized, dockerignore
    | \bimage\s+size\b
    | \b(?:shrink|smaller|reduce)\w*\s+(?:the\s+)?(?:image|container)\b
    | \bbuild\s+(?:faster|speed|time|cache)\b
    | \b(?:slow|faster)\s+\w*\s*build\b
    | \blayer\s+cach\w*\b
    | \bmulti-?stage\b
    | \buv\s+sync\b.*\b(?:image|build)\b
    ''',
    re.IGNORECASE | re.VERBOSE,
)

CONTEXT = (
    'This prompt looks Docker-related. Before acting, consider the relevant skill: '
    'the `docker-fastapi` skill covers the Python/FastAPI backend image — multi-stage '
    'uv builds, shrinking image size, speeding up builds, layer caching, and keeping '
    'heavy ML deps out of the runtime image. For a frontend/Vite image, use `docker-web-ui`. '
    'Invoke the matching skill via the Skill tool before scaffolding or editing Docker files.'
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    prompt = str(payload.get('prompt', ''))
    if not TRIGGERS.search(prompt):
        return 0

    json.dump(
        {
            'hookSpecificOutput': {
                'hookEventName': 'UserPromptSubmit',
                'additionalContext': CONTEXT,
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
