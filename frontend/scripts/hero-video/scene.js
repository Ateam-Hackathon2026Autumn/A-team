// Original vector-like Canvas art. Time is deterministic so frame 0 and frame 400 match.
const canvas = document.querySelector('canvas');
const c = canvas.getContext('2d', { alpha: false });
const W = 1280, H = 720, TAU = Math.PI * 2;
const C = { green:'#2f6b4f', dark:'#24553e', ivory:'#fafaf6', sage:'#eef2ea', orange:'#f4a261', red:'#9a3220', ink:'#26332b' };
const smooth = x => { x=Math.max(0,Math.min(1,x)); return x*x*(3-2*x); };
const wave = (t, speed=1, phase=0) => Math.sin(TAU*t*speed+phase);
function path(points, close=true){c.beginPath();c.moveTo(...points[0]);for(const p of points.slice(1))c.lineTo(...p);if(close)c.closePath();}
function ellipse(x,y,rx,ry,color){c.fillStyle=color;c.beginPath();c.ellipse(x,y,rx,ry,0,0,TAU);c.fill();}
function line(points,color,width=3){path(points,false);c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.lineJoin='round';c.stroke();}
function poly(points,color){path(points);c.fillStyle=color;c.fill();}
function rr(x,y,w,h,r,color){c.fillStyle=color;c.beginPath();c.roundRect(x,y,w,h,r);c.fill();}
function leaf(x,y,angle,size,color){c.save();c.translate(x,y);c.rotate(angle);c.fillStyle=color;c.beginPath();c.moveTo(0,0);c.bezierCurveTo(size*.23,-size*.55,size*.95,-size*.52,size,0);c.bezierCurveTo(size*.75,size*.52,size*.18,size*.5,0,0);c.fill();c.restore();}
function hill(y,amp,color,phase=0){c.fillStyle=color;c.beginPath();c.moveTo(0,H);c.lineTo(0,y);for(let x=0;x<=W+16;x+=16)c.lineTo(x,y+Math.sin(x/260+phase)*amp+Math.sin(x/95+phase*.4)*amp*.17);c.lineTo(W,H);c.fill();}
function base(t){
  const sky=c.createLinearGradient(0,0,0,H);sky.addColorStop(0,'#537f68');sky.addColorStop(.52,'#779885');sky.addColorStop(1,'#aec3a6');c.fillStyle=sky;c.fillRect(0,0,W,H);
  const sx=975+14*wave(t), sy=155+8*wave(t,1,.3);
  const glow=c.createRadialGradient(sx,sy,20,sx,sy,240);glow.addColorStop(0,'rgba(244,162,97,.27)');glow.addColorStop(1,'rgba(244,162,97,0)');c.fillStyle=glow;c.fillRect(680,0,600,450);
  ellipse(sx,sy,62,62,'#f1c894');ellipse(sx,sy,49,49,'#f6d9ad');
  for(let i=0;i<3;i++){ellipse(690+i*205+13*wave(t,1,i),135+i*27,74,13,'rgba(238,242,234,.17)');ellipse(740+i*205+13*wave(t,1,i),132+i*27,60,10,'rgba(238,242,234,.17)');}
  hill(350,45,'#628b73',.4);hill(433,58,'#477a5d',1.2);hill(538,47,C.green,2.1);
  poly([[0,597],[290,550],[490,575],[760,535],[980,575],[1280,540],[1280,720],[0,720]],'#2b6148');
  for(let i=0;i<9;i++){const x=i*170-70;line([[x,720],[x+190,580+12*Math.sin(i)]],'rgba(207,223,193,.14)',2);}
  // Subtle vignette keeps the headline area quiet under the site's overlay.
  const shade=c.createLinearGradient(0,0,780,0);shade.addColorStop(0,'rgba(26,65,47,.40)');shade.addColorStop(.67,'rgba(35,82,58,.17)');shade.addColorStop(1,'rgba(35,82,58,0)');c.fillStyle=shade;c.fillRect(0,0,W,H);
  for(let i=0;i<7;i++){const x=80+i*135;line([[x,610],[x+3*wave(t,1,i),587]],'rgba(166,199,151,.27)',2);leaf(x,589, -.6,15,'rgba(180,209,162,.25)');}
}
function tomato(x,y,r,t){ellipse(x,y+3,r,r*.9,C.red);ellipse(x-r*.2,y-r*.3,r*.38,r*.22,'rgba(246,197,145,.18)');for(let k=0;k<5;k++)leaf(x,y-r*.76,k*TAU/5,r*.55,C.dark);line([[x,y-r*.8],[x+3,y-r*1.38]],C.dark,3);}
function carrot(x,y,s,t){c.save();c.translate(x,y);c.rotate(.025*wave(t,1,x));poly([[-18*s,0],[17*s,0],[2*s,91*s]],'#df8c4d');line([[-9*s,28*s],[5*s,33*s]],'rgba(154,50,32,.28)',2);line([[-4*s,52*s],[7*s,55*s]],'rgba(154,50,32,.28)',2);for(let k=-1;k<=1;k++)leaf(k*4*s,-3*s,k*.7-Math.PI/2,29*s,'#397452');c.restore();}
function corn(x,y,s,t){c.save();c.translate(x,y);c.rotate(.025*wave(t,1,x));ellipse(0,0,24*s,58*s,'#e2b76e');for(let j=-2;j<=2;j++)for(let i=-4;i<=4;i++)ellipse(j*7*s,i*11*s,2.5*s,3.5*s,'rgba(255,224,152,.52)');leaf(-12*s,28*s,-2.4,76*s,C.dark);leaf(12*s,22*s,-.7,82*s,'#347553');c.restore();}
function grapes(x,y,s,t){line([[x,y-48*s],[x+8*s,y-72*s]],C.dark,4);leaf(x+8*s,y-65*s,-.4,33*s,'#397452');for(let row=0;row<4;row++)for(let col=0;col<4-row;col++)ellipse(x+(col-(3-row)/2)*19*s,y+row*17*s,11*s,12*s,'#626070');}
function produce(t){
  const bob=3*wave(t);
  // Terraced harvest bed, all action concentrated to the right of the copy.
  ellipse(1010,639,300,55,'rgba(19,63,43,.30)');
  poly([[676,593],[895,530],[1260,576],[1280,720],[675,720]],'#356f4e');
  for(let i=0;i<5;i++)line([[650,645+i*30],[940,577+i*20],[1280,620+i*16]],'rgba(169,197,140,.28)',4);
  line([[785,571],[770,481],[745,447]],'#1e573d',8);leaf(765,488,-2.7,66,'#4a8a5b');leaf(785,522,-.4,72,'#538c60');tomato(733,472+bob,41,t);tomato(822,528-bob,31,t);
  carrot(934,473+bob*.4,1.1,t);carrot(1004,499-bob*.5,.8,t);
  corn(1124,468-bob*.4,.9,t);grapes(1205,484+bob*.6,.85,t);
  for(let i=0;i<5;i++)leaf(875+i*80,607+i%2*22,-.8+wave(t,1,i)*.04,36,'#6d9f68');
}
function sea(t){
  c.fillStyle='#709b9a';c.beginPath();c.moveTo(780,451);c.bezierCurveTo(920,419,1080,469,1280,437);c.lineTo(1280,720);c.lineTo(685,720);c.bezierCurveTo(718,617,715,534,780,451);c.closePath();c.fill();
  for(let i=0;i<6;i++){const y=505+i*32;line([[680+i*17,y],[805+i*9,y-2],[1000+i*31,y+3],[1240,y]],'rgba(238,242,234,.30)',3);}
  poly([[700,632],[935,564],[1280,620],[1280,720],[685,720]],'#366f58');
  const bx=940+13*wave(t), by=530+4*wave(t,1,.4);
  ellipse(bx,by+89,158,20,'rgba(35,87,72,.20)');
  poly([[bx-138,by+58],[bx+138,by+58],[bx+100,by+98],[bx-96,by+98]],'#6b5848');
  line([[bx-139,by+58],[bx+136,by+58]],'#d9b885',6);
  line([[bx,by+57],[bx,by-117]],C.dark,6);
  poly([[bx+4,by-110],[bx+4,by+39],[bx+91,by+42]],'#eef2ea');
  poly([[bx-9,by-88],[bx-9,by+18],[bx-72,by+24]],'#dbddc3');
  ellipse(bx-19,by+29,11,11,'#dfae87');rr(bx-31,by+38,24,25,7,C.dark);
  line([[bx-19,by+51],[bx-64,by+64]],C.dark,5);
  for(let i=0;i<4;i++)line([[bx-100+i*63,by+105],[bx-63+i*63,by+105]],'rgba(250,250,246,.35)',2);
  // A shoreline harvest crate connects the sea scene to the later market.
  rr(1160,534,85,67,7,'#ab835a');for(let i=0;i<3;i++)line([[1170,551+i*18],[1236,551+i*18]],'#d7b789',3);
  ellipse(1190,536,14,10,'#a8b9a1');ellipse(1212,536,14,10,'#a8b9a1');
}
function person(x,y,s,coat,t){ellipse(x,y-59*s,13*s,14*s,'#e4bd93');rr(x-17*s,y-44*s,34*s,48*s,10*s,coat);line([[x-7*s,y+1*s],[x-10*s,y+29*s]],C.dark,5*s);line([[x+7*s,y+1*s],[x+13*s,y+29*s]],C.dark,5*s);line([[x-14*s,y-27*s],[x-28*s,y-10*s]],coat,5*s);line([[x+14*s,y-27*s],[x+27*s,y-9*s]],coat,5*s);}
function market(t){
  ellipse(1040,663,305,42,'rgba(21,67,46,.25)');
  rr(845,462,327,170,8,'#e4d9b9');
  poly([[813,464],[881,385],[1138,385],[1205,464]],'#f1e5ca');
  for(let i=0;i<6;i++)poly([[881+i*43,385],[924+i*43,385],[923+i*47,464],[813+i*65,464]],i%2?'#f4a261':'#f1e5ca');
  rr(810,459,394,20,9,'#d3af82');rr(829,566,362,26,6,'#a87555');
  for(let i=0;i<5;i++){rr(844+i*65,588,56,45,4,'#916848');tomato(868+i*65,568,12,t);}
  for(let i=0;i<3;i++)carrot(958+i*24,555,.26,t);
  person(909,516,.75,C.dark,t);person(1114,523,.7,C.green,t);
  person(769+4*wave(t),601,.86,'#8b7359',t);person(1219-3*wave(t),610,.82,'#6e7659',t);
  for(let i=0;i<4;i++){const x=856+i*107;line([[x,382],[x,348]],'#567a57',2);ellipse(x,347,5,5,'#edcf9b');}
  // A hand basket with produce in front of the stall.
  rr(1005,623,77,46,8,'#ae865a');line([[1014,629],[1019,605],[1068,605],[1075,629]],'#bd9870',5);ellipse(1031,620,12,10,C.red);ellipse(1053,619,11,9,C.orange);
}
function windowWeight(t,center){let d=Math.abs(t-center);d=Math.min(d,20-d);return 1-smooth((d-2)/2.7);}
function render(seconds){const t=((seconds%20)+20)%20/20;c.clearRect(0,0,W,H);base(t);const p=windowWeight(seconds,5),s=windowWeight(seconds,10),m=windowWeight(seconds,15);if(p>0){c.save();c.globalAlpha=p;produce(t);c.restore();}if(s>0){c.save();c.globalAlpha=s;sea(t);c.restore();}if(m>0){c.save();c.globalAlpha=m;market(t);c.restore();}}
render(0);window.renderHeroFrame=render;
