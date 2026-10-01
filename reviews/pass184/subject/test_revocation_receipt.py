import unittest
from dataclasses import replace
from revocation_receipt import *
class T(unittest.TestCase):
 def setUp(self):
  self.p=RevocationPolicy("P",7,"DIRECT_COMPLETE_CRL_V1","ISS","crl")
  self.r=RevocationReceipt("P",7,"DIRECT_COMPLETE_CRL_V1","CERT","ISS","CRL","good",100,200,"TIME","E")
 def a(self,r=None,p=None,cert="CERT",time="TIME",iv=(120,130)):return authorize(p or self.p,r or self.r,cert,time,iv)
 def test_ok(self):self.assertEqual(self.a(),"good")
 def test_wrong_time(self):
  with self.assertRaises(Hold):self.a(time="OTHER")
 def test_wrong_leaf(self):
  with self.assertRaises(Hold):self.a(cert="OTHER")
 def test_policy_generation(self):
  with self.assertRaises(Hold):self.a(replace(self.r,policy_generation=8))
 def test_wrong_issuer(self):
  with self.assertRaises(Hold):self.a(replace(self.r,issuer_digest="X"))
 def test_wrong_source_role(self):
  with self.assertRaises(Hold):self.a(p=replace(self.p,revocation_source_id="ocsp"))
 def test_indirect_profile(self):
  with self.assertRaises(Hold):self.a(replace(self.r,profile="INDIRECT_CRL"))
 def test_delta_profile(self):
  with self.assertRaises(Hold):self.a(replace(self.r,profile="DELTA_CRL"))
 def test_unknown(self):
  with self.assertRaises(Hold):self.a(replace(self.r,status="unknown"))
 def test_partial_future(self):
  with self.assertRaises(Hold):self.a(iv=(90,120))
 def test_partial_stale(self):
  with self.assertRaises(Hold):self.a(iv=(190,210))
 def test_missing_object(self):
  with self.assertRaises(Hold):self.a(replace(self.r,object_digest=""))
if __name__=="__main__":unittest.main()
