"""Synthetic TIFF fixtures only, not real imagery."""
import struct
import unittest
import qc_imagery as q


def fixture(*, west=q.W, epsg=32636, pixel=1, alpha=255, cols=480, compression=1):
    tags=[(256,4,(cols,)),(257,4,(480,)),(258,3,(8,8,8,8)),(259,3,(compression,)),(262,3,(2,)),(273,4,(0,)),(277,3,(4,)),(278,4,(480,)),(279,4,(480*480*4,)),(284,3,(1,)),(338,3,(2,)),(33550,12,(4.,4.,0.)),(33922,12,(0.,0.,0.,west,q.N,0.)),(34735,3,(1,1,0,3,1024,0,1,1,1025,0,1,pixel,3072,0,1,epsg))]
    forms={3:'H',4:'I',12:'d'}; offset=8+2+len(tags)*12+4; ext=bytearray(); entries=[]
    for k,t,v in tags:
        b=struct.pack('<'+str(len(v))+forms[t],*v)
        if len(b)>4:
            val=struct.pack('<I',offset+len(ext));ext.extend(b)
        else:val=b.ljust(4,b'\0')
        entries.append(struct.pack('<HHI',k,t,len(v))+val)
    dataoff=offset+len(ext)
    entries[5]=struct.pack('<HHII',273,4,1,dataoff)
    pixels=bytes((15,60,90,alpha,120,190,75,255))*(480*480//2)
    return b'II'+struct.pack('<HIH',42,8,len(tags))+b''.join(entries)+b'\0'*4+ext+pixels


class QC(unittest.TestCase):
    def test_valid(self):
        r=q.inspect(fixture());self.assertEqual(r['opaque'],230400);self.assertEqual(r['source_acceptance'],'NOT_ESTABLISHED');self.assertEqual(r['grm_alignment'],'NOT_RUN')
    def test_refusals(self):
        for kw,reason in [({'west':q.W+2},'BOUNDS'),({'epsg':32635},'CRS'),({'pixel':2},'PIXEL_IS_AREA'),({'alpha':0},'ALPHA_GAP'),({'cols':481},'DIMENSIONS'),({'compression':5},'RGBA_STRICT_ENCODING')]:
            with self.subTest(kw=kw),self.assertRaisesRegex(ValueError,reason):q.inspect(fixture(**kw))
    def test_truncated(self):
        with self.assertRaisesRegex(ValueError,'STRIP_BYTES'):q.inspect(fixture()[:-1])
    def test_node(self):
        self.assertAlmostEqual(q.grm_sample(0,479)[0],q.W);self.assertAlmostEqual(q.grm_sample(0,479)[1],q.S)
        self.assertAlmostEqual(q.grm_sample(479,0)[0],q.E-4);self.assertAlmostEqual(q.grm_sample(479,0)[1],q.N-4)
        with self.assertRaisesRegex(ValueError,'GRM_INDEX'):q.grm_sample(480,0)

if __name__=='__main__':unittest.main()
