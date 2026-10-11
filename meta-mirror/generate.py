#!/usr/bin/env python3
"""Зеркало меты Liquid Launcher — только stdlib, без зависимостей.

Что делает:
  1. Копирует как есть Prism-индексы (mc + 4 загрузчика) в `v1/<uid>/index.json`.
     Формат НЕ меняем — лаунчер парсит его тем же кодом, что и Prism.
  2. Кладёт рядом сырой Mojang-манифест `v1/mojang-manifest.json`
     (оттуда инсталлер берёт url JSON версии → клиент/библиотеки/ассеты).
  3. Собирает `v1/java.json` из Adoptium API: свежие JRE по мажорам
     и платформам (релиз, прямая ссылка, sha256, размер).

Запуск:
  python3 meta-mirror/generate.py --out meta      # для репо launcher/
  python3 meta-mirror/generate.py --out /tmp/meta # проверка локально

В проде крутится по крону (см. refresh-meta.yml), руками дёргать не надо.
User-Agent представляемся честно — чужие CDN это любят.
"""
import datetime
import json
import os
import sys
import urllib.request

PRISM = 'https://meta.prismlauncher.org/v1'
MOJANG_MANIFEST = ('https://piston-meta.mojang.com/mc/game/'
                   'version_manifest_v2.json')
ADOPTIUM = 'https://api.adoptium.net/v3'

UIDS = [
    'net.minecraft',
    'net.minecraftforge',
    'net.neoforged',
    'net.fabricmc.fabric-loader',
    'org.quiltmc.quilt-loader',
]

JAVA_MAJORS = [8, 17, 21]
JAVA_OSES = ['windows', 'linux', 'mac']
JAVA_ARCHS = ['x64', 'aarch64']

UA = {'User-Agent': ('LiquidLauncher-meta-mirror/1.0 '
                     '(+https://github.com/pochmak55-lgtm/launcher)')}


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if r.status != 200:
            raise RuntimeError('http %s %s' % (r.status, url))
        return r.read()


def main():
    out = 'out'
    if '--out' in sys.argv:
        out = sys.argv[sys.argv.index('--out') + 1]
    root = os.path.join(out, 'v1')
    os.makedirs(root, exist_ok=True)

    for uid in UIDS:
        data = get('%s/%s/index.json' % (PRISM, uid))
        obj = json.loads(data)
        if not obj.get('versions'):
            raise RuntimeError('empty index: %s' % uid)
        d = os.path.join(root, uid)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'index.json'), 'wb') as f:
            f.write(data)
        print('mirror %s: %d versions' % (uid, len(obj['versions'])),
              flush=True)

    manifest = get(MOJANG_MANIFEST)
    mobj = json.loads(manifest)
    if not mobj.get('versions'):
        raise RuntimeError('empty mojang manifest')
    with open(os.path.join(root, 'mojang-manifest.json'), 'wb') as f:
        f.write(manifest)
    print('mirror mojang-manifest: %d versions' % len(mobj['versions']),
          flush=True)

    runtimes = []
    for major in JAVA_MAJORS:
        platforms = {}
        for o in JAVA_OSES:
            for a in JAVA_ARCHS:
                url = ('%s/assets/latest/%d/hotspot?architecture=%s'
                       '&heap_size=normal&image_type=jre&os=%s&vendor=eclipse'
                       % (ADOPTIUM, major, a, o))
                try:
                    arr = json.loads(get(url, timeout=30))
                except Exception as e:  # нет такой связки — пропускаем
                    print('java %d %s-%s: skip (%s)' % (major, o, a, e),
                          flush=True)
                    continue
                if not arr:
                    continue
                # /assets/latest/*: {'release_name', 'binary': {'package': …}},
                # /assets/feature_releases/*: {'binaries': [{'package': …}]}.
                first = arr[0]
                rel_name = first.get('release_name', '')
                pkg = {}
                if isinstance(first.get('binary'), dict):
                    pkg = first['binary'].get('package', {}) or {}
                elif first.get('binaries'):
                    bins = first['binaries']
                    if bins:
                        pkg = bins[0].get('package', {}) or {}
                if not pkg.get('link'):
                    continue
                platforms['%s-%s' % (o, a)] = {
                    'release': rel_name,
                    'url': pkg.get('link', ''),
                    'sha256': pkg.get('checksum', ''),
                    'size': pkg.get('size', 0),
                }
        runtimes.append({'major': major, 'platforms': platforms})
        print('java %d: %d platforms' % (major, len(platforms)), flush=True)

    with open(os.path.join(root, 'java.json'), 'w',
              encoding='utf-8') as f:
        f.write(json.dumps({
            'generated': datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
            'runtimes': runtimes,
        }, ensure_ascii=False, indent=1))
    print('OK -> %s' % os.path.abspath(root))


if __name__ == '__main__':
    main()
