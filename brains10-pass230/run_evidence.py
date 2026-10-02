"""Bounded real-etcd capture. A complete capture is not controller adjudication."""
import argparse, hashlib, json, os, pathlib, re, shutil, socket, subprocess, sys
import tarfile, tempfile, time, zipfile, signal

BASE = pathlib.Path(__file__).resolve().parent
ARCHIVE_SHA = '66bad39ed920f6fc15fd74adcb8bfd38ba9a6412f8c7852d09eb11670e88cac3'
ARCHIVE_URL = 'https://github.com/etcd-io/etcd/releases/download/v3.6.5/etcd-v3.6.5-linux-amd64.tar.gz'
ORIGINAL_SHA = '001a00097f98a4f8d82804d3b0dade72ad5663e3a8d5f648ecc8fb1f83497779'
REPAIRED_SHA = '9e78ad38390a26bd84db56b8fa468af7d6d378a7e5edabc191cf3c87fb36284b'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')

def verify_source(base, expected):
    manifest = base/'SOURCE_MANIFEST.json'
    if sha(manifest) != expected:
        raise ValueError('source manifest identity mismatch')
    files = json.loads(manifest.read_text())
    actual = {p.name for p in base.iterdir() if p.is_file()}
    if actual != set(files)|{'SOURCE_MANIFEST.json'}:
        raise ValueError('source inventory mismatch')
    for name, digest in files.items():
        if pathlib.Path(name).name != name or (base/name).is_symlink() or sha(base/name) != digest:
            raise ValueError('source member mismatch: '+name)

def extract_gate(archive, dest):
    if sha(archive) != REPAIRED_SHA:
        raise ValueError('repaired gate archive mismatch')
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or z.testzip() is not None:
            raise ValueError('gate ZIP integrity failure')
        m = json.loads(z.read('GATE_MANIFEST.json'))
        if set(names) != set(m)|{'GATE_MANIFEST.json'}:
            raise ValueError('gate inventory mismatch')
        for n in names:
            if pathlib.PurePosixPath(n).name != n:
                raise ValueError('gate requires flat file names')
            data = z.read(n)
            if n in m and hashlib.sha256(data).hexdigest() != m[n]:
                raise ValueError('gate manifest mismatch')
            (dest/n).write_bytes(data)

def command(args, output, *, env=None, cwd=None, timeout=30):
    with output.open('wb') as f:
        try:
            p = subprocess.Popen(args, stdout=f, stderr=subprocess.STDOUT,
                                 env=env, cwd=cwd, start_new_session=True)
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            p.wait()
            f.write(b'\nHARNESS_COMMAND_TIMEOUT\n')
            rc = 124
        except OSError as e:
            f.write(('\nHARNESS_COMMAND_ERROR '+str(e)+'\n').encode())
            rc = 127
    write_json(output.with_suffix(output.suffix+'.command.json'), {'argv':args,'exit_code':rc})
    return rc

def require(rc, stage):
    if rc != 0:
        raise RuntimeError(stage+' exit '+str(rc))

