"""Metadata-only Linux CPython 3.12 storage calculation; installs nothing.

Reads public dependency metadata and ZIP central directories with HTTP Range.
Wheel payload sums are not measured installed filesystem allocation/peak usage.
Simple fixed-point resolver validates final constraints, not a replacement for pip.
"""
import concurrent.futures as cf
import email
import html
import io
import json
import re
import sys
import urllib.request as u
import zipfile
from pathlib import Path
try:
    from packaging.requirements import Requirement
    from packaging.version import Version
    from packaging.specifiers import SpecifierSet
    from packaging.utils import canonicalize_name, parse_wheel_filename
    from packaging.tags import cpython_tags, compatible_tags
except ImportError:
    from pip._vendor.packaging.requirements import Requirement
    from pip._vendor.packaging.version import Version
    from pip._vendor.packaging.specifiers import SpecifierSet
    from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
    from pip._vendor.packaging.tags import cpython_tags, compatible_tags

OUT = Path(__file__).resolve().parent
CACHE = {}
ENV = dict(implementation_name='cpython', implementation_version='3.12.3',
           os_name='posix', platform_machine='x86_64', platform_release='',
           platform_system='Linux', platform_version='', python_full_version='3.12.3',
           platform_python_implementation='CPython', python_version='3.12', extra='')
PLATFORMS = [f'manylinux_2_{i}_x86_64' for i in range(39, 4, -1)] + ['manylinux2014_x86_64', 'linux_x86_64']
TAGS = list(cpython_tags((3, 12), platforms=PLATFORMS)) + list(compatible_tags((3, 12), 'cp312', PLATFORMS))
RANK = {t: i for i, t in reversed(list(enumerate(TAGS)))}

def fetch(url):
    if url not in CACHE:
        with u.urlopen(url, timeout=35) as r:
            CACHE[url] = r.read()
    return CACHE[url]

def js(url):
    return json.loads(fetch(url))

def wheel_rank(f):
    try:
        tags = parse_wheel_filename(f['filename'])[3]
        return min((RANK[t] for t in tags if t in RANK), default=10**9)
    except Exception:
        return 10**9

def python_ok(spec):
    return not spec or Version('3.12.3') in SpecifierSet(spec)

def select(name, specs):
    data = js(f'https://pypi.org/pypi/{name}/json')
    valid = []
    for ver in data['releases']:
        try: valid.append((Version(ver), ver))
        except ValueError: pass
    for _, ver in sorted(valid, reverse=True):
        v = Version(ver)
        if v.is_prerelease or not all(v in s for s in specs):
            continue
        files = [f for f in data['releases'][ver] if not f.get('yanked') and python_ok(f.get('requires_python')) and wheel_rank(f) < 10**9]
        if files:
            f = min(files, key=wheel_rank)
            md = js(f'https://pypi.org/pypi/{name}/{ver}/json')['info']
            return dict(name=name, version=ver, filename=f['filename'], url=f['url'],
                        compressed_bytes=f['size'], sha256=f['digests']['sha256'],
                        requirements=md.get('requires_dist') or [])
    raise ValueError(f'No compatible wheel: {name}, {specs}')

def torch(variant):
    index = fetch(f'https://download.pytorch.org/whl/{variant}/torch/').decode()
    links = [html.unescape(x) for x in re.findall(r'href="([^"]+)"', index)
             if '2.14.1' in x and 'cp312-cp312' in x and 'linux' in x and 'x86_64' in x]
    assert len(links) == 1, links
    url = links[0].split('#')[0]
    md = email.message_from_bytes(fetch(url + '.metadata'))
    return dict(name='torch', version=md['Version'], filename=url.rsplit('/', 1)[1],
                url=url, sha256=links[0].split('sha256=')[-1],
                requirements=md.get_all('Requires-Dist') or [])

def resolve(variant):
    t = torch(variant)
    roots = ['torch==2.14.1', 'gymnasium==1.4.0', 'stable-baselines3==2.9.2', 'sb3-contrib==2.9.2', 'numpy==2.5.4']
    chosen = {'torch': t}
    for iteration in range(30):
        constraints, extras, pending = {}, {}, list(roots)
        processed = set()
        while pending:
            r = Requirement(pending.pop())
            name = canonicalize_name(r.name)
            constraints.setdefault(name, []).append(r.specifier)
            extras.setdefault(name, set()).update(r.extras)
            key = (name, tuple(sorted(extras[name])))
            if key in processed:
                continue
            processed.add(key)
            if name not in chosen:
                chosen[name] = t if name == 'torch' else select(name, constraints[name])
            for raw in chosen[name]['requirements']:
                dep = Requirement(raw)
                if dep.marker is None or any(dep.marker.evaluate({**ENV, 'extra': e}) for e in [''] + sorted(extras[name])):
                    pending.append(raw)
        updated = {}
        for name, specs in constraints.items():
            current = chosen[name]
            updated[name] = current if all(Version(current['version']) in s for s in specs) else select(name, specs)
        old = {k: v['version'] for k, v in chosen.items()}
        chosen = updated
        if old == {k: v['version'] for k, v in chosen.items()}:
            return chosen
    raise ValueError('Dependency resolution failed to converge')

class RemoteZip(io.RawIOBase):
    def __init__(self, url):
        self.url, self.pos, self.transferred = url, 0, 0
        req = u.Request(url, headers={'Range': 'bytes=0-0'})
        with u.urlopen(req, timeout=35) as r:
            if r.status != 206:
                raise ValueError('Server does not support bounded range reads')
            self.size = int(r.headers['Content-Range'].split('/')[-1])
            r.read(1)
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        return self.pos
    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0: return b''
        if n > 16 * 1024**2: raise ValueError('Refusing large read')
        req = u.Request(self.url, headers={'Range': f'bytes={self.pos}-{self.pos+n-1}'})
        with u.urlopen(req, timeout=35) as r:
            if r.status != 206: raise ValueError('Range ignored')
            data = r.read(n + 1)
        assert len(data) == n
        self.pos += n
        self.transferred += n
        return data

def measure(row):
    row = dict(row)
    stream = RemoteZip(row['url'])
    with zipfile.ZipFile(stream) as z:
        row['unpacked_payload_bytes'] = sum(x.file_size for x in z.infolist())
        row['archive_file_count'] = len(z.infolist())
    row['compressed_bytes'] = stream.size
    row['range_bytes_read'] = stream.transferred
    return row

def main():
    variants = sys.argv[1:] or ['cpu', 'cu126']
    measured = {}
    results = {}
    for variant in variants:
        rows = resolve(variant)
        missing = [r for r in rows.values() if r['url'] not in measured]
        with cf.ThreadPoolExecutor(max_workers=8) as pool:
            for row in pool.map(measure, missing):
                measured[row['url']] = row
        packages = [measured[r['url']] for r in rows.values()]
        results[variant] = dict(packages=sorted(packages, key=lambda r: r['name']),
            compressed_bytes=sum(r['compressed_bytes'] for r in packages),
            unpacked_payload_bytes=sum(r['unpacked_payload_bytes'] for r in packages),
            metadata_range_bytes_read=sum(r['range_bytes_read'] for r in packages))
        (OUT/'package-storage-calculation.json').write_text(json.dumps(results, indent=2)+'\n')
        print(json.dumps({'variant':variant, 'packages':len(packages),
            'download_GiB':round(results[variant]['compressed_bytes']/1024**3,3),
            'unpacked_GiB':round(results[variant]['unpacked_payload_bytes']/1024**3,3)}), flush=True)

if __name__ == '__main__': main()
