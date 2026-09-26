#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Exercise the Java bundle JAR offline, without access to the original native bundle."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import socket
import shutil
import uuid
import subprocess

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--classifier',choices=['macos-arm64','linux-x64','windows-x64'])
parser.add_argument('--output',type=Path)
parser.add_argument('--network-namespace',action='store_true',help='Verify Linux namespace has only loopback and record network isolation')
parser.add_argument('--jdk',type=Path,help='JDK home; otherwise tools/jdk, JAVA_HOME, or javac on PATH')
parser.add_argument('--windows-firewall',action='store_true',help='Temporarily block java.exe outbound network access; requires elevated Windows shell')
parser.add_argument('--jna',type=Path,default=ROOT/'tools/maven-repository/net/java/dev/jna/jna/5.19.1/jna-5.19.1.jar')
parser.add_argument('--version',help='Artifact version to check; defaults to the version in java/pom.xml')
args=parser.parse_args()
if args.network_namespace and (platform.system() != 'Linux' or {name for _,name in socket.if_nameindex()} != {'lo'}):
    raise SystemExit('--network-namespace requires a Linux namespace with only loopback')
classifier=args.classifier or {'Darwin':'macos-arm64','Linux':'linux-x64','Windows':'windows-x64'}[platform.system()]
classes=ROOT/'java/target/example-classes'
classes.mkdir(parents=True,exist_ok=True)
# Follow java/pom.xml rather than a hard-coded version, so a release bump reaches this check.
version=args.version or re.search(r'<version>([^<]+)</version>',(ROOT/'java/pom.xml').read_text(encoding='utf-8')).group(1)
api=ROOT/f'released/java/decisiongator-java-{version}.jar'
bundle=ROOT/f'released/java/decisiongator-java-{version}-{classifier}.jar'
for jar in (api,bundle):
    if not jar.is_file(): raise SystemExit(f'Missing released artifact: {jar}')
jna=args.jna.resolve()
classpath=os.pathsep.join(map(str,[classes,api,jna,bundle]))
jdk_candidates=[args.jdk] if args.jdk else [ROOT/'tools/jdk',Path(os.environ['JAVA_HOME']) if os.environ.get('JAVA_HOME') else None,Path(shutil.which('javac')).resolve().parent.parent if shutil.which('javac') else None]
if not args.jdk and os.name=='nt':
    programs=Path(os.environ.get('ProgramFiles',r'C:\Program Files'))
    for vendor in ['Java','Microsoft','Eclipse Adoptium']:
        for candidate in sorted((programs/vendor).glob('jdk*'),reverse=True):
            release=candidate/'release'
            if release.is_file() and 'JAVA_VERSION="17.' in release.read_text(encoding='utf-8'):
                jdk_candidates.append(candidate)
jdk=next((path.resolve() for path in jdk_candidates if path and (path/'bin'/('javac.exe' if os.name=='nt' else 'javac')).is_file()),None)
if jdk is None: raise SystemExit('A JDK is required; supply --jdk PATH or set JAVA_HOME')
if args.windows_firewall and os.name!='nt': raise SystemExit('--windows-firewall is only available on Windows')
bin_dir=jdk/'bin'
suffix='.exe' if os.name=='nt' else ''
java=bin_dir/('java'+suffix)
javac=bin_dir/('javac'+suffix)
subprocess.run([str(javac),'-encoding','UTF-8','--release','17','-cp',classpath,'-d',str(classes),str(ROOT/'java/examples/BundledExample.java')],check=True)
command=[str(java),'-cp',classpath,'BundledExample',str(ROOT/'java/target'/('bundle-test-cache-'+classifier))]
if platform.system()=='Darwin':
    # JAR paths are allowed; original native bundle directory is denied.
    policy='(version 1)(allow default)(deny network*)(deny file-read* (subpath '+json.dumps(str(ROOT/'released'/classifier))+'))'
    command=['sandbox-exec','-p',policy,*command]
firewall_name='DecisionGator-test-'+uuid.uuid4().hex
firewall_created=False

def powershell(script):
    return subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],check=True,text=True,capture_output=True)

try:
    if args.windows_firewall:
        quoted_program="'"+str(java).replace("'", "''")+"'"
        # Fail rather than claim isolation when the Windows firewall is disabled.
        powershell("$ErrorActionPreference='Stop'; if ((Get-Service MpsSvc).Status -ne 'Running') { throw 'Windows Firewall service is not running' }; if (@(Get-NetFirewallProfile | Where-Object { -not $_.Enabled }).Count -gt 0) { throw 'All firewall profiles must be enabled for this check' }; New-NetFirewallRule -Name '"+firewall_name+"' -DisplayName '"+firewall_name+"' -Direction Outbound -Action Block -Enabled True -Profile Any -Program "+quoted_program+" | Out-Null")
        firewall_created=True
        powershell("$ErrorActionPreference='Stop'; $r=Get-NetFirewallRule -PolicyStore ActiveStore -Name '"+firewall_name+"'; if ($r.Enabled -ne 'True' -or $r.Action -ne 'Block' -or $r.Direction -ne 'Outbound') { throw 'Java outbound block is not active' }")
    result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True,check=True)
finally:
    if firewall_created:
        powershell("$ErrorActionPreference='Stop'; Remove-NetFirewallRule -Name '"+firewall_name+"'")
report={'status':'passed','classifier':classifier,'version':version,'java_version':subprocess.check_output([str(java),'--version'],text=True).splitlines()[0],
        'exit_code':result.returncode,'network_denied':platform.system()=='Darwin' or args.network_namespace,
        'firewall_rule_configured':args.windows_firewall,
        'network_isolation':'Linux network namespace (loopback only)' if args.network_namespace else 'macOS sandbox' if platform.system()=='Darwin' else 'Windows Firewall outbound block configured for java.exe; denial not independently probed' if args.windows_firewall else None,
        'original_bundle_read_denied':platform.system()=='Darwin','stdout':result.stdout,'stderr':result.stderr,
        'api_jar_bytes':api.stat().st_size,'bundle_jar_bytes':bundle.stat().st_size}
report_path=args.output or ROOT/f'reports/java-bundle-{classifier}.json'
report_path.parent.mkdir(parents=True,exist_ok=True)
report_path.write_text(json.dumps(report,indent=2)+'\n', encoding="utf-8")
print(json.dumps(report,indent=2))