def seal(evidence):
    files = {str(p.relative_to(evidence)):sha(p) for p in sorted(evidence.rglob('*'))
             if p.is_file() and p.name != 'EVIDENCE_MANIFEST.json'}
    write_json(evidence/'EVIDENCE_MANIFEST.json', files)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--expected-manifest', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--local-rehearsal', action='store_true')
    ap.add_argument('--release-archive')
    args = ap.parse_args()
    evidence = pathlib.Path(args.output).resolve()
    # Exclusive creation: existing evidence is never erased or overwritten.
    evidence.mkdir(parents=True, exist_ok=False)
    result = {'status':'INDETERMINATE','controlling_pass':186,'promotion':False,'freeze':False,
              'scope':'single-node implementation observations',
              'execution_mode':'LOCAL_REHEARSAL' if args.local_rehearsal else 'GITHUB_HOSTED',
              'gate_subject_sha256':REPAIRED_SHA,'original_subject_sha256':ORIGINAL_SHA}
    process = None
    gate = None
    server_log = None
    with tempfile.TemporaryDirectory(prefix='brains10-etcd-') as td:
        work = pathlib.Path(td)
        try:
            verify_source(BASE, args.expected_manifest)
            if sha(BASE/'original_gate.zip') != ORIGINAL_SHA:
                raise ValueError('original gate identity mismatch')
            if not args.local_rehearsal:
                if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('PASS230_RUNNER_ENVIRONMENT') != 'github-hosted':
                    raise ValueError('GitHub-hosted context missing')
                for k in ['GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_REPOSITORY_ID']:
                    if not re.fullmatch(r'[1-9][0-9]*', os.environ.get(k,'')):
                        raise ValueError('invalid '+k)
                if not re.fullmatch(r'[0-9a-f]{40}',os.environ.get('GITHUB_SHA','')):
                    raise ValueError('missing commit binding')
            keys = ['GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_SHA','GITHUB_REF',
                    'GITHUB_REPOSITORY','GITHUB_REPOSITORY_ID','GITHUB_WORKFLOW_REF',
                    'GITHUB_WORKFLOW_SHA','GITHUB_EVENT_NAME','RUNNER_OS','RUNNER_ARCH',
                    'PASS230_RUNNER_ENVIRONMENT','ImageOS','ImageVersion']
            write_json(evidence/'CONTEXT.json',{k:os.environ.get(k) for k in keys})
            require(command(['uname','-a'],evidence/'UNAME.txt'),'uname')
            shutil.copy2(BASE/'SOURCE_MANIFEST.json',evidence/'SOURCE_MANIFEST.json')
            shutil.copy2(BASE/'repaired_gate.zip',evidence/'repaired_gate.zip')
            workflow = BASE.parent/'.github/workflows/pass230-etcd-evidence.yml'
            if workflow.is_file():
                shutil.copy2(workflow,evidence/'EXECUTED_WORKFLOW.yml')
            archive = work/'release.tar.gz'
            if args.release_archive:
                if not args.local_rehearsal:
                    raise ValueError('archive override allowed only for labelled local rehearsal')
                shutil.copyfile(args.release_archive,archive)
            else:
                require(command(['curl','--fail','--location','--silent','--show-error',
                                 '--proto','=https','--tlsv1.2','--max-time','120',
                                 '--output',str(archive),ARCHIVE_URL],evidence/'DOWNLOAD.txt',timeout=130),'download')
            if sha(archive) != ARCHIVE_SHA:
                raise ValueError('official release archive digest mismatch')
            bin_dir = work/'bin'; bin_dir.mkdir()
            with tarfile.open(archive,'r:gz') as t:
                for name in ['etcd','etcdctl']:
                    member = t.getmember('etcd-v3.6.5-linux-amd64/'+name)
                    if not member.isfile(): raise ValueError('nonregular release binary')
                    (bin_dir/name).write_bytes(t.extractfile(member).read())
                    (bin_dir/name).chmod(0o700)
            write_json(evidence/'BINARY_IDENTITY.json',{'archive_url':ARCHIVE_URL,'archive_sha256':ARCHIVE_SHA,
                'binary_sha256':{n:sha(bin_dir/n) for n in ['etcd','etcdctl']}})
            require(command([str(bin_dir/'etcd'),'--version'],evidence/'SERVER_VERSION.txt'),'server version')
            require(command([str(bin_dir/'etcdctl'),'version'],evidence/'CLIENT_VERSION.txt'),'client version')
            env = {k:v for k,v in os.environ.items() if not k.startswith(('ETCD_','ETCDCTL_'))}
            env['PATH'] = str(bin_dir)+os.pathsep+os.environ.get('PATH','')
            env['PYTHONDONTWRITEBYTECODE']='1'
            endpoint = 'http://127.0.0.1:2379'
            ns = '/brains10/pass230/'+(work.name if args.local_rehearsal else os.environ['GITHUB_RUN_ID']+'/'+os.environ['GITHUB_RUN_ATTEMPT'])
            write_json(evidence/'CONFIGURATION.json',{'endpoint':endpoint,'namespace':ns,'tls':False,'member_count':1})
            for port in [2379,2380]:
                with socket.socket() as s: s.bind(('127.0.0.1',port))
            argv = [str(bin_dir/'etcd'),'--name','pass230','--data-dir',str(work/'data'),
                    '--listen-client-urls',endpoint,'--advertise-client-urls',endpoint,
                    '--listen-peer-urls','http://127.0.0.1:2380',
                    '--initial-advertise-peer-urls','http://127.0.0.1:2380',
                    '--initial-cluster','pass230=http://127.0.0.1:2380',
                    '--initial-cluster-token',work.name,'--initial-cluster-state','new']
            write_json(evidence/'SERVER_COMMAND.json',argv)
            server_log=(evidence/'SERVER_LOG.txt').open('wb')
            process=subprocess.Popen(argv,stdout=server_log,stderr=subprocess.STDOUT,env=env)
            ctl=[str(bin_dir/'etcdctl'),'--endpoints='+endpoint,'--command-timeout=2s','--dial-timeout=2s']
            ready=False
            for attempt in range(20):
                if process.poll() is not None: raise RuntimeError('own etcd process exited before readiness')
                rc=command(ctl+['endpoint','health'],evidence/f'HEALTH_{attempt:02}.txt',env=env,timeout=4)
                if rc==0:
                    ready=True;break
                time.sleep(0.25)
            if not ready or process.poll() is not None: raise RuntimeError('etcd readiness missing')
            require(command(ctl+['endpoint','status','-w','json'],evidence/'ENDPOINT_BEFORE.json',env=env),'endpoint before')
            gate=work/'gate';gate.mkdir();extract_gate(BASE/'repaired_gate.zip',gate)
            env.update({'ETCDCTL_ENDPOINTS':endpoint,'BRAINS10_ETCD_NAMESPACE':ns})
            require(command([sys.executable,'-B','PREFLIGHT.py'],evidence/'PREFLIGHT.txt',env=env,cwd=gate),'preflight')
            gate_rc=command(['bash','RUN_LIVE_GATE.sh'],evidence/'GATE_WRAPPER.txt',env=env,cwd=gate,timeout=120)
            result['gate_exit_code']=gate_rc
            require(gate_rc,'gate')
            endpoint_env={k:v for k,v in env.items() if not k.startswith('ETCDCTL_')}
            require(command(ctl+['endpoint','status','-w','json'],evidence/'ENDPOINT_AFTER.json',env=endpoint_env),'endpoint after')
            if process.poll() is not None: raise RuntimeError('own etcd process exited during capture')
            result['status']='CAPTURE_COMPLETE_PENDING_ADJUDICATION'
        except Exception as e:
            result['error']=str(e)
        finally:
            if gate and (gate/'PASS230_LIVE_RESULT').is_dir():
                shutil.copytree(gate/'PASS230_LIVE_RESULT',evidence/'PASS230_LIVE_RESULT')
            if process is not None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait();result['cleanup_forced_kill']=True
            if server_log: server_log.close()
            write_json(evidence/'CAPTURE_STATUS.json',result)
            seal(evidence)
    print(json.dumps(result,sort_keys=True))
    return 0 if result['status']=='CAPTURE_COMPLETE_PENDING_ADJUDICATION' else 2

if __name__=='__main__': sys.exit(main())
