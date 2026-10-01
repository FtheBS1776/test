import unittest
from revocation_source_selection import *
class T(unittest.TestCase):
 def E(self,s,st="good"):return Evidence(s,st,True,True,s+"D",s+"E")
 def test_single_ocsp_good(self):self.assertEqual(decide(SourcePolicy("P",1,frozenset({"ocsp"}),"SINGLE_REQUIRED"),[self.E("ocsp")],"P",1),"good")
 def test_single_crl_revoked(self):self.assertEqual(decide(SourcePolicy("P",1,frozenset({"crl"}),"SINGLE_REQUIRED"),[self.E("crl","revoked")],"P",1),"revoked")
 def test_primary_ocsp_does_not_fallback(self):
  p=SourcePolicy("P",1,frozenset({"ocsp","crl"}),"PRIMARY_NO_FALLBACK","ocsp")
  with self.assertRaises(Hold):decide(p,[self.E("ocsp","unknown"),self.E("crl","good")],"P",1)
 def test_consensus_conflict_holds(self):
  p=SourcePolicy("P",1,frozenset({"ocsp","crl"}),"ALL_REQUIRED_CONSENSUS")
  with self.assertRaises(Hold):decide(p,[self.E("ocsp","good"),self.E("crl","revoked")],"P",1)
 def test_consensus_good(self):
  p=SourcePolicy("P",1,frozenset({"ocsp","crl"}),"ALL_REQUIRED_CONSENSUS")
  self.assertEqual(decide(p,[self.E("ocsp"),self.E("crl")],"P",1),"good")
 def test_missing_consensus_source(self):
  p=SourcePolicy("P",1,frozenset({"ocsp","crl"}),"ALL_REQUIRED_CONSENSUS")
  with self.assertRaises(Hold):decide(p,[self.E("ocsp")],"P",1)
 def test_backend_error(self):
  p=SourcePolicy("P",1,frozenset({"ocsp"}),"SINGLE_REQUIRED")
  with self.assertRaises(Hold):decide(p,[self.E("ocsp","error")],"P",1)
 def test_stale(self):
  p=SourcePolicy("P",1,frozenset({"ocsp"}),"SINGLE_REQUIRED");e=self.E("ocsp");e=Evidence(e.source,e.status,False,e.authorized,e.object_digest,e.execution_id)
  with self.assertRaises(Hold):decide(p,[e],"P",1)
 def test_policy_generation(self):
  p=SourcePolicy("P",1,frozenset({"ocsp"}),"SINGLE_REQUIRED")
  with self.assertRaises(Hold):decide(p,[self.E("ocsp")],"P",2)
 def test_unsupported_newest_wins(self):
  p=SourcePolicy("P",1,frozenset({"ocsp","crl"}),"NEWEST_WINS")
  with self.assertRaises(Hold):decide(p,[self.E("ocsp"),self.E("crl")],"P",1)
 def test_single_required_rejects_irrelevant_primary(self):
  p=SourcePolicy("P",1,frozenset({"ocsp"}),"SINGLE_REQUIRED","ocsp")
  with self.assertRaises(Hold):decide(p,[self.E("ocsp")],"P",1)
 def test_consensus_rejects_irrelevant_primary(self):
  p=SourcePolicy("P",1,frozenset({"ocsp","crl"}),"ALL_REQUIRED_CONSENSUS","ocsp")
  with self.assertRaises(Hold):decide(p,[self.E("ocsp"),self.E("crl")],"P",1)
if __name__=="__main__":unittest.main()
