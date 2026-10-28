# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import math
import unittest
from tools.boardgen.usbroute import route_usb, validate_usb
from tools.boardgen.place import place
from tools.boardgen.route import Track
from tools.boardgen.variants import VARIANTS

class USBTopologyTests(unittest.TestCase):
    def fixture(self):
        p=place(VARIANTS['a'])
        t,v=route_usb(VARIANTS['a'],p)
        return p,t,v

    def test_both_variants(self):
        for variant in VARIANTS.values():
            p=place(variant)
            t,v=route_usb(variant,p)
            validate_usb(t,v,p)

    def test_divergent_spine_is_rejected(self):
        p,t,v=self.fixture()
        a=next(a for a in t if a.purpose=='usb:trunk-mcu')
        a.pts[1]=(a.pts[1][0]+.2,a.pts[1][1])
        with self.assertRaisesRegex(ValueError,'divergent'):
            validate_usb(t,v,p)

    def test_detached_pad_is_rejected(self):
        p,t,v=self.fixture()
        a=next(a for a in t if a.purpose=='usb:output-N')
        # Rotate the escape without changing its length: only the real-pad
        # anchor guard should fail, rather than a length or skew bound.
        distance=math.dist(a.pts[0],a.pts[-1])
        a.pts[0]=(a.pts[-1][0],a.pts[-1][1]+distance)
        with self.assertRaisesRegex(ValueError,'outside real pad'):
            validate_usb(t,v,p)

    def test_extra_copper_is_rejected(self):
        p,t,v=self.fixture()
        t.append(Track('USB_D_N',.25,'F.Cu',[(10,20),(16,20)]))
        with self.assertRaisesRegex(ValueError,'unclassified'):
            validate_usb(t,v,p)

    def test_return_pair_is_required(self):
        p,t,v=self.fixture()
        v=[q for q in v if q.net!='GND']
        with self.assertRaisesRegex(ValueError,'return-via'):
            validate_usb(t,v,p)

    def test_public_emitter_rejects_long_copper_inside_breakout_area(self):
        from tools.boardgen.pcb import emit
        p,t,v=self.fixture()
        a=next(a for a in t if a.purpose=='usb:input-N')
        # This meander stays inside the classified horizontal escape area,
        # but its complete length exceeds six millimetres. Spatial DRC alone
        # is insufficient; the canonical emitter must reject it independently.
        a.pts=[(10.075 if i%2==0 else 9.2,18.2) for i in range(9)]+[(9.45,18.8)]
        with self.assertRaisesRegex(ValueError,'breakout exceeds input-N'):
            emit(VARIANTS['a'],p,t,v)

    def test_public_emitter_rejects_six_mm_divergent_main_trunk(self):
        from tools.boardgen.pcb import emit
        p,t,v=self.fixture()
        a=next(a for a in t if a.purpose=='usb:trunk-mcu')
        a.pts=[a.pts[0],(a.pts[0][0]+6,a.pts[0][1])]
        with self.assertRaisesRegex(ValueError,'divergent USB trunk'):
            emit(VARIANTS['a'],p,t,v)

    def test_public_emitter_requires_each_usb_supply_ground_return(self):
        from tools.boardgen.pcb import emit
        for anchor in ('U5','C14'):
            p,t,v=self.fixture()
            by_ref={part.ref:part for part in p}
            from tools.boardgen import geometry as G
            part=by_ref[anchor]
            start=G.xform(*G.get(part.footprint).pads['2'][0],part.x,part.y,part.rot)
            t=[a for a in t if not (a.net=='GND' and a.pts[0]==start)]
            with self.subTest(anchor=anchor):
                with self.assertRaisesRegex(ValueError,anchor+r'.2 ground return detached'):
                    emit(VARIANTS['a'],p,t,v)
