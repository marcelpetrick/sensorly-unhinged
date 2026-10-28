# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reviewed USB topology; the inherited aggregate 2mm DRC is NOT changed here.

All coordinates and local limits below are engineering geometry assumptions.
They do not establish 90ohm impedance or USB qualification. TI TUSB320LI
section10.1 p29 supplies the separate <=3.5mm receptacle contact-join bound.
https://www.ti.com/lit/ds/symlink/tusb320li.pdf
Espressif USB guidance requires parallel equal-length routing, continuous
reference, and ground-return pairs at transitions:
https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c6/pcb-layout-design.html#usb
"""
from __future__ import annotations
import math
from . import geometry as G
from .route import Track, Via

WIDTH=.25
GAP=.20
REFERENCE_RECT=(8.0,21.3,13.3,26.2)
SPINES={
 'mcu':[(13.6,16.4),(13.6,17.4),(10.3,17.95),(10.3,18.2)],
 'connector':[(10.3,22.8),(10.3,24.0),(7.4,24.0)],
}
REVIEWED={
 'U1':(14,11.5,0),'J1':(3.19,24.5,270),'U5':(10.3,20.5,90),
 'D1':(18,21,90),'C14':(12.6,21.4,270),
 'TP7':(16.62,22.04,0),'TP8':(19.16,22.04,0),
 'TP10':(11.5,25,0),'TP11':(9.5,22.3,0),
 'TP13':(9,27.12,0),'TP14':(11.54,27.12,0),
}
# Bounds on complete polylines, not independently waived individual segments.
# Input N's dogleg tunes the main nominal copper path to within0.1mm.
LOCAL_LIMITS={
 'input-N':1.75,'input-P':1.0,'output-N':1.0,'output-P':1.0,
 'join-N':3.5,'join-P':3.5,
 'fixture-N-F':.90,'fixture-N-B':1.10,
 'fixture-P-F':1.10,'fixture-P-B':1.10,
}

def length(track):
 return sum(math.dist(a,b) for a,b in zip(track.pts,track.pts[1:]))

def pair(spine,name):
 """Offset both rails from one spine; preserve physical gap through miters."""
 out=[]
 for suffix,sign in [('N',1),('P',-1)]:
  lines=[]
  for (ax,ay),(bx,by) in zip(spine,spine[1:]):
   dx,dy=bx-ax,by-ay;norm=math.hypot(dx,dy)
   if norm<=0:raise ValueError('zero USB spine segment')
   ox,oy=-dy/norm*(WIDTH+GAP)/2*sign,dx/norm*(WIDTH+GAP)/2*sign
   lines.append(((ax+ox,ay+oy),(bx+ox,by+oy)))
  pts=[lines[0][0]]
  for (a,b),(c,d) in zip(lines,lines[1:]):
   dx,dy=b[0]-a[0],b[1]-a[1];ex,ey=d[0]-c[0],d[1]-c[1]
   determinant=dx*ey-dy*ex
   if abs(determinant)<1e-12:raise ValueError('collinear/reversed USB spine corner')
   scale=((c[0]-a[0])*ey-(c[1]-a[1])*ex)/determinant
   pts.append((a[0]+scale*dx,a[1]+scale*dy))
  pts.append(lines[-1][1])
  out.append(Track('USB_D_'+suffix,WIDTH,'F.Cu',pts,'usb:trunk-'+name))
 return out

def route_usb(v,placed):
 by_ref={p.ref:p for p in placed}
 for ref,coords in REVIEWED.items():
  p=by_ref[ref]
  if any(abs(a-b)>1e-7 for a,b in zip((p.x,p.y,p.rot),coords)):
   raise ValueError(f'USB placement changed: {ref}; review routes and fixture')
 tracks=pair(SPINES['mcu'],'mcu')+pair(SPINES['connector'],'connector')
 def add(suffix,points,group,layer='F.Cu'):
  tracks.append(Track('USB_D_'+suffix,WIDTH,layer,points,'usb:'+group))
 add('N',[(10.075,18.2),(9.2,18.2),(9.2,18.8),(9.45,18.8)],'input-N')
 add('P',[(10.525,18.2),(11.15,18.8)],'input-P')
 add('N',[(9.45,22.2),(10.075,22.8)],'output-N')
 add('P',[(11.15,22.2),(10.525,22.8)],'output-P')
 add('N',[(7.4,23.775),(6.175,23.775),(6.175,24.725),(7.4,24.725)],'join-N')
 add('P',[(7.4,24.225),(8.4,24.225),(8.4,25.25),(7.4,25.25)],'join-P')
 add('N',[(10.075,23.0),(9.3,23.0)],'fixture-N-F')
 add('P',[(10.525,24),(11.5,24)],'fixture-P-F')
 add('N',[(9.3,23.0),(9.5,22.3)],'fixture-N-B','B.Cu')
 add('P',[(11.5,24),(11.5,25)],'fixture-P-B','B.Cu')
 vias=[Via('USB_D_N',9.3,23.0),Via('USB_D_P',11.5,24),
       Via('GND',8.5,23.1),Via('GND',11.3,23),Via('GND',12.6,23.3),
       Via('GND',9,20.5),Via('GND',13.6,20.8)]
 tracks += [
  Track('GND',.15,'F.Cu',[(10.3,21.65),(10.3,20.675),(9.175,20.675),(9,20.5)],'plane-neckdown'),
  Track('VBUS',.15,'F.Cu',[(10.3,19.35),(10.3,20.225),(11.9,20.225)],'power-neckdown'),
  Track('VBUS',.4,'F.Cu',[(11.9,20.225),(12.6,20.925),(12.6,20.92)]),
  Track('GND',.4,'F.Cu',[(12.6,21.88),(13.6,21.88),(13.6,20.8)]),
 ]
 validate_usb(tracks,vias,placed)
 return tracks,vias

def validate_usb(tracks,vias,placed):
 """Validate emitted copper, including extra/divergent USB geometry controls."""
 groups={}
 for t in tracks:
  if t.net not in {'USB_D_N','USB_D_P'}:continue
  if abs(t.width-WIDTH)>1e-9:raise ValueError('USB trace width changed')
  if not t.purpose.startswith('usb:'):raise ValueError('unclassified USB copper')
  groups.setdefault(t.purpose[4:],[]).append(t)
 expected=set(LOCAL_LIMITS)|{'trunk-mcu','trunk-connector'}
 if set(groups)!=expected:raise ValueError('missing or extra USB route sections')
 for name,spine in SPINES.items():
  actual=sorted(groups['trunk-'+name],key=lambda t:t.net)
  required=sorted(pair(spine,name),key=lambda t:t.net)
  if len(actual)!=2:raise ValueError('USB trunk needs two rails')
  for a,b in zip(actual,required):
   if a.net!=b.net or a.layer!='F.Cu' or len(a.pts)!=len(b.pts) or any(
      math.dist(x,y)>1e-7 for x,y in zip(a.pts,b.pts)):
    raise ValueError('divergent USB trunk or changed spine/gap')
   if length(a)>5.0:raise ValueError('USB trunk exceeded reviewed length')
 for name,cap in LOCAL_LIMITS.items():
  ts=groups[name]
  if len(ts)!=1 or length(ts[0])>cap+1e-9:raise ValueError('USB breakout exceeds '+name)
  t=ts[0];suffix=name.split('-')[1] if name.startswith('fixture-') else name[-1]
  expected_layer='B.Cu' if name.endswith('-B') else 'F.Cu'
  if t.net!='USB_D_'+suffix or t.layer!=expected_layer:raise ValueError('USB breakout polarity/layer changed')
 # The two complete fixture branches share no main trunk. Include both copper
 # faces, while recording the through barrel separately in the review report.
 for suffix in ('N','P'):
  if sum(length(groups[f'fixture-{suffix}-{layer}'][0]) for layer in ('F','B'))>2.25:
   raise ValueError('USB fixture copper branch exceeds2.25mm')
 usb_vias=[q for q in vias if q.net in {'USB_D_N','USB_D_P'}]
 required={('USB_D_N',9.3,23.0),('USB_D_P',11.5,24)}
 if {(q.net,q.x,q.y) for q in usb_vias}!=required or len(usb_vias)!=2:
  raise ValueError('USB transition count/location changed')
 if any(abs(q.size-.6)>1e-9 or abs(q.drill-.3)>1e-9 for q in usb_vias):
  raise ValueError('USB must use standard0.6/0.3mm vias')
 ground=[q for q in vias if q.net=='GND']
 for q in usb_vias:
  near=sorted(math.hypot(q.x-g.x,q.y-g.y) for g in ground)
  if len(near)<2 or near[1]>2.0:raise ValueError('USB return-via pair missing')
 main={n:0 for n in ('USB_D_N','USB_D_P')}
 for name,ts in groups.items():
  if name.startswith(('trunk-','input-','output-')):
   for t in ts:main[t.net]+=length(t)
 if abs(main['USB_D_N']-main['USB_D_P'])>.1:
  raise ValueError('USB main nominal copper skew exceeds0.1mm')
 # Placement snapshots prevent moving a pad while leaving a branch dangling;
 # actual filled KiCad connectivity/clearance is mandatory independently.
 by_ref={p.ref:p for p in placed}
 for ref,coords in REVIEWED.items():
  p=by_ref[ref]
  if any(abs(a-b)>1e-7 for a,b in zip((p.x,p.y,p.rot),coords)):
   raise ValueError('USB pad placement changed: '+ref)
 # Anchor every breakout to its real pad, via, or constructed trunk.
 def same(a,b):
  if math.dist(a,b)>1e-7:raise ValueError('USB breakout endpoint detached')
 def pad_contains(ref,pin,point):
  p=by_ref[ref];fp=G.get(p.footprint)
  w,h=fp.pad_size[pin]
  if p.rot%180:w,h=h,w
  for q in fp.pads[pin]:
   x,y=G.xform(*q,p.x,p.y,p.rot)
   if abs(point[0]-x)<=w/2+1e-8 and abs(point[1]-y)<=h/2+1e-8:return
  raise ValueError(f'USB endpoint outside real pad {ref}.{pin}')
 def rail(name,suffix):
  return next(t for t in groups['trunk-'+name] if t.net=='USB_D_'+suffix)
 for suffix,mpin,upin in [('N','17','6'),('P','18','4')]:
  a=groups['input-'+suffix][0]
  same(a.pts[0],rail('mcu',suffix).pts[-1])
  pad_contains('U1',mpin,rail('mcu',suffix).pts[0])
  pad_contains('U5',upin,a.pts[-1])
 for suffix,upin in [('N','1'),('P','3')]:
  a=groups['output-'+suffix][0]
  pad_contains('U5',upin,a.pts[0]);same(a.pts[-1],rail('connector',suffix).pts[0])
 for suffix,pins in [('N',('B7','A7')),('P',('A6','B6'))]:
  a=groups['join-'+suffix][0]
  pad_contains('J1',pins[0],a.pts[0]);pad_contains('J1',pins[1],a.pts[-1])
  pad_contains('J1',pins[0],rail('connector',suffix).pts[-1])
 for suffix,ref in [('N','TP11'),('P','TP10')]:
  a=groups['fixture-'+suffix+'-F'][0];b=groups['fixture-'+suffix+'-B'][0]
  trunk=rail('connector',suffix)
  if min(G.distance_to_segment(a.pts[0],u,w) for u,w in zip(trunk.pts,trunk.pts[1:]))>1e-7:
   raise ValueError('fixture spur detached from paired trunk')
  q=next(q for q in usb_vias if q.net=='USB_D_'+suffix)
  same(a.pts[-1],(q.x,q.y));same(b.pts[0],(q.x,q.y))
  same(b.pts[-1],(by_ref[ref].x,by_ref[ref].y));pad_contains(ref,'1',b.pts[-1])
 # The dedicated module replaces the former generic U5 ground helper.
 # Prove actual top-copper connectivity from both supply-return pads to a
 # plated GND via; a source edit deleting either return must fail at emit.
 from collections import defaultdict
 from .design import NETS
 def grounded(ref,pin):
  if (ref,pin) not in NETS['GND']:raise ValueError('USB return anchor is no longer GND')
  p=by_ref[ref];fp=G.get(p.footprint)
  start=tuple(round(x,7) for x in G.xform(*fp.pads[pin][0],p.x,p.y,p.rot))
  selected=[t for t in tracks if t.net=='GND' and t.layer=='F.Cu']
  points={tuple(round(x,7) for x in q) for t in selected for q in t.pts}
  points.add(start)
  destinations={tuple(round(x,7) for x in (q.x,q.y)) for q in vias if q.net=='GND'}
  points.update(destinations);graph=defaultdict(set)
  for t in selected:
   for a,b in zip(t.pts,t.pts[1:]):
    split=sorted((q for q in points if G.distance_to_segment(q,a,b)<1e-7),
      key=lambda q:math.dist(q,a))
    for u,w in zip(split,split[1:]):graph[u].add(w);graph[w].add(u)
  seen={start};todo=[start]
  while todo:
   for q in graph[todo.pop()]-seen:seen.add(q);todo.append(q)
  if not seen&destinations:raise ValueError(f'USB {ref}.{pin} ground return detached')
 grounded('U5','2');grounded('C14','2')
 return groups

def reference_zones(v,netidx):
 from .pcb import _zone
 x0,y0,x1,y1=REFERENCE_RECT
 polygon=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
 return _zone('USB bottom reference GND','GND',netidx,['In2.Cu'],polygon,
    f'usb-bottom-ground/{v.key}',priority=3,solid_pads=True)+_zone(
    'USB reference no inner tracks','',netidx,['In2.Cu'],polygon,
    f'usb-reference-guard/{v.key}',keepout=dict(tracks='not_allowed',vias='allowed',
    pads='allowed',copperpour='allowed',footprints='allowed'))


def trunk_areas(v,netidx,tracks):
 from .pcb import _zone
 out=[]
 for name,spine in SPINES.items():
  for i,((ax,ay),(bx,by)) in enumerate(zip(spine,spine[1:])):
   # Both offset rails fit inside this conservative segment rectangle.
   margin=.7
   polygon=[(min(ax,bx)-margin,min(ay,by)-margin),
     (max(ax,bx)+margin,min(ay,by)-margin),
     (max(ax,bx)+margin,max(ay,by)+margin),
     (min(ax,bx)-margin,max(ay,by)+margin)]
   out.append(_zone(f'USB paired trunk {name} {i}','',netidx,['F.Cu'],polygon,
    f'usb-trunk-guard/{v.key}/{name}/{i}',keepout=dict(tracks='allowed',vias='allowed',pads='allowed',copperpour='allowed',footprints='allowed')))
 # Areas only cover classified local polylines, with a narrow margin.
 # The generator independently rejects any unclassified USB geometry.
 for group,cap in LOCAL_LIMITS.items():
  for track in tracks:
   if track.purpose!='usb:'+group:continue
   for i,((ax,ay),(bx,by)) in enumerate(zip(track.pts,track.pts[1:])):
    margin=.15
    polygon=[(min(ax,bx)-margin,min(ay,by)-margin),(max(ax,bx)+margin,min(ay,by)-margin),
      (max(ax,bx)+margin,max(ay,by)+margin),(min(ax,bx)-margin,max(ay,by)+margin)]
    out.append(_zone(f'USB classified breakout {group} {i}','',netidx,[track.layer],polygon,
     f'usb-local-guard/{v.key}/{group}/{i}',keepout=dict(tracks='allowed',vias='allowed',pads='allowed',copperpour='allowed',footprints='allowed')))
 return ''.join(out)
