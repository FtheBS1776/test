// Read-only bounded fixture observer; no repair, provider mutation or authority use.
package main

import (
 "bytes"
 "crypto/sha256"
 "encoding/base64"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
 "github.com/gogo/protobuf/jsonpb"
 "go.etcd.io/etcd/api/v3/etcdserverpb"
 "go.etcd.io/etcd/server/v3/storage/wal"
 "go.etcd.io/etcd/server/v3/storage/wal/walpb"
 "go.etcd.io/raft/v3/raftpb"
 "go.uber.org/zap"
)

type Entry struct {
 Index uint64 `json:"index"`
 Term uint64 `json:"term"`
 Type string `json:"type"`
 DataB64 string `json:"data_b64"`
 SHA256 string `json:"sha256"`
 Request json.RawMessage `json:"request"`
 RoundtripExact bool `json:"roundtrip_exact"`
}
func must(err error) { if err != nil { panic(err) } }
func main() {
 if len(os.Args)!=2 { panic("expected one snapshot directory") }
 root:=os.Args[1]
 files,err:=filepath.Glob(filepath.Join(root,"member","wal","*.wal"));must(err)
 if len(files)!=1 || filepath.Base(files[0])!="0000000000000000-0000000000000000.wal" {panic("control requires exact initial segment")}
 snaps,err:=filepath.Glob(filepath.Join(root,"member","snap","*.snap"));must(err)
 if len(snaps)!=0 {panic("control does not support Raft snapshots")}
 w,err:=wal.OpenForRead(zap.NewNop(),filepath.Join(root,"member","wal"),walpb.Snapshot{});must(err)
 metadata,state,entries,err:=w.ReadAll();must(err)
 // ReadAll closes read-only descriptors. No repair or write-capable open is used.
 var m etcdserverpb.Metadata;must(m.Unmarshal(metadata))
 if m.NodeID==0 || m.ClusterID==0 || state.Commit==0 || state.Term==0 || len(entries)==0 {panic("missing WAL metadata/state/entries")}
 out:=make([]Entry,0,len(entries)); marshaler:=jsonpb.Marshaler{EmitDefaults:true}
 for _,e:=range entries {
  h:=sha256.Sum256(e.Data)
  v:=Entry{Index:e.Index,Term:e.Term,Type:e.Type.String(),DataB64:base64.StdEncoding.EncodeToString(e.Data),SHA256:hex.EncodeToString(h[:]),Request:json.RawMessage("null")}
  if e.Type==raftpb.EntryNormal && len(e.Data)>0 {
   var req etcdserverpb.InternalRaftRequest;must(req.Unmarshal(e.Data))
   var b bytes.Buffer;must(marshaler.Marshal(&b,&req));v.Request=b.Bytes()
   raw,err:=req.Marshal();must(err);v.RoundtripExact=bytes.Equal(raw,e.Data)
  }
  out=append(out,v)
 }
 result:=map[string]interface{}{"schema":"WAL_CONTROL_V1","scope":"POST_STOP_INITIAL_SEGMENT_COMMITTED_CONTROL","node_id":fmt.Sprint(m.NodeID),"cluster_id":fmt.Sprint(m.ClusterID),"term":state.Term,"vote":fmt.Sprint(state.Vote),"commit_index":state.Commit,"metadata_b64":base64.StdEncoding.EncodeToString(metadata),"entries":out}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ");must(enc.Encode(result))
}
