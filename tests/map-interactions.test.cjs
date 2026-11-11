/* Regression tests use the real application functions with a small DOM fixture. */
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const regions = JSON.parse(fs.readFileSync(path.join(root, 'data/regions.json'), 'utf8'));
function harness() {
  const handlers = {}, captures = [], releases = [];
  const nodes = new Map();
  const generic = () => ({classList:{add(){},remove(){},toggle(){}}, addEventListener(){},
    setAttribute(){}, append(){}, appendChild(){}, removeAttribute(){}, textContent:''});
  const viewport = {...generic(), replaceChildren(){}, addEventListener(name, fn){handlers[name]=fn},
    getBoundingClientRect(){return {width:1000,height:700,left:0,top:0}},
    setPointerCapture(id){captures.push(id)}, releasePointerCapture(id){releases.push(id)},
    hasPointerCapture(id){return captures.includes(id)&&!releases.includes(id)}};
  nodes.set('#map-viewport', viewport);
  const drawingChildren=[];
  const drawingGroup={...generic(),localName:'g',hasAttribute(){return true},
    transform:{baseVal:{consolidate(){return {matrix:{a:1,b:0,c:0,d:1,e:200,f:640}}}}},
    appendChild(node){drawingChildren.push(node)}};
  const svg = {...generic(),children:[drawingGroup], getAttribute(){return '0 0 12400 12030'},
    getScreenCTM(){return {inverse(){return {}}}},
    createSVGPoint(){return {x:0,y:0,matrixTransform(){return {x:this.x,y:this.y}}}}};
  const context = vm.createContext({console, URLSearchParams, setTimeout,
    location:{hash:''}, fetch:async()=>({ok:true,text:async()=>'<svg/>'}),
    DOMParser:class {parseFromString(){return {querySelector(){return null},documentElement:svg}}},
    document:{querySelector(selector){if(!nodes.has(selector))nodes.set(selector,generic());return nodes.get(selector)},
      querySelectorAll(){return []}, createElementNS(){return generic()}, importNode(){return svg}}});
  const source = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
  assert.match(source, /\nstart\(\);\s*$/);
  vm.runInContext(source.replace(/\nstart\(\);\s*$/, '\n'), context);
  return {context, handlers, captures, releases, drawingChildren};
}
test('all 11 region boxes are consumed as x,y,width,height', () => {
  const h = harness();
  vm.runInContext(`regions=${JSON.stringify(regions)}; focusBounds=(...args)=>globalThis.observed=args;`, h.context);
  for (const region of regions) {
    vm.runInContext(`focusRegion(${JSON.stringify(region.code)},false)`, h.context);
    assert.deepEqual(Array.from(h.context.observed), [...region.bbox, .22], region.code);
  }
});
test('a simple map click is not captured away from a building marker', async () => {
  const h = harness();
  await vm.runInContext('installSVG()', h.context);
  const event = {button:0,pointerType:'mouse',isPrimary:true,pointerId:1,clientX:100,clientY:200};
  h.handlers.pointerdown(event);
  h.handlers.pointerup(event);
  assert.deepEqual(h.captures, []);
  assert.equal(vm.runInContext('suppressClick', h.context), false);
});
test('dragging captures only after the threshold and releases on pointerup', async () => {
  const h = harness();
  await vm.runInContext('installSVG()', h.context);
  const event = {button:0,pointerType:'mouse',isPrimary:true,pointerId:1,clientX:100,clientY:200};
  h.handlers.pointerdown(event);
  h.handlers.pointermove({...event,clientX:102});
  assert.deepEqual(h.captures, []);
  h.handlers.pointermove({...event,clientX:120});
  assert.deepEqual(h.captures, [1]);
  h.handlers.pointerup({...event,clientX:120});
  assert.deepEqual(h.releases, [1]);
  assert.equal(vm.runInContext('suppressClick', h.context), true);
});
test('a secondary pointer does not replace the active drag', async () => {
  const h = harness();
  await vm.runInContext('installSVG()', h.context);
  h.handlers.pointerdown({button:0,pointerType:'touch',isPrimary:true,pointerId:1,clientX:10,clientY:20});
  h.handlers.pointerdown({button:0,pointerType:'touch',isPrimary:false,pointerId:2,clientX:90,clientY:90});
  h.handlers.pointermove({pointerId:2,clientX:150,clientY:150});
  assert.equal(vm.runInContext('drag.id', h.context), 1);
  assert.deepEqual(h.captures, []);
});

test('drawing-to-page translation is shared by camera and marker overlay', async () => {
  const h=harness();
  await vm.runInContext('installSVG()',h.context);
  vm.runInContext(`regions=${JSON.stringify(regions)}; focusBounds=(...args)=>globalThis.observed=args; focusRegion('R07',false);`,h.context);
  const [x,y,w,height]=regions.find(r=>r.code==='R07').bbox;
  assert.deepEqual(Array.from(h.context.observed),[x+200,y+640,w,height,.22]);
  assert.equal(h.drawingChildren.length,1,'markers must be appended inside the transformed drawing group');
});
