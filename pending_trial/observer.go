// Read-only bounded fixture observer; no repair, provider mutation or authority use.
package main

import (
 "bytes"
 "encoding/binary"
 "errors"
 "io"
 "crypto/sha256"
 "encoding/base64"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "path/filepath"
 "github.com/gogo/protobuf/jsonpb"
 "go.etcd.io/etcd/api/v3/etcdserverpb"
 "go.etcd.io/etcd/client/pkg/v3/fileutil"
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
func fileHash(name string) string {
 f,err:=os.Open(name);must(err);defer f.Close();h:=sha256.New();_,err=io.Copy(h,f);must(err);return hex.EncodeToString(h.Sum(nil))
}
// Strict terminal format check, separate from high-level ReadAll history semantics.
func strictTerminal(name string) map[string]interface{} {
 before:=fileHash(name)
 f,err:=os.Open(name);must(err);defer f.Close();info,err:=f.Stat();must(err)
 if info.Size()<=0 || info.Size()>64000000 {panic("bounded initial segment size required")}
 d:=wal.NewDecoder(fileutil.NewFileReader(f));var rec walpb.Record;var offset int64;count:=0
 for {
  err=d.Decode(&rec)
  if errors.Is(err,io.EOF) {break}
  if err!=nil {panic(fmt.Sprintf("strict_terminal_error: %v",err))}
  count++;if count>10000 {panic("record limit")}
  var header [8]byte;_,err=f.ReadAt(header[:],offset);must(err);word:=binary.LittleEndian.Uint64(header[:]);n:=word&((uint64(1)<<56)-1);pad:=(8-n%8)%8
  expected:=n;if pad>0 {expected|=(0x80|pad)<<56}
  if word!=expected || n==0 || n>1000000 || offset+8+int64(n+pad)!=d.LastOffset() {panic("noncanonical_frame_boundary")}
  padding:=make([]byte,int(pad));if pad>0 {_,err=f.ReadAt(padding,offset+8+int64(n));must(err)}
  for _,b:=range padding {if b!=0 {panic("nonzero_padding")}}
  if rec.Type==wal.CrcType {
   crc:=d.LastCRC();if crc!=0 {must(rec.Validate(crc))};d.UpdateCRC(rec.Crc)
  }
  offset=d.LastOffset()
 }
 _,err=f.Seek(offset,io.SeekStart);must(err);buf:=make([]byte,65536);var trailing int64
 for {
  n,readErr:=f.Read(buf);for _,b:=range buf[:n] {if b!=0 {panic("nonzero_tail_after_terminal_eof")}};trailing+=int64(n)
  if errors.Is(readErr,io.EOF) {break};must(readErr)
 }
 if offset+trailing!=info.Size() || count==0 || fileHash(name)!=before {panic("raw_file_changed_or_incomplete")}
 return map[string]interface{}{"condition":"EOF","last_valid_offset":offset,"record_count":count,"file_size":info.Size(),"zero_suffix_bytes":trailing,"file_sha256":before,"canonical_frames_and_padding":true,"unexpected_eof_accepted":false,"completeness_claim":"FORMAT_ONLY; target/history/capture chronology require separate binding"}
}
func main() {
 if len(os.Args)!=2 { panic("expected one snapshot directory") }
 root:=os.Args[1]
 files,err:=filepath.Glob(filepath.Join(root,"member","wal","*.wal"));must(err)
 if len(files)!=1 || filepath.Base(files[0])!="0000000000000000-0000000000000000.wal" {panic("control requires exact initial segment")}
 snaps,err:=filepath.Glob(filepath.Join(root,"member","snap","*.snap"));must(err)
 if len(snaps)!=0 {panic("control does not support Raft snapshots")}
 terminal:=strictTerminal(files[0])
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
 result:=map[string]interface{}{"schema":"WAL_DECODE_V2","scope":"INITIAL_SEGMENT_READ_ONLY_DECODE","terminal":terminal,"node_id":fmt.Sprint(m.NodeID),"cluster_id":fmt.Sprint(m.ClusterID),"term":state.Term,"vote":fmt.Sprint(state.Vote),"commit_index":state.Commit,"metadata_b64":base64.StdEncoding.EncodeToString(metadata),"entries":out}
 enc:=json.NewEncoder(os.Stdout);enc.SetIndent("","  ");must(enc.Encode(result))
}
