#!/usr/bin/env python3
"""Inject scenarios.json, the side and the scenario ids into driver.js.

usage: build-driver.py <scenarios.json> <before|after> <out.js> [ID ...]

scenarios.json must have "root" (absolute dir; videos land in <root>/<side>/<ID>/).
Write <out.js> somewhere the Playwright MCP may read (the session workspace
root, e.g. <workspace>/.playwright-mcp/wt-<side>.js), then run it with
browser_run_code_unsafe(filename=...).
"""
import json, re, sys, os

if len(sys.argv) < 4 or sys.argv[2] not in ('before', 'after'):
    sys.exit(__doc__)
cfg_path, side, out, ids = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
cfg = json.load(open(cfg_path))
for k in ('root', 'sides', 'scenarios'):
    if k not in cfg:
        sys.exit(f'scenarios.json: missing "{k}"')
for i in ids:
    if i not in cfg['scenarios']:
        sys.exit(f'unknown scenario id: {i}')
tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'driver.js')).read()

def inject(src, tag, value):
    pat = re.compile(r'/\*' + tag + r'\*/.*?/\*END\*/', re.S)
    if not pat.search(src):
        sys.exit(f'driver.js: marker {tag} not found')
    return pat.sub(lambda m: f'/*{tag}*/ {value} /*END*/', src, count=1)

js = inject(tpl, 'CFG', json.dumps(cfg, indent=1))
js = inject(js, 'SIDE', json.dumps(side))
js = inject(js, 'RUN', json.dumps(ids) if ids else 'null')
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
open(out, 'w').write(js)
print(f'wrote {out} ({side}, {len(ids) or len(cfg["scenarios"])} scenario(s))')
