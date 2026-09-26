#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Build/test Java API and native classifier JAR using project-local Java/Maven.
Run: uv run java/build.py [--bundle released/macos-arm64] [--output released/java] [--install]
"""
import argparse
import hashlib
import math
import os
import platform
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    detected={('Darwin','arm64'):'macos-arm64',('Linux','x86_64'):'linux-x64',('Windows','AMD64'):'windows-x64',('Windows','x86_64'):'windows-x64'}.get((platform.system(),platform.machine()))
    parser.add_argument('--bundle',type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'released/java',help='Artifact output directory (default: released/java)')
    parser.add_argument('--expected-probability',type=float,help='Independent native result for the cancellation fixture (supply both expected probabilities for alternate weights)')
    parser.add_argument('--expected-unicode-probability',type=float,help='Independent native result for the Unicode/criteria fixture')
    parser.add_argument('--classifier',choices=['macos-arm64','windows-x64','linux-x64'],default=detected)
    parser.add_argument('--install',action='store_true',help='Install to the project-local Maven repository')
    parser.add_argument('--package-only',action='store_true',help='Package a different platform; its tests must run on that platform')
    parser.add_argument('--jdk',type=Path,default=ROOT/'tools/jdk')
    parser.add_argument('--maven',type=Path,default=ROOT/'tools/maven/bin'/('mvn.cmd' if os.name=='nt' else 'mvn'))
    args=parser.parse_args()
    expected=(args.expected_probability,args.expected_unicode_probability)
    if any(value is not None for value in expected):
        if any(value is None or not math.isfinite(value) or not 0 <= value <= 1 for value in expected):
            parser.error('Supply both expected probabilities as finite numbers between 0 and 1')
    if args.classifier is None: parser.error('Select a supported --classifier')
    if args.classifier != detected and not args.package_only: parser.error('Use --package-only to package another platform without running its tests')
    jdk=args.jdk.resolve()
    maven=args.maven.resolve()
    if not (jdk/'bin'/('java.exe' if os.name=='nt' else 'java')).exists() or not maven.exists():
        raise SystemExit('Missing local JDK or Maven. See java/README.md for setup.')
    source=(args.bundle or ROOT/'released'/args.classifier).resolve()
    if not (source/'manifest.json').is_file(): raise SystemExit('A built native bundle is required')
    library={'macos-arm64':'libdecisiongator.dylib','linux-x64':'libdecisiongator.so','windows-x64':'decisiongator.dll'}[args.classifier]
    if not (source/library).is_file(): raise SystemExit(f'Missing matching native library: {library}')
    target=ROOT/'java/target'
    # Clear compiled/resources output, keeping other completed platform JARs in released/.
    if target.exists(): shutil.rmtree(target)
    resource_root=target/'native-bundle'
    if resource_root.exists(): shutil.rmtree(resource_root)
    resource=resource_root/'META-INF/decisiongator'/args.classifier
    shutil.copytree(source,resource)
    index=[]
    for path in sorted(resource.rglob('*')):
        if not path.is_file(): continue
        relative=path.relative_to(resource).as_posix()
        if '\t' in relative or '\n' in relative: raise ValueError('Invalid bundle filename')
        with path.open('rb') as stream: checksum=hashlib.file_digest(stream,'sha256').hexdigest()
        index.append(checksum+'\t'+relative)
    (resource/'bundle.index').write_text('\n'.join(index)+'\n', encoding="utf-8")
    env=os.environ.copy()
    env['JAVA_HOME']=str(jdk)
    env['PATH']=str(jdk/'bin')+os.pathsep+env.get('PATH','')
    command=[str(maven),'-B','-f',str(ROOT/'java/pom.xml'),
             '-Dmaven.repo.local='+str(ROOT/'tools/maven-repository'),
             '-Ddecisiongator.bundle='+str(source),'-Dnative.classifier='+args.classifier,
             '-Pbundle','install' if args.install else 'package']
    if args.package_only:
        command.append('-DskipTests')
    if args.expected_probability is not None:
        command.extend(['-Ddecisiongator.expectedProbability='+str(args.expected_probability),
                        '-Ddecisiongator.expectedUnicodeProbability='+str(args.expected_unicode_probability)])
    subprocess.run(command,env=env,check=True)
    released=args.output.resolve()
    released.mkdir(parents=True,exist_ok=True)
    for suffix in ['', '-sources', '-javadoc', '-'+args.classifier]:
        jar=target/('decisiongator-java-0.4.1'+suffix+'.jar')
        if not jar.is_file(): raise SystemExit(f'Missing built artifact: {jar}')
        shutil.copy2(jar,released/jar.name)
    shutil.copy2(ROOT/'java/pom.xml',released/'decisiongator-java-0.4.1.pom')
    print('Java artifacts:',released)

if __name__=='__main__': main()
