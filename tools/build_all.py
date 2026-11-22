"""Build every published stage in its preserved order from one shared command list.

The default includes baseline PDF preparation. CI uses --prepare-only before its
baseline tests and --site-only afterwards; its validation gates stay separate.
Builds require Python 3.11, matching the runtime of the preserved public assets.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PREPARE = [
    ('Check current summaries', [('python', 'tools/current_state.py', '--check')]),
    ('Assemble unchanged baseline PDF', [('python', 'tools/assemble_pdf.py')]),
]
SITE = [
    ('Preserved research, terrain and B1—B8', [
        ('python', 'tools/build_site.py'),
        ('python', 'tools/research_v25.py'),
        ('python', 'tools/milestone_v26.py'),
        ('python', 'tools/link_model_points_v26.py'),
        ('python', 'tools/network_v27.py'),
        ('python', 'tools/portal_v28.py'),
        ('python', 'tools/chronology_v29.py'),
        ('python', 'tools/terrain_v30.py'),
        ('python', 'tools/dual_release.py'),
        ('python', 'tools/west_b3.py'),
        ('python', 'tools/historical_frame_b4.py'),
        ('python', 'tools/north_b4.py'),
        ('python', 'tools/historical_datum_b5.py'),
        ('python', 'tools/west_roads_b5.py'),
        ('python', 'tools/ground_review_b6.py'),
        ('python', 'tools/southeast_b6.py'),
        ('python', 'tools/source_continuity_b7.py'),
        ('python', 'tools/luonan_b7.py'),
        ('python', 'tools/city_review_b8.py'),
        ('python', 'tools/homepage_v1.py'),
    ]),
    ('Prosperity documentary maps and source-geographic layout', [
        ('python', 'tools/prosperity_v1.py'),
        ('python', 'tools/prosperity_core_v2.py'),
        ('python', 'tools/prosperity_gate_v3.py'),
        ('python', 'tools/prosperity_axis_v4.py'),
        ('python', 'tools/prosperity_axis_sources_p41.py'),
        ('python', 'tools/prosperity_taiji_courts_p42.py'),
        ('python', 'tools/prosperity_palace_boundaries_p43.py'),
        ('python', 'tools/prosperity_architecture_p44.py'),
    ]),
    ('Preserved approved homepage and P4 city studies', [
        ('python', 'tools/homepage_approved_v9.py'),
        ('python', 'tools/prosperity_city_distribution_p451.py'),
        ('python', 'tools/prosperity_road_functions_p452.py'),
        ('python', 'tools/prosperity_street_clusters_p453.py'),
        ('python', 'tools/prosperity_hydro_roads_p46.py'),
    ]),
    ('R4 city atlas', [
        ('node', '--check', 'research/prosperity-r4/atlas.js'),
        ('python', 'tools/prosperity_city_atlas_r4.py'),
    ]),
    ('R5 panorama and approved current homepage', [
        ('node', '--check', 'research/prosperity-r5/panorama.js'),
        ('python', 'tools/prosperity_city_panorama_r5.py'),
    ]),
    ('R6.1 source road atlas', [('python', 'tools/road_location_atlas.py')]),
    ('R6.2 complete road evidence atlas', [
        ('node', '--check', 'research/roads-r62/atlas.js'),
        ('python', 'tools/all_road_atlas_r62.py'),
    ]),
    ('R7 city nodes, joined evidence and approved homepage guide', [
        ('node', '--check', 'research/city-nodes-r7/atlas.js'),
        ('python', 'tools/city_nodes_r7.py'),
    ]),
    ('R8.1 evidence-led panorama candidate review', [
        ('node', '--check', 'web/panorama-v13.js'),
        ('python', 'tools/panorama_v13.py'),
    ]),
]


def source_environment(source_commit=None):
    """Give local builds the same full-SHA provenance used by CI's preservation contracts."""
    commit = source_commit or os.environ.get('GITHUB_SHA')
    if not commit:
        try:
            commit = subprocess.run(['git', 'rev-parse', '--verify', 'HEAD'], cwd=ROOT,
                                    check=True, capture_output=True, text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as error:
            raise ValueError('Cannot resolve the source commit. Supply --source-commit with the full 40-character Git SHA.') from error
    if not re.fullmatch(r'[0-9a-fA-F]{40}', commit):
        raise ValueError('GITHUB_SHA / --source-commit must be a full 40-character Git SHA.')
    return dict(os.environ, GITHUB_SHA=commit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare-only', action='store_true', help='Prepare baseline PDF and check current summaries')
    mode.add_argument('--site-only', action='store_true', help='Build the site after the preparation and preflight gates')
    parser.add_argument('--list', action='store_true', help='Print the ordered commands without running them')
    parser.add_argument('--source-commit', help='Full source Git SHA; defaults to CI GITHUB_SHA or the local Git HEAD')
    args = parser.parse_args()
    if not args.list and sys.version_info[:2] != (3, 11):
        parser.error('Full builds require Python 3.11, matching Pages CI and protected SVG byte output. '
                     'Run python3.11 tools/build_all.py in a Python 3.11 environment. '
                     '--list is available on other Python versions.')
    try:
        environment = None if args.list else source_environment(args.source_commit)
    except ValueError as error:
        parser.error(str(error))
    stages = PREPARE if args.prepare_only else SITE if args.site_only else PREPARE + SITE
    for title, commands in stages:
        print(title, flush=True)
        for command in commands:
            print('  ' + ' '.join(command), flush=True)
            if not args.list:
                invocation = [sys.executable, *command[1:]] if command[0] == 'python' else list(command)
                subprocess.run(invocation, cwd=ROOT, env=environment, check=True)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode)
