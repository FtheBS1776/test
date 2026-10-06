"""Prepare only SHA-256-pinned official etcd binaries in this experiment directory."""
from pathlib import Path
import hashlib,tarfile,urllib.request
ROOT=Path(__file__).resolve().parent
ARCHIVE_SHA='66bad39ed920f6fc15fd74adcb8bfd38ba9a6412f8c7852d09eb11670e88cac3'
PINS={'etcd':'030b4b2efd1bcc9ab043080c35f7bb68551e962b23efe62e2f2713429bd9e0f2','etcdctl':'18416269c49d0f25624938b0b45d5bd5d3eb980ab92048dc4652c66a4246141e'}
def main():
    root=ROOT/'runtime';root.mkdir(exist_ok=True)
    archive=root/'etcd-v3.6.5-linux-amd64.tar.gz'
    if not archive.exists():
        with urllib.request.urlopen('https://github.com/etcd-io/etcd/releases/download/v3.6.5/etcd-v3.6.5-linux-amd64.tar.gz',timeout=30) as response:
            data=response.read(40000001)
        if len(data)>40000000 or hashlib.sha256(data).hexdigest()!=ARCHIVE_SHA:raise RuntimeError('ARCHIVE_MISMATCH')
        with archive.open('xb') as f:f.write(data)
    if archive.is_symlink() or hashlib.sha256(archive.read_bytes()).hexdigest()!=ARCHIVE_SHA:raise RuntimeError('ARCHIVE_MISMATCH')
    with tarfile.open(archive,'r:gz') as tar:
        for name,pin in PINS.items():
            member=tar.getmember('etcd-v3.6.5-linux-amd64/'+name)
            if not member.isfile():raise RuntimeError('NOT_REGULAR')
            data=tar.extractfile(member).read()
            if hashlib.sha256(data).hexdigest()!=pin:raise RuntimeError('BINARY_MISMATCH')
            target=root/name
            if target.exists():
                if target.is_symlink() or target.read_bytes()!=data:raise RuntimeError('EXISTING_BINARY_MISMATCH')
            else:
                with target.open('xb') as f:f.write(data)
            target.chmod(0o700)
    print('PINNED_RUNTIME_READY')
if __name__=='__main__':main()
